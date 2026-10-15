"""M2bl fixed-source mathematical gate; never loads a target program or CPU.

Only this trusted validator reads fixed repository source paths. The two pure
models consume invented JSON claims and opaque offset identities, not opcodes.
AST controls are defense in depth for pinned reviewed source, not a sandbox.
"""
import ast
import hashlib
import json
import re
import sys
from pathlib import Path


BASE_SHA = "c52dccad5416e87be07b775998e29ebb7daed13b"
COMPOSITE_SHA = "91ffb46922def91764f5d4da166ef2cfc9834ed0effcc051d3f97246fa147ab1"
CONTRACT_SHA = "8aaacbbcccbbdd4b139e64d7b88a6395360a3a241b8e9a625cfa13172c358278"
SOURCE_SHA = {
    "synthetic_adapter_feasibility_oracle.py": "4414f6de4fe705f4b097a00c7aed3fac951d5951f050589f3276b21e4c406268",
    "synthetic_adapter_feasibility_analysis.py": "5f4f8310524ff1dcaa704561b0984622be4ece6dca14bd68cc5c751a2c3474a3",
    "synthetic_adapter_feasibility_tests.py": "e21a1d3795df9087d9880b1adc4f360a0b19217fea900cc009716cac1cbe97ee",
}
ORACLE_MODEL_DIGEST = "7e61ac4607d78c8e4713043f206793b7738008f16d9fee9947a95b8a3a4cf073"
PSW_DIGEST = "750575c886569e03326eb29e2a0c3e3dc53621c00306ef21c281904d0936663e"
AREAS = ["admission", "evidence", "fetchExit", "mapping", "permissions", "psw", "snapshot"]
GAPS = [
    "SyntheticProgramMappingCapabilityNotEstablished",
    "Exact16FormIsolatedAdmissionNotEstablished",
    "ClosedSyntheticEntrySnapshotCapabilityNotEstablished",
    "IndependentDataReadWritePermissionsNotEstablished",
    "OrderedInstructionFetchObservationNotEstablished",
    "PswSnapshotRoundTripCapabilityNotEstablished",
]


def require(condition, code):
    if not condition:
        raise ValueError(code)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def unique_object(pairs):
    result = {}
    for name, value in pairs:
        require(name not in result, "DuplicateJsonKey")
        result[name] = value
    return result


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_object)


def assert_pure_source(source):
    """Parse only; attack strings below are never evaluated or imported."""
    tree = ast.parse(source)
    imports = {"copy", "hashlib", "json"}
    denied_calls = {"eval", "exec", "compile", "__import__", "open", "input", "print",
                    "breakpoint", "help", "globals", "locals", "vars", "getattr", "setattr",
                    "delattr", "bytes", "bytearray", "memoryview"}
    denied_attrs = {"open", "read_text", "read_bytes", "write_text", "write_bytes", "system",
                    "popen", "Popen", "run", "connect", "execute", "fromhex", "from_bytes",
                    "to_bytes", "encode_instruction", "decode_instruction", "emit_synthetic_composite"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            require(all(item.name in imports for item in node.names), "PureImportBoundary")
        if isinstance(node, ast.ImportFrom):
            require(node.level == 0 and node.module in imports, "PureImportBoundary")
        if isinstance(node, ast.Constant):
            require(type(node.value) is not bytes, "NoProgramPayloadLiteral")
        if isinstance(node, ast.Attribute):
            require(node.attr not in denied_attrs and not node.attr.startswith("__"), "PureAttributeBoundary")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            require(node.func.id not in denied_calls, "PureCallBoundary")
    return len(tuple(ast.walk(tree)))


def source_policy_controls():
    attacks = ["import subprocess", "from ctypes import CDLL", "import socket", "import os",
               "import pathlib", "open('unopened')", "eval('1')", "exec('x=1')", "compile('x','','exec')",
               "__import__('os')", "input()", "print('not-run')", "help()", "breakpoint()",
               "getattr(x,'open')", "x.__class__", "x.write_bytes(x)", "x.to_bytes(1)",
               "bytes([1])", "bytearray([1])", "b'opaque-not-program'", "x.fromhex('00')",
               "x.emit_synthetic_composite()", "from synthetic_composite_emitter import x"]
    for attack in attacks:
        try:
            assert_pure_source(attack)
        except ValueError:
            pass
        else:
            raise ValueError("ParseOnlyAttackAccepted")
    require(assert_pure_source("from hashlib import sha256\nimport json\ndef f(x):\n    return json.dumps(x)\n") > 0,
            "SourceValidControl")
    return {"parseOnlyRefusals": len(attacks), "validControls": 1, "executedAttackFixtures": 0,
            "classification": "TrustedHashBoundSourceDefenseInDepth_NotArbitraryPythonSandbox"}


def verify_contract_projection(directory, contract):
    """Cross-bind typed identities, not encoder/decoder/CPU outputs."""
    upstream = read_json(directory / "synthetic_execution_protocol_contract.json")
    eligibility = read_json(directory / "composite_emission_eligibility_contract.json")
    rules = eligibility["futurePrimaryVerification"]["ruleInventory"]
    expected_nodes = []
    for row in eligibility["typedRequestMapping"]:
        node = next(n for n in upstream["nodes"] if n["logicalId"] == row["nodeId"])
        rule = next(r for r in rules if r["form"] == row["formId"])
        operands = [{"kind": op["kind"], "fields": {"value": node["target"]}}
                    if op["kind"] == "TargetPC16" else op for op in row["operandDescriptors"]]
        expected_nodes.append({"nodeId": row["nodeId"], "originalLogicalSiteId": row["originalLogicalSiteId"],
                               "syntheticPc": node["syntheticPc"], "formId": row["formId"],
                               "length": row["plannedLength"], "documentedIncomingDD": rule["incomingDDValues"],
                               "plannedIncomingDD": row["incomingDDDomain"], "typedOperands": operands,
                               "successors": node["successors"], "primaryEvidence": {
                                   "pdfPage": rule["primaryPage"]["pdfPage"],
                                   "printedPage": rule["primaryPage"]["printedPage"],
                                   "symbolicCodeColumnRoles": rule["symbolicCodeColumnRoles"]},
                               "bytePayloadPresent": False})
    require(contract["nodes"] == expected_nodes and len(expected_nodes) == 20
            and len({n["formId"] for n in expected_nodes}) == 16, "IndependentUpstreamNodeProjection")
    require(contract["exactBase"] == BASE_SHA and contract["m2bjIdentity"]["sha256"] == COMPOSITE_SHA,
            "ExactUpstreamIdentity")
    require(contract["programMapping"]["basePc16"] == 4096
            and contract["programMapping"]["endExclusive"] == 4147
            and contract["programMapping"]["exactLength"] == 51
            and contract["programMapping"]["paddingBytes"] == 0
            and contract["programMapping"]["programAddressingMode"] == "SubtractBase_NoModulo_NoPadding",
            "ClosedProgramGeometry")
    require(contract["fetchAndExit"]["paths"] == upstream["paths"]
            and contract["fetchAndExit"]["successfulInstructionBudget"] == {"A": 11, "B": 13, "C": 14, "D": 16}
            and contract["dataPolicy"]["inventory"] == upstream["dataInventory"], "InheritedPathDataScope")
    require([g["gap"] for g in contract["sixGapDesign"]] == GAPS, "ExactlySixDesignGaps")
    psw = contract["pswRepresentation"]
    require((psw["readsOne"], psw["storage"], psw["low12Domain"], psw["representable"],
             psw["nonrepresentable"], psw["namedCombinations"]) == (3272, 823, 4096, 128, 3968, 16),
            "PinnedPswDomain")
    require(contract["independentOracle"]["sha256"] == SOURCE_SHA["synthetic_adapter_feasibility_oracle.py"]
            and not contract["independentOracle"]["m2bkOracleModified"]
            and contract["statuses"]["adapter"] == "RustAdapterNotImplemented"
            and contract["statuses"]["futureExecution"] == "ActualSyntheticExecutionBlocked"
            and contract["statuses"]["FirmwareReady"] is False, "AuthorityNotPromoted")
    return {"nodes": 20, "forms": 16, "paths": 4, "programLengthIdentityOnly": 51,
            "upstreamOracleUnchanged": True, "opcodeSemanticsExecuted": False}


def source_capability_design_audit(repo):
    def source(name):
        return (repo / "rust/p28-slice-runner/src" / name).read_text(encoding="utf-8")
    cpu, bus, execution, runner, protocol = [source(n) for n in ("cpu.rs", "bus.rs", "exec.rs", "runner.rs", "protocol.rs")]
    require("const PSW_READS_ONE: u16 = 0x0CC8;" in cpu
            and "self.psw_other = val & Self::PSW_STORAGE;" in cpu
            and "(self.psw_other & Self::PSW_STORAGE) | Self::PSW_READS_ONE" in cpu, "CurrentPswSourceMasks")
    require("self.rom.get(address).copied()" in bus and "self.rom.get(address as usize)" in bus
            and "rom: Vec<u8>" in bus, "CurrentAbsoluteProgramMapping")
    require(re.search(r"pub fn step\(cpu: &mut Cpu, bus: &mut Bus\)", execution) is not None,
            "ConcreteBusExecutionCoupling")
    require("pub fn configure_scoped_access" in bus and "data_ranges: Option<Vec<[u16; 2]>>" in bus,
            "CurrentSharedPermissionsSource")
    require(runner.index("if contract.exit_pcs.contains(&cpu.pc)")
            < runner.index("if result.steps >= contract.instruction_budget")
            < runner.index("let decoded = decode(cpu.dd"), "ExistingPreDecodeExitPrimitive")
    image = re.search(r"pub struct Image\s*\{([^}]+)\}", protocol)
    require(image is not None and "base" not in image.group(1), "NoCurrentProgramSegmentDescriptor")
    fetch = bus.split("pub fn fetch_code_u8", 1)[1].split("pub fn read_code_u8", 1)[0]
    require("program_reads" not in fetch, "CurrentFetchNotOrderedProgramDataJournal")
    return {"evidence": "ExistingRustSourceCapability", "gaps": GAPS,
            "mapping": "AbsoluteZeroBasedVector", "dropInBusWrapperSufficient": False,
            "futureResearchBusExecIntegration": "DesignOnly_NotImplementedOrCompiled",
            "zeroStepExitMembershipInsufficient": True, "pswReadsOne": 3272, "pswStorage": 823,
            "productionChanges": 0, "actualAdapterImplementation": "NotRun"}


def validate():
    directory = Path(__file__).resolve().parent
    repo = directory.parents[1]
    contract_path = directory / "synthetic_adapter_feasibility_contract.json"
    require(digest(contract_path.read_bytes()) == CONTRACT_SHA, "PinnedContractBeforeBindings")
    contract = read_json(contract_path)
    require(len(contract["sourceBindings"]) == 153, "CompleteUpstreamBindingInventory")
    seen, bindings = set(), []
    for row in contract["sourceBindings"]:
        require(type(row) is dict and set(row) == {"path", "bytes", "sha256"}, "BindingSchema")
        name = row["path"]
        require(type(name) is str and name not in seen and not name.startswith(("/", "\\"))
                and ":" not in name and ".." not in name.split("/"), "BindingPath")
        seen.add(name)
        path = (repo / name).resolve()
        require(path.is_relative_to(repo), "BindingOutsideRepository")
        data = path.read_bytes()
        require(len(data) == row["bytes"] and digest(data) == row["sha256"], "UpstreamSourceMismatch:" + name)
        bindings.append(row)
    ast_nodes, new_bindings = {}, []
    for name, expected in SOURCE_SHA.items():
        data = (directory / name).read_bytes()
        require(digest(data) == expected, "PinnedNewSource:" + name)
        require(b"\r" not in data, "SourceLfIdentityRequired")
        if name != "synthetic_adapter_feasibility_tests.py":
            ast_nodes[name] = assert_pure_source(data.decode("utf-8"))
        new_bindings.append({"file": name, "bytes": len(data), "sha256": digest(data)})
    projection = verify_contract_projection(directory, contract)
    capability = source_capability_design_audit(repo)
    policy = source_policy_controls()
    # All trusted model and test sources are pinned before importing any of them.
    from synthetic_adapter_feasibility_oracle import self_check
    from synthetic_adapter_feasibility_tests import run_tests
    independent = self_check()
    require(independent["modelPositiveCases"] == 117 and independent["nodeDdContextChecks"] == 40
            and independent["relationRefusalCount"] == 68 and independent["metadataRefusalCount"] == 6
            and independent["jsonBoundaryRefusalCount"] == 5
            and independent["expectationDigest"] == ORACLE_MODEL_DIGEST
            and independent["pswExpectationDigest"] == PSW_DIGEST
            and independent["pswCartesianCases"] == 65536 and independent["pswRepresentableLow12"] == 128
            and independent["pswIncompatibleLow12"] == 3968 and independent["analyzerCalls"] == 0
            and independent["cpuExecutions"] == 0, "IndependentPreAnalyzerOracleExpectations")
    tests = run_tests()
    require(tests["passed"] is True and tests["failed"] == 0 and tests["skipped"] == 0
            and tests["pswFullRecordComparisons"] == 65536 and tests["pswRecordDigest"] == PSW_DIGEST
            and tests["pswRepresentableLow12"] == 128 and tests["pswIncompatibleLow12"] == 3968
            and tests["nodeCoverage"] == 20 and tests["formCoverage"] == 16
            and tests["positiveAreas"] == AREAS and tests["pathCoverage"] == list("ABCD")
            and tests["allScb"] == list(range(8)) and tests["incomingDD"] == [0, 1]
            and tests["mandatoryCategoryCount"] == 39 and len(tests["mandatoryCategoryCoverage"]) == 39
            and tests["wholeExpectedCaseEquality"] == 65866
            and tests["positiveCasesByArea"] == {"admission": 2, "evidence": 1, "fetchExit": 132,
                                               "mapping": 51, "permissions": 80, "psw": 65536, "snapshot": 64}
            and tests["semanticNegativeCases"] == 122 and tests["identityNegativeCases"] == 6
            and tests["authorityNegativeCases"] == 8 and tests["jsonBoundaryRefusals"] == 5
            and tests["uniqueNegativeInputs"] == 136
            and tests["positiveExpectedDigest"] == "f6aedde47dfeb95e966c3835a0106bc2944436587d75051bd5324525ca1750ec"
            and tests["negativeInputDigest"] == "708e168e91085a98b0eb77549faa3ae5825af196c5320003deb19d7f1b4d792f"
            and tests["cpuExecutions"] == 0 and tests["originalRomExecutions"] == 0
            and tests["programPayloadBytes"] == 0 and tests["upstreamOracleDomainChanged"] is False,
            "CompleteNonvacuousIndependentSuite")
    for name in (contract_path.name, Path(__file__).name):
        path = directory / name
        new_bindings.append({"file": name, "bytes": path.stat().st_size, "sha256": digest(path.read_bytes())})
    return {"milestone": "M2bl", "status": "M2bl Synthetic Adapter Design and Feasibility Established",
            "classification": "ObservedIndependentMathematicalChecks_NotRustAdapterImplementation",
            "passed": True, "failed": 0, "skipped": 0, "firstMismatch": None,
            "exactBase": BASE_SHA, "compositeIdentityOnlySha256": COMPOSITE_SHA,
            "sourceBindings": bindings, "newSourceBindings": new_bindings,
            "contractProjection": projection, "sourceCapabilityDesignAudit": capability,
            "pureSourceAstNodes": ast_nodes, "sourcePolicyControls": policy,
            "independentOracle": independent, "adapterTests": tests,
            "privatePrimaryEvidence": "IdentityOnlyInPublicCi_LocalFullPageReviewAndCrcReceiptSeparate",
            "PswRepresentableDomainEstablished": True,
            "FullInventedPswDomainRuntimeCompatibilityNotEstablished": True,
            "upstreamOracleDomainChanged": False, "RustAdapterNotImplemented": True,
            "actualAdapterImplementation": "NotRun", "actualSyntheticCompositeExecution": "NotRun",
            "CPUExecutions": 0, "actualROMExecutions": 0, "targetObjects": 0, "targetHEX": 0,
            "FirmwareBIN": 0, "persistentExecutablePayloads": 0, "FirmwareReady": False,
            "nativeExitIsolation": "NotEstablished", "actualDownstreamRejoin": "NotEstablished",
            "physicalRomPlacement": "NotEstablished", "targetProgramEquivalence": "NotEstablished",
            "firmwareIntegration": "NotEstablished", "runtimeExecutionAdmission": "Blocked"}


def main():
    require(len(sys.argv) == 1, "NoExternalPathsProgramsOrExecutionArguments")
    print("M2BL_EVIDENCE_JSON=" + json.dumps(validate(), sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
