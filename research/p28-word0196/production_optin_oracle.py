"""Independent expectations, produced before new production observations.

ISA effects: immutable primary/M2bk/M2av-derived M2bo reference, reproduced
against all51 sealed literals. New event topology: separately source-bound
observation protocol model, NOT manufacturer semantics or runtime evidence.
No Rust Cpu, decoder or executor is called by this module.
"""
from copy import deepcopy
from hashlib import sha256

import production_exec_parity_oracle as source_reference
import synthetic_composite_execution_oracle as instrumentation
import production_optin_corpus as corpus

PROJECTION = {
    "classification": "CompleteDeclaredActualProductionOptInObservation",
    "platformExclusions": [], "removedRuntimeFields": [],
    "comparison": "ExactTypes_ExactKeys_OrderedArrays_AllFields",
    "program": "ActualBusDecoderCallbacksAndSeparateSelectedReads_NoBytesSerialized",
    "data": "ActualBusLogicalCallsAndRawConstituents_SeedFunctionalDiagnosticSeparated",
    "state": "EveryCpuFieldAndAll3968RamBytesBeforeAfter",
    "instructionSemanticsOracle": "ImmutablePrimary_M2bk_M2av_M2boReference",
    "journalTopologyOracle": "SeparatelyFrozenBusAndDecoderObservationProtocolModel_NotISAOracle",
    "noFullProductionComposite": True,
}


def difference(expected, actual, path="$"):
    return source_reference._difference(expected, actual, path)


def permissions(profile, form):
    reads = [{"address": a, "width": w} for a, w in sorted(corpus.READS[profile])]
    writes = [{"access": {"address": a, "width": 8},
               "rmw_required": form in corpus.RMW_FORMS} for a in sorted(corpus.WRITES[profile])]
    raw_reads = sorted({row["address"] + delta for row in reads for delta in range(row["width"] // 8)})
    raw_writes = sorted({row["access"]["address"] for row in writes})
    return {"reads": reads, "writes": writes, "raw_reads": raw_reads, "raw_writes": raw_writes}


def callback_offsets(request, patterns):
    """Frozen matcher acquisition topology; no instruction state/effects."""
    data, dd = request["bytes"] + request["guards"], request["entry"]["dd"]
    fixed = lambda token: len(token) == 2 and all(c in "0123456789abcdefABCDEF" for c in token)
    candidates = [(index, row) for index, row in enumerate(patterns)
                  if row[1] and fixed(row[1][0]) and int(row[1][0], 16) == data[0]]
    candidates.sort(key=lambda item: (-sum(fixed(token) for token in item[1][1]), -len(item[1][1])))
    offsets = [0]
    selected = None
    for index, (_, tokens, mode) in candidates:
        if mode == "1" and not dd or mode == "0" and dd:
            continue
        for offset, token in enumerate(tokens):
            offsets.append(offset)
            if offset >= len(data):
                raise ValueError("IndependentStrictDecoderProbeOutsideSegment")
            if fixed(token) and int(token, 16) != data[offset]:
                break
        else:
            selected = index
            break
    if selected != request["expected_decoded_index"]:
        raise ValueError("IndependentMatcherIdentityDisagreement")
    return offsets


def program_events(request, patterns):
    length = request["expected_length"]
    events = []
    for purpose, offsets in (("DecoderProbe", callback_offsets(request, patterns)),
                             ("ArchitecturalSelectedFetch", range(length))):
        for offset in offsets:
            events.append({"ordinal": len(events), "pc": 4096, "address": 4096 + offset,
                           "segment_offset": offset, "instruction_offset": offset,
                           "acquired_purpose": purpose,
                           "selection_association": ("SelectedExtent" if offset < length else "DecoderLookahead")
                           if purpose == "DecoderProbe" else None,
                           "selected_length": length, "serviced": True, "refusal": None})
    return events


class ExpectedDataProtocol:
    """Only expected Bus events; never exported as actual observations."""
    def __init__(self, request):
        self.memory = {address: 0xa5 for address in range(0x80, 0x1000)}
        self.logical = []
        self.raw = []
        self.write_ordinal = 0
        self.raw_write_ordinal = 0
        self.diagnostics = []
        self.request = request

    def event(self, address, width, operation, value=None, phase="Functional", index=None):
        ordinal = len(self.logical)
        old = sum(self.memory[address + delta] << (8 * delta) for delta in range(width // 8))
        write = operation == "Write"
        observed = value if write else old
        self.logical.append({"ordinal": ordinal, "phase": phase, "pc": 4096,
                             "instruction_index": index, "address": address, "width": width,
                             "operation": operation, "requested_value": value if write else None,
                             "value": observed, "old_value": old if write else None,
                             "write_ordinal": self.write_ordinal if write else None,
                             "same_value": old == value if write else None,
                             "serviced": True, "refusal": None})
        if write:
            self.write_ordinal += 1
        for delta in range(width // 8):
            raw_address = address + delta
            raw_old = self.memory[raw_address]
            raw_value = (observed >> (8 * delta)) & 255
            self.raw.append({"ordinal": len(self.raw), "logical_ordinal": ordinal,
                             "address": raw_address, "operation": operation,
                             "requested_value": raw_value if write else None,
                             "value": raw_value, "old_value": raw_old if write else None,
                             "write_ordinal": self.raw_write_ordinal if write else None,
                             "same_value": raw_old == raw_value if write else None,
                             "serviced": True, "refusal": None})
            if write:
                self.raw_write_ordinal += 1
                self.memory[raw_address] = raw_value
        return observed

    def seed(self):
        for address, value in sorted(self.request["data"].items(), key=lambda pair: int(pair[0])):
            self.event(int(address), 8, "Write", value, "Seed")
        for bank, row in enumerate(self.request["entry"]["pointing_banks"]):
            for slot, name in enumerate(("x1", "x2", "dp", "usp")):
                self.event(0x80 + bank * 8 + slot * 2, 16, "Write", row[name], "Seed")

    def snapshot(self):
        self.diagnostics.append({"ordinal": len(self.diagnostics), "kind": "RawRamSnapshot",
                                 "range": [0x80, 0x1000], "byte_count": 3968})
        return [self.memory[address] for address in range(0x80, 0x1000)]


def expected_case(item, patterns):
    if item["expected_admission"] != "Accepted":
        return {"kind": "admission_refusal", "case_id": item["request"]["case_id"],
                "accepted": False,
                "error": {"code": "StricterPermissionContextIncompatible",
                          "detail": "unchanged M2bo microcontext outside its predicate-derived permissions"},
                "cpu_instances": 0, "bus_instances": 0, "actual_step_calls": 0}
    request = item["request"]
    reference_input = deepcopy(request)
    reference_input["physical_entry_pc"] = 4096
    result = source_reference.reference_effect(reference_input)
    data = ExpectedDataProtocol(request)
    data.seed()
    before_ram = data.snapshot()
    index = request["expected_decoded_index"]
    for address, width, *_ in result["reads"]:
        data.event(int(address, 16), width, "Read", index=index)
    for address, _old, value, *_ in result["writes"]:
        data.event(int(address, 16), 8, "Write", int(value, 16), index=index)
    after_ram = data.snapshot()
    assert before_ram == source_reference.expected_ram(request)
    assert after_ram == source_reference.expected_ram(request, result["after_data"])
    decoded = {key: value for key, value in result["decode"].items() if key != "form"}
    after_pc = result["after"]["pc"]
    external = after_pc if request["form"] == "j-address" else None
    cpu_before = source_reference.raw_cpu(result["before"], request["internal_sf"])
    cpu_after = source_reference.raw_cpu(result["after"], request["internal_sf"], result["cycles"], 1)
    audit = {"entry_pc": 4096, "current_pc": after_pc,
             "program_base": 4096, "program_end_exclusive": 4102,
             "program_sha256": request["content_digest"],
             "program_events": program_events(request, patterns), "data_events": data.logical,
             "raw_data_events": data.raw, "diagnostic_events": data.diagnostics,
             "data_admission_refusals": [],
             "permissions": permissions(item["profile"], request["form"]),
             "phase": "Sealed", "budget": 1, "successful_retirements": 1,
             "step_calls": 1, "execution_calls": 1, "shared_execution_calls": 1,
             "sealed": True, "terminal_reason": "ActualDirectJCompleted" if external is not None else "OneStepComplete",
             "external_exit": external, "first_fault": None}
    outcome = {"pc_before": 4096, "pc_after": after_pc, "decoded_index": index,
               "mnemonic": decoded["mnemonic"], "len": decoded["len"], "decoded": decoded,
               "selected_extent": [4096, 4096 + decoded["len"]],
               "selected_extent_sha256": sha256(bytes(request["bytes"])).hexdigest(),
               "retired": True, "external_exit": external}
    return {"kind": "optin_observation", "accepted": True,
            "case_id": request["case_id"], "source_case_id": item["source_case_id"],
            "source_family": item["source_family"], "family": request["family"],
            "form": request["form"], "permission_profile": item["profile"],
            "provenance": request["entry"]["provenance"],
            "physical_entry_pc": 4096, "logical_entry_pc": 4096,
            "historical_physical_pc_metadata": request["physical_entry_pc"], "pc_relocated": False,
            "before": {"cpu": cpu_before, "ram": before_ram, "ram_range": [128, 4096]},
            "after": {"cpu": cpu_after, "ram": after_ram, "ram_range": [128, 4096]},
            "outcome": outcome, "error": None, "audit": audit,
            "actual_step_calls": 1, "cpu_instances": 1, "bus_instances": 1,
            "scope": "ClosedInventedSingleStep_NotCompositePathReachability",
            "full_production_composite_executions": 0, "original_rom_executions": 0,
            "firmware_ready": False}


def reproduce_historical_literals():
    # This immutable function independently reproduces all51 historical literal
    # states/effects, not only their best-candidate count or one terminal flag.
    return source_reference.reproduce_sealed_literals()
