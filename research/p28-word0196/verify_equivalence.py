"""Compiled C versus the original unchanged C# oracle; invented inputs only.

The optional native comparison reads only sealed offline snapshots. It never
executes a ROM, creates a native machine, or turns imported owner IDs into proof.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path


def demand(condition, message):
    if not condition:
        raise AssertionError(message)


def digest(path):
    checksum = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            checksum.update(block)
    return checksum.hexdigest()


def first_difference(expected, actual, path="result"):
    if type(expected) is not type(actual):
        return f"{path}: type {type(expected).__name__} != {type(actual).__name__}"
    if isinstance(expected, dict):
        if set(expected) != set(actual):
            return f"{path}: keys {sorted(expected)} != {sorted(actual)}"
        for key in expected:
            difference = first_difference(expected[key], actual[key], f"{path}.{key}")
            if difference:
                return difference
    elif isinstance(expected, list):
        if len(expected) != len(actual):
            return f"{path}: length {len(expected)} != {len(actual)}"
        for index, (left, right) in enumerate(zip(expected, actual)):
            difference = first_difference(left, right, f"{path}[{index}]")
            if difference:
                return difference
    elif expected != actual:
        return f"{path}: {expected!r} != {actual!r}"
    return None


def invented_line(identifier, byte, flags, gates, word):
    # Every number is deliberately invented, not an OEM boundary fixture.
    local = [(byte * 37 + i * 29 + gates * 11) & 255 for i in range(8)]
    ram = [byte ^ 0xB3, (0xD2 & ~32) | (32 if gates & 2 else 0), 0x6D,
           (0x36 & ~128) | (128 if gates & 1 else 0), byte, byte ^ 0xCB,
           word & 255, word >> 8]
    values = [((byte ^ 0xA7) << 8) | 0x35, 0x0DCA | (flags << 12),
              0x556F, 0x21, 0x8123, 0xBEEF, 0x2A42, 0x180, 0x7FE,
              flags & 1, 0, 23, word, *local, *ram]
    demand(len(values) == 29, "Invented driver field count")
    return "\t".join([identifier, *(str(value) for value in values)]) + "\n"


def make_invented(path):
    count = 0
    with path.open("x", encoding="ascii", newline="\n") as stream:
        for byte in range(256):
            for flags in range(16):
                for gates in range(4):
                    word = (0, 0xBF, 0xC0, 0xC1, 0xFFFF)[(byte + flags + gates) % 5]
                    stream.write(invented_line(f"cartesian-{count}", byte, flags, gates, word))
                    count += 1
        for word in range(65536):
            stream.write(invented_line(f"word-{word}", word & 255, (word >> 4) & 15, word & 3, word))
            count += 1
    demand(count == 81920, "Natural invented count changed unexpectedly")
    return count


def run_driver(command, inputs, output):
    demand(not output.exists(), f"Refuse output overwrite: {output}")
    with inputs.open("rb") as source, output.open("xb") as destination:
        result = subprocess.run(command, stdin=source, stdout=destination,
                                stderr=subprocess.PIPE, check=False)
    demand(result.returncode == 0, f"Driver exit{result.returncode}: {result.stderr.decode(errors='replace')}")
    return {"command": [str(value) for value in command], "exitCode": result.returncode,
            "outputSha256": digest(output), "outputBytes": output.stat().st_size}


def compare_oracle(c_file, oracle_file, count):
    compared = steps = writes = 0
    paths, domains = {}, {"below": 0, "equal": 0, "above": 0}
    with c_file.open(encoding="utf-8") as c_stream, oracle_file.open(encoding="utf-8") as oracle_stream:
        while True:
            c_line, oracle_line = c_stream.readline(), oracle_stream.readline()
            if not c_line or not oracle_line:
                demand(c_line == oracle_line == "", "Differential row completeness")
                break
            actual, expected = json.loads(c_line), json.loads(oracle_line)
            difference = first_difference(expected, actual)
            demand(difference is None, f"First C/oracle mismatch row{compared}: {difference}")
            compared += 1
            steps += len(actual["steps"])
            writes += len(actual["writes"])
            path = "/".join(f"{step['pc']:04X}" for step in actual["steps"])
            paths[path] = paths.get(path, 0) + 1
            value = actual["compare"]["left"]
            domains["below" if value < 192 else "equal" if value == 192 else "above"] += 1
    demand(compared == count and len(paths) == 4, "Differential domain/path completeness")
    return {"inventedCompared": compared, "perPcSnapshots": steps, "orderedWrites": writes,
            "cfgPaths": paths, "wordDomains": domains, "mismatches": 0}


def compare_native(c_file, native_rows):
    evidence = json.loads(native_rows.read_text(encoding="utf-8-sig"))
    demand(evidence["newActualRomExecutions"] == 0 and evidence["nativeInputsCreated"] == 0,
           "Native source is not an offline export")
    observed_fields = ("pc", "psw", "lrb", "x1", "x2", "dp", "usp", "ssp", "registers")
    ram_keys = {"0117": "ram0117", "0124": "ram0124", "0128": "ram0128",
                "012A": "ram012A", "018E": "ram018E", "018F": "ram018F",
                "0196": "ram0196Lo", "0197": "ram0196Hi"}
    count = snapshots = writes = original = child = 0
    with c_file.open(encoding="utf-8") as stream:
        for row in evidence["rows"]:
            actual = json.loads(stream.readline())
            demand(actual["id"] == row["id"], "Cross-machine/event replay substitution")
            for boundary in ("entry", "final"):
                expected_cpu, actual_cpu = row[boundary], actual[boundary]
                for field in observed_fields:
                    demand(actual_cpu[field] == expected_cpu[field], f"Native{row['id']}/{boundary}/{field}")
                demand(actual_cpu["a"] == expected_cpu["accumulator"], "Native accumulator mismatch")
                demand(bool(actual_cpu["psw"] & 0x1000) == expected_cpu["dd"], "Native DD mismatch")
                demand(actual_cpu["psw"] & 7 == expected_cpu["scbDerivedFromPsw"], "Native derived SCB mismatch")
                for address, name in ram_keys.items():
                    demand(actual_cpu[name] == row[boundary + "Ram"][address], "Native relevant RAM mismatch")
            for field in ("steps", "accesses", "branchTaken", "stopPc"):
                demand(first_difference(row[field], actual[field]) is None, f"Native {row['id']} {field}")
            demand(actual["compare"] == {key: row["compare"][key] for key in ("left", "right", "cf", "zf")},
                   "Native comparison operands/flags mismatch")
            expected_writes = [{key: write[key] for key in
                                ("pc", "address", "width", "oldValue", "newValue", "eventIndex", "writeOrdinal")}
                               for write in row["writes"]]
            demand(first_difference(expected_writes, actual["writes"]) is None, "Native ordered generation annotation mismatch")
            count += 1
            snapshots += len(actual["steps"])
            writes += len(actual["writes"])
            original += row["image"] == "A"
            child += row["image"] == "B"
        demand(stream.readline() == "", "Unexpected native replay row")
    return {"historicalRowsCompared": count, "originalACompared": original, "historicalBCompared": child,
            "perPcSnapshots": snapshots, "orderedWrites": writes, "incompleteNotCompared": len(evidence["incompleteCases"]),
            "unavailableOriginalFields": evidence["unavailableOriginalFields"], "mismatches": 0,
            "newActualRomExecutions": 0}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--driver", type=Path, required=True)
    parser.add_argument("--oracle", type=Path, required=True)
    parser.add_argument("--core", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--native-input", type=Path)
    parser.add_argument("--native-rows", type=Path)
    arguments = parser.parse_args()
    output = arguments.output.resolve()
    demand(not output.exists(), "Refuse overwrite equivalence receipt")
    output.parent.mkdir(parents=True, exist_ok=True)
    stem = output.stem
    invented = output.parent / f"{stem}-invented.tsv"
    c_rows, oracle_rows = (output.parent / f"{stem}-{kind}.jsonl" for kind in ("c", "oracle"))
    count = make_invented(invented)
    commands = [run_driver([str(arguments.driver.resolve())], invented, c_rows),
                run_driver(["dotnet", str(arguments.oracle.resolve()), str(arguments.core.resolve())], invented, oracle_rows)]
    result = {"milestone": "M2av", "passed": True, "classification": "CompiledCToOriginalUnchangedCSharpOracle",
              "actualRomExecutions": 0, "invented": compare_oracle(c_rows, oracle_rows, count), "commands": commands,
              "native": None, "inputsSha256": digest(invented), "cBinarySha256": digest(arguments.driver),
              "oracleBinarySha256": digest(arguments.oracle), "coreBinarySha256": digest(arguments.core)}
    demand(bool(arguments.native_input) == bool(arguments.native_rows), "Both native offline paths are required together")
    if arguments.native_input:
        native_c = output.parent / f"{stem}-native-c.jsonl"
        result["nativeCommand"] = run_driver([str(arguments.driver.resolve())], arguments.native_input, native_c)
        result["native"] = compare_native(native_c, arguments.native_rows)
        result["nativeInputSha256"] = digest(arguments.native_input)
        result["nativeRowsSha256"] = digest(arguments.native_rows)
    with output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print(json.dumps({key: result[key] for key in ("milestone", "passed", "invented", "native")}, sort_keys=True))


if __name__ == "__main__":
    main()
