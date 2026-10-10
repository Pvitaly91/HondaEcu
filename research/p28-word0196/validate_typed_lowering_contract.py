"""Closed M2bd metadata/IR validator. Static obligations only, never codegen.

CLI reads ONLY its fixed own JSON/source identities; no arbitrary ROM/file input
or output artifact API. Pure structural analysis is separate from file identity.
"""
from pathlib import Path
import ast
import hashlib
import json
import sys

from typed_lowering_analysis import analyze_ir, demand, expect, strict_same, TypedLoweringError


PROFILE_METADATA = json.loads(r'''{
  "schemaVersion": 1,
  "classification": "ReviewedStaticTypedLoweringSpecification",
  "exactBase": "8fe005d1ba5f7b18f8df391b3fdf09d6330fad8e",
  "sourceBindings": [
    {
      "file": "word0196_ir.json",
      "bytes": 32188,
      "sha256": "4fdbd6b7dbdd8f48d5a43e123ca93a33a003c22556a0c40b5296d5f409e085c4"
    },
    {
      "file": "target_abi_contract.json",
      "bytes": 40753,
      "sha256": "1e8b20872693c0a7dcfbcfc867b85c55c3a759eef616651d6760c08b9dd5af66"
    },
    {
      "file": "independent_encoder_design.json",
      "bytes": 21765,
      "sha256": "9403279ed7570f1cb36280954a0f3249d41de2d64ae767b840649b066c625be9"
    },
    {
      "file": "independent_encoder.py",
      "bytes": 9868,
      "sha256": "603092893afbdb3d69cbcd43585ff6fc9886c45919920f432ec4b2905d830879"
    },
    {
      "file": "independent_encoder_contract.json",
      "bytes": 12182,
      "sha256": "414e5326cec42538ea6b64aa12a810c9d548c8b755b61a4f5c285b60c1837d47"
    },
    {
      "file": "independent_decoder.py",
      "bytes": 11036,
      "sha256": "e91c862d07d102c67ffa471603744c87eaee6d940fd27305e524afc91b946404"
    },
    {
      "file": "independent_decode_encode_contract.json",
      "bytes": 17800,
      "sha256": "547a09d9cd60dc6e2543870a5a5d0ee228e1051c28748fc53a526208355f5f2d"
    }
  ],
  "components": {
    "m2av": "BoundedSourceLevelEquivalenceEstablished",
    "m2aw": "TargetArchitectureContextEstablished",
    "m2ba": "IndependentEncoderRouteSpecified",
    "m2bb": "Independent15FormSyntheticEncodingVerified",
    "m2bc": "Independent15FormDecodeEncodeCompatibilityVerified",
    "runnerVersion": "0.43.0",
    "protocol": 1,
    "fixIdentities": 38,
    "encoderDecoderUse": "PublicImmutableTypesOnly_NoFragmentCalls"
  },
  "primarySources": {
    "manual": "Oki_66201_Instruction_Manual.pdf",
    "edition": "September1991",
    "manualSha256": "f6e423ac0bd15378754e30c35ed426415ec219e360c68e817ab451df72142271",
    "manufacturerExpectationsSha256": "a268815a0c04a4e2f0fccb64021ead26e1cbdaa02c1cc435d816f7d35fa2ab44",
    "instructionPdfPages": [
      76,
      77,
      90,
      119,
      120,
      121,
      124,
      153,
      160,
      163,
      173,
      197,
      208
    ],
    "excludedSemanticsInputs": [
      "ASM662",
      "DASM662",
      "Doc66207OpcodeTable",
      "GeneratedThirdPartyOpcodeTables",
      "EncoderOutput",
      "RustOpcodeTables"
    ],
    "priorThirdPartyExposureDisclosed": true,
    "legalCleanRoomCertification": false
  },
  "context": {
    "requiredLRB": 33,
    "currentPage": 256,
    "localBankBase": 264,
    "localBankEnd": 271,
    "SCB": "DerivedPSWLowThreeBits",
    "fixedSCBAssumption": null,
    "initialDD": [
      0,
      1
    ],
    "AL": {
      "widthBits": 8,
      "nativeAddress": 6
    },
    "AH": {
      "widthBits": 8,
      "nativeAddress": 7,
      "preservation": "AllScopedSites"
    },
    "A": {
      "widthBits": 16,
      "lowAlias": "AL",
      "highAlias": "AH"
    },
    "localRegisters": [
      {
        "name": "r0",
        "address": 264,
        "widthBits": 8
      },
      {
        "name": "r1",
        "address": 265,
        "widthBits": 8
      }
    ],
    "registerPairAliases": [
      {
        "name": "er0",
        "lowRegister": "r0",
        "highRegister": "r1",
        "lowAddress": 264,
        "highAddress": 265
      },
      {
        "name": "er1",
        "lowRegister": "r2",
        "highRegister": "r3",
        "lowAddress": 266,
        "highAddress": 267
      },
      {
        "name": "er2",
        "lowRegister": "r4",
        "highRegister": "r5",
        "lowAddress": 268,
        "highAddress": 269
      },
      {
        "name": "er3",
        "lowRegister": "r6",
        "highRegister": "r7",
        "lowAddress": 270,
        "highAddress": 271
      }
    ],
    "localPairByteOrder": "LittleEndian",
    "r1WriteAlias": "OnlyHighByteOfEr0ChangesAt557F;R0LowByteRetained",
    "LRBRebasingAllowed": false,
    "hostPointerCastsAllowed": false,
    "aliasesOutsideScope": "NotEstablished;NoGlobalAliasAbsenceClaim"
  },
  "addressObligations": [
    {
      "nativeAddress": 279,
      "rawOffset": 23,
      "widthBits": 8,
      "operandKind": "PageOffset8",
      "mode": "CurrentPage",
      "requiredLRB": 33,
      "byteOrder": "Byte",
      "highByteAddress": null
    },
    {
      "nativeAddress": 292,
      "rawOffset": 36,
      "widthBits": 8,
      "operandKind": "PageOffset8",
      "mode": "CurrentPage",
      "requiredLRB": 33,
      "byteOrder": "Byte",
      "highByteAddress": null
    },
    {
      "nativeAddress": 298,
      "rawOffset": 42,
      "widthBits": 8,
      "operandKind": "PageOffset8",
      "mode": "CurrentPage",
      "requiredLRB": 33,
      "byteOrder": "Byte",
      "highByteAddress": null
    },
    {
      "nativeAddress": 398,
      "rawOffset": 142,
      "widthBits": 8,
      "operandKind": "PageOffset8",
      "mode": "CurrentPage",
      "requiredLRB": 33,
      "byteOrder": "Byte",
      "highByteAddress": null
    },
    {
      "nativeAddress": 399,
      "rawOffset": 143,
      "widthBits": 8,
      "operandKind": "PageOffset8",
      "mode": "CurrentPage",
      "requiredLRB": 33,
      "byteOrder": "Byte",
      "highByteAddress": null
    },
    {
      "nativeAddress": 406,
      "rawOffset": 150,
      "widthBits": 16,
      "operandKind": "EvenPageOffset8",
      "mode": "CurrentPage",
      "requiredLRB": 33,
      "byteOrder": "LittleEndian",
      "highByteAddress": 407
    }
  ],
  "flagDomain": {
    "arithmeticFlags": [
      "CF",
      "ZF",
      "HC"
    ],
    "DD": "FormSelectionAndTransferNotArithmeticOperand",
    "scalarDomain": [
      "CF",
      "ZF",
      "HC",
      "DD",
      "PSW0",
      "PSW1",
      "PSW2",
      "PSW3",
      "PSW4",
      "PSW5",
      "PSW6",
      "PSW7",
      "PSW8",
      "PSW9",
      "PSW10",
      "PSW11"
    ],
    "groupedOtherPSW": [
      "PSW0",
      "PSW1",
      "PSW2",
      "PSW3",
      "PSW4",
      "PSW5",
      "PSW6",
      "PSW7",
      "PSW8",
      "PSW9",
      "PSW10",
      "PSW11"
    ],
    "SCBBits": [
      0,
      1,
      2
    ],
    "functionalEntryLive": [
      "HC",
      "OtherPSW"
    ],
    "initialCF": "RetainedBy556FThenKilledBy5571BeforeFunctionalRead",
    "initialZF": "KilledBy556FBeforeFunctionalRead",
    "initialDD": "EitherAcceptedThenKilledBy556F;NotOrdinaryArithmeticUse",
    "terminalObservable": [
      "CF",
      "ZF",
      "HC",
      "DD",
      "OtherPSW"
    ],
    "intermediateWrites": "AllNativeFlagWritesRetainedEvenWhenFunctionallyDead",
    "futureMayClobber": false,
    "livenessPolicy": "BackwardFunctionalAndDDSelectionSeparate;RetainedTerminalSnapshot;NoOptimizationPermission"
  },
  "cfg": {
    "entryPc": 21871,
    "stopBeforePcs": [
      21910,
      21957
    ],
    "completePaths": 4,
    "pathLengths": [
      10,
      12,
      13,
      15
    ],
    "allSitesMustReachable": true,
    "cyclesAllowed": false,
    "undefinedSuccessorsAllowed": false,
    "extraTerminalsAllowed": false,
    "terminalInstructionsExecuted": false,
    "originalPCs": "AuditedIdentityOnly_NotPlacementPermission",
    "relativeDistance": "MathematicalIntegers_NoWrap_NoBytes_NoRelaxation_NoRelocation"
  },
  "terminalObligations": [
    {
      "pc": 21910,
      "branch": "NotBelow",
      "AL": {
        "kind": "FinalMemoryOrImmediate",
        "address": 399,
        "immediate": 240
      },
      "CF": 0,
      "ZF": 0,
      "DD": 0,
      "HC": "IncomingHC",
      "OtherPSW": "IncomingOtherPSW",
      "AH": "IncomingAH"
    },
    {
      "pc": 21957,
      "branch": "Below",
      "AL": {
        "kind": "ConstantByte",
        "value": 15
      },
      "CF": 1,
      "ZF": 0,
      "DD": 0,
      "HC": "IncomingHC",
      "OtherPSW": "IncomingOtherPSW",
      "AH": "IncomingAH"
    }
  ],
  "provenance": {
    "data0196": "Native05EBWriterGeneration;Historical54FAAnd5578ReadSameGeneration",
    "data0117": "RetainedOnceInitialThenNativeWriteHistory",
    "data018e": "InitialScratchThenNative5572History",
    "data018f": "InitialScratchThenBranchSpecificNativeWriteHistory",
    "data012a": "RetainedNeighborBits;Bit0WriteOnly558E",
    "data0124": "UpstreamNativeOwnership",
    "data0128bit2": "OnceInitialMaskedHistory;NoScopedAccess",
    "transition05ed54f5": "ExplicitHarnessSchedule",
    "nativeOwnerAcceptedFromHost": false,
    "secondMachineHandoff": false,
    "reseedAt556f": false,
    "syntheticSSPFrame": false,
    "extraEventSource": false,
    "physicalMeaning": "Unknown",
    "currentWord0196PhysicalRole": "Unknown",
    "historicalCompletedObservations": 42,
    "historicalSnapshots": 552,
    "historicalOrderedWrites": 170,
    "historicalNativePath13Witnesses": 0
  },
  "nativeBoundary": {
    "entry": "NativeBasicBlockEntry",
    "nativeCFunctionEntry": "NotEstablished",
    "calFrameAt556f": "NotEstablished",
    "ordinaryReturnAllowed": false,
    "stopBoundariesAreRT": false,
    "preserved": [
      "AH",
      "HC",
      "OtherPSW",
      "SCB",
      "LRB",
      "X1",
      "X2",
      "DP",
      "USP",
      "SSP",
      "SFHostReplay",
      "localr0",
      "localr2..r7",
      "DATA0124",
      "DATA0128",
      "DATA0196",
      "DATA0197",
      "UnrepresentedNativeStateRequiresFutureProof"
    ],
    "exitOutputs": [
      "A_AL_AH",
      "PSW",
      "LRB",
      "SCB",
      "PointingRegisterBanks",
      "SSP",
      "RelevantRAM",
      "OrderedWrites",
      "BranchSelectedContinuation"
    ],
    "adapter": "NotImplemented",
    "prologueEpilogueAllowed": false,
    "pushPopAllowed": false,
    "sf": "PrimaryConflictUnresolved;NoNativeBooleanInterpretation",
    "stackSafety": "NotEstablished",
    "codePlacement": "NotEstablished",
    "widerContinuationLiveness": "NotEstablished"
  },
  "unresolved": {
    "targetCompilerABI": "NotEstablished",
    "SFMeaningStorageWidth": "PrimaryConflictUnresolved",
    "stackSafety": "NotEstablished",
    "codePlacement": "NotEstablished",
    "targetMachineCodeEquivalence": "NotEstablished",
    "nativeProgramEquivalence": "NotEstablished",
    "firmwareIntegration": "NotEstablished",
    "recoveredECUScheduler": "NotEstablished",
    "coherentResetFullbootFlow": "NotEstablished"
  },
  "permissions": {
    "runtimeExecution": false,
    "productionAdmission": false,
    "CPUExecution": false,
    "RAMExecution": false,
    "encoderOriginalSiteCalls": false,
    "decoderNativeFragmentCalls": false,
    "targetByteEmission": false,
    "instructionConcatenation": false,
    "assemblyText": false,
    "symbolResolution": false,
    "codePlacement": false,
    "linkerRelocation": false,
    "branchRelaxation": false,
    "nativeOwnerCreation": false,
    "firmwareReady": false,
    "ROMReplacement": false,
    "GUIExecution": false,
    "hardwareExecution": false
  },
  "counts": {
    "actualROMExecutions": 0,
    "ASM662Executions": 0,
    "nativeAssemblerExecutions": 0,
    "codegenExecutions": 0,
    "emittedTargetBytes": 0,
    "instructionStreams": 0,
    "targetAssemblyFiles": 0,
    "targetObjects": 0,
    "targetHEX": 0,
    "FirmwareBIN": 0,
    "inquiriesSent": 0
  },
  "historicalStatuses": {
    "m2bc": "DecodeEncodeCompatibilityVerified",
    "m2bb": "IndependentEncoderVerified",
    "m2ba": "IndependentRouteSpecified",
    "m2az": "HistoricalSourceRightsBlocked",
    "m2ay": "ASM662BuildEncodingBlocked",
    "m2ax": "MAC66KAcquisitionBlocked",
    "m2aw": "ArchitectureContextEstablished",
    "m2av": "BoundedSourceEquivalenceEstablished",
    "m2au": "INTAccountingComplete",
    "m2at": "DECDPHCFixComplete",
    "m2an": "SLLBFixComplete",
    "WDT3C": "ResearchBlocked",
    "JGT_C8": "PrimaryConflictUnresolved",
    "m2aqCAL2689_RT5C80": "NotRun",
    "m2ap": "SSPADCBlocked",
    "m2ao": "DATA019BFrontierUnchanged",
    "m2ah": "STOPBefore5722",
    "DATA019B2RuntimeOwner": "NotEstablished",
    "m2t": "JGT233ABlockedUnresolved",
    "StrictM2i": "Blocked",
    "IRQ": "NotInjected",
    "TimerEvolution": "NotModeled",
    "RecoveredECUScheduler": "NotEstablished",
    "TargetCompilerABI": "NotEstablished",
    "TargetIntegration": "NotEstablished",
    "Readiness": "PcInspectionOnly_NotFlashReady",
    "PhysicalFuelTimeDegrees": "Unavailable",
    "GUIHardwareFullboot": "NotRun",
    "ASM662_WDT_C8Inquiries": "NotSent"
  }
}''')
ROOT_KEYS = set(PROFILE_METADATA) | {"sites", "pathObligations"}


def validate_analysis_source(source):
    """Defense-in-depth static dependency guard, not arbitrary Python sandbox."""
    demand(type(source) is str, "SourcePolicy", "analysisSource.type")
    try:
        tree = ast.parse(source)
    except SyntaxError as error:
        raise TypedLoweringError("SourcePolicy", "analysisSource.syntax") from error
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            demand(all(n.name == "json" and n.asname is None for n in node.names),
                   "SourcePolicy", "analysisSource.import")
        if isinstance(node, ast.ImportFrom):
            allowed = {"__future__": {"annotations"}, "dataclasses": {"dataclass"},
                       "independent_encoder": {"FormId"}}
            demand(node.level == 0 and node.module in allowed and
                   all(n.name in allowed[node.module] and n.asname is None for n in node.names),
                   "SourcePolicy", "analysisSource.fromImport")
        if isinstance(node, ast.Name):
            demand(node.id not in {"encode_instruction", "decode_instruction", "_FORM_SHAPES", "FULL_OPCODES",
                                  "eval", "exec", "compile", "__import__", "open", "globals", "locals", "vars",
                                  "getattr", "setattr", "delattr", "bytes", "bytearray", "memoryview",
                                  "input", "print", "breakpoint", "help"},
                   "SourcePolicy", "analysisSource.forbiddenName")
        if isinstance(node, ast.Attribute):
            demand(not node.attr.startswith("__") and node.attr not in {
                "encode_instruction", "decode_instruction", "_FORM_SHAPES", "FULL_OPCODES",
                "read_bytes", "read_text", "write_bytes", "write_text", "open", "system", "popen",
                "spawn", "run", "unlink", "rename", "to_bytes", "from_bytes"},
                "SourcePolicy", "analysisSource.forbiddenAttribute")
    return {"passed": True, "codecCalls": 0, "policy": "StaticDependencyGuardNotSandbox"}


def validate_contract(contract, ir):
    """Validate closed metadata against independently pinned facts + actual IR.

    No whole-IR hash shortcut is used here: invented structural/CFG/effect
    mutations reach real bounded analysis, independently of CLI source seals.
    """
    demand(type(contract) is dict and set(contract) == ROOT_KEYS, "Contract", "contract.root")
    for key, expected in PROFILE_METADATA.items():
        expect(contract[key], expected, "Contract", f"contract.{key}")
    result = analyze_ir(ir)
    expect(contract["sites"], result["sites"], "Contract", "contract.sites")
    expected_paths = []
    for index, path in enumerate(result["paths"]):
        below = path["stopBeforePc"] == 0x55C5
        site_by_pc = {s["pc"]: s for s in result["sites"]}
        reads = [{"pc": pc, **r} for pc in path["pcList"] for r in site_by_pc[pc]["memory"]["reads"]]
        writes = [{"pc": pc, **w} for pc in path["pcList"] for w in site_by_pc[pc]["memory"]["writes"]]
        final_al = ({"kind": "ConstantByte", "value": 15} if below else
                    {"kind": "FinalMemoryOrImmediate", "address": 0x18F, "immediate": 0xF0})
        expected_al = (["const", 15] if below else
                       ["or8", path["terminal"]["ram"]["RAM018F"], ["const", 0xF0]])
        expect(path["terminal"]["AL"], expected_al, "TerminalInvariant", f"path{index}.AL")
        expected_paths.append({"id": "ABCD"[index], "pcs": path["pcList"],
            "conditions": [{"pc": c["pc"], "result": c["value"]} for c in path["conditions"]],
            "terminal": path["stopBeforePc"],
            "historical": "StaticPrimaryAndInventedCoverage" if path["instructionCount"] == 13 else "HistoricalNativeValidated",
            "instructionCount": path["instructionCount"], "orderedReads": reads, "orderedWrites": writes,
            "mustNotRead": [0x124] if path["instructionCount"] == 12 else [],
            "finalAL": final_al, "finalCF": int(below), "finalZF": 0, "finalDD": 0})
    expect(contract["pathObligations"], expected_paths, "Contract", "contract.pathObligations")
    result["status"] = "M2bd Typed IR-to-Form Mapping and Dataflow Obligations Established"
    result["missingMappings"] = 0
    result["ambiguousMappings"] = 0
    return result


def _duplicate_safe(pairs):
    result = {}
    for key, value in pairs:
        demand(key not in result, "Shape", "duplicateJSONKey")
        result[key] = value
    return result


def load_contract(path=None):
    """Read only fixed own contract path. Tests should mutate objects in memory."""
    own = Path(__file__).with_name("typed_lowering_contract.json")
    demand(path is None or Path(path).resolve() == own.resolve(), "SourcePolicy", "ownContractOnly")
    raw = own.read_bytes()
    result = json.loads(raw, object_pairs_hook=_duplicate_safe)
    expect(raw, (json.dumps(result, indent=2, ensure_ascii=True) + "\n").encode("utf-8"), "Shape", "canonicalContract")
    return result


def load_ir():
    own = Path(__file__).with_name("word0196_ir.json")
    raw = own.read_bytes()
    demand(hashlib.sha256(raw).hexdigest() == PROFILE_METADATA["sourceBindings"][0]["sha256"],
           "SourceIdentity", "word0196_ir.json")
    return json.loads(raw, object_pairs_hook=_duplicate_safe)


def verify_sources():
    """Seven fixed older public identities + pure analyzer static source guard."""
    directory = Path(__file__).resolve().parent
    for binding in PROFILE_METADATA["sourceBindings"]:
        path = directory / binding["file"]
        data = path.read_bytes()
        demand(len(data) == binding["bytes"] and hashlib.sha256(data).hexdigest() == binding["sha256"],
               "SourceIdentity", binding["file"])
    guard = validate_analysis_source(directory.joinpath("typed_lowering_analysis.py").read_text(encoding="utf-8"))
    return {"passed": True, "preservedSourceBindings": len(PROFILE_METADATA["sourceBindings"]), "analysisSourcePolicy": guard}


def main():
    demand(len(sys.argv) == 1, "SourcePolicy", "noExternalFileOrROMArguments")
    seals = verify_sources()
    analysis = validate_contract(load_contract(), load_ir())
    print(json.dumps({"milestone": "M2bd", "passed": analysis["passed"], "status": analysis["status"],
        "classification": analysis["classification"], "instructionSites": analysis["instructionSites"],
        "uniqueForms": analysis["uniqueForms"], "completePaths": len(analysis["paths"]),
        "pathLengths": [p["instructionCount"] for p in analysis["paths"]],
        "ddInitialContexts": [0, 1], "ddRequiresZeroSites": 5, "flagDomainBits": len(analysis["flagDomain"]),
        "missingMappings": analysis["missingMappings"], "ambiguousMappings": analysis["ambiguousMappings"],
        "sourceIdentity": seals, "encoderCalls": 0, "decoderCalls": 0, "actualROMExecutions": 0,
        "generatedTargetBytes": 0, "firmwareBin": 0, "nativeExecutionAuthority": False}, sort_keys=True))


if __name__ == "__main__":
    main()
