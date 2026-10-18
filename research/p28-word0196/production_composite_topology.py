"""M2bq source draft: independent PROGRAM-observation protocol expectations.

This is deliberately separate from manufacturer instruction semantics. The
immutable M2bn model obtains candidate order from the frozen decoder table and
bytes from the independent primary oracle. Its events are EXPECTED callbacks,
never observations. Production must acquire its own callbacks from the real
Bus. No target byte values are returned or persisted here.
"""

from functools import lru_cache
from production_composite_common import binding, reference_modules, require

DECODER_SHA = "4fb9a08edf9f06724fd45a1e0959c1d505c303b161ff691e3b97c9eedc9f7288"
TABLE_SHA = "77697d4b0e3c90372326156bf1a8544486d07f4aa8f93c67cf9e5f2af6c7eff1"
SCHEMA = {"classification": "ExpectedProductionProgramCallbackTopology_NotInstructionSemantics",
          "acquisition": "UnchangedProductionStrictDecoderCandidateOrder_ThenExactSelectedExtent",
          "association": "OnlyCurrentStepDecoderProbeSpan_PreviousEventsImmutable",
          "ordinalBase": 0, "spans": "GlobalHalfOpenEventIndexRanges",
          "forbidden": ["SyntheticCallbackInsertedInActualJournal", "FetchAfterTerminalJ",
                        "ProgramPayloadSerialization", "PostMismatchFieldExclusion"]}


def source_bindings(root):
    result = []
    for name, digest in (("decoder.rs", DECODER_SHA), ("full_decoder.rs", TABLE_SHA)):
        row = binding(root, "rust/p28-slice-runner/src/" + name)
        require(row["sha256"] == digest, "UnchangedDecoderTopologySource:" + name)
        result.append(row)
    return result


@lru_cache(maxsize=2)
def _patterns(root):
    source_bindings(root)
    with reference_modules(root) as modules:
        return modules["synthetic_composite_execution_oracle"].load_instrumentation_patterns(root)


def expected_program_events(root, reference_result):
    with reference_modules(root) as modules:
        model = modules["synthetic_composite_execution_oracle"]
        patterns = _patterns(str(root))
        expected = model._program_events(reference_result, patterns)
    events, spans = [], []
    for step in range(1, len(reference_result["trace"]) + 1):
        start = len(events)
        for event in expected:
            if event["step"] != step:
                continue
            purpose = event["acquired_purpose"]
            require(purpose in ("DecoderProbe", "ArchitecturalSelectedFetch"), "ClosedProgramPurpose")
            length = event["selected_extent_length"]
            association = ("SelectedExtent" if event["instruction_offset"] < length else "DecoderLookahead") \
                if purpose == "DecoderProbe" else None
            events.append({"ordinal": len(events), "pc": event["pc"], "address": event["address"],
                           "segment_offset": event["offset"], "instruction_offset": event["instruction_offset"],
                           "acquired_purpose": purpose, "selection_association": association,
                           "selected_length": length, "serviced": True, "refusal": None})
        spans.append([start, len(events)])
        require(spans[-1][0] < spans[-1][1], "ActualInstructionMustAcquireProgramBytes")
    require(len(events) == len(expected), "EveryExpectedProgramEventAssignedExactlyOnce")
    return events, spans


def verify_step_span_prefix(prior, current, span):
    """Useful strict actual-observation check; never fills a missing callback."""
    require(type(span) is list and len(span) == 2 and all(type(v) is int for v in span),
            "ClosedProgramSpan")
    require(span[0] == len(prior) and span[1] == len(current), "ContiguousGlobalProgramSpan")
    require(current[:len(prior)] == prior, "PriorStepProgramEventMutation")
    return True
