"""Fail-closed bounded architecture/context research validator; never an ECU ABI.

This schema separates reusable evidence layers. The only reviewed profile here
is word0196SoftwareAlternate556F. Adding another fragment requires an explicit
independent profile review, not silently broadening the existing one. Document
references are obligations/citations, not cryptographic proof of their contents.
No code generation, executable loading, host pointer mapping or ROM is accepted.
"""

from pathlib import Path
import json
import sys


ROOT_KEYS = {
    "schemaVersion", "contractKind", "fragmentId", "target", "scope",
    "evidenceSources", "architectureContract", "compilerAbi",
    "firmwareIntegration", "toolchains", "codeGenerationRoutes", "permissions",
    "preservation",
}
SOURCE_CLASSES = {
    "ManufacturerPrimary", "HistoricalBoundedNativeEvidence",
    "IndependentHostSourceRepresentation", "CrossFamilyPrimaryLead",
    "DerivedThirdPartyLead",
}
SOURCE_IDS = {"IM1991", "DS1998", "MAC1993", "M2Z", "M2AV", "M2Y", "CC665S", "ASM662"}
HOST_FIELDS = {
    "a": ("A", 16, "ConfirmedArchitecture"),
    "a.low8": ("AL", 8, "ConfirmedArchitecture"),
    "a.high8": ("AH", 8, "ConfirmedArchitecture"),
    "psw": ("PSW", 16, "ConfirmedArchitecture"),
    "pc": ("NativePC", 16, "ConfirmedArchitecture"),
    "lrb": ("LRB", 16, "ConfirmedArchitecture"),
    "x1": ("X1 selected by SCB", 16, "ConfirmedArchitecture"),
    "x2": ("X2 selected by SCB", 16, "ConfirmedArchitecture"),
    "dp": ("DP selected by SCB", 16, "ConfirmedArchitecture"),
    "usp": ("USP selected by SCB", 16, "ConfirmedArchitecture"),
    "ssp": ("SSP", 16, "ConfirmedArchitecture"),
    "sf": ("SF (CAL/RT clear symbol; location not established)", 1, "ConditionalPrimaryConflictUnresolved"),
    "halted": ("HostReplayHaltedMetadata", 1, "HostOnly"),
    "local[0..7]": ("r0..r7 at LRB-selected DATA0108..010F", 8, "ConfirmedArchitecture"),
    "ram0117": ("DATA0117", 8, "ConfirmedWithinBoundedEvidence"),
    "ram0124": ("DATA0124", 8, "ConfirmedWithinBoundedEvidence"),
    "ram0128": ("DATA0128", 8, "ConfirmedWithinBoundedEvidence"),
    "ram012a": ("DATA012A", 8, "ConfirmedWithinBoundedEvidence"),
    "ram018e": ("DATA018E", 8, "ConfirmedWithinBoundedEvidence"),
    "ram018f": ("DATA018F", 8, "ConfirmedWithinBoundedEvidence"),
    "ram0196[0..1]": ("DATA0196/0197 little-endian word", 16, "ConfirmedWithinBoundedEvidence"),
}
RAM_PROFILE = {
    0x108: (8, "LocalRegister", ["5575"], ["557F"]),
    0x117: (8, "CurrentPage", ["557F", "5582"], ["5582", "55C1"]),
    0x124: (8, "CurrentPage", ["5588"], []),
    0x128: (8, "RetainedBoundaryState", [], []),
    0x12A: (8, "CurrentPage", ["5585", "558E"], ["558E"]),
    0x18E: (8, "CurrentPage", ["556F", "5572", "5576"], ["5572"]),
    0x18F: (8, "CurrentPage", ["558B", "5592"], ["558B", "55C3"]),
    0x196: (16, "CurrentPage", ["5578"], []),
}
UNKNOWN_ABI = {
    "targetCompiler", "compilerVersion", "targetSupportProof", "argumentPassing",
    "returnValues", "callerSavedRegisters", "calleeSavedRegisters", "stackFrameLayout",
    "stackAlignment", "CHAR_BIT", "charBits", "shortBits", "intBits", "longBits",
    "pointerWidths", "pointerAddressSpaces", "structAlignment", "structPacking",
    "boolRepresentation", "integerPromotions", "fixedWidthTypesAvailability",
    "symbolNaming", "runtimeHelpers", "memoryModel", "linkerConfiguration",
}
FORBIDDEN_KEYS = {
    "bytes", "rawbytes", "opcodebytes", "romwindow", "imageid", "machineid",
    "nativeownerid", "sourceidentity", "nativeordinal", "targetobjectbytes",
    "targetassemblysource", "firmwarebytes", "executablepath",
}



# Safety-bearing obligations are pinned per reviewed profile, not a JSON digest.
# Prose here is intentionally machine-checked, not an editable permission field.
REGISTER_OBLIGATIONS = {
    "a": {
        "sourceRefs": [
            "IM1991",
            "DS1998",
            "M2AV"
        ],
        "ownership": "Current native accumulator lineage; host value only OfflineReplaySnapshot",
        "preservation": "Reproduce reviewed AL writes; retain AH"
    },
    "a.low8": {
        "sourceRefs": [
            "IM1991",
            "M2AV"
        ],
        "ownership": "Low byte of A",
        "preservation": "LB/SLL/AND/OR effects exactly as M2av; no sign extension"
    },
    "a.high8": {
        "sourceRefs": [
            "IM1991",
            "M2AV"
        ],
        "ownership": "High byte of A",
        "preservation": "Preserved by every scoped byte AL update"
    },
    "psw": {
        "sourceRefs": [
            "IM1991",
            "DS1998",
            "M2AV"
        ],
        "ownership": "Retained native PSW; host snapshot is not authorization",
        "preservation": "CF/ZF/DD effects only as specified; HC and all other PSW bits retained"
    },
    "pc": {
        "sourceRefs": [
            "IM1991",
            "M2Z",
            "M2AV"
        ],
        "ownership": "Native instruction address, not host C return address",
        "preservation": "Entry556F; native branch-selected continuation5596/55C5 before P2"
    },
    "lrb": {
        "sourceRefs": [
            "IM1991",
            "M2Y",
            "M2AV"
        ],
        "ownership": "Retained native LRB0021; not an adapter seed",
        "preservation": "Preserve0021; required current page0100 and local bank0108"
    },
    "x1": {
        "sourceRefs": [
            "IM1991",
            "DS1998",
            "M2Y"
        ],
        "ownership": "Native pointing register bank PSW&7",
        "preservation": "Preserve selected bank value and all unselected banks; no hidden allocation"
    },
    "x2": {
        "sourceRefs": [
            "IM1991",
            "DS1998",
            "M2Y"
        ],
        "ownership": "Native pointing register bank PSW&7",
        "preservation": "Preserve selected bank value and all unselected banks; no hidden allocation"
    },
    "dp": {
        "sourceRefs": [
            "IM1991",
            "DS1998",
            "M2Y"
        ],
        "ownership": "Native pointing register bank PSW&7",
        "preservation": "Preserve selected bank value and all unselected banks; no hidden allocation"
    },
    "usp": {
        "sourceRefs": [
            "IM1991",
            "DS1998",
            "M2Y"
        ],
        "ownership": "Native pointing register bank PSW&7",
        "preservation": "Preserve selected bank value and all unselected banks; no hidden allocation"
    },
    "ssp": {
        "sourceRefs": [
            "IM1991",
            "M2Y"
        ],
        "ownership": "Native retained system stack pointer; actual reset/caller frame unknown",
        "preservation": "No stack writes/calls/prologue/epilogue in this fragment; retain incoming SSP"
    },
    "sf": {
        "sourceRefs": [
            "M2AV",
            "IM1991",
            "MAC1993"
        ],
        "ownership": "MSM66201 CAL/RT print SF-clear; MAC66K4-116 says stackflag only nX-8/300; conflict retained, host SF not native observation",
        "preservation": "No scoped SF writer; retain host replay value; no inferred SF0 or nX-8/300 STACK/A interpretation"
    },
    "halted": {
        "sourceRefs": [
            "M2AV"
        ],
        "ownership": "Host driver testing metadata; not an ordinary native CPU register",
        "preservation": "Host replay requiresfalse; not target runtime owner"
    },
    "local[0..7]": {
        "sourceRefs": [
            "IM1991",
            "M2AV"
        ],
        "ownership": "Current native local-bank bytes; retained historical r0; only r1 written in suffix",
        "preservation": "r0 and r2..r7 retained; r1 changed only by557F in not-below path"
    },
    "ram0117": {
        "sourceRefs": [
            "M2Z",
            "M2AV"
        ],
        "ownership": "Once-initial historical source, then native5582/55C1 lineage",
        "preservation": "Native branch-specific stores/order; no per-event reseed"
    },
    "ram0124": {
        "sourceRefs": [
            "M2Z",
            "M2AV"
        ],
        "ownership": "Retained upstream native software lineage",
        "preservation": "Read only when first gatefalse; retain all bits"
    },
    "ram0128": {
        "sourceRefs": [
            "M2Y",
            "M2Z",
            "M2AV"
        ],
        "ownership": "Once-initial masked0128.2 historical input; not runtimephysicalsourceproof",
        "preservation": "Retained; no fragment access"
    },
    "ram012a": {
        "sourceRefs": [
            "M2Z",
            "M2AV"
        ],
        "ownership": "Retained upstream bit1/neighbors, native558E bit0 history",
        "preservation": "First-gate bit7 read; OR bit0 only both gatesfalse; retain neighbors"
    },
    "ram018e": {
        "sourceRefs": [
            "M2Z",
            "M2AV"
        ],
        "ownership": "Historical initial scratch then native5572 history",
        "preservation": "ROL through CF; ordered store even equal value"
    },
    "ram018f": {
        "sourceRefs": [
            "M2Z",
            "M2AV"
        ],
        "ownership": "Historical initial scratch then native558B/55C3 history",
        "preservation": "Branch-specific RMW/STB order; retained if skipped"
    },
    "ram0196[0..1]": {
        "sourceRefs": [
            "IM1991",
            "M2Z",
            "M2AV"
        ],
        "ownership": "Current native05EB generation, same-generation54FA/5578 readers in historical corpus",
        "preservation": "Read-only word in suffix; retain both bytes; no host-derived generation"
    }
}
FLAG_OBLIGATIONS = {
    "CF": {
        "liveIn": "FirstLB556F retains incomingCF; SLL5571 overwrites before ROL5572",
        "liveOut": "CF from wordCMP5578:1below,0equal/above; no later CF writer",
        "sourceRefs": [
            "IM1991",
            "DS1998",
            "M2AV"
        ]
    },
    "ZF": {
        "liveIn": "FirstLB556F overwrites from018E",
        "liveOut": "Below:0 fromLB0F; not-below:0 from finalAL ORF0",
        "sourceRefs": [
            "IM1991",
            "DS1998",
            "M2AV"
        ]
    },
    "HC": {
        "liveIn": "Retained original value",
        "liveOut": "IncomingHC unchanged",
        "sourceRefs": [
            "IM1991",
            "DS1998",
            "M2AV"
        ]
    },
    "DD": {
        "liveIn": "Either0or1; firstLB556F clears0 before sensitive AL forms",
        "liveOut": "0 on both exits",
        "sourceRefs": [
            "IM1991",
            "DS1998",
            "M2AV"
        ]
    },
    "SCB": {
        "liveIn": "PSW&7; historical2 is not universal ABI constant",
        "liveOut": "IncomingSCB unchanged",
        "sourceRefs": [
            "IM1991",
            "DS1998",
            "M2Y",
            "M2AV"
        ]
    }
}
RAM_OBLIGATIONS = {
    "264": {
        "ownership": "Native r0 from earlier54F8; retained",
        "sourceRefs": [
            "IM1991",
            "DS1998",
            "M2Z",
            "M2AV"
        ]
    },
    "279": {
        "ownership": "Historical once-initial then native suffix history",
        "sourceRefs": [
            "IM1991",
            "DS1998",
            "M2Z",
            "M2AV"
        ]
    },
    "292": {
        "ownership": "Upstream retained software gate",
        "sourceRefs": [
            "IM1991",
            "DS1998",
            "M2Z",
            "M2AV"
        ]
    },
    "296": {
        "ownership": "Historical once-initial masked gate; no access in suffix",
        "sourceRefs": [
            "IM1991",
            "DS1998",
            "M2Z",
            "M2AV"
        ]
    },
    "298": {
        "ownership": "Retained neighboring bits; native bit0 write",
        "sourceRefs": [
            "IM1991",
            "DS1998",
            "M2Z",
            "M2AV"
        ]
    },
    "398": {
        "ownership": "Historical scratch initial, then native ROL history",
        "sourceRefs": [
            "IM1991",
            "DS1998",
            "M2Z",
            "M2AV"
        ]
    },
    "399": {
        "ownership": "Historical scratch initial, then native branch history",
        "sourceRefs": [
            "IM1991",
            "DS1998",
            "M2Z",
            "M2AV"
        ]
    },
    "406": {
        "ownership": "Native05EB word generation; historical same-generation54FA and5578",
        "sourceRefs": [
            "IM1991",
            "DS1998",
            "M2Z",
            "M2AV"
        ]
    }
}
ROUTE_OBLIGATIONS = {
    "A": {
        "route": "StructuredC->NativeCCompiler->NX8_200ObjectLinker",
        "requiredEvidence": [
            "ExactTargetCCompiler",
            "CompilerABI",
            "CTypePointerLayout",
            "MemoryModel",
            "RuntimeHelpers",
            "Linker",
            "GeneratedCodeVerification"
        ],
        "foundTools": [
            "MAC66K assembler documentation is not a C compiler"
        ],
        "nextExperiment": "ObtainApplicablePrimaryNX8_200CompilerAndABIDocument;NotPerformed"
    },
    "B": {
        "route": "VerifiedIR->NativeAssembly->VerifiedAssemblerLinker",
        "requiredEvidence": [
            "ExactEncoding",
            "RegisterAllocation",
            "StatePreservation",
            "LabelBranchLayout",
            "AbsoluteDataAccess",
            "OrderedWrites",
            "Flags",
            "SectionsRelocationPlacement",
            "NativeContinuation",
            "OperationalToolProvenance"
        ],
        "foundTools": [
            "MAC66K_RAS66K_RL66K manufacturer documentation"
        ],
        "nextExperiment": "AfterSeparateProvenanceLicenseRuntimeAuthorizationObtainInvented15FormTYPE_M66201ListingAndIndependentEncodingDDCheck;NotPerformed"
    },
    "C": {
        "route": "VerifiedAlgorithm->ManuallyReviewedBoundedAssembly",
        "requiredEvidence": [
            "ExactInstructionSemantics",
            "VerifiedAssembler",
            "ContextContract",
            "GeneratedInstructionReview",
            "NativeEquivalence",
            "PlacementAndContinuation"
        ],
        "foundTools": [
            "MAC66K assembler documentation;derived asm662 lead"
        ],
        "nextExperiment": "AfterSeparateVerifiedAssemblerAuthorizationReviewInventedBoundedNativeFragmentWithFlagsOrderedWritesTwoContinuations;NotPerformed"
    }
}
SOURCE_CITATIONS = {
    "IM1991": {
        "title": "MSM66201 Instruction Manual",
        "edition": "First edition September 1991",
        "url": "https://mycomputerninja.com/~jon/www.pgmfi.org/twiki/pub/Library/66kAssemblerDocs/Oki_66201_Instruction_Manual.pdf",
        "pages": [
            "1-5",
            "1-7",
            "1-10..1-24",
            "3-29",
            "3-125"
        ],
        "applicability": "MSM66201/nX-8/200 architecture; not OEM ASIC identity"
    },
    "DS1998": {
        "title": "MSM66201/66P201/66207/66P207",
        "edition": "E2E1027-27-Y4 January 1998",
        "url": None,
        "pages": [
            "1",
            "9",
            "10",
            "11",
            "13"
        ],
        "applicability": "Named standard devices; not proof of customer-specific ECU ASIC"
    },
    "MAC1993": {
        "title": "MAC66K Assembler Package User's Manual",
        "edition": "Third edition November 1993; MAC66K Ver.4.XX",
        "url": "https://datasheet.datasheetarchive.com/originals/library/Datasheets-UEA1/DSAFRAZ0014345.pdf",
        "pages": [
            "1-1",
            "1-5",
            "1-7",
            "3-3..3-8",
            "3-32..3-33",
            "4-23..4-24",
            "4-73",
            "4-116",
            "4-150",
            "4-157",
            "4-159",
            "4-163..4-185",
            "4-194..4-210",
            "4-242",
            "5-1..5-32",
            "7-3..7-12"
        ],
        "applicability": "nX-8/200 assembler target support; nX-8/300 STACK/A statement is not nX-8/200 proof"
    },
    "M2Z": {
        "title": "M2z native word0196 software-alternate comparison chain",
        "edition": "Historical software-only corpus",
        "url": "docs/M2Z_WORD0196_SOFTWARE_ALTERNATE.md",
        "pages": [
            "Native entry; generation; CFG"
        ],
        "applicability": "Retained technical same-machine bounded historical observations; not recovered ECU scheduler"
    },
    "M2AV": {
        "title": "M2av bounded word0196 structured IR and C11 equivalence",
        "edition": "M2av",
        "url": "docs/M2AV_WORD0196_STRUCTURED_C_EQUIVALENCE.md",
        "pages": [
            "Compact state; primary semantics; evidence limits"
        ],
        "applicability": "Host replay equivalence only; not native ABI or target binary"
    },
    "M2Y": {
        "title": "M2y native consumerWord0196 scheduled handoff",
        "edition": "M2y",
        "url": "docs/M2Y_WORD0196_CONSUMER_HANDOFF.md",
        "pages": [
            "Source entry live-ins; alias limits"
        ],
        "applicability": "Technical retained SSP07FE, SCB2 and LRB0021; not an actual reset/caller frame"
    },
    "CC665S": {
        "title": "CC665S User's Manual",
        "edition": "First edition March 1999; CC665S Ver.2.01",
        "url": "https://datasheet.datasheetarchive.com/originals/library/Datasheets-A1/DSAUTAZ0012723.pdf",
        "pages": [
            "User6..8",
            "User22",
            "User90",
            "User153..157",
            "Language22"
        ],
        "applicability": "Reviewed primary targets500/500S; /T string unvalidated; no200 compiler/ABI support established"
    },
    "ASM662": {
        "title": "asm662/dasm662 research context",
        "edition": "Pinned historical source",
        "url": "docs/M2J_ADD_ER3_ISA_EVIDENCE.md",
        "pages": [
            "Source independence"
        ],
        "applicability": "Derived encoding/tool hints; neither manufacturer ISA proof nor OEM ABI"
    }
}
TOOL_FEATURE_OBLIGATIONS = [
    {
        "id": "DeviceSelection",
        "mechanism": "TYPE uses authoritative matching deviceDCL; DCL includes allowedmemory/SFR/instructions",
        "pages": [
            "4-23",
            "4-24",
            "3-32",
            "3-33"
        ]
    },
    {
        "id": "AssemblySyntax",
        "mechanism": "Labels; A/Rn/ERn and OFF operands; individual core restrictions must be checked",
        "pages": [
            "4-27",
            "4-28",
            "4-122..4-127",
            "A-5..A-14"
        ]
    },
    {
        "id": "AbsoluteAndTypedAddresses",
        "mechanism": "CODE/DATA typed symbols; CSEG/DSEG AT; ORG constrained bysegment",
        "pages": [
            "4-157",
            "4-159",
            "4-163",
            "4-165",
            "4-178"
        ]
    },
    {
        "id": "RelocationAndSymbols",
        "mechanism": "SEGMENT/RSEG; PUBLIC/EXTRN; RL resolves external/library symbols and emits allocationmap",
        "pages": [
            "4-168..4-174",
            "4-184",
            "4-185",
            "5-1"
        ]
    },
    {
        "id": "LinkerPlacement",
        "mechanism": "RL /CODE and /DATA documented; exactsafeECUplacementNotEstablished",
        "pages": [
            "5-12..5-19",
            "5-31",
            "5-32"
        ]
    },
    {
        "id": "UsingState",
        "mechanism": "USING declares/checks assumptions; emitsNO native stateinitialization",
        "pages": [
            "3-7",
            "3-8",
            "4-194..4-208"
        ]
    },
    {
        "id": "No500LocalBankImport",
        "mechanism": "USING LREG unavailable100..400; AER/AR/LRBANK500-only; not200LRBcontext",
        "pages": [
            "4-210",
            "A-5",
            "A-9"
        ]
    }
]
REVIEWED_HAZARDS = [
    "Exact ECU device/revision/customer-specific ASIC identity and applicable mapping not established",
    "Independent target C compiler and nX-8/200 compiler ABI not established",
    "Target C type/pointer/struct layout not established",
    "Provenance-verified operational assembler/linker runtime not verified",
    "Native entry adapter implementation/register-allocation/flags/stack proof absent",
    "Actual incoming system stack value and frame availability not established by technical07FE",
    "SF primary conflict: MSM66201 CAL/RT printSFclear; MAC66K4-116 limitsstackflagto300;200 mode/storage/compiler treatment unresolved",
    "Continuation transfer and downstream live-out integration not executed",
    "Native source/generation continuity requires same retained CPU/Bus history, not host replay",
    "13-step CFG path lacks historical native witness",
    "Target generated-code equivalence and safe placement/linking not established",
    "Whole-ROM checksum/identity/flash/physical integration not established"
]

def demand(condition, message):
    if not condition:
        raise ValueError(message)


def same(value, expected):
    """JSON booleans are not interchangeable with integer 0/1."""
    if type(value) is not type(expected):
        return False
    if isinstance(value, dict):
        return value.keys() == expected.keys() and all(same(value[k], expected[k]) for k in value)
    if isinstance(value, list):
        return len(value) == len(expected) and all(same(a, b) for a, b in zip(value, expected))
    return value == expected


def expect(value, expected, message):
    demand(same(value, expected), message)


def walk(value):
    if isinstance(value, dict):
        for key, child in value.items():
            demand(key.lower() not in FORBIDDEN_KEYS, f"Private/runtime key prohibited: {key}")
            if key == "sourceRefs":
                demand(isinstance(child, list) and child and len(set(child)) == len(child)
                       and set(child) <= SOURCE_IDS, "Missing/unknown/duplicate source reference")
            walk(child)
    elif isinstance(value, list):
        for child in value:
            walk(child)


def context_geometry(lrb, psw):
    """Architectural address algebra only; not an adapter or execution permit."""
    demand(type(lrb) is int and 0 <= lrb <= 0xFFFF, "LRB is unknown/out of range")
    demand(type(psw) is int and 0 <= psw <= 0xFFFF, "PSW is unknown/out of range")
    scb = psw & 7
    return {
        "localBankBase": (lrb << 3) & 0xFFFF,
        "currentPage": ((lrb >> 5) << 8) & 0xFFFF,
        "scb": scb,
        "pointingRegisterBankBase": 0x80 + scb * 8,
    }


def word_from_bytes(low, high):
    demand(type(low) is int and type(high) is int and 0 <= low <= 255 and 0 <= high <= 255,
           "Unknown/out of range little-endian byte")
    return low | (high << 8)


def project_host_snapshot(state):
    """Invented/offline typed projection, explicitly not native source ownership."""
    keys = {"a", "psw", "pc", "lrb", "x1", "x2", "dp", "usp", "ssp", "sf",
            "halted", "local", "ram0117", "ram0124", "ram0128", "ram012a",
            "ram018e", "ram018f", "ram0196"}
    demand(isinstance(state, dict) and set(state) == keys, "Missing/extra replay field")
    for key in ["a", "psw", "pc", "lrb", "x1", "x2", "dp", "usp", "ssp"]:
        demand(type(state[key]) is int and 0 <= state[key] <= 0xFFFF, f"Unknown/out of range {key}")
    demand(type(state["sf"]) is bool and state["halted"] is False, "Wrong host-only metadata")
    expect(state["pc"], 0x556F, "Not the bounded replay entry")
    expect(state["lrb"], 0x21, "Alternative bank is not this fragment contract")
    for key, count in [("local", 8), ("ram0196", 2)]:
        demand(isinstance(state[key], list) and len(state[key]) == count and
               all(type(v) is int and 0 <= v <= 255 for v in state[key]), "Wrong byte array")
    for key in ["ram0117", "ram0124", "ram0128", "ram012a", "ram018e", "ram018f"]:
        demand(type(state[key]) is int and 0 <= state[key] <= 255, f"Unknown/out of range {key}")
    result = context_geometry(state["lrb"], state["psw"])
    result.update(
        classification="OfflineReplaySnapshotOnly", nativeOwner=False,
        al=state["a"] & 255, ah=state["a"] >> 8,
        word0196=word_from_bytes(*state["ram0196"]),
        sfNativeCounterpart="PrimaryConflictUnresolved;NoPhysicalBooleanMapping", haltedNativeRegister=False,
    )
    return result


def verify_ordered_effects(expected, proposed):
    """Checks an invented effect ledger, never grants native generation authority."""
    demand(isinstance(expected, list) and isinstance(proposed, list), "Effects must be ordered lists")
    site_addresses = {"5572": 0x18E, "557F": 0x109, "5582": 0x117, "558B": 0x18F,
                      "558E": 0x12A, "55C1": 0x117, "55C3": 0x18F}
    reviewed_paths = [
        ["5572", "55C1", "55C3"],
        ["5572", "557F", "5582"],
        ["5572", "557F", "5582", "558B", "558E"],
    ]
    for rows in [expected, proposed]:
        demand([row.get("site") for row in rows if isinstance(row, dict)] in reviewed_paths,
               "Unreviewed/skipped/reordered effect path")
    for row in expected + proposed:
        demand(isinstance(row, dict) and set(row) == {"site", "address", "widthBits", "old", "new"},
               "Effects have hidden source/owner/runtime fields")
        demand(row["site"] in site_addresses and row["address"] == site_addresses[row["site"]]
               and type(row["address"]) is int and type(row["widthBits"]) is int
               and row["widthBits"] == 8, "Unsupported effect site/address/width")
        demand(all(type(row[x]) is int and 0 <= row[x] <= 255 for x in ["old", "new"]),
               "Unknown effect byte is not zero")
    expect(proposed, expected, "Reordered/skipped/merged/changed native effect obligation")
    return True


def validate(contract):
    demand(isinstance(contract, dict) and set(contract) == ROOT_KEYS, "Contract root schema changed")
    expect(contract["schemaVersion"], 1, "Unsupported schema version")
    expect(contract["contractKind"], "BoundedTargetContextResearch", "Not a bounded research contract")
    expect(contract["fragmentId"], "word0196SoftwareAlternate556F", "Unreviewed profile")
    walk(contract)
    expect(contract["target"], {
        "manufacturer": "OKI", "core": "nX-8/200", "standardDevices": ["MSM66201", "MSM66207"],
        "deviceApplicability": "NamedStandardDeviceArchitectureOnly;CustomerAsicConditional",
        "customerAsicIdentity": "NotEstablished",
        "standardDeviceMemory": {
            "MSM66201": {"internalRamStart": 0x80, "internalRamEnd": 0x27F, "ramBytes": 512,
                          "rangeStatus": "ConfirmedPrimaryArchitecture", "sourceRefs": ["IM1991", "DS1998"]},
            "MSM66207": {"internalRamStart": None, "internalRamEnd": None, "ramBytes": 1024,
                          "rangeStatus": "SizeConfirmed;ExactFullRangeNotEstablishedInReviewedPrimary", "sourceRefs": ["DS1998"]},
        },
    }, "Cross-family/device applicability promotion")
    expect(contract["scope"], {
        "entryPc": 0x556F, "stopBeforePcs": [0x5596, 0x55C5], "instructionSites": 18,
        "exactForms": 15, "excluded": ["P2", "Timer", "IRQ", "Reset", "WDT", "ROMReplacement",
        "TargetAssemblyGeneration", "TargetObject", "FirmwareBIN"],
        "hostSourceLevelEquivalence": "BoundedSourceLevelEquivalenceEstablished",
        "targetMachineCodeEquivalence": "NotEstablished", "actualRomExecutions": 0, "firmwareBin": 0,
    }, "Scope/execution/equivalence promotion")
    sources = contract["evidenceSources"]
    demand(isinstance(sources, list) and len(sources) == len(SOURCE_IDS), "Wrong evidence inventory")
    demand({s.get("id") for s in sources} == SOURCE_IDS, "Wrong/duplicate evidence IDs")
    for source in sources:
        demand(set(source) == {"id", "classification", "title", "edition", "url", "pages", "applicability"},
               "Evidence source schema changed")
        demand(source["classification"] in SOURCE_CLASSES and isinstance(source["pages"], list)
               and source["pages"] and source["title"] and source["edition"] and source["applicability"],
               "Missing evidence classification/applicability")
        expect({key: source[key] for key in SOURCE_CITATIONS[source["id"]]}, SOURCE_CITATIONS[source["id"]],
               "Evidence citation/edition/pages/applicability changed")
    classes = {s["id"]: s["classification"] for s in sources}
    expect(classes, {"IM1991": "ManufacturerPrimary", "DS1998": "ManufacturerPrimary",
                     "MAC1993": "ManufacturerPrimary", "M2Z": "HistoricalBoundedNativeEvidence",
                     "M2AV": "IndependentHostSourceRepresentation", "M2Y": "HistoricalBoundedNativeEvidence",
                     "CC665S": "CrossFamilyPrimaryLead", "ASM662": "DerivedThirdPartyLead"},
           "Derived/host/cross-family source promoted to applicable primary")
    architecture = contract["architectureContract"]
    demand(set(architecture) == {"status", "addressSpaces", "registerMappings", "flagRequirements",
                                 "bankContext", "ramAccessMap", "wordAliasMap", "stackRequirements",
                                 "ramLayoutStatus", "nativeContextMapping"}, "Architecture schema changed")
    expect(architecture["status"], "TargetArchitectureVerifiedWithinScope", "Architecture claim changed")
    expect(architecture["ramLayoutStatus"], "DataMemoryLayoutVerifiedWithinScopeForStandardMSM66201;MSM66207AndASICConditional",
           "Unreviewed variant/ASIC RAM map promoted")
    expect(architecture["nativeContextMapping"], "NativeContextMapped", "Context mapping status changed")
    spaces = architecture["addressSpaces"]
    expect(spaces, {"program": {"widthBits": 16, "role": "InstructionAndExplicitProgramData", "sourceRefs": ["IM1991"]},
                    "data": {"widthBits": 16, "role": "RegistersRamSfrAndExternalData", "sourceRefs": ["IM1991", "DS1998"]},
                    "distinct": True, "hostPointerRepresentsNativeAddress": False}, "Code/data conflation")
    registers = architecture["registerMappings"]
    demand(isinstance(registers, list) and len(registers) == len(HOST_FIELDS), "Missing host/native field")
    demand({r.get("hostField") for r in registers} == set(HOST_FIELDS), "Duplicate/unknown host field")
    for register in registers:
        name = register["hostField"]
        base_keys = {"hostField", "native", "widthBits", "status", "sourceRefs", "ownership", "preservation"}
        extra_keys = {
            "a": {"nativeDataAddress"}, "psw": {"nativeDataAddress"}, "lrb": {"nativeDataAddress"},
            "ssp": {"nativeDataAddress", "historicalTechnicalValue", "actualEntryValueStatus"},
            "sf": {"nativeLocation", "nativeWidthBits", "widthBasis", "actualNativeStateSerialized", "evidenceInterpretations"},
            "halted": {"nativeLocation", "nativeWidthBits", "widthBasis"}, "local[0..7]": {"count"},
        }.get(name, set())
        demand(set(register) == base_keys | extra_keys, "Hidden register permission/schema field")
        expect([register["native"], register["widthBits"], register["status"]], list(HOST_FIELDS[name]),
               f"Wrong native field width/classification {name}")
        demand(register["ownership"] and register["preservation"] and register["sourceRefs"],
               f"Missing native owner/preservation/evidence {name}")
        expect({key: register[key] for key in REGISTER_OBLIGATIONS[name]}, REGISTER_OBLIGATIONS[name],
               f"Contradictory register ownership/preservation/evidence {name}")
    by_name = {r["hostField"]: r for r in registers}
    for name, address in [("a", 6), ("psw", 4), ("lrb", 2), ("ssp", 0)]:
        expect(by_name[name].get("nativeDataAddress"), address, "Register SFR is not a host struct offset")
    expect(by_name["sf"].get("nativeLocation"), None, "Cross-family SF native location invented")
    expect(by_name["sf"]["nativeWidthBits"], None, "SF host bool width became native width")
    expect(by_name["sf"]["widthBasis"], "HostLogicalBooleanDomainOnly;NeitherCStorageSizeNorNativeWidth", "SF width applicability invented")
    expect(by_name["sf"]["actualNativeStateSerialized"], False, "Historical SF observation invented")
    expect(by_name["sf"]["evidenceInterpretations"], [
        {"source": "IM1991", "pages": ["3-29", "3-125"], "statement": "Applicable MSM66201 CAL/RT Function prints SF<-0"},
        {"source": "MAC1993", "pages": ["4-73", "4-116"], "statement": "STACK/A stackflag described only for nX-8/300"},
    ], "SF primary conflict silently resolved")
    expect(by_name["halted"].get("nativeLocation"), None, "Halted became ordinary native register")
    expect(by_name["halted"]["nativeWidthBits"], None, "Halted width became native register width")
    expect(by_name["halted"]["widthBasis"], "HostLogicalBooleanDomainOnly;NoOrdinaryNativeRegisterOrCStorageSize", "Host halted mapped as physical register")
    expect(by_name["ssp"].get("actualEntryValueStatus"), "NotEstablished", "Technical SSP became actual source")
    expect(by_name["ssp"].get("historicalTechnicalValue"), 0x7FE, "Historical technical SSP changed")
    expect(by_name["local[0..7]"].get("count"), 8, "Local register width/count changed")
    flags = architecture["flagRequirements"]
    demand(isinstance(flags, list) and len(flags) == 5, "Missing flag mapping")
    demand({r.get("name") for r in flags} == {"CF", "ZF", "HC", "DD", "SCB"}, "Unknown/duplicate flags")
    for row in flags:
        demand(set(row) == {"name", "bit", "mask", "liveIn", "liveOut", "changes", "sourceRefs"},
               "Hidden flag permission/schema field")
        expected = {"CF": (15, 0x8000), "ZF": (14, 0x4000), "HC": (13, 0x2000),
                    "DD": (12, 0x1000), "SCB": (0, 7)}[row["name"]]
        expect([row["bit"], row["mask"]], list(expected), "Wrong PSW flag/bank layout")
        demand(row["liveIn"] and row["liveOut"] and row["sourceRefs"], "Missing flag liveness/evidence")
        expect({key: row[key] for key in FLAG_OBLIGATIONS[row["name"]]}, FLAG_OBLIGATIONS[row["name"]],
               "Contradictory flag liveness/evidence")
    by_flag = {r["name"]: r for r in flags}
    expect(by_flag["HC"]["changes"], [], "HC not preserved")
    expect(by_flag["CF"]["changes"], ["SLL5571", "ROL5572", "CMP5578"], "CF producer changed")
    expect(by_flag["ZF"]["changes"], ["LB", "ANDB", "ORB", "CMP"], "ZF producer changed")
    expect(by_flag["SCB"]["changes"], [], "SCB not preserved")
    expect(by_flag["DD"]["changes"], ["LB556F", "LB5575", "LB5592", "LB55BF"], "DD source changed")
    bank = architecture["bankContext"]
    expect(bank, {"requiredLrb": 0x21, "currentPage": 0x100, "localBankBase": 0x108,
                  "localBankEnd": 0x10F, "localBankFormula": "(LRB << 3) & 0xFFFF",
                  "currentPageFormula": "((LRB >> 5) << 8) & 0xFFFF", "scbFormula": "PSW & 7",
                  "pointingRegisterBankFormula": "0x80 + 8*SCB", "pointingRegisterOrder": ["X1", "X2", "DP", "USP"],
                  "pointingRegisterOffsets": [0, 2, 4, 6],
                  "historicalScb": 2, "historicalPointingStorage": [0x90, 0x97],
                  "alternativeLocalBankExample": {"lrb": 0x20, "currentPage": 0x100,
                  "localBankBase": 0x100, "localBankEnd": 0x107,
                  "classification": "ArchitectureAliasExample;NotPermittedFragmentContext"}}, "Bank/alias contract changed")
    rows = architecture["ramAccessMap"]
    demand(isinstance(rows, list) and len(rows) == len(RAM_PROFILE), "Missing RAM bytes")
    demand({r.get("address") for r in rows} == set(RAM_PROFILE), "Duplicate/wrong RAM addresses")
    for row in rows:
        row_keys = {"address", "widthBits", "space", "byteOrder", "mode", "requiredLrb", "sourceRefs",
                    "readerSites", "writerSites", "ownership", "physicalRole", "standardDevicePlacement",
                    "customerAsicApplicability", "aliasesOutsideScope"}
        extra_keys = {0x108: {"count", "endAddress", "localWrites", "localAliases"},
                      0x196: {"highByteAddress", "lowByteAddress", "immediateComparison"}}.get(row["address"], set())
        demand(set(row) == row_keys | extra_keys, "Hidden RAM permission/schema field")
        expected = RAM_PROFILE[row["address"]]
        expect([row["widthBits"], row["mode"], row["readerSites"], row["writerSites"]], list(expected),
               "Wrong RAM access footprint/order/width")
        expect([row["space"], row["requiredLrb"], row["physicalRole"], row["customerAsicApplicability"]],
               ["Data", 0x21, "Unknown", "ConditionalNotEstablished"], "RAM/runtime/physical applicability promotion")
        expect(row["byteOrder"], "LittleEndian" if row["widthBits"] == 16 else "Byte", "Wrong LE storage")
        expect(row["standardDevicePlacement"], "ConfirmedMSM66201InternalRAM0080..027F;MSM66207FullRangeConditional",
               "Standard memory map changed")
        expect(row["aliasesOutsideScope"], "PossibleIndirectIndexedStackOrDifferentLRB;NotGloballyExcluded",
               "Indirect/stack/context aliases silently excluded")
        demand(row["ownership"] and row["sourceRefs"], "Missing RAM provenance")
        obligations = RAM_OBLIGATIONS[str(row["address"])]
        expect({key: row[key] for key in obligations}, obligations, "Contradictory RAM ownership/evidence")
    ram = {r["address"]: r for r in rows}
    expect([ram[0x108].get("count"), ram[0x108].get("endAddress"), ram[0x108].get("localWrites")],
           [8, 0x10F, [{"address": 0x109, "pc": "557F"}]], "Local bank aliases changed")
    expect(ram[0x108].get("localAliases"), "r0..r7; er0..er3 pair consecutive LE bytes", "Wrong local byte/word alias")
    expect([ram[0x196].get("lowByteAddress"), ram[0x196].get("highByteAddress"),
            ram[0x196].get("immediateComparison")], [0x196, 0x197, 0xC0], "Word0196 endian/immediate changed")
    expect(architecture["wordAliasMap"], {
        "systemWordAddressRule": "EffectiveAddressAndFFFE;ExistingBoundedInputsUseEvenAddresses",
        "relevantAlignedPairs": [[0x116, 0x117], [0x124, 0x125], [0x128, 0x129],
                                 [0x12A, 0x12B], [0x18E, 0x18F], [0x196, 0x197]],
        "oddWord0197EffectiveAddress": 0x196, "highByte0197OverlapsWord0196": True,
        "aliasesGrantAccessPermission": False,
        "indirectIndexedStackAliasesOutsideScope": "Possible;NoGlobalAbsenceProof",
        "sourceRefs": ["IM1991", "M2Y", "M2AV"],
    }, "Word/high-byte/odd-effective-address aliases changed or authorized")
    stack = architecture["stackRequirements"]
    expect(stack, {"nativeRegister": "SSP", "widthBits": 16, "frameAvailability": "NotEstablished",
                   "actualEntryValue": None, "technicalHistoricalValue": 0x7FE,
                   "technicalValueIsNotRuntimeProof": True, "fragmentAccesses": 0,
                   "hiddenStackWritesAllowed": False, "systemWordRule": "EvenAddressLittleEndian",
                   "unknownSspMayAliasRegistersRamOrSfr": True,
                   "callSemantics": "CALaddr16 writes nextPC at oldSSP then decrementsSSP by2",
                   "returnSemantics": "RT incrementsSSP by2 then reads wordPC", "entryCreatesCallFrame": False,
                   "priorCallFrames": "NotEstablished",
                   "returnFrameMustNotBeSynthesized": True, "sourceRefs": ["IM1991", "M2Y"],
                   "sfClearDocumentedForCalRt": True,
                   "sfMeaningAndStorage": "PrimaryConflictUnresolved;DoNotImportNX8_300STACK_A",
                   "sfFromCrossFamilyApplied": False}, "Unproved frame/stack/SF permission")
    abi = contract["compilerAbi"]
    demand(set(abi) == {"status", "nativeCCompiler", "cTypeLayout", "hostStructIsNativeLayout",
                       "absoluteHostPointerCastAllowed", "unknownFields", "unknownIsZero",
                       "hostCompilationImpliesTargetCompilation"}, "ABI schema changed")
    expect([abi["status"], abi["nativeCCompiler"], abi["cTypeLayout"]],
           ["CompilerAbiNotEstablished", "TargetCCompilerNotEstablished", "TargetCTypeLayoutNotEstablished"], "Invented ABI/compiler/layout")
    for key in ["hostStructIsNativeLayout", "absoluteHostPointerCastAllowed", "unknownIsZero", "hostCompilationImpliesTargetCompilation"]:
        expect(abi[key], False, "Host/unknown value became target ABI")
    unknowns = abi["unknownFields"]
    demand(isinstance(unknowns, list) and len(unknowns) == len(UNKNOWN_ABI) and
           {u.get("name") for u in unknowns} == UNKNOWN_ABI, "Missing unknown ABI dependency")
    for row in unknowns:
        expect(row, {"name": row["name"], "status": "NotEstablished", "value": None}, "Guessed ABI field/zero default")
    validate_integration(contract["firmwareIntegration"])
    validate_toolchains(contract["toolchains"], contract["codeGenerationRoutes"])
    expect(contract["permissions"], {
        "firmwareReady": False, "targetCodeGeneration": "NotRun", "targetCompilation": False,
        "targetAssembly": False, "targetObject": False, "firmwareImage": False, "romReplacement": False,
        "nativeTrampoline": False, "hardwareExecution": False, "guiExecution": False,
        "unverifiedToolchainExecution": False, "peripheralAccess": False, "interruptInjection": False,
    }, "Unsupported generation/execution/firmware permission")
    expect(contract["preservation"], {"runnerVersion": "0.43.0", "protocol": 1, "semanticFixCount": 38,
                                     "m2avSemantics": "Unchanged", "irLayer": "SeparateTargetMetadata;NoIRModification",
                                     "hostFieldMappingIsNotTargetAbi": True}, "Historical/prod/IR boundary changed")
    return {"milestone": "M2aw", "passed": True, "contractProfiles": 1,
            "registerMappings": len(registers), "ramIntervals": len(rows),
            "compilerAbiEstablished": False, "targetCodeGenerationReady": False,
            "inventedOnly": True, "actualRomExecutions": 0, "firmwareBin": 0, "targetToolExecutions": 0}


def validate_integration(integration):
    demand(set(integration) == {"status", "entry", "exit", "preservedContext", "semanticObligations", "provenance", "hazards"},
           "Integration schema changed")
    expect(integration["status"], "FirmwareIntegrationNotEstablished", "Firmware integration promotion")
    expect(integration["entry"], {
        "classification": "NativeBasicBlockEntry", "pc": 0x556F, "nativePredecessor": "JNE5501",
        "nativeSubroutineEntry": "NotEstablished", "hostEntry": "HostReplayFunctionEntry",
        "proposedAdapter": "ProposedTargetAdapterEntry;NotImplemented", "ordinaryCCallAllowed": False,
        "contextSource": "RetainedSameCpuBusNativeHistory", "scheduleSeam": "05ED->54F5 ExplicitHarnessSchedule",
        "requiredLrb": 0x21, "scb": "RetainIncomingPSWLow3;Historical2", "dd": "Either;556Fclears0",
        "sf": "PrimaryConflictUnresolved;NoPhysicalBooleanMappingOrAssumedClearInFragment", "liveStateSource": "NativeCurrentGenerationOnly",
        "inventedRegisterPrologueAllowed": False,
        "status": "NativeEntryContractConditional",
    }, "Basic-block entry replaced by C call/reseed/hidden prologue")
    expect(integration["exit"], {
        "classification": "NativeExitContinuationIdentified", "targets": [
        {"pc": 0x5596, "branch": "NotBelow", "lastSite": "5594", "al": "018F|F0", "cf": 0, "zf": 0, "dd": 0},
        {"pc": 0x55C5, "branch": "Below", "lastSite": "55C3", "al": 15, "cf": 1, "zf": 0, "dd": 0}],
        "stopBeforePeripheral": True, "ordinaryRTAllowed": False, "implicitCReturnAllowed": False,
        "transferOption": "FutureVerifiedNativeJumpOrTrampoline;StaticOptionOnly", "p2ExecutionAllowed": False,
        "downstreamLiveOutKnowledge": "P2BoundaryAndIncomingAL/PSWIdentified;WiderContinuationNotEstablished",
    }, "Wrong continuation/flags/ordinary RT/P2 execution")
    expect(integration["preservedContext"], ["AH", "HC", "OtherPSW", "SCB", "LRB", "X1", "X2", "DP", "USP",
           "SSP", "SFHostReplay", "localr0", "localr2..r7", "DATA0124", "DATA0128", "DATA0196", "DATA0197",
           "UnrepresentedNativeStateRequiresFutureProof"], "Retained/live-out context waived")
    expect(integration["semanticObligations"], {
        "nativeLoadFlags": "LB writesAL only, ZF frombyte, DD0; CF/HC retained",
        "rotate": "ByteROLthroughIncomingCF; CFonly",
        "compare": "Unsigned16 word0196 vs codeOwnedImmediate00C0; CFborrow/ZFequality; A/HC/DDretained",
        "gates": "012A.7 first;0124.5 only firstfalse; flagsretained",
        "memoryWriteOrder": "RetainExactNativeSiteOrder", "sameValueWrites": "RetainSeparateOrderedWrites",
        "skippedWrites": "DoNotEmitOnSkippedCFGPaths", "volatileAloneEstablishesEquivalence": False,
        "compilerReorderingAllowed": False, "physicalTimingEstablished": False,
    }, "Flags/ordered effects/volatile/timing equivalence relaxed")
    expect(integration["provenance"], {
        "hostReplayAnnotations": "OfflineAnnotationOnly", "nativeOwnerAcceptedFromHost": False,
        "secondMachineHandoffAllowed": False, "reseedAt556FAllowed": False,
        "nativeCurrent0196": "Writer05EB,currentEventAndAllNativeOrdinal;54FAAnd5578SameGeneration",
        "staleEqualValueAccepted": False, "unknownSourceDefaultZero": False, "unknownPeripheralDefaultZero": False,
        "nativePath13Witnesses": 0, "actualExecutionPermission": False,
    }, "Host/second-machine/stale/unknown source became native proof")
    hazards = integration["hazards"]
    expect(hazards, REVIEWED_HAZARDS, "Documented blocker/uncertainty silently waived")
    demand(isinstance(hazards, list) and len(hazards) >= 12 and len(set(hazards)) == len(hazards), "Missing blockers")
    for term in ["customer-specific", "compiler ABI", "type/pointer/struct", "runtime not verified", "adapter",
                 "stack", "SF", "Continuation", "same retained", "13-step", "generated-code", "flash"]:
        demand(any(term in row for row in hazards), f"Missing hazard {term}")


def validate_toolchains(toolchains, routes):
    demand(isinstance(toolchains, list) and len(toolchains) == 3, "Missing toolchain evidence")
    demand({t.get("id") for t in toolchains} == {"MAC66K_RAS66K_RL66K", "CC665S", "ASM662_DASM662"},
           "Unknown/duplicate target toolchain")
    by_id = {t["id"]: t for t in toolchains}
    common = {"id", "classification", "runtime", "manufacturerDocumentation", "documentedCore",
              "compilerAbiEstablished", "executableVerified", "sourceRefs"}
    for tool in toolchains:
        extras = {"MAC66K_RAS66K_RL66K": {"documentedTypeTargets", "objectLinkerSupport", "documentedVersion",
                  "exactDeviceDcl", "matchingDclAcquired", "objectVersionCompatibility", "conversion",
                  "documentedFeatures", "usingInitializesNativeRegisters", "full15FormEncodingVerified"},
                  "CC665S": {"nx8_200Compatibility", "documentedVersion", "documentedTargetOptions", "defaultTarget",
                             "typeStringValidated", "typeStringEstablishesTargetSupport", "abiDocumentApplicability"},
                  "ASM662_DASM662": set()}[tool["id"]]
        demand(set(tool) == common | extras, "Hidden tool permission/schema field")
    mac = by_id["MAC66K_RAS66K_RL66K"]
    expect([mac["classification"], mac["runtime"], mac["documentedCore"], mac["documentedTypeTargets"]],
           ["AssemblerTargetSupportDocumented", "AssemblerRuntimeNotVerified", "nX-8/200", ["M66201"]],
           "Documented assembler became working tool or wrong target")
    expect(mac["manufacturerDocumentation"], True, "Assembler manufacturer source missing")
    expect(mac["documentedVersion"], "4.XX", "Tool version boundary changed")
    expect(mac["exactDeviceDcl"], {"MSM66201": "TYPE(M66201)Documented;DclBytesNotAcquired",
                                  "MSM66207": "ExactDclNotEstablished"}, "TYPE naming became unobserved DCL proof")
    expect(mac["matchingDclAcquired"], False, "DCL runtime availability invented")
    expect(mac["objectLinkerSupport"], "RASRelocatableOBJ->RLResolvedABS;OperationalPipelineNotRun",
           "Tool documentation became executed object/linker proof")
    expect(mac["objectVersionCompatibility"], {"v2_to_v4": "ExplicitlyIncompatible", "binaryObjectSchema": "NotEstablished"},
           "Incompatible object versions silently interchangeable")
    expect(mac["conversion"], {"tool": "OH", "inputRequirement": "NoUnresolvedRelocation",
                              "documentedOutputs": ["IntelHEX(default)", "MotorolaS2(/S)"],
                              "flatBinEstablished": False, "imageGenerationRun": False},
           "Documented HEX/S2 conversion became flat BIN or firmware image")
    features = mac["documentedFeatures"]
    feature_ids = {"DeviceSelection", "AssemblySyntax", "AbsoluteAndTypedAddresses", "RelocationAndSymbols",
                   "LinkerPlacement", "UsingState", "No500LocalBankImport"}
    demand(isinstance(features, list) and len(features) == 7 and {f.get("id") for f in features} == feature_ids,
           "Missing documented assembler/linker obligation")
    for feature in features:
        demand(set(feature) == {"id", "mechanism", "pages"} and feature["mechanism"] and feature["pages"],
               "Missing/hidden assembler feature permission")
    expect(features, TOOL_FEATURE_OBLIGATIONS, "Contradictory documented feature/evidence")
    expect(mac["usingInitializesNativeRegisters"], False, "USING is not runtime register initialization")
    expect(mac["full15FormEncodingVerified"], False, "Document syntax became verified output encoding")
    cc = by_id["CC665S"]
    expect([cc["classification"], cc["runtime"], cc["documentedCore"], cc["nx8_200Compatibility"]],
           ["CrossFamilyTargetSupportNotApplicable", "NotRun", ["nX-8/500", "nX-8/500S"], "NotEstablished"],
           "CC665S cross-family support promoted to200")
    expect(cc["manufacturerDocumentation"], True, "Other-family primary proof missing")
    expect(cc["documentedVersion"], "2.01", "CC version changed")
    expect(cc["documentedTargetOptions"], ["/nX500", "/nX500S"], "Invented200 compiler target option")
    expect(cc["defaultTarget"], "nX-8/500S", "CC default target forged")
    expect([cc["typeStringValidated"], cc["typeStringEstablishesTargetSupport"]], [False, False],
           "Arbitrary /T string became validated target support")
    expect(cc["abiDocumentApplicability"], "500/500SOnly;Not200", "Other-family C ABI imported")
    asm = by_id["ASM662_DASM662"]
    expect([asm["classification"], asm["runtime"], asm["manufacturerDocumentation"]],
           ["DerivedResearchLeadOnly", "NotRun", False], "Derived assembler became primary/OEM ABI")
    expect(asm["documentedCore"], "DerivedContext;NotManufacturerProof", "Derived assembler core compatibility invented")
    for tool in toolchains:
        expect([tool["compilerAbiEstablished"], tool["executableVerified"]], [False, False],
               "Tool documentation became compiler ABI/verified executable")
        demand(tool["sourceRefs"], "No tool source")
        expect(tool["sourceRefs"], {"MAC66K_RAS66K_RL66K": ["MAC1993"], "CC665S": ["CC665S"],
                                  "ASM662_DASM662": ["ASM662"]}[tool["id"]], "Wrong tool evidence applicability")
    demand(isinstance(routes, list) and len(routes) == 3 and {r.get("id") for r in routes} == {"A", "B", "C"},
           "Missing generation route distinction")
    by_route = {r["id"]: r for r in routes}
    for route in routes:
        route_keys = {"id", "route", "status", "requiredEvidence", "foundTools", "nextExperiment"}
        if route["id"] == "B":
            route_keys.add("fewerUnknownCompilerDependenciesThanA")
        demand(set(route) == route_keys, "Hidden route permission/schema field")
        expect({key: route[key] for key in ROUTE_OBLIGATIONS[route["id"]]}, ROUTE_OBLIGATIONS[route["id"]],
               "Route/required proof/found tool/future experiment contradicts reviewed obligations")
    expect(by_route["A"]["status"], "Blocked", "Native C route prematurely ready")
    for name in ["B", "C"]:
        expect(by_route[name]["status"], "DocumentedRouteConditionalNotReady", "Native assembly route prematurely ready")
    expect(by_route["B"]["fewerUnknownCompilerDependenciesThanA"], True, "IR route distinction missing")
    for route in routes:
        demand(isinstance(route["requiredEvidence"], list) and len(route["requiredEvidence"]) >= 6
               and route["foundTools"] and route["nextExperiment"], "Missing required route proof")


def load_contract(path):
    raw = Path(path).read_bytes()
    contract = json.loads(raw)
    expect(raw, (json.dumps(contract, indent=2, ensure_ascii=True) + "\n").encode("utf-8"),
           "Noncanonical UTF-8/LF/two-space contract")
    return contract


if __name__ == "__main__":
    path = Path(sys.argv[1]) if len(sys.argv) == 2 else Path(__file__).with_name("target_abi_contract.json")
    demand(len(sys.argv) <= 2, "Only one contract JSON path is accepted")
    print(json.dumps(validate(load_contract(path)), sort_keys=True))
