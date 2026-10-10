"""Independent M2bd static expectations, authored before the analyzer.

Functional facts come from complete manufacturer pages and the retained reviewed
IR identity. This module imports no analyzer, codec, CPU, C or C# implementation.
Invented algebra below is not an instruction executor or a native write journal.
"""

FLAG_DOMAIN = ("CF", "ZF", "HC", "DD") + tuple(f"PSW{bit}" for bit in range(12))
COMMON = (0x556F, 0x5571, 0x5572, 0x5575, 0x5576, 0x5578, 0x557D)
PATH_PCS = {
    "A": COMMON + (0x55BF, 0x55C1, 0x55C3),
    "B": COMMON + (0x557F, 0x5582, 0x5585, 0x5592, 0x5594),
    "C": COMMON + (0x557F, 0x5582, 0x5585, 0x5588, 0x5592, 0x5594),
    "D": COMMON + (0x557F, 0x5582, 0x5585, 0x5588, 0x558B, 0x558E, 0x5592, 0x5594),
}

# Each operand tuple is (public immutable type name, exact scalar fields).
# These are audit identities/obligations, never assembled instructions or bytes.
MAPPING = (
    (0x556F, "lb-a-page", 2, (("AccumulatorA", ()), ("PageOffset8", (0x8E,)))),
    (0x5571, "sllb-a", 1, (("AccumulatorA", ()),)),
    (0x5572, "rolb-page", 3, (("PageOffset8", (0x8E,)),)),
    (0x5575, "lb-a-r0", 1, (("AccumulatorA", ()), ("Register0", (0,)))),
    (0x5576, "andb-a-page", 2, (("AccumulatorA", ()), ("PageOffset8", (0x8E,)))),
    (0x5578, "cmp-page-imm16", 5, (("EvenPageOffset8", (0x96,)), ("Immediate16", (0xC0,)))),
    (0x557D, "jlt-rel8", 2, (("TargetPC16", (0x55BF,)),)),
    (0x557F, "movb-r1-page", 3, (("Register1", (1,)), ("PageOffset8", (0x17,)))),
    (0x5582, "andb-page-a", 3, (("PageOffset8", (0x17,)), ("AccumulatorA", ()))),
    (0x5585, "jbs-page-bit7", 3, (("PageBit7", (0x2A, 7)), ("TargetPC16", (0x5592,)))),
    (0x5588, "jbs-page-bit5", 3, (("PageBit5", (0x24, 5)), ("TargetPC16", (0x5592,)))),
    (0x558B, "andb-page-a", 3, (("PageOffset8", (0x8F,)), ("AccumulatorA", ()))),
    (0x558E, "orb-page-imm8", 4, (("PageOffset8", (0x2A,)), ("Immediate8", (1,)))),
    (0x5592, "lb-a-page", 2, (("AccumulatorA", ()), ("PageOffset8", (0x8F,)))),
    (0x5594, "orb-a-imm8", 2, (("AccumulatorA", ()), ("Immediate8", (0xF0,)))),
    (0x55BF, "lb-a-imm8", 2, (("AccumulatorA", ()), ("Immediate8", (0x0F,)))),
    (0x55C1, "stb-a-page", 2, (("AccumulatorA", ()), ("PageOffset8", (0x17,)))),
    (0x55C3, "stb-a-page", 2, (("AccumulatorA", ()), ("PageOffset8", (0x8F,)))),
)

SUCCESSORS = {
    0x556F: (0x5571,), 0x5571: (0x5572,), 0x5572: (0x5575,),
    0x5575: (0x5576,), 0x5576: (0x5578,), 0x5578: (0x557D,),
    0x557D: (0x55BF, 0x557F), 0x557F: (0x5582,), 0x5582: (0x5585,),
    0x5585: (0x5592, 0x5588), 0x5588: (0x5592, 0x558B),
    0x558B: (0x558E,), 0x558E: (0x5592,), 0x5592: (0x5594,),
    0x5594: (0x5596,), 0x55BF: (0x55C1,), 0x55C1: (0x55C3,),
    0x55C3: (0x55C5,),
}

DD_ZERO_REQUIRED = (0x5571, 0x5576, 0x5594, 0x55C1, 0x55C3)
DD_ZERO_WRITERS = (0x556F, 0x5575, 0x5592, 0x55BF)
FUNCTIONAL_FLAG_READS = {0x5572: ("CF",), 0x557D: ("CF",)}
FLAG_WRITES = {
    0x556F: ("ZF", "DD"), 0x5571: ("CF",), 0x5572: ("CF",),
    0x5575: ("ZF", "DD"), 0x5576: ("ZF",), 0x5578: ("CF", "ZF"),
    0x557D: (), 0x557F: (), 0x5582: ("ZF",), 0x5585: (), 0x5588: (),
    0x558B: ("ZF",), 0x558E: ("ZF",), 0x5592: ("ZF", "DD"),
    0x5594: ("ZF",), 0x55BF: ("ZF", "DD"), 0x55C1: (), 0x55C3: (),
}

# (mode, physical DATA address, width); RMW and local writes are never removed.
MEMORY = {
    0x556F: (("Read", 0x018E, 8),),
    0x5571: (),
    0x5572: (("Read", 0x018E, 8), ("Write", 0x018E, 8)),
    0x5575: (("Read", 0x0108, 8),),
    0x5576: (("Read", 0x018E, 8),),
    0x5578: (("Read", 0x0196, 16),),
    0x557D: (),
    0x557F: (("Read", 0x0117, 8), ("Write", 0x0109, 8)),
    0x5582: (("Read", 0x0117, 8), ("Write", 0x0117, 8)),
    0x5585: (("Read", 0x012A, 8),),
    0x5588: (("Read", 0x0124, 8),),
    0x558B: (("Read", 0x018F, 8), ("Write", 0x018F, 8)),
    0x558E: (("Read", 0x012A, 8), ("Write", 0x012A, 8)),
    0x5592: (("Read", 0x018F, 8),),
    0x5594: (), 0x55BF: (),
    0x55C1: (("Write", 0x0117, 8),),
    0x55C3: (("Write", 0x018F, 8),),
}

PAGE_MAP = ((0x0117, 0x17), (0x0124, 0x24), (0x012A, 0x2A),
            (0x018E, 0x8E), (0x018F, 0x8F), (0x0196, 0x96))
PRESERVED = ("AH", "HC", "OtherPSW", "SCB", "LRB", "X1", "X2", "DP",
             "USP", "SSP", "SFUninterpreted", "localr0", "localr2..r7",
             "RAM0124", "RAM0128", "RAM0196", "RAM0197")


def expected_mapping():
    """Return fresh independent scalar audit rows, not typed codec requests."""
    return [
        {"pc": pc, "formId": form, "length": length,
         "typedOperands": [{"type": kind, "fields": list(values)}
                           for kind, values in operands],
         "successors": list(SUCCESSORS[pc]),
         "ddPrecondition": "RequiresDD0" if pc in DD_ZERO_REQUIRED else "AcceptsBothIncomingDD",
         "ddTransfer": "SetsDD0WhenExecuted" if pc in DD_ZERO_WRITERS else "PreservesDD",
         "functionalFlagsRead": list(FUNCTIONAL_FLAG_READS.get(pc, ())),
         "ddSelectionRead": pc in DD_ZERO_REQUIRED,
         "flagsWritten": list(FLAG_WRITES[pc]),
         "flagsPreserved": [flag for flag in FLAG_DOMAIN if flag not in FLAG_WRITES[pc]]}
        for pc, form, length, operands in MAPPING
    ]


def expected_paths():
    conditions = {
        "A": ((0x557D, "CF", 1),),
        "B": ((0x557D, "CF", 0), (0x5585, "RAM012A.7", 1)),
        "C": ((0x557D, "CF", 0), (0x5585, "RAM012A.7", 0), (0x5588, "RAM0124.5", 1)),
        "D": ((0x557D, "CF", 0), (0x5585, "RAM012A.7", 0), (0x5588, "RAM0124.5", 0)),
    }
    result = []
    for name, pcs in PATH_PCS.items():
        accesses = [{"site": pc, "mode": mode, "address": address, "widthBits": width}
                    for pc in pcs for mode, address, width in MEMORY[pc]]
        result.append({
            "name": name, "pcList": list(pcs), "instructionCount": len(pcs),
            "stopBeforePc": 0x55C5 if name == "A" else 0x5596,
            "conditions": [{"pc": pc, "predicate": predicate, "value": value}
                           for pc, predicate, value in conditions[name]],
            "memoryAccesses": accesses,
            "orderedWrites": [
                {"site": row["site"], "address": row["address"],
                 "widthBits": row["widthBits"], "sameValueWrite": "RetainFreshOrdinal"}
                for row in accesses if row["mode"] == "Write"],
            "terminalFlags": {"CF": 1 if name == "A" else 0, "ZF": 0, "DD": 0},
            "terminalFlagWriters": {"CF": 0x5578, "ZF": 0x55BF if name == "A" else 0x5594,
                                    "DD": 0x55BF if name == "A" else 0x5592},
            "historicalWitness": "StaticPrimaryAndInventedCoverage" if name == "C"
                                 else "HistoricalCompletedPathExists",
            "preserved": list(PRESERVED),
        })
    return result


def expected_dd(initial_dd=(0, 1)):
    """Path-enumerated may union/must intersection, distinct from worklist analysis."""
    if type(initial_dd) is not tuple or not initial_dd or any(type(x) is not int or x not in (0, 1)
                                                            for x in initial_dd):
        raise ValueError("Invalid invented DD domain")
    arrivals = {pc: [] for pc, *_ in MAPPING}
    departures = {pc: [] for pc, *_ in MAPPING}
    for pcs in PATH_PCS.values():
        domain = set(initial_dd)
        for pc in pcs:
            arrivals[pc].append(set(domain))
            if pc in DD_ZERO_REQUIRED and domain != {0}:
                raise ValueError("Independent DD conflict")
            if pc in DD_ZERO_WRITERS:
                domain = {0}
            departures[pc].append(set(domain))
    result = []
    for pc, *_ in MAPPING:
        may = set.union(*arrivals[pc])
        must = set.intersection(*arrivals[pc])
        result.append({"pc": pc, "mayIncoming": sorted(may), "mustIncoming": sorted(must),
                       "mayOutgoing": sorted(set.union(*departures[pc])),
                       "mustOutgoing": sorted(set.intersection(*departures[pc])),
                       "classification": "IncomingDDUnknown" if len(may) > 1 else f"KnownDD{next(iter(may))}"})
    return result


def expected_flags():
    """Independent path-wise reaching writers and backward value liveness.

    Terminal state preservation seeds every declared PSW bit as observable.
    Intermediate architectural writes remain obligations even if value-dead.
    """
    before = {pc: {flag: set() for flag in FLAG_DOMAIN} for pc, *_ in MAPPING}
    after = {pc: {flag: set() for flag in FLAG_DOMAIN} for pc, *_ in MAPPING}
    live_in = {pc: set() for pc, *_ in MAPPING}
    live_out = {pc: set() for pc, *_ in MAPPING}
    for pcs in PATH_PCS.values():
        writer = {flag: "Initial" for flag in FLAG_DOMAIN}
        for pc in pcs:
            for flag in FLAG_DOMAIN:
                before[pc][flag].add(writer[flag])
            for flag in FLAG_WRITES[pc]:
                writer[flag] = pc
            for flag in FLAG_DOMAIN:
                after[pc][flag].add(writer[flag])
        needed = set(FLAG_DOMAIN)
        for pc in reversed(pcs):
            live_out[pc].update(needed)
            needed.difference_update(FLAG_WRITES[pc])
            needed.update(FUNCTIONAL_FLAG_READS.get(pc, ()))
            if pc in DD_ZERO_REQUIRED:
                needed.add("DD")
            live_in[pc].update(needed)
    rows = []
    for pc, *_ in MAPPING:
        rows.append({"pc": pc,
                     "reachingWritersIn": {flag: sorted(before[pc][flag], key=str) for flag in FLAG_DOMAIN},
                     "reachingWritersOut": {flag: sorted(after[pc][flag], key=str) for flag in FLAG_DOMAIN},
                     "liveIn": [flag for flag in FLAG_DOMAIN if flag in live_in[pc]],
                     "liveOut": [flag for flag in FLAG_DOMAIN if flag in live_out[pc]],
                     "initialValueLive": {flag: "Initial" in before[pc][flag] and flag in live_in[pc]
                                          for flag in FLAG_DOMAIN},
                     "futureClobberPermitted": False,
                     "valueDeadWritesStillArchitectural": True})
    return rows


def expected_bundle():
    return {"classification": "IndependentStaticPrimaryAndInventedOracle",
            "mapping": expected_mapping(), "paths": expected_paths(),
            "ddBoth": expected_dd(), "dd0": expected_dd((0,)), "dd1": expected_dd((1,)),
            "flagDomain": list(FLAG_DOMAIN), "flags": expected_flags(),
            "pageMap": [{"address": address, "offset": offset} for address, offset in PAGE_MAP],
            "branchDistances": [{"pc": 0x557D, "target": 0x55BF, "difference": 64},
                                {"pc": 0x5585, "target": 0x5592, "difference": 10},
                                {"pc": 0x5588, "target": 0x5592, "difference": 7}],
            "entry": "NativeBasicBlockEntry", "exits": "StopBeforeNotRT",
            "aliasObligations": {"A": ["AL", "AH"], "er0": ["r0", "r1"],
                                 "r1WritesHighEr0Byte": True, "wholeEr0Preserved": False,
                                 "word0196": [0x0196, 0x0197]},
            "actualRomExecutions": 0, "generatedTargetBytes": 0}


def invented_algebra(state):
    """Closed equations on invented scalars; no PC loop, IR input, CPU or journal."""
    byte_names = ("RAM018E", "r0", "r1", "RAM0117", "RAM018F", "RAM012A", "RAM0124", "AH")
    if any(type(state[name]) is not int or not 0 <= state[name] < 256 for name in byte_names):
        raise ValueError("Invented byte domain")
    if type(state["RAM0196"]) is not int or not 0 <= state["RAM0196"] < 65536:
        raise ValueError("Invented word domain")
    if any(type(state[name]) is not int or state[name] not in (0, 1)
           for name in ("DD", "HC", "CF", "ZF")):
        raise ValueError("Invented flag domain")
    x, f, old117 = state["RAM018E"], state["RAM018F"], state["RAM0117"]
    q = (2 * x + x // 128) % 256
    mask = state["r0"] & q
    below = state["RAM0196"] < 192
    gate1 = state["RAM012A"] // 128 == 1
    gate2 = (state["RAM0124"] // 32) % 2 == 1
    path = "A" if below else "B" if gate1 else "C" if gate2 else "D"
    final_f = 15 if below else f if path in ("B", "C") else f & mask
    final_al = 15 if below else final_f | 240
    return {"path": path, "AL": final_al, "AH": state["AH"],
            "CF": int(below), "ZF": 0, "HC": state["HC"], "DD": 0,
            "OtherPSW": state["OtherPSW"], "RAM018E": q,
            "RAM0117": 15 if below else old117 & mask, "RAM018F": final_f,
            "RAM012A": state["RAM012A"] | (1 if path == "D" else 0),
            "r1": state["r1"] if below else old117}
