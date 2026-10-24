"""Closed M2bu requirements validation; never runtime evidence or authority."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

from . import corpus, oracle

ROOT = Path(__file__).resolve().parents[3]
PATH = Path(__file__).with_name("contract.json")
BASE = "7eb26571d8ee1f849efe5ffa619b0201008b267c"
SOURCES = (
    ("docs/M2Y_WORD0196_CONSUMER_HANDOFF.md", 8295, "4df6ed9227027a8723eeacf27a4c44bf6be647c3d939c135f54c31cd4c904f09"),
    ("research/p28-word0196/original_rom_boundary/contract.json", 17557, "b8a1a482dfa8f48f310db89d291014d1f4ebf83f51022cf7f70fb1dea0c1da30"),
    ("research/p28-word0196/original_rom_boundary/decode.py", 13934, "ad7079c1894488834fa85d3f24b483e530440853eade244ff54556a3b442ad58"),
    ("research/p28-word0196/original_rom_execution/contract.json", 5497, "b2ef4234d6a7866f95fdc292faff307a2c8fb3dbe15f43120f837a6aa3a32e9a"),
    ("research/p28-word0196/original_rom_execution/corpus.py", 17843, "3c9b374d37b79db548eed5bdb7bd3a10417f527da123d6d664f302704a5d1180"),
    ("research/p28-word0196/original_rom_execution/oracle.py", 26779, "166d18ebd1f5c5fb165a8628e750c18c0a4a90dbc8b536cfc70999c6cba0d804"),
    ("research/p28-word0196/word0196_ir.json", 32188, "4fdbd6b7dbdd8f48d5a43e123ca93a33a003c22556a0c40b5296d5f409e085c4"),
    ("research/p28-word0196/word0196_equivalent.c", 8507, "4b189d4ed3e97e0d197f6c558755cf056a89c1dc7122653c5c557e7ab62d76d3"),
)
UNRESOLVED = ["ActualHardwareEcuExecutionNotObserved", "RecoveredFullEcuSchedulerNotEstablished",
    "PhysicalSFNotEstablished", "NativeStackSafetyNotEstablished", "PeripheralStateOwnershipNotEstablished",
    "ActualNativeDownstreamRejoinNotEstablished", "SafeROMPlacementNotEstablished",
    "TargetProgramEquivalenceNotEstablished", "FirmwareIntegrationNotEstablished"]


def need(condition, code):
    if condition is not True:
        raise ValueError(code)


def _exact(actual, expected, label):
    oracle._equal(actual, expected, "contract/" + label)


def validate_contract(contract=None, source_bindings=None):
    contract = json.loads(PATH.read_bytes()) if contract is None else deepcopy(contract)
    need(type(contract) is dict and set(contract) == {"schemaVersion", "milestone", "baseCommit", "classification",
        "sourceBindings", "manufacturer", "program", "predecessor", "paths", "branchControls", "entry", "corpus",
        "publicFixture", "provenance", "comparison", "delivery", "unresolved", "firmwareReady"}, "ClosedM2buContract")
    for name, expected in (("schemaVersion", 1), ("milestone", "M2bu"), ("baseCommit", BASE),
        ("classification", "ClosedEntryContinuityRequirements_NotRuntimeEvidence"), ("unresolved", UNRESOLVED), ("firmwareReady", False)):
        _exact(contract[name], expected, name)
    source_rows = [{"path": path, "bytes": size, "sha256": digest} for path, size, digest in SOURCES]
    _exact(contract["sourceBindings"], source_rows, "frozenSources")
    for path, size, digest in SOURCES:
        raw = (ROOT / path).read_bytes()
        need(len(raw) == size and sha256(raw).hexdigest() == digest, "FrozenUpstreamSourceChanged:" + path)
    _exact(contract["manufacturer"], {"source": "MSM66201 Instruction Manual September1991",
        "sha256": "f6e423ac0bd15378754e30c35ed426415ec219e360c68e817ab451df72142271",
        "predecessorPages": ["3-64", "3-99", "3-69", "3-154", "3-42", "3-66/3-67"],
        "productionOpcodeTableIsPrimaryAuthority": False}, "manufacturer")
    _exact(contract["program"], {"entryPc": 0x54F5, "segmentEndExclusive": 0x55C5, "segmentBytes": 208,
        "closedInstructionSites": 24, "selectedInstructionBytes": 59, "originalPcsRelocated": False,
        "oneImmutableSourcePerCase": True, "executionPermissionFromClosedCfgOnly": True,
        "terminalInstructionRetirements": 0, "p2FunctionalReads": 0, "p2FunctionalWrites": 0}, "program")
    _exact(contract["predecessor"], {"pcs": list(corpus.PREFIX), "lengths": [3, 2, 2, 1, 4, 2],
        "positiveGateBitValue": 1, "positiveByte0117MustNotEqual": 15, "jbrAlternateStopBefore": 0x5533,
        "jneAlternateStopBefore": 0x5503, "jneTakenDestination": 0x556F, "jneSignedDisplacement": 108,
        "wordLoadOverwritesAH": True, "wordStoreLocalAddress": 0x010A, "wordStoreWidthBits": 16,
        "r0WrittenValue": 255, "r0ReadBySuffix": True, "er1ReadBySuffix": False, "er1RetainedAsLiveOut": True,
        "prefixLogicalReads": 3, "prefixLogicalWrites": 2, "prefixRawWriteBytes": 3}, "predecessor")
    expected_paths = {}
    for case in corpus.iter_cases():
        expected = oracle.expected_case(case)
        row = {"retirements": expected["instruction_count"], "logicalReads": expected["logical_read_count"],
            "logicalWrites": expected["write_count"],
            "rawWriteBytes": sum(event["width"] // 8 for event in expected["ordered_data_events"] if event["operation"] == "Write"),
            "stopBeforePc": expected["stop_before_pc"]}
        need(case["path"] not in expected_paths or expected_paths[case["path"]] == row, "PathEffectsMustBeStateIndependentCounts")
        expected_paths[case["path"]] = row
    _exact(contract["paths"], expected_paths, "recomputedPaths")
    controls = {}
    for case in corpus.iter_branch_controls():
        expected = oracle.expected_case(case)
        controls[case["path"]] = {"retirements": expected["instruction_count"], "logicalReads": expected["logical_read_count"],
            "logicalWrites": expected["write_count"], "stopBeforePc": expected["stop_before_pc"], "positiveCompleted": False}
    _exact(contract["branchControls"], controls, "branchBoundaries")
    _exact(contract["entry"], {"lrb": 33, "fullRepresentablePswPredicateUnchanged": True,
        "incomingDd": [False, True], "hcOtherPswScbRetained": True, "selectedAndUnselectedPointingBanks": 8,
        "physicalSf": "Unknown", "hostSfExperiments": [False, True], "oneCpuAndBusPerCase": True,
        "hostPcSetAfterEntry": False, "midExecutionReseed": False, "secondMachineStateTransfer": False,
        "nativeStackFrameClaimed": False}, "entry")
    coverage = corpus.coverage()
    need(coverage["cases"] == 32 and coverage["paths"] == dict.fromkeys("ABCD", 8)
         and coverage["retirements"] == 592 and len(coverage["incomingFlagVectors"]) == 16
         and coverage["scbs"] == list(range(8))
         and {0, 191, 192, 193, 255, 256, 65535} <= set(coverage["words"]), "IndependentCorpusCoverageIncomplete")
    _exact(contract["corpus"], {"privatePositiveCases": 32, "publicPositiveCases": 32,
        "perPathCases": dict.fromkeys("ABCD", 8), "retirementsPerPositiveCorpus": 592,
        "predecessorRetirementsPerPositiveCorpus": 192, "requiredWordBoundaries": [0, 191, 192, 193, 255, 256, 65535],
        "sameValueWritesRetained": True, "positiveBelow0117StoreCanBeSameValue": False,
        "boundaryControlsCountedAsPositive": False}, "corpus")
    _exact(contract["publicFixture"], {"entryPc": 0x6200, "segmentEndExclusive": 0x62D0, "segmentBytes": 208,
        "gateByteAddress": 0x0130, "algorithmEntryPc": 0x627A, "independentlyInventedTypedEncoding": True,
        "privateSourceBinding": None, "originalRomExecutionClaimed": False}, "publicFixture")
    _exact(contract["provenance"], {"technicalMode": corpus.MODE, "current05ebProducerExecuted": False,
        "data0196InputOwner": "TechnicalInitialSeedPair_NoNativeGenerationOwner",
        "historical05eb54fa5578Relationship": "SeparateQualifiedPriorObservation_NotCurrentMachineOwnership",
        "pathCHistoricalNativeWitness": False, "nativeSchedulerEstablished": False, "physicalExecutionClaimed": False}, "provenance")
    _exact(contract["comparison"], {"oracleUsesActualRuntimeOutput": False, "completeExpectedFrozenBeforeRuntime": True,
        "fullIntermediateStateAndPsw": True, "allProgramLogicalAndRawDataEvents": True,
        "orderedSameValueWritesRetained": True, "wordWritesAreOneLogicalAndTwoRawEvents": True,
        "canonicalFieldExclusions": [], "firstMismatchBlocksAcceptance": True, "retirementCountsArePhysicalTime": False}, "comparison")
    _exact(contract["delivery"], {"cargoFeature": "p28-word0196-entry-continuity", "dependsOnExistingOriginalRomAudit": True,
        "featureDefaultOff": True, "maximumBudget": 21, "legacyMaximumBudget": 16, "legacyAdmissionsUnchanged": True,
        "cargoTarget": ".tmp/m2bu-owned/cargo-target", "requiredCiGuarantees": ["Ubuntu", "Windows", "Desktop", "HistoricalPinnedQa"],
        "fullDecompressedCanonicalByteEquality": True, "historicalPreservationExceptionCount": 1,
        "newUnauthorizedProtectedDifferencesAllowed": 0, "strictHistoricalPreservationPass": False,
        "contractCreatesRuntimeOrDeliveryAuthority": False}, "delivery")
    if source_bindings is not None:
        need(type(source_bindings) is list and source_bindings
             and all(type(row) is dict and set(row) == {"path", "mode", "bytes", "sha256"}
                     and type(row["path"]) is str and row["mode"] == "100644"
                     and type(row["bytes"]) is int and row["bytes"] >= 0
                     and type(row["sha256"]) is str and oracle.previous.SHA.fullmatch(row["sha256"]) is not None
                     for row in source_bindings)
             and [row["path"] for row in source_bindings] == sorted({row["path"] for row in source_bindings}),
             "ClosedOrderedActiveSourceBindingsRequired")
        supplied = {row["path"]: row for row in source_bindings}
        for row in source_rows:
            need(supplied.get(row["path"]) == {"mode": "100644", **row}, "FrozenSourcesMustJoinCompleteActiveInventory")
    return {"passed": True, "classification": "StaticM2buContractAndIndependentMathValidated_NotRuntimeEvidence",
        "positiveCases": 32, "positiveRetirements": 592, "paths": expected_paths,
        "branchControls": controls, "upstreamSourceBindings": source_rows, "actualCpuExecutions": 0,
        "runtimeOrAcceptanceAuthorityCreated": False, "firmwareReady": False}
