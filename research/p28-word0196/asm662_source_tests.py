"""Invented M2ay refusal/security models; no third-party source or execution."""
import copy
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
import validate_asm662_source as policy

counts = {"positive": 0, "negative": 0, "properties": 0, "propertyVectors": 0}


def accept(action):
    result = action()
    counts["positive"] += 1
    return result


def refuse(action):
    try:
        action()
    except (ValueError, TypeError, UnicodeError, json.JSONDecodeError):
        counts["negative"] += 1
        return
    raise AssertionError("Forged or unsafe input was accepted")


def model():
    return {"scope": "InventedPolicyModel", "gates": {
        name: True for name in ["sourcePinned", "rightsApplicable", "rcsIndependentlyValidated",
                               "coherentTree", "generatedSourcesChecked", "dependenciesTrusted",
                               "commandsAudited", "boundsSafe", "pathsSafe", "diagnosticsFatal",
                               "overlapsRejected", "ddChecked", "isolated", "networkAbsent",
                               "privateInputsAbsent", "resourceLimits"]},
        "claims": {"runtimeVerified": False, "buildVerified": False,
                   "firmwareReady": False, "executionPermission": False}}


def smoke():
    output = [0] * 32768
    output[0x140:0x142] = [0x12, 0x34]  # Pure mock bytes, NOT actual ISA expectations.
    return {"scope": "InventedPolicyModel", "exitCode": 0, "diagnostics": "",
            "output": output, "expected": [0x12, 0x34], "regionStart": 0x140, "unusedByte": 0,
            "fileAccesses": ["auditedSyntheticInputRead", "freshSyntheticOutputWrite"],
            "dd": 0, "requiredDd": 0, "expectedIndependent": True,
            "claims": {"actualBuildVerified": False, "actualRuntimeVerified": False,
                       "targetSemanticsVerified": False, "firmwareReady": False}}


def leaves(value, path=()):
    if isinstance(value, dict):
        for key, child in value.items():
            yield from leaves(child, path + (key,))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from leaves(child, path + (index,))
    else:
        yield path, value


def replace(record, path, value):
    result = copy.deepcopy(record)
    node = result
    for key in path[:-1]:
        node = node[key]
    node[path[-1]] = value
    return result


def main():
    demand = policy.demand
    demand(len(sys.argv) <= 2, "At most one research directory")
    directory = Path(sys.argv[1]) if len(sys.argv) == 2 else Path(__file__).parent
    contract = policy.load_contract(directory / "asm662_source_verification.json")
    result = accept(lambda: policy.validate(contract))
    demand(not result["runtimeVerified"] and not result["executionPermission"], "Actual profile promoted")
    accept(lambda: policy.parse_contract((json.dumps(contract, indent=2) + "\n").encode()))
    complete = accept(lambda: policy.classify_preflight_model(model()))
    demand(complete["classification"] == "ModelPreflightSatisfiedNotExecutionPermission"
           and not complete["executionPermission"] and not complete["buildVerified"], "Model became evidence")
    accept(lambda: policy.check_write_model(0, 1, []))
    accept(lambda: policy.check_write_model(32767, 1, [[0, 32767]]))
    accept(lambda: policy.check_write_model(16, 16, [[0, 16], [32, 64]]))
    for op, a, b, wanted in [("+", 1, 2, 3), ("-", 5, 7, -2), ("*", -2, 3, -6),
                            ("/", -7, 3, -2), ("%", -7, 3, -1), ("<<", 1, 30, 1073741824),
                            (">>", 2147483647, 31, 0)]:
        demand(accept(lambda: policy.check_expression_model(op, a, b)) == wanted, "Expression model mismatch")
    accept(lambda: policy.check_smoke_model(smoke()))
    nonzero_filler = smoke()
    nonzero_filler["unusedByte"] = 255
    nonzero_filler["output"] = [255] * 32768
    nonzero_filler["output"][0x140:0x142] = nonzero_filler["expected"]
    accept(lambda: policy.check_smoke_model(nonzero_filler))
    for key in contract:
        bad = copy.deepcopy(contract)
        del bad[key]
        refuse(lambda: policy.validate(bad))
    for path, value in leaves(contract):
        variants = [None, False, True, 0, 1, "ForgedVerified", [], {}]
        for variant in variants:
            if not policy.equal(value, variant):
                refuse(lambda: policy.validate(replace(contract, path, variant)))
                counts["propertyVectors"] += 1
    counts["properties"] += 1
    bad = copy.deepcopy(contract)
    bad["hiddenExecutionPermission"] = True
    refuse(lambda: policy.validate(bad))
    for raw in [b'{"x":1,"x":2}\n', b'{"x":NaN}\n', b'{"x":Infinity}\n',
                b'{}', b'{}\r\n', b'\xef\xbb\xbf{}\n', b'\xff', b'[' + b'0,' * 40000 + b'0]']:
        refuse(lambda: policy.parse_contract(raw))
    for key in model()["gates"]:
        hypothetical = model()
        hypothetical["gates"][key] = False
        blocked = accept(lambda: policy.classify_preflight_model(hypothetical))
        demand(blocked["classification"] == "ModelBlocked" and blocked["blockers"] == [key], "Gate waived")
        for value in [None, 0, "PASS"]:
            refuse(lambda: policy.classify_preflight_model(replace(model(), ("gates", key), value)))
    for key in model()["claims"]:
        refuse(lambda: policy.classify_preflight_model(replace(model(), ("claims", key), True)))
    for field, value in [("scope", "ActualSourceEvidence"), ("gates", {}), ("claims", {})]:
        refuse(lambda: policy.classify_preflight_model(replace(model(), (field,), value)))
    for pc, length, used in [(-1, 1, []), (32768, 1, []), (2147483647, 1, []),
                             (0, -1, []), (0, 0, []), (0, 32769, []), (True, 1, []),
                             (0, True, []), (0, 2, [[1, 3]]), (5, 2, [[0, 6]]),
                             (0, 1, [[-1, 1]]), (0, 1, [[3, 2]]), (0, 1, [[0, 32769]])]:
        refuse(lambda: policy.check_write_model(pc, length, used))
    for op, a, b in [("+", 2147483647, 1), ("-", -2147483648, 1), ("*", 65536, 65536),
                     ("/", 1, 0), ("%", 1, 0), ("/", -2147483648, -1),
                     ("%", -2147483648, -1), ("<<", -1, 1), (">>", -1, 1),
                     ("<<", 1, -1), ("<<", 1, 32), ("<<", 1, 31),
                     ("+", True, 1), ("?", 1, 1)]:
        refuse(lambda: policy.check_expression_model(op, a, b))
    changes = [("exitCode", 1), ("exitCode", True), ("diagnostics", "warning: unresolved symbol"),
               ("diagnostics", "error: out of range"), ("diagnostics", None),
               ("scope", "ActualAssemblerOutput"), ("output", [0] * 32767), ("unusedByte", True),
               ("unusedByte", 256), ("unusedByte", 255),
               ("expected", [0x34, 0x12]), ("expected", []), ("expected", [True]),
               ("regionStart", -1), ("regionStart", 32767), ("dd", 1), ("dd", False),
               ("requiredDd", False), ("expectedIndependent", False),
               ("fileAccesses", ["preload:../../private/secret", "freshSyntheticOutputWrite"]),
               ("fileAccesses", ["absoluteUserPathRead", "freshSyntheticOutputWrite"]),
               ("fileAccesses", []), ("claims", {})]
    for field, value in changes:
        refuse(lambda: policy.check_smoke_model(replace(smoke(), (field,), value)))
    for path, value in [(("output", 0), 1), (("output", 0x140), 0),
                        (("output", 0x140), 256), (("output", 0x140), True)]:
        refuse(lambda: policy.check_smoke_model(replace(smoke(), path, value)))
    for key in smoke()["claims"]:
        refuse(lambda: policy.check_smoke_model(replace(smoke(), ("claims", key), True)))
    # Exhaustive representable starting positions at two widths, with no side effects.
    for pc in range(32768):
        for width in [1, 2]:
            if width <= 32768 - pc:
                checked = policy.check_write_model(pc, width, [])
                demand(checked["end"] == pc + width and not checked["executionPermission"], "Write gate mismatch")
            else:
                refuse(lambda: policy.check_write_model(pc, width, []))
            counts["propertyVectors"] += 1
    counts["properties"] += 1
    for mask in range(65536):
        sample = model()
        for i, key in enumerate(sample["gates"]):
            sample["gates"][key] = bool(mask & (1 << i))
        checked = policy.classify_preflight_model(sample)
        demand(len(checked["blockers"]) == 16 - mask.bit_count()
               and not checked["runtimeVerified"] and not checked["executionPermission"], "Gate algebra promoted model")
        counts["propertyVectors"] += 1
    counts["properties"] += 1
    print(json.dumps(dict(milestone="M2ay", passed=True, **counts, actualAsm662Executions=0,
                         actualBuilds=0, syntheticAssemblerOutputs=0, firmwareBin=0), sort_keys=True))


if __name__ == "__main__":
    main()
