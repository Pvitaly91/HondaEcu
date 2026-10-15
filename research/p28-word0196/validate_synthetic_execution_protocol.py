"""Fixed-source M2bk static protocol gate. Never constructs or executes machine code.

Filesystem access belongs only to this trusted, fixed-path validator. The separate
analyzer/reference APIs have no filesystem, process, emulator or codec dependency.
Source guards are defense in depth for reviewed source, not a Python sandbox.
"""
import ast
import hashlib
import json
import re
import sys
from pathlib import Path


BASE_SHA = "be7ed4a72dc5f8758bfa4293db0f881ba9bb7536"
STREAM_SHA = "91ffb46922def91764f5d4da166ef2cfc9834ed0effcc051d3f97246fa147ab1"
CONTRACT_SHA = "f89226773936ee999f6038a91ab74cf1d17ed699120c6d6a75b17ff851214cb9"
CANONICAL_CONTRACT_SHA = "83bbc32a3c150c3466ff5160890d9046cdc9a69f94438cfc1078df079af81fcd"
NEW_SOURCE_SHA = {
    "synthetic_execution_protocol_analysis.py": "9749063c69fdb9252213933f805541863dfa933cccd95d47f7154b9020cd86a3",
    "synthetic_execution_protocol_oracle.py": "6448541d61e1bdfad9578c73f34260f45271dfb2df0247cfe2fc9072f8e9c4ba",
    "synthetic_execution_protocol_tests.py": "d0802f79e5cd33a81ee30bccd7189faf0b37d48a915b11f81c9b40ef54625c45",
}
GAPS = [
    "SyntheticProgramMappingCapabilityNotEstablished",
    "Exact16FormIsolatedAdmissionNotEstablished",
    "ClosedSyntheticEntrySnapshotCapabilityNotEstablished",
    "IndependentDataReadWritePermissionsNotEstablished",
    "OrderedInstructionFetchObservationNotEstablished",
    "PswSnapshotRoundTripCapabilityNotEstablished",
]


def require(value, label):
    if not value:
        raise ValueError(label)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def closed_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "DuplicateJsonKey")
        result[key] = value
    return result


def fixed_json(path):
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=closed_object)


def assert_pure_source(source):
    """Parse only. Malicious source fixtures are never imported or evaluated."""
    tree = ast.parse(source)
    allowed = {"json", "hashlib", "copy", "ast"}
    forbidden_calls = {"eval", "exec", "compile", "__import__", "open", "input",
                       "breakpoint", "help", "globals", "locals", "vars", "setattr", "delattr"}
    forbidden_attrs = {"open", "read_text", "read_bytes", "write_text", "write_bytes",
                       "system", "popen", "Popen", "run", "connect", "execute",
                       "from_bytes", "to_bytes", "encode_instruction", "decode_instruction",
                       "emit_synthetic_composite"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            require(all(item.name in allowed for item in node.names), "PureImportBoundary")
        if isinstance(node, ast.ImportFrom):
            require(node.level == 0 and node.module in allowed, "PureImportBoundary")
        if isinstance(node, ast.Constant):
            require(type(node.value) is not bytes, "NoTargetPayloadLiteral")
        if isinstance(node, ast.Attribute):
            require(node.attr not in forbidden_attrs and not node.attr.startswith("__"),
                    "PureAttributeBoundary")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            require(node.func.id not in forbidden_calls, "PureCallBoundary")
            if node.func.id == "getattr":
                require(len(node.args) >= 2 and isinstance(node.args[1], ast.Constant)
                        and node.args[1].value in {"id", "attr", "name", "module", "code",
                                                   "location", "stage"}, "ReflectionBoundary")
    return len(tuple(ast.walk(tree)))


def source_guard_controls():
    fixtures = ("import subprocess", "from ctypes import CDLL", "import socket",
                "open('unopened')", "eval('1')", "exec('x=1')", "__import__('os')",
                "input()", "help()", "breakpoint()", "x.__class__", "x.write_bytes(x)",
                "x.to_bytes(1)", "getattr(x, '__subclasses__')", "x.emit_synthetic_composite()")
    refused = 0
    for fixture in fixtures:
        try:
            assert_pure_source(fixture)
        except ValueError:
            refused += 1
        else:
            raise ValueError("ParseOnlySourceFixtureAccepted")
    require(assert_pure_source("import json\ndef f(x):\n    return json.dumps(x)\n") > 0,
            "ValidSourceControl")
    return {"parseOnlyRefusals": refused, "validControls": 1, "executedAttackFixtures": 0,
            "scope": "TrustedSourceDefenseInDepth_NotArbitraryPythonSandbox"}


def source_capability_audit(repo, contract):
    """Read and compare frozen Rust source facts; never import/compile/run Rust."""
    def text(name):
        return (repo / "rust/p28-slice-runner/src" / name).read_text(encoding="utf-8")
    bus, cpu, runner, protocol = (text(name) for name in ("bus.rs", "cpu.rs", "runner.rs", "protocol.rs"))
    require("rom: Vec<u8>" in bus and "ram: [u8; RAM_SIZE]" in bus, "SeparateMemorySource")
    require("self.rom.get(address).copied()" in bus
            and "self.rom.get(address as usize)" in bus, "AbsoluteZeroBasedProgramSource")
    image = re.search(r"pub struct Image\s*\{([^}]+)\}", protocol)
    require(image is not None and "pub rom: Vec<u8>" in image.group(1)
            and "base" not in image.group(1), "NoSegmentBaseInImage")
    require(runner.index("if contract.exit_pcs.contains(&cpu.pc)")
            < runner.index("if result.steps >= contract.instruction_budget")
            < runner.index("let decoded = decode(cpu.dd"), "StopBeforeDecodeSourceOrder")
    require("pub fn fetch_code_u8" in bus and "pub fn read_code_u8" in bus
            and "pub fn program_reads_within" in bus, "FetchVsProgramDataSeparateApis")
    fetch_body = bus.split("pub fn fetch_code_u8", 1)[1].split("pub fn read_code_u8", 1)[0]
    require("program_reads" not in fetch_body, "NoOrderedInstructionFetchJournalSource")
    require("const PSW_READS_ONE: u16 = 0x0CC8;" in cpu
            and "(self.psw_other & Self::PSW_STORAGE) | Self::PSW_READS_ONE" in cpu
            and "self.psw_other = val & Self::PSW_STORAGE;" in cpu, "PswNormalizationSource")
    require(contract["capabilityAudit"]["gaps"] == GAPS
            and contract["capabilityAudit"]["futureExecution"] == "Blocked", "GapClassification")
    facts = []
    for row in contract["capabilityAudit"]["sourceEvidence"]:
        path = repo / row["path"]
        facts.append({"file": row["path"], "sourceSha256": digest(path.read_bytes()),
                      "reviewedLines": row["lines"], "fact": row["fact"]})
    return {"classification": "ExistingEmulatorCapabilityAudit", "evidence": "SourceInspectionOnly",
            "gaps": GAPS, "facts": facts, "mapping": "AbsoluteZeroBasedRomVector_NoSegmentBase",
            "stopPrimitive": "ExitPcBeforeDecode_SourceOnly_NotNewStreamProof",
            "pswRoundTrip": {"storageMask": 823, "readsOneMask": 3272,
                             "compatibleSubset": "(OtherPSW&0x0CC8)==0x0CC8",
                             "referenceDomainNarrowedToFitCpu": False},
            "futureExecution": "Blocked", "actualSyntheticExecution": "NotRun",
            "CPUExecutions": 0, "productionChanges": 0}


def extended_context_equivalence(ir, composition, contract):
    """A separate448-case domain covers HC1 and all8 SCB selectors as well.

    This overlaps the smaller independently authored test matrix; counts are
    reported per domain, not added as independent instruction-semantic proofs.
    Every record remains an expected reference calculation, never a CPU trace.
    """
    from synthetic_execution_protocol_analysis import analyze_protocol, validate_expected_trace
    from synthetic_execution_protocol_oracle import make_scenario, reference_case
    aggregate = hashlib.sha256()
    cases, paths, scbs, hc_values = 0, set(), set(), set()
    for word in (0, 191, 192, 193, 255, 256, 65535):
        for gate_a, gate_b in ((0, 0), (128, 0), (0, 32), (129, 33)):
            for dd in (0, 1):
                for variant in range(8):
                    scenario = make_scenario(word, gate_a, gate_b, dd, variant)
                    original = canonical(scenario)
                    expected = reference_case(scenario)
                    actual = analyze_protocol(ir, composition, contract, scenario)
                    require(actual == expected, "ExtendedWholeExpectedCaseMismatch")
                    require(validate_expected_trace(ir, composition, contract, scenario, expected)
                            == expected, "ExtendedTraceAcceptance")
                    require(canonical(scenario) == original, "ExtendedInputImmutability")
                    aggregate.update(canonical(expected))
                    paths.add(expected["path"])
                    scbs.add(scenario["entry"]["scb"])
                    hc_values.add(scenario["entry"]["hc"])
                    cases += 1
    require(cases == 448 and scbs == set(range(8)) and hc_values == {0, 1}
            and paths == {"A", "B", "C", "D"}, "ExtendedContextCoverage")
    require(aggregate.hexdigest()
            == "e7af22151891ab435349b3bc7fdcdae21af98b4da86de866c0f98fdcc066d435",
            "ExtendedImmutableReferenceDigest")
    return {"classification": "ExtendedStaticReferenceComparison_NoExecutionObservation",
            "cases": cases, "exactWholeCaseEquality": cases, "scb": sorted(scbs),
            "hc": sorted(hc_values), "paths": sorted(paths),
            "referenceCasesSha256": aggregate.hexdigest(), "failed": 0, "skipped": 0,
            "countsOverlapIndependentMatrix_NotSummedAsUniqueIsaProof": True}


def validate():
    directory = Path(__file__).resolve().parent
    repo = directory.parents[1]
    contract_path = directory / "synthetic_execution_protocol_contract.json"
    require(digest(contract_path.read_bytes()) == CONTRACT_SHA, "ProtocolSourceIdentity")
    contract = fixed_json(contract_path)
    require(digest(canonical(contract)) == CANONICAL_CONTRACT_SHA
            and contract["exactBase"] == BASE_SHA
            and contract["program"]["sha256"] == STREAM_SHA, "ProtocolIdentity")
    bindings = []
    seen = set()
    require(len(contract["sourceBindings"]) == 147, "FullSourceInventory")
    for row in contract["sourceBindings"]:
        require(type(row) is dict and set(row) == {"path", "bytes", "sha256"}, "BindingShape")
        name = row["path"]
        require(type(name) is str and name not in seen and not name.startswith(("/", "\\"))
                and ".." not in name.split("/") and ":" not in name, "BindingPath")
        seen.add(name)
        path = (repo / name).resolve()
        require(path.is_relative_to(repo), "BindingOutsideRepository")
        data = path.read_bytes()
        require(len(data) == row["bytes"] and digest(data) == row["sha256"], "UpstreamSourceIdentity")
        bindings.append(row)
    pure_nodes = {}
    new_bindings = []
    for name, expected in NEW_SOURCE_SHA.items():
        data = (directory / name).read_bytes()
        require(digest(data) == expected, "NewResearchSourceIdentity_" + name)
        if name != "synthetic_execution_protocol_tests.py":
            pure_nodes[name] = assert_pure_source(data.decode("utf-8"))
        new_bindings.append({"file": name, "bytes": len(data), "sha256": digest(data)})
    policy_controls = source_guard_controls()
    audit = source_capability_audit(repo, contract)
    # Only trusted, source-bound reviewed modules are imported after all guards.
    from synthetic_execution_protocol_oracle import self_check
    from synthetic_execution_protocol_tests import run_tests
    ir = fixed_json(directory / "word0196_ir.json")
    composition = fixed_json(directory / "synthetic_composite_contract.json")
    independent = self_check()
    require(independent["passed"] and independent["cases"] == 448
            and independent["expectedCasesSha256"]
            == "e7af22151891ab435349b3bc7fdcdae21af98b4da86de866c0f98fdcc066d435",
            "IndependentReferenceSelfCheck")
    tests = run_tests(ir, composition, contract)
    require(tests["passed"] and tests["failed"] == 0 and tests["skipped"] == 0
            and tests["wholeExpectedCaseEquality"] == 224, "IndependentProtocolSuite")
    extended = extended_context_equivalence(ir, composition, contract)
    new_bindings.append({"file": contract_path.name, "bytes": contract_path.stat().st_size,
                         "sha256": CONTRACT_SHA})
    new_bindings.append({"file": Path(__file__).name, "bytes": Path(__file__).stat().st_size,
                         "sha256": digest(Path(__file__).read_bytes())})
    return {"milestone": "M2bk", "status": "M2bk Bounded Synthetic Execution Protocol Established",
            "classification": "ObservedStaticChecks_ExecutionObservationsNotRun", "passed": True,
            "failed": 0, "skipped": 0, "firstMismatch": None, "exactBase": BASE_SHA,
            "compositeIdentityOnlySha256": STREAM_SHA, "sourceBindings": bindings,
            "newSourceBindings": new_bindings, "pureSourceAstNodes": pure_nodes,
            "sourceGuardControls": policy_controls, "independentReference": independent,
            "protocolTests": tests, "extendedContextEquivalence": extended, "capabilityAudit": audit,
            "actualSyntheticCompositeExecution": "NotRun", "TargetCPUExecutionNotObserved": True,
            "CPUExecutions": 0, "actualROMExecutions": 0, "targetObjects": 0,
            "targetHEX": 0, "FirmwareBIN": 0, "FirmwareReady": False,
            "nativeExitIsolation": "NotEstablished", "actualDownstreamRejoin": "NotEstablished",
            "targetProgramEquivalence": "NotEstablished", "firmwareIntegration": "NotEstablished"}


def main():
    require(len(sys.argv) == 1, "NoExternalPathsProgramsOrExecutionArguments")
    result = validate()
    print("M2BK_EVIDENCE_JSON=" + json.dumps(result, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
