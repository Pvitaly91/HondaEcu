"""M2br private draft: expected real PROGRAM callback topology, not ISA rules.

The immutable decoder source has exactly one 03 and one 77 first-byte candidate.
Its first-byte probe is repeated by that candidate, then the production audit
acquires the selected extent. No invented callback is inserted into observations.
Stage metadata is a separate parallel journal: old ProgramEvent objects remain
complete, with only their true global ordinal and per-segment offset.
"""

from copy import deepcopy
from production_transfer_common import bq_modules, binding, require, segment_identities

DECODER_SHA = "4fb9a08edf9f06724fd45a1e0959c1d505c303b161ff691e3b97c9eedc9f7288"
TABLE_SHA = "77697d4b0e3c90372326156bf1a8544486d07f4aa8f93c67cf9e5f2af6c7eff1"
SCHEMA = {"classification": "ExpectedSourceBoundRealProgramCallbacks_NotManufacturerTiming",
          "globalOrdinals": "ZeroBasedCumulativeAcrossOneCpuBusSession",
          "attribution": "ParallelAtAcquisition_ExistingProgramEventFieldsNeverReclassified",
          "selectedExtent": "ExactCurrentAdmittedSegmentOnly",
          "callerProbeOffsets": [0, 0, 1, 2], "callerSelectedOffsets": [0, 1, 2],
          "continuationProbeOffsets": [0, 0, 1], "continuationSelectedOffsets": [0, 1],
          "positiveGapPendingOrPostCheckpointProgramAttempts": 0,
          "programByteValuesInJournal": False, "persistentFullPayload": False}


def source_bindings(root):
    result = []
    for name, digest in (("decoder.rs", DECODER_SHA), ("full_decoder.rs", TABLE_SHA)):
        row = binding(root, "rust/p28-slice-runner/src/" + name)
        require(row["sha256"] == digest, "UnchangedDecoderObservationAuthority:" + name)
        result.append(row)
    return result


def tiny_events(role, global_start):
    require(role in ("Caller", "ContinuationBelow", "ContinuationNotBelow")
            and type(global_start) is int and global_start >= 0, "ClosedTinyProgramTopology")
    segment = next(row for row in segment_identities() if row["role"] == role)
    length, base = segment["length"], segment["base"]
    result = []
    for purpose, offsets in (("DecoderProbe", [0] + list(range(length))),
                             ("ArchitecturalSelectedFetch", range(length))):
        for offset in offsets:
            result.append({"ordinal": global_start + len(result), "pc": base, "address": base + offset,
                           "segment_offset": offset, "instruction_offset": offset,
                           "acquired_purpose": purpose,
                           "selection_association": "SelectedExtent" if purpose == "DecoderProbe" else None,
                           "selected_length": length, "serviced": True, "refusal": None})
    require(len(result) == (7 if role == "Caller" else 5), "ClosedTinyCallbackCount")
    return result


def expected_program_components(root, reference):
    source_bindings(root)
    with bq_modules(root) as modules:
        old, old_spans = modules["production_composite_topology"].expected_program_events(root, reference)
    caller = tiny_events("Caller", 0)
    composite = deepcopy(old)
    for event in composite:
        event["ordinal"] += len(caller)
    composite_spans = [[start + len(caller), end + len(caller)] for start, end in old_spans]
    continuation_role = "ContinuationBelow" if reference["path"] == "A" else "ContinuationNotBelow"
    continuation = tiny_events(continuation_role, len(caller) + len(composite))
    events = caller + composite + continuation
    spans = [[0, len(caller)]] + composite_spans + [[len(caller) + len(composite), len(events)]]
    stages = ["Caller"] + ["Composite"] * len(old_spans) + [continuation_role]
    stage_events = []
    stage_begin = {"Caller": 0, "Composite": len(caller), continuation_role: len(caller) + len(composite)}
    for absolute_step, (stage, span) in enumerate(zip(stages, spans), 1):
        stage_step = absolute_step - 1 if stage == "Composite" else 1
        for ordinal in range(*span):
            stage_events.append({"program_ordinal": ordinal, "stage": stage,
                                 "stage_program_ordinal": ordinal - stage_begin[stage],
                                 "global_instruction_ordinal": absolute_step,
                                 "stage_instruction_ordinal": stage_step})
    require(len(events) == len(stage_events) and all(row["ordinal"] == index for index, row in enumerate(events)),
            "EveryActualCallbackHasOneContiguousStageAttribution")
    return {"events": events, "stage_events": stage_events, "step_spans": spans,
            "stage_spans": {"Caller": [0, len(caller)],
                            "Composite": [len(caller), len(caller) + len(composite)],
                            continuation_role: [len(caller) + len(composite), len(events)]},
            "historical_m2bq_events": old, "historical_m2bq_step_spans": old_spans}
