"""Invented-only M2ca primary-semantic expectations; never a CPU executor.

No PROGRAM bytes, ROM reader, Bus, production module, process, clock, hardware
or filesystem access exists here. Effects are static architectural obligations,
not observed production logical/raw journals. Original-ROM admission stays
blocked by the separately described M2bz011F/011B provenance gap.
"""
from copy import deepcopy
from hashlib import sha256


INVENTED = "InventedOnly_NotNativeRuntimeOrCurrentM2bzState"
STATIC = "InventedStaticGateReview_NoCpuOrRomExecution"
UNOWNED = "UnownedTechnicalBusCanary_NotBranchAuthority"
ZF_MASK = 0x4000
STOP_PCS = (0x0657, 0x0664, 0x0667)
ROM_IDENTITY_SENTINEL = sha256(b"M2ca invented identity sentinel; not ROM bytes").hexdigest()
SOURCE_IDENTITY_SENTINEL = sha256(b"M2ca invented source sentinel; not current source fingerprint").hexdigest()
VECTOR_FIELDS = {"classification", "case_id", "gate_bytes", "retained"}
RETAINED_FIELDS = {"a", "psw", "lrb", "scb", "ssp", "pointing", "local_r"}
FORM_CONTRACT = [
    {"pc": 0x064C, "form": "JBS off011F.3,rel8", "length": 3,
     "reader_address": 0x011F, "bit": 3, "taken": 0x065F, "fallthrough": 0x064F},
    {"pc": 0x064F, "form": "JBS off011B.7,rel8", "length": 3,
     "reader_address": 0x011B, "bit": 7, "taken": 0x065F, "fallthrough": 0x0652},
    {"pc": 0x0652, "form": "RB off012A.0", "length": 3,
     "reader_address": 0x012A, "bit": 0, "taken": None, "fallthrough": 0x0655},
    {"pc": 0x0655, "form": "JEQ rel8", "length": 2,
     "reader_address": None, "bit": None, "taken": 0x065F, "fallthrough": 0x0657},
    {"pc": 0x065F, "form": "RB off012A.3", "length": 3,
     "reader_address": 0x012A, "bit": 3, "taken": None, "fallthrough": 0x0662},
    {"pc": 0x0662, "form": "JNE rel8", "length": 2,
     "reader_address": None, "bit": None, "taken": 0x0667, "fallthrough": 0x0664},
]


class StaticReviewRefusal(ValueError):
    """A static fixture/refusal result, never a production execution fault."""


def require(condition, reason):
    if condition is not True:
        raise StaticReviewRefusal(reason)


def validate_vector(vector):
    require(type(vector) is dict and set(vector) == VECTOR_FIELDS, "ClosedInventedVectorRequired")
    require(vector["classification"] == INVENTED and type(vector["case_id"]) is str
            and vector["case_id"].startswith("invented-m2ca-") and len(vector["case_id"]) <= 80,
            "ExplicitInventedOnlyVectorRequired")
    data, retained = vector["gate_bytes"], vector["retained"]
    require(type(data) is dict and set(data) == {"011F", "011B", "012A"}
            and all(type(value) is int and 0 <= value <= 255 for value in data.values()),
            "ThreeInventedBytesOnly_NotCurrentM2bzAdmission")
    require(type(retained) is dict and set(retained) == RETAINED_FIELDS,
            "ClosedInventedRetainedStateRequired")
    require(all(type(retained[key]) is int and 0 <= retained[key] <= 65535
                for key in ("a", "psw", "ssp")) and retained["lrb"] == 0x0021
            and type(retained["lrb"]) is int and type(retained["scb"]) is int
            and retained["scb"] == retained["psw"] & 7,
            "InventedLrbAndPswScbRelationRequired")
    require(type(retained["pointing"]) is list and len(retained["pointing"]) == 4
            and all(type(value) is int and 0 <= value <= 65535 for value in retained["pointing"])
            and type(retained["local_r"]) is list and len(retained["local_r"]) == 8
            and all(type(value) is int and 0 <= value <= 255 for value in retained["local_r"]),
            "InventedRetainedRegisterValuesRequired")
    return True


def _state(vector, pc, psw, data):
    return {"pc": pc, **deepcopy(vector["retained"]), "psw": psw, "data": deepcopy(data)}


def _read(address, value):
    return {"operation": "Read", "address": address, "width": 8, "value": value}


def _write(address, old, value):
    return {"operation": "Write", "address": address, "width": 8,
            "old_value": old, "value": value, "same_value": old == value,
            "source": "InventedPrimarySemanticExpectedWrite_NotObservedGeneration"}


def primary_expected_trace(vector):
    """Six reviewed static forms only; no opcode decoding or machine stepping."""
    validate_vector(vector)
    data = deepcopy(vector["gate_bytes"])
    psw, pc, steps = vector["retained"]["psw"], 0x064C, []
    contracts = {row["pc"]: row for row in FORM_CONTRACT}
    for index in range(6):
        require(pc in contracts, "StaticExpectedPcOutsideSixReviewedForms")
        form = contracts[pc]
        before, reads, writes, decision = _state(vector, pc, psw, data), [], [], None
        if pc in (0x064C, 0x064F):
            key, bit = ("011F", 3) if pc == 0x064C else ("011B", 7)
            old = data[key]
            reads.append(_read(int(key, 16), old))
            decision = bool(old & (1 << bit))
            next_pc = form["taken"] if decision else form["fallthrough"]
        elif pc in (0x0652, 0x065F):
            bit = 0 if pc == 0x0652 else 3
            old = data["012A"]
            reads.append(_read(0x012A, old))
            psw = (psw & ~ZF_MASK) | (ZF_MASK if old & (1 << bit) == 0 else 0)
            data["012A"] = old & ~(1 << bit)
            writes.append(_write(0x012A, old, data["012A"]))
            next_pc = form["fallthrough"]
        elif pc == 0x0655:
            decision = bool(psw & ZF_MASK)
            next_pc = 0x065F if decision else 0x0657
        else:
            require(pc == 0x0662, "OnlyReviewedJneMayRemain")
            decision = not bool(psw & ZF_MASK)
            next_pc = 0x0667 if decision else 0x0664
        steps.append({"expected_index": index + 1, "pc": pc, "form": form["form"],
            "length": form["length"], "before": before,
            "after": _state(vector, next_pc, psw, data), "branch_taken": decision,
            "expected_reads": reads, "expected_writes": writes})
        pc = next_pc
        if pc in STOP_PCS:
            break
    require(pc in STOP_PCS, "BoundedStaticReferenceMustStopWithinSixInstructions")
    sequence = tuple(step["pc"] for step in steps)
    paths = {
        (0x064C, 0x065F, 0x0662): ("PrimaryTakenSkipCAL", 0x0667, 52),
        (0x064C, 0x064F, 0x065F, 0x0662): ("FallthroughDirectToCALBoundary", 0x0664, 53),
        (0x064C, 0x064F, 0x0652, 0x0655, 0x065F, 0x0662): ("FallthroughVia012A0", 0x0664, 55),
        (0x064C, 0x064F, 0x0652, 0x0655): ("FallthroughToTRNSITBoundary", 0x0657, 53),
    }
    require(sequence in paths, "InventedVectorOutsideFourReviewedConditionalClasses")
    route, terminal, budget = paths[sequence]
    require(pc == terminal and budget == 49 + len(steps),
            "ConditionalPathPredicateAndTerminalMustAgree")
    return {"classification": "PrimarySemanticStaticExpectedTrace_NotRuntimeObservation",
        "case_id": vector["case_id"], "route_class": route,
        "prefix_retirements_reference_only": 49, "expected_gate_instructions": len(steps),
        "expected_full_route_retirements": budget, "expected_pc_sequence": list(sequence),
        "expected_terminal_pc": terminal, "expected_steps": steps,
        "expected_final_state": _state(vector, pc, psw, data),
        "excluded_instruction_retirements": [],
        "effect_scope": "StaticArchitecturalEffects_NotProductionLogicalRawJournal",
        "cpu_executions": 0, "rom_executions": 0, "original_rom_route_admitted": False}


def current_source_admission_obligations():
    """A fixed source-domain constraint, not a recovered live RAM snapshot."""
    return {"classification": "M2bzSourceDomainConstraint_NotRuntimeStateTransfer",
        "sources": {
            "011F": {"width": 8, "reader_pc": 0x064C, "bit": 3,
                "classification": UNOWNED, "generation": None, "new_seed_allowed": False},
            "011B": {"width": 8, "reader_pc": 0x064F, "bit": 7,
                "classification": UNOWNED, "generation": None, "new_seed_allowed": False},
            "012A": {"width": 8, "reader_pcs": [0x0652, 0x065F], "bits": [0, 3],
                "classification": "ExistingAuthorizedTechnicalSource",
                "generation": "Fresh5685ByteWriteRequiredIfPrefixRuns_NotImportedHere",
                "native_input_owner_established": False, "new_seed_allowed": False}},
        "historical_source_transfers": [], "new_source_inputs": [],
        "original_rom_routes_admitted": [], "first_blocked_reader_pc": 0x064C,
        "unowned_a5_may_select_branch": False}


def build_review_envelope(vector):
    """Make an explicitly invented static comparison fixture, with no authority."""
    return {"schemaVersion": 1, "milestone": "M2ca", "classification": STATIC,
        "vector": deepcopy(vector), "expected_trace": primary_expected_trace(vector),
        "instruction_contract": deepcopy(FORM_CONTRACT),
        "expected_bindings": {
            "rom": {"classification": "InventedIdentitySentinel_NotOriginalRomVerification",
                    "sha256": ROM_IDENTITY_SENTINEL},
            "source": {"classification": "InventedIdentitySentinel_NotCurrentSourceFingerprint",
                       "sha256": SOURCE_IDENTITY_SENTINEL}},
        "source_admission": current_source_admission_obligations(),
        "runtime_authority": {"entry_mode": "StaticExpectationOnly_NoHostCpuEntry",
            "cpu_instances": 0, "bus_instances": 0, "host_reseed_events": [],
            "producer56be_entries": 0, "observed_peripherals": [],
            "original_rom_executions": 0, "firmware_ready": False},
        "retained_frame_identity": {"classification": "InventedReference_NotActualCallFrame",
            "writer_pc": 0x063B, "consumer_pc": 0x5688, "return_pc": 0x063E,
            "consumed_before_gates": True},
        "retained_selector_identity": {"classification": "InventedReference_NotActualSelectorGeneration",
            "writer_pc": 0x064A, "retirement": 49, "generation": 1},
        "analysis_case_ids": [vector["case_id"]],
        "cargo_authority": {"builds_allowed": False, "owned_target_token": "M2caOwnedTargetOnly",
            "historical_output_allowed": False},
        "proof_kind": "FabricatedStaticExpectedTraceAndMetadataRefusal_NotCpuRefusal"}


def _exact_equal(left, right):
    if type(left) is not type(right):
        return False
    if type(left) is dict:
        return set(left) == set(right) and all(_exact_equal(left[key], right[key]) for key in left)
    if type(left) is list:
        return len(left) == len(right) and all(_exact_equal(a, b) for a, b in zip(left, right))
    return left == right


def validate_review_envelope(value):
    require(type(value) is dict and type(value.get("vector")) is dict, "StaticReviewObjectRequired")
    expected = build_review_envelope(value["vector"])
    # Exact comparison keeps unknown keys, flags, source claims and same-value
    # writes in scope. It grants no production admission or runtime observation.
    require(_exact_equal(value, expected), "ClosedStaticExpectationOrAuthorityMismatch")
    return {"passed": True, "classification": STATIC, "cpu_executions": 0,
            "original_rom_executions": 0, "runtime_admission_granted": False}
