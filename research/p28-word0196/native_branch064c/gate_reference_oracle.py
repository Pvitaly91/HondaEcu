"""Independent declarative M2ca invented route/outcome oracle.

No import from gate_model or production sources; no decoder/CPU/ROM/file API.
The route is selected directly from the four specified Boolean predicates.
Per-PC states below are formula-derived expected values, not observations.
"""
from copy import deepcopy


def reference_outcome(vector):
    data = vector["gate_bytes"]
    f, b, a = data["011F"], data["011B"], data["012A"]
    psw = vector["retained"]["psw"]
    first, second, low, high = bool(f & 8), bool(b & 128), bool(a & 1), bool(a & 8)
    if first and high:
        route, sequence, terminal, budget = "PrimaryTakenSkipCAL", [0x064C, 0x065F, 0x0662], 0x0667, 52
    elif not first and second and not high:
        route, sequence, terminal, budget = "FallthroughDirectToCALBoundary", [0x064C, 0x064F, 0x065F, 0x0662], 0x0664, 53
    elif not first and not second and not low and not high:
        route, sequence, terminal, budget = "FallthroughVia012A0", [0x064C, 0x064F, 0x0652, 0x0655, 0x065F, 0x0662], 0x0664, 55
    elif not first and not second and low:
        route, sequence, terminal, budget = "FallthroughToTRNSITBoundary", [0x064C, 0x064F, 0x0652, 0x0655], 0x0657, 53
    else:
        raise ValueError("OutsideFourDeclarativeConditionalPredicates")
    forms = {
        0x064C: ("JBS off011F.3,rel8", 3), 0x064F: ("JBS off011B.7,rel8", 3),
        0x0652: ("RB off012A.0", 3), 0x0655: ("JEQ rel8", 2),
        0x065F: ("RB off012A.3", 3), 0x0662: ("JNE rel8", 2)}
    # Formula tables describe a route selected above; no PC dispatch or branch
    # execution engine is used. RB0 cannot change oldbit3; RB3 preserves bit0.
    zf_after_low = (psw & 0xBFFF) | (0 if low else 0x4000)
    zf_after_high = (psw & 0xBFFF) | (0 if high else 0x4000)
    states = {}
    for position, pc in enumerate(sequence):
        earlier = sequence[:position]
        psw_before = zf_after_high if 0x065F in earlier else zf_after_low if 0x0652 in earlier else psw
        byte_before = a & (~1 if 0x0652 in earlier else 255) & (~8 if 0x065F in earlier else 255)
        psw_after = zf_after_low if pc == 0x0652 else zf_after_high if pc == 0x065F else psw_before
        byte_after = byte_before & (254 if pc == 0x0652 else 247 if pc == 0x065F else 255)
        next_pc = sequence[position + 1] if position + 1 < len(sequence) else terminal
        before_data, after_data = dict(data), dict(data)
        before_data["012A"], after_data["012A"] = byte_before, byte_after
        before = {"pc": pc, **deepcopy(vector["retained"]), "psw": psw_before, "data": before_data}
        after = {"pc": next_pc, **deepcopy(vector["retained"]), "psw": psw_after, "data": after_data}
        reads, writes, decision = [], [], None
        if pc == 0x064C:
            reads = [{"operation": "Read", "address": 0x011F, "width": 8, "value": f}]
            decision = first
        elif pc == 0x064F:
            reads = [{"operation": "Read", "address": 0x011B, "width": 8, "value": b}]
            decision = second
        elif pc in (0x0652, 0x065F):
            reads = [{"operation": "Read", "address": 0x012A, "width": 8, "value": byte_before}]
            writes = [{"operation": "Write", "address": 0x012A, "width": 8,
                "old_value": byte_before, "value": byte_after, "same_value": byte_before == byte_after,
                "source": "InventedPrimarySemanticExpectedWrite_NotObservedGeneration"}]
        elif pc == 0x0655:
            decision = not low
        elif pc == 0x0662:
            decision = high
        states[pc] = {"expected_index": position + 1, "pc": pc, "form": forms[pc][0],
            "length": forms[pc][1], "before": before, "after": after,
            "branch_taken": decision, "expected_reads": reads, "expected_writes": writes}
    final_psw = zf_after_high if 0x065F in sequence else zf_after_low
    final_data = dict(data)
    final_data["012A"] = a & (~1 if 0x0652 in sequence else 255) & (~8 if 0x065F in sequence else 255)
    return {"classification": "PrimarySemanticStaticExpectedTrace_NotRuntimeObservation",
        "case_id": vector["case_id"], "route_class": route,
        "prefix_retirements_reference_only": 49, "expected_gate_instructions": len(sequence),
        "expected_full_route_retirements": budget, "expected_pc_sequence": sequence,
        "expected_terminal_pc": terminal, "expected_steps": [states[pc] for pc in sequence],
        "expected_final_state": {"pc": terminal, **deepcopy(vector["retained"]), "psw": final_psw, "data": final_data},
        "excluded_instruction_retirements": [],
        "effect_scope": "StaticArchitecturalEffects_NotProductionLogicalRawJournal",
        "cpu_executions": 0, "rom_executions": 0, "original_rom_route_admitted": False}
