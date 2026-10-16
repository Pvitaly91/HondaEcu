"""M2bn actual, bounded research execution and independent streaming comparison.

The unchanged M2bj emitter supplies the only executable bytes, through an
in-memory pipe. Persisted records are the predeclared byte-free semantic
projection, not a payload. This is not production Bus/exec/runner integration.
"""
from __future__ import annotations

import argparse
from collections import Counter
import copy
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import threading
import time

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
BASE = "b9e580f7cd554dd44676a5829444ece265bb517c"
STREAM = "91ffb46922def91764f5d4da166ef2cfc9834ed0effcc051d3f97246fa147ab1"
CONTRACT = HERE / "synthetic_composite_execution_contract.json"
RESERVE = 4 * 1024**3


def require(condition, label):
    if not condition:
        raise AssertionError(label)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def strict(text):
    def pairs(rows):
        value = {}
        for key, item in rows:
            require(key not in value, "DuplicateJsonKey:" + key)
            value[key] = item
        return value
    return json.loads(text, object_pairs_hook=pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError("NonfiniteJson")))


def identity(path):
    path = Path(path).resolve()
    require(path.is_relative_to(ROOT), "RepositoryRelativeSourceRequired")
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            size += len(block)
            digest.update(block)
    return {"path": path.relative_to(ROOT).as_posix(), "bytes": size,
            "sha256": digest.hexdigest()}


def write_new(path, value):
    with Path(path).open("xb") as destination:
        destination.write(canonical(value) + b"\n")


def disk(stage):
    value = {"stage": stage, "freeBytes": shutil.disk_usage(ROOT).free,
             "totalBytes": shutil.disk_usage(ROOT).total}
    require(value["freeBytes"] >= RESERVE, "LowDiskReserve_NoCleanup:" + stage)
    return value


def semantic_body(source, name, following=None):
    text = source.read_text(encoding="utf-8")
    start = text.index("fn " + name + "(")
    opening = text.index("{", start)
    # The copied source has no braces in string literals in the effect body.
    end = text.index("\nfn " + following + "(", opening) if following else len(text)
    return text[opening:end].strip()


def source_checks():
    import synthetic_composite_execution_oracle as oracle
    contract = strict(CONTRACT.read_text(encoding="utf-8"))
    require(contract["milestone"] == "M2bn" and contract["exactBase"] == BASE,
            "ExactM2bnScopeAndBaseRequired")
    require(contract["compositeSha256"] == STREAM and contract["instructionBudget"] == 16,
            "FrozenCompositeAndBudgetRequired")
    require(contract["projection"]["programByteValuesPersisted"] is False,
            "ByteFreePublicSemanticProjectionRequired")
    require(contract["projection"] == {**oracle.PROJECTION_RULES, "programByteValuesPersisted": False}
            and contract["expectedExecutions"] == 5470,
            "PredeterminedWholeProjectionAndFiniteCorpusRequired")
    bindings = []
    for expected in contract["sourceBindings"]:
        actual = identity(ROOT / expected["path"])
        require(actual == expected, "SourceIdentityMismatch:" + expected["path"])
        bindings.append(actual)
    old = HERE / "rust-synthetic-adapter/src/executor.rs"
    new = HERE / "rust-synthetic-composite/src/effects.rs"
    for name, following in (("execute_one", "relative"), ("relative", None)):
        require(semantic_body(old, name, following) == semantic_body(new, name, following),
                "CopiedSemanticBodyChanged:" + name)
    return contract, bindings


def closed_nodes():
    # Identical public manufacturer/source-bound metadata transformation used
    # by unchanged M2bm compare_component_inventory; never CPU observations.
    import validate_synthetic_rust_adapter_contract as old
    model = strict((HERE / "synthetic_adapter_feasibility_contract.json").read_text())
    kinds = {"PageOffset8": "Page", "EvenPageOffset8": "EvenPage",
             "Immediate8": "Immediate8", "Immediate16": "Immediate16",
             "ProgramTarget16": "Target", "TargetPC16": "Target"}
    result = []
    for node in model["nodes"]:
        operands = []
        for operand in node["typedOperands"]:
            kind, fields = operand["kind"], operand["fields"]
            if kind == "AccumulatorA":
                value = {"kind": "Accumulator"}
            elif kind in ("Register0", "Register1"):
                value = {"kind": "LocalRegister", "value": fields["value"]}
            elif kind in ("PageBit5", "PageBit7"):
                value = {"kind": "PageBit", "value": {"offset": fields["offset"], "bit": fields["bit"]}}
            else:
                value = {"kind": kinds[kind], "value": fields["value"]}
            operands.append(value)
        result.append({"pc": node["syntheticPc"],
                       "node_identity": node["nodeId"] if isinstance(node["nodeId"], str) else f"{node['nodeId']:04X}",
                       "form": node["formId"], "length": node["length"],
                       "architectural_dd": list(map(bool, node["documentedIncomingDD"])),
                       "reachable_dd": list(map(bool, node["plannedIncomingDD"])),
                       "operands": operands, "successors": node["successors"],
                       "primary_pdf_page": node["primaryEvidence"]["pdfPage"],
                       "primary_pattern": old.FORM_IDENTITY[node["formId"]][1],
                       "manual_sha256": "f6e423ac0bd15378754e30c35ed426415ec219e360c68e817ab451df72142271",
                       "source_identity": "M2bjVerifiedSyntheticComposite_20Nodes_51Bytes",
                       "source_sha256": STREAM})
    require(len(result) == 20, "ClosedTwentyNodesRequired")
    return result


def emitted_program():
    import validate_synthetic_composite_contract as frozen
    import synthetic_composite_emitter as emitter
    import synthetic_composite_tests as tests
    models, _, _ = frozen.load_inputs()
    results = [emitter.emit_synthetic_composite(*models, tests.request(dd)) for dd in (0, 1)]
    require(all(isinstance(row, emitter.VerifiedSyntheticComposite) for row in results),
            "UnchangedM2bjEmitterRefused")
    require(results[0].encoded_bytes == results[1].encoded_bytes,
            "DdEmissionBytesDiffer")
    payload = results[0].encoded_bytes
    require(len(payload) == 51 and hashlib.sha256(payload).hexdigest() == STREAM,
            "ActualInMemoryCompositeHashMismatch")
    return {"kind": "program", "base": 4096, "end_exclusive": 4147,
            "source": "M2bjVerifiedSyntheticComposite_20Nodes_51Bytes",
            "provenance": "InventedOnly_NoNativeGenerationOwner",
            "content_digest": STREAM, "nodes": closed_nodes(), "bytes": list(payload)}


def run_command(arguments, directory, label, cwd=ROOT):
    before = disk(label + "-before")
    started = time.monotonic()
    with (directory / (label + ".stdout.log")).open("xb") as stdout, \
            (directory / (label + ".stderr.log")).open("xb") as stderr:
        result = subprocess.run(arguments, cwd=cwd, stdout=stdout, stderr=stderr,
                                check=False, timeout=1800)
    receipt = {"arguments": arguments if isinstance(arguments, str) else list(map(str, arguments)), "exitCode": result.returncode,
               "durationSeconds": time.monotonic() - started,
               "diskBefore": before, "diskAfter": disk(label + "-after"),
               "stdout": identity(directory / (label + ".stdout.log")),
               "stderr": identity(directory / (label + ".stderr.log"))}
    write_new(directory / (label + ".json"), receipt)
    require(result.returncode == 0, "ActualCommandFailed:" + label)
    return receipt


def build_host(directory):
    target = directory / "host"
    target.mkdir()
    driver = target / ("word0196-driver.exe" if os.name == "nt" else "word0196-driver")
    sources = [HERE / "word0196_equivalent.c", HERE / "word0196_host_driver.c"]
    if os.name == "nt":
        vswhere = Path(os.environ["ProgramFiles(x86)"]) / "Microsoft Visual Studio/Installer/vswhere.exe"
        found = subprocess.run([str(vswhere), "-latest", "-products", "*", "-requires",
                                "Microsoft.VisualStudio.Component.VC.Tools.x86.x64", "-property", "installationPath"],
                               capture_output=True, text=True, check=True).stdout.strip()
        require(bool(found), "InstalledMsvcRequired")
        vcvars = Path(found) / "VC/Auxiliary/Build/vcvars64.bat"
        command = 'call "' + str(vcvars) + '" >nul && cl /nologo /std:c11 /W4 /WX /O2 /TC '
        command += ' /Fe"' + str(driver) + '" ' + " ".join('"' + str(p) + '"' for p in sources)
        # cmd.exe does not use the C-runtime argv quoting convention. Passing
        # an argv list would introduce literal backslash-quotes via list2cmdline.
        # This is a fixed host compiler invocation, not filesystem shell surgery.
        arguments = "cmd.exe /d /c " + command
    else:
        arguments = ["cc", "-std=c11", "-Wall", "-Wextra", "-Wpedantic", "-Werror", "-O2",
                     *map(str, sources), "-o", str(driver)]
    run_command(arguments, directory, "c11-driver-build", cwd=target)
    return driver


def freeze_expectations(directory, bindings, contract):
    import synthetic_composite_execution_corpus as corpus
    import synthetic_composite_execution_oracle as oracle
    patterns = oracle.load_instrumentation_patterns(ROOT)
    cases, expectations = hashlib.sha256(), hashlib.sha256()
    count, families, paths, psws = 0, Counter(), Counter(), set()
    for request in corpus.iter_cases():
        cases.update(canonical(request) + b"\n")
        expected = oracle.expected_case(request, patterns)
        expectations.update(canonical(expected) + b"\n")
        families[request["family"]] += 1
        paths[request["path"]] += 1
        psws.add(request["entry"]["psw"])
        count += 1
    require(count == contract["expectedExecutions"] and len(psws) == 2048,
            "FinitePredeclaredCorpusOrPswCoverageMismatch")
    frozen = {"milestone": "M2bn", "classification": "IndependentExpectationsFrozenBeforeCompositeObservation",
              "cases": count, "families": dict(families), "paths": dict(paths),
              "representablePswWords": len(psws), "caseStreamSha256": cases.hexdigest(),
              "expectationStreamSha256": expectations.hexdigest(), "sourceBindings": bindings,
              "projection": contract["projection"], "CPUExecutionsBeforeThisFreeze": 0}
    write_new(directory / "pre-runtime-freeze.json", frozen)
    return frozen


def exchange(process, value):
    process.stdin.write(canonical(value) + b"\n")
    process.stdin.flush()
    line = process.stdout.readline(64 * 1024 * 1024)
    require(line.endswith(b"\n"), "MissingBoundedCompleteRuntimeRecord")
    return strict(line.decode("utf-8"))


def actual_runtime(directory, target, frozen, contract):
    import synthetic_composite_execution_corpus as corpus
    import synthetic_composite_execution_oracle as oracle
    patterns = oracle.load_instrumentation_patterns(ROOT)
    executable = target / "release" / ("m2bn-composite.exe" if os.name == "nt" else "m2bn-composite")
    driver = build_host(directory)
    record_hash = hashlib.sha256()
    record_bytes = 0
    counts, per_path, forms = Counter(), Counter(), set()
    per_family = {}
    sensitivity = []
    before = disk("actual-composite-before")
    with (directory / "runtime.stderr.log").open("xb") as stderr, \
            (directory / "c11.stderr.log").open("xb") as c_stderr, \
            (directory / "canonical.jsonl.gz").open("xb") as compressed:
        runtime = subprocess.Popen([str(executable)], cwd=ROOT, stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, stderr=stderr)
        host = None
        watchdog = threading.Timer(900, runtime.kill)
        watchdog.start()
        try:
            with gzip.GzipFile(filename="", mode="wb", fileobj=compressed, mtime=0) as records:
                def record(value):
                    nonlocal record_bytes
                    raw = canonical(value) + b"\n"
                    record_hash.update(raw)
                    record_bytes += len(raw)
                    records.write(raw)
                ready = exchange(runtime, emitted_program())
                require(ready["kind"] == "program_admitted" and ready["base"] == 4096
                        and ready["end_exclusive"] == 4147 and ready["length"] == 51
                        and ready["nodes"] == 20 and ready["forms"] == 16
                        and ready["actual_content_sha256"] == STREAM
                        and ready["full_bytes_verified_in_memory"] is True
                        and ready["program_byte_values_persisted"] is False
                        and ready["effect_body_identical"] is True,
                        "ExecutableBoundaryMustAdmitRealEmission")
                require(len(ready["source_bindings"]) == 11, "AllActualCompiledSourceBindingsRequired")
                for row in ready["source_bindings"]:
                    source = ROOT / "rust/p28-slice-runner"
                    source = source / row["path"] if row["path"] == "Cargo.toml" else source / "src" / row["path"]
                    current = identity(source)
                    require(row == {**current, "path": row["path"]}, "ActualCompiledSourceIdentityMismatch")
                record(ready)
                template = next(corpus.iter_cases())
                runtime.stdin.write(canonical({"kind": "admission_sweep", "template": template}) + b"\n")
                runtime.stdin.flush()
                accepted = 0
                for word in range(65536):
                    actual = strict(runtime.stdout.readline(1024 * 1024).decode("utf-8"))
                    require(actual["kind"] == "admission" and actual["psw"] == word,
                            "EveryAdmissionCandidateMustBeActuallyObservedInOrder")
                    representable = word & 0x0CC8 == 0x0CC8
                    require(actual["admitted"] == representable, "ActualAdmissionClassificationMismatch")
                    require(actual["instruction_retirements"] == actual["functional_data_writes"] == actual["program_execution_fetches"] == actual["cpu_instances"] == 0,
                            "AdmissionBoundaryMutatedOrExecuted")
                    if not representable:
                        require(actual["error"]["code"] == "NotRepresentableByCurrentCanonicalRustCpu",
                                "IncompatiblePswMustNotBeNormalized")
                    accepted += int(representable)
                    record(actual)
                admission = strict(runtime.stdout.readline().decode("utf-8"))
                require(admission["kind"] == "admission_summary" and accepted == 2048,
                        "ActualExhaustiveAdmissionSummaryRequired")
                record(admission)
                require(admission["representable"] == 2048 and admission["incompatible"] == 63488
                        and admission["low12_representable"] == 128 and admission["low12_incompatible"] == 3968,
                        "ActualPswFullAndLow12DomainsRequired")
                components = exchange(runtime, {"kind": "component_checks", "template": template})
                require(components["kind"] == "component_checks" and components["passed"] is True
                        and components["checks"] and all(row["passed"] is True for row in components["checks"]),
                        "ActualExecutableBoundaryAndAccessNegativesMustPass")
                for check in components["checks"]:
                    error = check["actual_error"]
                    require((error["code"] if type(error) is dict else error) == check["expected_error"],
                            "ActualNegativeRefusalDoesNotMatchExpected")
                negative = components["budget_observation"]
                expected_prefix = oracle.expected_case(template, patterns)
                require(negative["accepted"] is False and negative["cpu_instances"] == 1
                        and negative["retired_instructions"] == negative["instructions"] == 1
                        and negative["error"]["code"] == "InstructionBudgetExhausted"
                        and negative["steps"] == expected_prefix["steps"][:1]
                        and negative["after"] == expected_prefix["steps"][0]["after"]
                        and negative["after_data"] == template["data"]
                        and all(event["operation"] == "Read" for event in negative["data_journal"]),
                        "ActualPartialBudgetFailureMustMatchIndependentFirstLbAndZeroWrites")
                record(components)
                prior_pair = None
                for index, request in enumerate(corpus.iter_cases()):
                    actual = exchange(runtime, request)
                    mismatch = oracle.compare_observation(request, actual, patterns)
                    if mismatch is not None:
                        write_new(directory / "first-mismatch.json", {"request": request, "firstMismatch": mismatch,
                                                                      "actual": actual})
                        raise AssertionError("IndependentCompositeComparatorMismatch")
                    if not request["internal_sf"]:
                        prior_pair = copy.deepcopy(actual)
                    else:
                        left, right = prior_pair, copy.deepcopy(actual)
                        for item in (left, right):
                            item["internal_sf_before"] = item["internal_sf_after"] = False
                            item["case_id"] = "PairedCaseIdentity"
                        require(left == right, "InternalSfWholeArchitecturalAndJournalParityFailed")
                    record(actual)
                    counts["executions"] += 1
                    counts["retirements"] += actual["retired_instructions"]
                    counts["logicalReads"] += sum(e["operation"] == "Read" for e in actual["data_journal"])
                    counts["writes"] += sum(e["operation"] == "Write" for e in actual["data_journal"])
                    counts["sameValueWrites"] += sum(e["operation"] == "Write" and e["same_value"] for e in actual["data_journal"])
                    counts["programEvents"] += len(actual["program_events"])
                    counts["rawDataEvents"] += len(actual["raw_data_journal"])
                    counts["programAttempts"] += len(actual["program_events"])
                    counts["programServiced"] += sum(event["serviced"] for event in actual["program_events"])
                    counts["programRefused"] += sum(not event["serviced"] for event in actual["program_events"])
                    counts["externalProgramAttempts"] += sum(not 4096 <= event["address"] < 4147
                                                              for event in actual["program_events"])
                    per_path[request["path"]] += 1
                    family = per_family.setdefault(request["family"], Counter())
                    family["baseCases"] += int(not request["internal_sf"])
                    family["executions"] += 1
                    family["cpuInstances"] += actual["cpu_instances"]
                    family["retirements"] += actual["retired_instructions"]
                    family["logicalReads"] += sum(event["operation"] == "Read" for event in actual["data_journal"])
                    family["writes"] += sum(event["operation"] == "Write" for event in actual["data_journal"])
                    family["rawDataEvents"] += len(actual["raw_data_journal"])
                    family["programEvents"] += len(actual["program_events"])
                    for step in actual["steps"]:
                        forms.add(step["form"])
                    if request["path"] not in {row["path"] for row in sensitivity} or request["family"] == "same-value-writers":
                        sensitivity.append({"path": request["path"], "result": oracle.sensitivity_checks(request, actual, patterns)})
                    if index % 500 == 0:
                        disk("composite-case-" + str(index))
                        print("M2bn actual composite cases:", index + 1, "/", frozen["cases"], flush=True)
                final = exchange(runtime, {"kind": "finish"})
                require(final["kind"] == "run_summary" and final["cases"] == final["accepted"]
                        == final["cpu_instances"] == frozen["cases"] and final["refused"] == 0
                        and final["retired_instructions"] == counts["retirements"] == 73784
                        and final["admission_sweeps"] == 1 and final["actual_rom_executions"] == 0
                        and final["native_downstream_executions"] == 0
                        and final["production_exec_integrated"] is False and final["firmware_ready"] is False,
                        "ActualCompletedLifecycleSummaryRequired")
                record(final)
                runtime.stdin.close()
                require(runtime.wait(timeout=60) == 0 and runtime.stdout.read() == b"",
                        "ActualRuntimeFailedOrProducedExtraRecords")
                # The unchanged C driver uses ordinary stdio buffering. Feed
                # its entire small input concurrently, while draining output;
                # never wait for a flushed line after only one supplied case.
                host = subprocess.Popen([str(driver)], cwd=ROOT, stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE, stderr=c_stderr)
                writer_errors = []
                def feed_c11():
                    try:
                        for request in corpus.iter_cases():
                            host.stdin.write(oracle.c11_input_line(request).encode("ascii"))
                        host.stdin.close()
                    except Exception as error:
                        writer_errors.append(str(error))
                writer = threading.Thread(target=feed_c11, daemon=True)
                writer.start()
                host_watchdog = threading.Timer(180, host.kill)
                host_watchdog.start()
                try:
                    for request in corpus.iter_cases():
                        c_actual = strict(host.stdout.readline(1024 * 1024).decode("utf-8"))
                        c_mismatch = oracle.compare_c11(request, c_actual)
                        if c_mismatch is not None:
                            write_new(directory / "first-c11-mismatch.json", {"request": request,
                                      "firstMismatch": c_mismatch, "actual": c_actual})
                            raise AssertionError("IndependentC11ComparatorMismatch")
                        record({"kind": "c11_observation", "record": c_actual})
                        counts["c11Comparisons"] += 1
                    writer.join(timeout=30)
                    require(not writer.is_alive() and not writer_errors,
                            "HostC11InputTransportFailed")
                    require(host.wait(timeout=30) == 0 and host.stdout.read() == b"",
                            "ActualHostC11FailedOrProducedExtraRecords")
                finally:
                    host_watchdog.cancel()
        finally:
            watchdog.cancel()
            for process in (runtime, host):
                if process is not None and process.poll() is None:
                    process.kill()
                    process.wait(timeout=60)
    require(counts["executions"] == frozen["cases"] and len(forms) == 16,
            "ActualFiniteCorpusNotCompletelyExecuted")
    require(counts["logicalReads"] == 49112 and counts["writes"] == 19162
            and counts["rawDataEvents"] == 73744 and counts["programRefused"] == 0
            and counts["externalProgramAttempts"] == 0 and counts["c11Comparisons"] == 5470,
            "ActualCompletePathEffectsAndNoPositiveExternalAttemptsRequired")
    return {"counts": dict(counts), "perPathExecutions": dict(per_path), "forms": sorted(forms),
            "actualCoverageFamilies": {name: dict(value) for name, value in per_family.items()},
            "actualCpuInstances": counts["executions"], "admissionCandidates": 65536,
            "negativeComponentCpuInstances": components["component_cpu_instances"],
            "negativeComponentRetirements": components["component_instruction_retirements"],
            "negativeComponentCompositeAttempts": components["component_composite_attempts"],
            "componentChecks": len(components["checks"]),
            "representablePswWords": 2048, "incompatiblePswWords": 63488,
            "sfPairs": counts["executions"] // 2, "sensitivity": sensitivity,
            "canonicalBytes": record_bytes, "canonicalSha256": record_hash.hexdigest(),
            "compressedRecord": identity(directory / "canonical.jsonl.gz"),
            "diskBefore": before, "diskAfter": disk("actual-composite-after"),
            "actualCompositeExecutionObserved": True, "firstMismatch": None}


def validate(args):
    directory = (ROOT / args.output_dir).resolve()
    target = (ROOT / args.target_dir).resolve()
    owned_output = directory.is_relative_to(ROOT / "private/reports/m2bn") or (
        directory.is_relative_to(ROOT / ".tmp") and directory.relative_to(ROOT / ".tmp").parts[0].startswith("m2bn-"))
    require(owned_output and target.is_relative_to(ROOT / ".tmp")
            and target.relative_to(ROOT / ".tmp").parts[0].startswith("m2bn-"),
            "M2bnOwnedRepositoryOutputsRequired")
    require(not directory.exists(), "NeverOverwriteAttemptEvidence")
    directory.mkdir(parents=True)
    contract, bindings = source_checks()
    import synthetic_composite_execution_oracle_tests as reference_tests
    static = reference_tests.static_checks(ROOT)
    require(static["passed"] is True and static["CPUExecutions"] == 0,
            "IndependentPreRuntimeStaticCoverageMustPass")
    write_new(directory / "static-oracle-checks.json", static)
    frozen = freeze_expectations(directory, bindings, contract)
    if args.freeze_only:
        print("M2BN_PRE_RUNTIME_FREEZE_JSON=" + canonical(frozen).decode())
        return
    commands = []
    manifest = HERE / "rust-synthetic-composite/Cargo.toml"
    cargo = ["cargo", "+1.85.1"]
    for label, arguments in (("build", ["build", "--release", "--locked", "--jobs", "1"]),
                             ("tests", ["test", "--release", "--locked", "--jobs", "1"]),
                             ("fmt", ["fmt", "--check"])):
        command = cargo + arguments + ["--manifest-path", str(manifest)]
        if label != "fmt":
            command += ["--target-dir", str(target)]
        commands.append(run_command(command, directory, label))
    test_text = (directory / "tests.stdout.log").read_text(encoding="utf-8")
    test_results = re.findall(r"test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored; (\d+) measured; (\d+) filtered out", test_text)
    require(test_results and all(all(int(n) == 0 for n in row[1:]) for row in test_results),
            "ActualRustTestsMustHaveNoFailuresIgnoredOrFiltered")
    require(sum(int(row[0]) for row in test_results) == 5, "ActualAllFiveNewRustUnitTestsRequired")
    runtime = actual_runtime(directory, target, frozen, contract)
    _, after_bindings = source_checks()
    require(bindings == after_bindings, "SourcesChangedDuringActualExecution")
    summary = {"milestone": "M2bn", "exactBase": BASE, "passed": True, "actualRustTests": sum(int(row[0]) for row in test_results),
               "commands": commands, "preRuntimeFreeze": identity(directory / "pre-runtime-freeze.json"),
               "runtime": runtime, "sourceBindings": bindings, "hostPlatform": sys.platform,
               "ActualSyntheticCompositeExecutionObserved": True,
               "ProductionBusExecIntegrationNotEstablished": True,
               "SFMeaningStorageNotEstablished": True, "TestedPswDomainRestricted": True,
               "actualRomExecutions": 0, "nativeDownstreamExecutions": 0,
               "targetObjects": 0, "targetHEX": 0, "FirmwareBIN": 0, "FirmwareReady": False}
    write_new(directory / "summary.json", summary)
    print("M2BN_EVIDENCE_JSON=" + canonical(summary).decode(), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default=".tmp/m2bn-public-evidence")
    parser.add_argument("--target-dir", default=".tmp/m2bn-cargo-target")
    parser.add_argument("--freeze-only", action="store_true")
    args = parser.parse_args()
    try:
        validate(args)
        return 0
    except Exception as error:
        directory = (ROOT / args.output_dir).resolve()
        if directory.is_relative_to(ROOT) and directory.is_dir() and not (directory / "failure.json").exists():
            write_new(directory / "failure.json", {"passed": False, "diagnostic": str(error),
                                                   "oldEvidenceUnchanged": True, "automaticRetry": False})
        print("M2BN_FAILURE_JSON=" + canonical({"passed": False, "diagnostic": str(error)}).decode(), flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
