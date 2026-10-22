"""Read-only reconciliation of selected, already recorded M2z source-CPU data.

No original-ROM instruction, emulator, reference model, replay or subprocess is
executed.  A private caller supplies three independently reviewed source bindings.
The adapter rereads those exact bytes, joins three original-A observations to the
old sealed independent C# proof, and reconciles recorded steps and DATA journals.
New in-memory attestations are explicitly *current reader outputs*, never claimed
to be historical files or a new independent C# execution.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
from typing import Any, Mapping

from .context import (
    ContextError, SelectedSource, build_context_matrix, select_source,
    verify_data0196_lineage,
)


class HistoricalError(ContextError):
    """Selected historical bytes or an actual observation relation did not match."""


_GENERATION_KEYS = {"writerPc", "eventIndex", "writeOrder", "value"}
_SNAPSHOT_KEYS = {"pc", "accumulator", "psw", "dd", "lrb", "x1", "x2", "dp", "usp", "ssp", "registers"}
_COMMON = (0x556F, 0x5571, 0x5572, 0x5575, 0x5576, 0x5578, 0x557D)
_PATHS = {
    "A": _COMMON + (0x55BF, 0x55C1, 0x55C3),
    "B": _COMMON + (0x557F, 0x5582, 0x5585, 0x5592, 0x5594),
    "D": _COMMON + (0x557F, 0x5582, 0x5585, 0x5588, 0x558B, 0x558E, 0x5592, 0x5594),
}
_WRITERS = {
    "A": ((0x5572, 0x018E), (0x55C1, 0x0117), (0x55C3, 0x018F)),
    "B": ((0x5572, 0x018E), (0x557F, 0x0109), (0x5582, 0x0117)),
    "D": ((0x5572, 0x018E), (0x557F, 0x0109), (0x5582, 0x0117),
          (0x558B, 0x018F), (0x558E, 0x012A)),
}
_FORMS = {
    0x54F5: "JBR off N8.2, rel8", 0x54F8: "MOVB r0, #N8", 0x54FA: "L A, off N8",
    0x54FC: "ST A, er1", 0x54FD: "CMPB off N'8, #N8", 0x5501: "JNE rel8",
    0x556F: "LB A, off N8", 0x5571: "SLLB A", 0x5572: "ROLB off N8", 0x5575: "LB A, r0",
    0x5576: "ANDB A, off N8", 0x5578: "CMP off N8, #N16", 0x557D: "JLT rel8",
    0x557F: "MOVB r1, off N8", 0x5582: "ANDB off N8, A", 0x5585: "JBS off N8.7, rel8",
    0x5588: "JBS off N8.5, rel8", 0x558B: "ANDB off N8, A", 0x558E: "ORB off N'8, #N8",
    0x5592: "LB A, off N8", 0x5594: "ORB A, #N8", 0x55BF: "LB A, #N8",
    0x55C1: "STB A, off N8", 0x55C3: "STB A, off N8",
}


def _require(condition: bool, reason: str) -> None:
    if not condition:
        raise HistoricalError(reason)


def _integer(value: Any, low: int = 0, high: int = 0xFFFF) -> None:
    _require(type(value) is int and low <= value <= high, "historical integer domain mismatch")


def _closed(value: Any, keys: set[str], reason: str) -> None:
    _require(isinstance(value, Mapping) and set(value) == keys, reason)


def _derived_source(source_id: str, kind: str, document: Any) -> SelectedSource:
    """Identity of an explicitly new current in-memory projection, not an old file."""
    payload = json.dumps(document, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return SelectedSource(source_id, kind, hashlib.sha256(payload).hexdigest(), len(payload), document,
                          "DerivedInMemory_NotHistoricalFile")


def _snapshot(snapshot: Any) -> None:
    _closed(snapshot, _SNAPSHOT_KEYS, "historical snapshot schema mismatch")
    for key in _SNAPSHOT_KEYS - {"dd", "registers"}:
        _integer(snapshot[key])
    _require(type(snapshot["dd"]) is bool and snapshot["dd"] == bool(snapshot["psw"] & 0x1000),
             "historical DD/PSW snapshot mismatch")
    registers = snapshot["registers"]
    _require(isinstance(registers, list) and len(registers) == 8, "historical local register inventory mismatch")
    for value in registers:
        _integer(value, high=255)


def _stage(stage: Any, entry: Any, exit_state: Any, expected_pcs: tuple[int, ...], terminal: int) -> None:
    _snapshot(entry)
    _snapshot(exit_state)
    _require(isinstance(stage, Mapping) and {"events", "result", "writes", "sspAfter"} <= set(stage),
             "historical stage missing actual events")
    result = stage["result"]
    _require(isinstance(result, Mapping), "historical result must be an object")
    _require(result.get("status") == 0 and type(result.get("status")) is int
             and result.get("usedAssumptions") == []
             and result.get("steps") == len(expected_pcs) and type(result.get("steps")) is int
             and result.get("stopPc") == terminal and result.get("programReads") == [],
             "historical strict result/step/stop contract mismatch")
    events, trace = stage["events"], result.get("trace")
    _require(isinstance(events, list) and isinstance(trace, list)
             and len(events) == len(trace) == len(expected_pcs), "historical actual event/trace count mismatch")
    accumulator, psw = entry["accumulator"], entry["psw"]
    for index, (event, row, pc) in enumerate(zip(events, trace, expected_pcs)):
        _require(isinstance(event, list) and len(event) == 8 and all(type(v) is int for v in event),
                 "historical scalar event shape mismatch")
        next_pc = expected_pcs[index + 1] if index + 1 < len(expected_pcs) else terminal
        _require(event[0:2] == [pc, next_pc] and event[2] == accumulator and event[4] == psw,
                 "historical actual PC/state event continuity mismatch")
        _require(isinstance(row, Mapping) and row.get("pc") == pc and row.get("nextPc") == next_pc
                 and row.get("accumulator") == event[3] and row.get("psw") == event[5]
                 and row.get("instruction") == _FORMS[pc], "historical trace and scalar events diverge")
        for value in event[2:6]:
            _integer(value)
        accumulator, psw = event[3], event[5]
    _require(exit_state["pc"] == terminal and entry["pc"] == expected_pcs[0]
             and (exit_state["accumulator"], exit_state["psw"]) == (accumulator, psw)
             and stage["sspAfter"] == entry["ssp"] == exit_state["ssp"],
             "historical stage snapshot/SSP endpoint mismatch")
    for field in ("lrb", "x1", "x2", "dp", "usp", "ssp"):
        _require(entry[field] == exit_state[field], "historical retained context mismatch")


def _proof_inventory(document: Any) -> dict[str, int]:
    _closed(document, {"passed", "quartetDerived", "gateControls", "proofs", "strictEvents", "classification"},
            "historical independent proof schema mismatch")
    _require(document["passed"] is True and document["strictEvents"] == 42
             and document["quartetDerived"] == 39 and document["gateControls"] == 3
             and document["classification"] == "Independent C# validated actual event-wide native proof;no new execution",
             "historical old independent proof did not pass its sealed scope")
    proofs = document["proofs"]
    _require(isinstance(proofs, list) and len(proofs) == 42, "historical old proof row count mismatch")
    seen, image_b, controls, strict_original_a = set(), 0, 0, 0
    for row in proofs:
        _require(isinstance(row, Mapping), "historical old proof row malformed")
        _require(row.get("image") in ("A", "B") and isinstance(row.get("corpus"), str),
                 "historical old image/corpus identity malformed")
        identity = (row["image"], row["corpus"], row.get("scratchPattern"), row.get("eventIndex"))
        _require(identity not in seen, "historical old proof duplicate case identity")
        seen.add(identity)
        image_b += row["image"] == "B"
        controls += row["corpus"] == "upstream-gate"
        strict_original_a += row["image"] == "A" and row["corpus"] != "upstream-gate"
        _require(row["image"] != "B" or row["corpus"] == "fuel-ab",
                 "historical one-cell B proof is outside the recorded fuel-ab family")
        _require(row["corpus"] != "upstream-gate" or row["image"] == "A",
                 "historical gate controls must be disjoint original-A observations")
        for key in ("no0196Overlap", "noSfr", "hcRetained", "ddRetained"):
            _require(row.get(key) is True, "historical old proof relation not verified")
    _require(image_b == 6 and controls == 3 and strict_original_a == 33,
             "historical old independent image/control census mismatch")
    return {"oldProofRows": len(proofs), "oldStrictOriginalA": strict_original_a,
            "oldOneCellB": image_b, "oldGateControls": controls}


def _join_original_report(report: SelectedSource, native: SelectedSource,
                           expected_rom_sha256: str) -> dict[str, Any]:
    """Bind the full raw observation projection to the old ROM-bound C# report.

    The report embeds each complete raw checkpoint under ``actual``; all of that
    object is compared, not selected fields or an expected result substituted for
    a missing observation.  Top-level native headers are separately pinned by the
    selected source identity, runner and exact entry-contract equality.
    """
    document = report.document
    _require(isinstance(document, Mapping), "historical ROM-bound C# report missing")
    identity = document.get("originalHash")
    _closed(identity, {"sha256", "crc32"}, "historical C# original ROM hash binding missing")
    _require(identity["sha256"] == expected_rom_sha256,
             "historical C# report is bound to a different original ROM candidate")
    _require(document.get("formatVersion") == 1 and type(document.get("formatVersion")) is int
             and document.get("purpose") == "word0196-software-alternate-test"
             and document.get("profileId") == "p28-304" and document.get("runnerVersion") == "0.33.0"
             and document.get("hasFailure") is False and document.get("mutation") is None
             and document.get("changedOffsets") == []
             and document.get("word0196AlternateSoftwareChain") == "Validated"
             and document.get("cmp5578") == "Validated"
             and document.get("timerContinuation") == "NotRun" and document.get("p2") == "NotRun"
             and document.get("physicalOutput") == "NotRun" and document.get("firmwareBin") == 0
             and document.get("physicalRpmAvailable") is False,
             "historical original-A independent C# verification did not pass its immutable scope")
    raw = native.document
    _require(isinstance(raw, Mapping) and document.get("entryContract") == raw.get("entryContracts")
             and isinstance(raw.get("entryContracts"), list)
             and document["runnerVersion"] == raw.get("runnerVersion"),
             "historical C# report and raw native source header/entry contract differ")
    report_sequences, native_sequences = document.get("sequences"), raw.get("word0196AlternateSequences")
    _require(isinstance(report_sequences, list) and isinstance(native_sequences, list)
             and len(report_sequences) == len(native_sequences) and bool(native_sequences),
             "historical C# report lacks the complete raw sequence projection")
    checkpoint_count, seen = 0, set()
    for sequence_index, (observed, verified) in enumerate(zip(native_sequences, report_sequences)):
        _require(isinstance(observed, Mapping) and isinstance(verified, Mapping)
                 and verified.get("image") == "A"
                 and verified.get("scratchPattern") == observed.get("scratchPattern")
                 and type(verified.get("scratchPattern")) is int,
                 "historical original-A C# source-session identity mismatch")
        scratch = verified["scratchPattern"]
        _require(scratch not in seen, "historical C# duplicate source-session projection")
        seen.add(scratch)
        actual_events, checked_events = observed.get("checkpoints"), verified.get("checkpoints")
        _require(isinstance(actual_events, list) and isinstance(checked_events, list)
                 and len(actual_events) == len(checked_events) and bool(actual_events),
                 "historical C# report lacks complete checkpoint observations")
        for event_index, (actual, checked) in enumerate(zip(actual_events, checked_events)):
            _require(isinstance(actual, Mapping) and isinstance(checked, Mapping)
                     and checked.get("actual") == actual,
                     "historical raw checkpoint differs from the full ROM-bound C# actual projection")
            _require(checked.get("index") == actual.get("index") == event_index
                     and checked.get("disposition") == actual.get("disposition")
                     and checked.get("provenance") == actual.get("provenance"),
                     "historical C# independent checkpoint identity/status differs")
            for field in ("producerGeneration0196", "readerGeneration0196", "compareGeneration0196"):
                _require(checked.get(field) == actual.get(field),
                         "historical C# independently expected generation differs from raw source")
            checkpoint_count += 1
    return {"passed": True, "classification": "OriginalRomBoundOldCsharpReport_FullRawCheckpointProjectionEqual",
            "report_binding": report.public_binding(), "native_binding": native.public_binding(),
            "original_rom_sha256": expected_rom_sha256, "sequences_compared": len(native_sequences),
            "whole_checkpoints_compared": checkpoint_count, "field_exclusions": [],
            "new_csharp_execution": False, "native_top_level_headers_pinned_separately": True}


def _old_byte_value(event: Mapping[str, Any], journal: list[Any], position: int, address: int) -> int:
    """Reconcile recorded read/write values, not CPU instructions or a RAM replay."""
    if address == 0x0109:
        return event["alternate"]["entry"]["registers"][1]
    names = {0x0117: "byte0117", 0x0128: "byte0128", 0x012A: "byte012a",
             0x0124: "byte0124", 0x018E: "byte018e", 0x018F: "byte018f"}
    before = event.get("stateBefore")
    _require(isinstance(before, Mapping) and names.get(address) in before,
             "historical old writer value lacks captured pre-upstream DATA state")
    known = before[names[address]]
    _integer(known, high=255)
    for _, _, operand_address, width, _, value in journal[:position]:
        aligned = operand_address & 0xFFFE if width == 16 else operand_address
        if aligned <= address < aligned + width // 8:
            # The latest actual read or write is direct value evidence.  This
            # calculation does not run an instruction or invent unrecorded RAM.
            known = (value >> (8 * (address - aligned))) & 255
    return known


def _selected_case(source: SelectedSource, corpus: str, scratch: int, proof: SelectedSource,
                    path: str) -> dict[str, Any]:
    document = source.document
    _require(isinstance(document, Mapping) and document.get("protocolVersion") == 1
             and document.get("operation") == "word0196SoftwareAlternateChain"
             and document.get("runnerVersion") == "0.33.0" and document.get("syntheticResult") is None,
             "historical raw source is not the recorded native software operation")
    sequences = document.get("word0196AlternateSequences")
    _require(isinstance(sequences, list), "historical sequence inventory missing")
    matches = [(index, sequence) for index, sequence in enumerate(sequences)
               if isinstance(sequence, Mapping) and sequence.get("scratchPattern") == scratch]
    _require(len(matches) == 1, "historical source session grouping missing or duplicated")
    sequence_index, sequence = matches[0]
    _require(sequence.get("machineInstances") == 1 and type(sequence.get("machineInstances")) is int,
             "historical second CPU/Bus instance refused")
    checkpoints = sequence.get("checkpoints")
    _require(isinstance(checkpoints, list) and checkpoints, "historical checkpoint missing")
    event = checkpoints[0]
    _require(isinstance(event, Mapping) and event.get("index") == 0 and event.get("machineId") == 1
             and type(event.get("machineId")) is int and type(event.get("index")) is int
             and event.get("disposition") == "QuartetDerived0196AlternateStrict"
             and event.get("provenance") == "QuartetDerived0196",
             "historical selected original-A strict source event mismatch")
    prefix = event.get("prefix")
    _require(isinstance(prefix, Mapping) and prefix.get("machineId") == 1
             and type(prefix.get("machineId")) is int
             and prefix.get("index") == 0 and event.get("abiWrites") == [[0, 0x05ED, 0x54F5]],
             "historical source CPU continuity or disclosed PC-only seam mismatch")
    _require(all(type(item) is int for row in event["abiWrites"] for item in row),
             "historical malformed PC-only seam journal")
    consumer, alternate = event.get("consumer"), event.get("alternate")
    _require(isinstance(consumer, Mapping) and isinstance(alternate, Mapping), "historical actual stages missing")
    terminal = 0x55C5 if path == "A" else 0x5596
    _stage(consumer["stage"], consumer["entry"], consumer["exit"],
           (0x54F5, 0x54F8, 0x54FA, 0x54FC, 0x54FD, 0x5501), 0x556F)
    _stage(alternate["stage"], alternate["entry"], alternate["exit"], _PATHS[path], terminal)
    _snapshot(prefix.get("after"))
    _require(prefix["after"]["pc"] == 0x05ED
             and {**prefix["after"], "pc": 0x54F5} == consumer["entry"],
             "historical hidden state/frame seed across the PC-only scheduling seam")
    _require(consumer["exit"] == alternate["entry"] and event.get("after") == alternate["exit"],
             "historical native5501-to556F boundary snapshot is not continuous")
    _require(alternate["entry"]["lrb"] == 0x0021, "historical current-page/local-bank mismatch")
    for key in ("lrb", "x1", "x2", "dp", "usp", "ssp"):
        _require(alternate["entry"][key] == alternate["exit"][key], "historical suffix retained context changed")
    _require(alternate["entry"]["accumulator"] >> 8 == alternate["exit"]["accumulator"] >> 8
             and (alternate["entry"]["psw"] & 0x2FFF) == (alternate["exit"]["psw"] & 0x2FFF),
             "historical AH/HC/OtherPSW preservation mismatch")
    for index in (0, 2, 3, 4, 5, 6, 7):
        _require(alternate["entry"]["registers"][index] == alternate["exit"]["registers"][index],
                 "historical unaffected local register changed")
    if path == "A":
        _require(alternate["entry"]["registers"][1] == alternate["exit"]["registers"][1],
                 "historical below path unexpectedly wrote r1")
    all_proofs = proof.document["proofs"]
    selected = [(index, item) for index, item in enumerate(all_proofs)
                if item["image"] == "A" and item["corpus"] == corpus
                and item.get("scratchPattern") == scratch and item.get("eventIndex") == 0]
    _require(len(selected) == 1, "historical original-A independent proof join missing or duplicated")
    proof_index, independent = selected[0]
    generation = event.get("producerGeneration0196")
    _closed(generation, _GENERATION_KEYS, "historical producer generation schema mismatch")
    _require(generation["writerPc"] == 0x05EB and generation["eventIndex"] == 0,
             "historical DATA0196 is not the recorded05EB generation")
    for value in generation.values():
        _integer(value)
    for other in (event.get("readerGeneration0196"), event.get("compareGeneration0196"),
                  prefix.get("resultGeneration"), independent.get("generation0196"),
                  independent.get("reader54fa"), independent.get("reader5578")):
        _require(other == generation, "historical writer/reader/current-generation identity mismatch")
    _require(independent.get("continuous556fBoundary") == alternate["entry"]
             and independent.get("nativeJne5501") == consumer["stage"]["events"][-1]
             and independent.get("cmp5578") == alternate["stage"]["events"][5]
             and independent.get("jlt557d") == alternate["stage"]["events"][6]
             and independent.get("stopBefore") == terminal
             and independent.get("selectedQuartetGeneration") == prefix.get("selectedGeneration"),
             "historical raw observations disagree with the old independent proof")
    comparison = alternate["stage"]["events"][5]
    _require(comparison[6:8] == [generation["value"], 0x00C0]
             and independent.get("cmpLeft") == generation["value"]
             and independent.get("cmpRightImmediate") == 0x00C0
             and independent.get("cfProducer") == 0x5578
             and independent.get("cmpCf") is bool(comparison[5] & 0x8000)
             and independent.get("cmpZf") is bool(comparison[5] & 0x4000),
             "historical exact unsigned-CMP/CF dependency mismatch")
    _require(bool(comparison[5] & 0x8000) == (generation["value"] < 0x00C0)
             and bool(comparison[5] & 0x4000) == (generation["value"] == 0x00C0),
             "historical actual compare flags violate reviewed primary semantics")
    journal = event.get("continuityJournal")
    _require(isinstance(journal, list) and journal, "historical full event journal missing")
    normalized, native_writes, raw_native_accesses = [], [], []
    for index, row in enumerate(journal):
        _require(isinstance(row, list) and len(row) == 6 and all(type(value) is int for value in row),
                 "historical malformed DATA journal row")
        origin, pc, address, width, write, value = row
        _require(origin in (0, 1) and write in (0, 1) and width in (8, 16),
                 "historical DATA journal kind/width malformed")
        _integer(address)
        _integer(value, high=(1 << width) - 1)
        if origin == 0:
            _require(pc == 0x10000, "historical hidden host instruction/PC seed refused")
            aligned = address & 0xFFFE if width == 16 else address
            _require(not (aligned <= 0x0197 and aligned + width // 8 > 0x0196),
                     "historical host-seeded DATA0196 generation refused")
            continue
        _integer(pc)
        raw_native_accesses.append(row)
        write_order = len(native_writes) if write else None
        if write:
            native_writes.append((index, row))
        normalized.append({"ordinal": index, "kind": "write" if write else "read", "pc": pc,
                           "address": address, "width": width, "value": value,
                           "write_ordinal": write_order,
                           "generation_write_ordinal": generation["writeOrder"]
                           if not write and pc in (0x54FA, 0x5578) else None,
                           "origin": "HistoricalSourceCpuOnly"})
    _require(generation["writeOrder"] < len(native_writes), "historical writer ordinal not in full journal")
    writer_position, writer = native_writes[generation["writeOrder"]]
    _require(writer == [1, 0x05EB, 0x0196, 16, 1, generation["value"]],
             "historical actual all-native-write ordinal is not the claimed producer")
    reader_positions = {}
    for reader_pc in (0x54FA, 0x5578):
        positions = [index for index, row in enumerate(journal)
                     if row == [1, reader_pc, 0x0196, 16, 0, generation["value"]]]
        _require(len(positions) == 1, "historical actual DATA0196 reader missing or duplicated")
        reader_positions[str(reader_pc)] = positions[0]
    _require(writer_position < reader_positions[str(0x54FA)] < reader_positions[str(0x5578)]
             and independent.get("journalPositions") == {str(0x05EB): writer_position, **reader_positions},
             "historical independent proof and actual journal positions differ")
    relation = verify_data0196_lineage({"machine_id": event["machineId"], "session_id": scratch,
                                      "event_ordinal": event["index"], "complete_event_writes": True,
                                      "accesses": normalized})
    suffix_accesses = alternate.get("accesses")
    consumer_accesses = consumer.get("accesses")
    _require(isinstance(suffix_accesses, list) and isinstance(consumer_accesses, list),
             "historical recorded stage operand accesses missing")
    boundary_tail = [row[1:] for row in raw_native_accesses if row[1] in
                     set(_PATHS[path]) | {0x54F5, 0x54F8, 0x54FA, 0x54FC, 0x54FD, 0x5501}]
    _require(boundary_tail == consumer_accesses + suffix_accesses,
             "historical full journal and bounded stage access streams differ")
    _require(all(len(row) == 5 and row[1] >= 0x0100 for row in suffix_accesses),
             "historical downstream SFR/P2 access is outside the verified suffix")
    if path == "B":
        _require(not any(row[1] == 0x0124 for row in suffix_accesses), "historical path B second gate was read")
    writes = [row for row in suffix_accesses if row[3] == 1]
    _require([(row[0], row[1]) for row in writes] == list(_WRITERS[path])
             and all(row[2] == 8 for row in writes)
             and alternate["stage"]["writes"] == [[row[1], row[2], row[4]] for row in writes],
             "historical ordered suffix DATA writers mismatch")
    proof_writes = independent.get("softwareWrites")
    _require(isinstance(proof_writes, list) and len(proof_writes) == len(writes),
             "historical old independent ordered-write count mismatch")
    same_value_count = 0
    for raw, old in zip(writes, proof_writes):
        _require(isinstance(old, Mapping), "historical old software writer malformed")
        matches = [(order, position) for order, (position, row) in enumerate(native_writes)
                   if row[1:] == raw]
        _require(len(matches) == 1, "historical suffix writer occurrence ambiguous")
        write_order, raw_position = matches[0]
        _require((old.get("writerPc"), old.get("address"), old.get("width"), old.get("newValue"))
                 == (raw[0], raw[1], raw[2], raw[4])
                 and old.get("generation") == {"writerPc": raw[0], "eventIndex": 0,
                                                "writeOrder": write_order, "value": raw[4]},
                 "historical old independent ordered DATA writer differs")
        _require(old.get("oldValue") == _old_byte_value(event, journal, raw_position, raw[1]),
                 "historical independent old writer value differs from captured DATA evidence")
        same_value_count += old.get("oldValue") == old.get("newValue")
    return {"path": path, "corpus": corpus, "scratch": scratch, "sequence_index": sequence_index,
            "event_index": 0, "proof_index": proof_index, "source": source, "event": event,
            "root_pointer": f"/word0196AlternateSequences/{sequence_index}/checkpoints/0",
            "session_pointer": f"/word0196AlternateSequences/{sequence_index}/scratchPattern",
            "lineage": relation, "same_value_suffix_writes": same_value_count,
            "native_pc_sequence": list(_PATHS[path]), "terminal": terminal}


def _make_record(field: str, value: Any, source_id: str, locators: dict[str, Any],
                  native: bool = True, ownership: bool = False) -> dict[str, Any]:
    return {"field": field, "classification": "ObservedNative" if native else "StaticRomDerived",
            "value": value, "source_id": source_id, "locators": locators,
            "execution_domain": "HistoricalSourceCpuOnly" if native else "ReadOnlyStaticRomSemantics",
            "native_ownership": ownership, "physical_execution": False, "authority_id": None}


def _join_selected_independent_model(case: Mapping[str, Any], report: SelectedSource,
                                     old_proof: SelectedSource) -> dict[str, Any]:
    checked = report.document["sequences"][case["sequence_index"]]["checkpoints"][case["event_index"]]
    independent = old_proof.document["proofs"][case["proof_index"]]
    for field in ("cmpLeft", "cmpRightImmediate", "cmpCf", "cmpZf", "softwareWrites"):
        _require(checked.get(field) == independent.get(field),
                 "historical ROM-bound independent model and sealed proof disagree")
    event = case["event"]
    _require(checked.get("stopPc") == case["terminal"] and checked.get("branchPc") == 0x557D
             and checked.get("branchTaken") is independent["cmpCf"]
             and checked.get("branchTarget") == event["alternate"]["stage"]["events"][6][1],
             "historical ROM-bound independent branch/continuation comparison mismatch")
    return {"passed": True, "report_binding": report.public_binding(),
            "model_checkpoint_pointer": f"/sequences/{case['sequence_index']}/checkpoints/{case['event_index']}",
            "independent_comparison": "ReusedOldCsharpExpectedFieldsAndSealedProof_NoNewModelExecution"}


def reconcile_historical(profile: Mapping[str, Any], expected_rom_sha256: str) -> dict[str, Any]:
    """Reconcile three actual selected source-CPU observations without execution.

    Closed profile has ``slots``, ``below``, ``proof``, ``slotsReport`` and
    ``belowReport`` roles, each ``{path,bytes,sha256}``.  The separately verified
    actual current ROM digest is mandatory and must equal both old report bindings.
    Identities must come from the caller's independently reviewed private baseline,
    not a hash just recomputed from an arbitrary replacement.  The public summary
    deliberately excludes paths, ROM identities, raw native listings and payloads.
    """
    _require(isinstance(expected_rom_sha256, str) and re.fullmatch(r"[0-9a-f]{64}", expected_rom_sha256) is not None,
             "historical separately verified actual ROM SHA-256 required")
    _closed(profile, {"slots", "below", "proof", "slotsReport", "belowReport"},
            "historical selected-role profile schema mismatch")
    selected = {}
    for role, binding in profile.items():
        _closed(binding, {"path", "bytes", "sha256"}, "historical selected-source binding schema mismatch")
        path = binding["path"]
        _require(isinstance(path, str) and bool(path) and "\x00" not in path,
                 "historical explicit local source path required")
        _require(not path.startswith(("\\\\", "//"))
                 and re.match(r"[A-Za-z][A-Za-z0-9+.-]*://", path) is None,
                 "NetworkSourceRequiresControlledRestore")
        selected[role] = select_source(binding["path"], "m2z-" + role, binding["sha256"], binding["bytes"],
                                       "HistoricalOfflineModel" if role in ("proof", "slotsReport", "belowReport")
                                       else "HistoricalSourceCpuObservations")
    rom_joins = [_join_original_report(selected["slotsReport"], selected["slots"], expected_rom_sha256),
                 _join_original_report(selected["belowReport"], selected["below"], expected_rom_sha256)]
    census = _proof_inventory(selected["proof"].document)
    cases = [_selected_case(selected["slots"], "slots", 0, selected["proof"], "D"),
             _selected_case(selected["slots"], "slots", 170, selected["proof"], "B"),
             _selected_case(selected["below"], "threshold191", 0, selected["proof"], "A")]
    for case in cases:
        role = "belowReport" if case["corpus"] == "threshold191" else "slotsReport"
        case["independent_model_join"] = _join_selected_independent_model(case, selected[role], selected["proof"])
    current_source_bytes = Path(__file__).read_bytes()
    current_source = SelectedSource("m2bs-current-historical-reader", "ReviewedHistoricalValidator",
                                    hashlib.sha256(current_source_bytes).hexdigest(), len(current_source_bytes), None,
                                    str(Path(__file__).resolve()))
    sources = [selected["slots"], selected["below"], current_source]
    records, derivatives, private_cases = [], [], []
    snapshot_fields = {"PC": "pc", "A": "accumulator", "PSW": "psw", "DD": "dd", "LRB": "lrb",
                       "SSP": "ssp", "X1": "x1", "X2": "x2", "DP": "dp", "USP": "usp"}
    for case in cases:
        event, pointer, source = case["event"], case["root_pointer"], case["source"]
        base_locators = {"value": None, "machine_id": pointer + "/machineId",
                         "session_id": case["session_pointer"], "event_ordinal": pointer + "/index",
                         "pc": None, "read_ordinal": None, "write_ordinal": None, "path": None}
        for phase in ("entry", "exit"):
            snapshot = event["alternate"][phase]
            snap_pointer = pointer + "/alternate/" + phase
            for field, key in snapshot_fields.items():
                locators = {**base_locators, "value": snap_pointer + "/" + key, "pc": snap_pointer + "/pc"}
                records.append(_make_record(field, snapshot[key], source.source_id, locators))
            for index, value in enumerate(snapshot["registers"]):
                locators = {**base_locators, "value": snap_pointer + f"/registers/{index}",
                            "pc": snap_pointer + "/pc"}
                records.append(_make_record(f"r{index}", value, source.source_id, locators))
            psw, a = snapshot["psw"], snapshot["accumulator"]
            derived_values = {"AL": a & 255, "AH": a >> 8, "CF": bool(psw & 0x8000),
                              "ZF": bool(psw & 0x4000), "HC": bool(psw & 0x2000),
                              "OtherPSW": psw & 0x0FFF, "SCB": psw & 7,
                              **{f"er{index}": snapshot["registers"][2 * index]
                                 | snapshot["registers"][2 * index + 1] << 8 for index in range(4)},
                              **{f"pointingBank{psw & 7}.{key.upper()}": snapshot[key]
                                 for key in ("x1", "x2", "dp", "usp")}}
            for field, value in derived_values.items():
                derivatives.append({"field": field, "value": value, "pc": snapshot["pc"],
                                    "source_binding": source.public_binding(), "snapshot_pointer": snap_pointer,
                                    "source_cpu_session_group": case["scratch"], "phase": phase,
                                    "classification": "StaticRomDerived_ArchitectureProjectionOfRecordedSnapshot",
                                    "not_a_separately_captured_flag_or_alias_observation": True})
        generation = event["producerGeneration0196"]
        generation_locators = {**base_locators, "value": pointer + "/producerGeneration0196/value",
                               "pc": pointer + "/producerGeneration0196/writerPc",
                               "write_ordinal": pointer + "/producerGeneration0196/writeOrder"}
        records.append(_make_record("DATA0196", generation["value"], source.source_id, generation_locators,
                                    ownership=True))
        operand_fields = {0x0117: "DATA0117", 0x0124: "DATA0124", 0x0128: "DATA0128",
                          0x012A: "DATA012A", 0x018E: "DATA018E", 0x018F: "DATA018F", 0x0196: "DATA0196"}
        for stage_name in ("consumer", "alternate"):
            for index, access in enumerate(event[stage_name]["accesses"]):
                field = operand_fields.get(access[1])
                if field is not None:
                    access_pointer = pointer + f"/{stage_name}/accesses/{index}"
                    locators = {**base_locators, "value": access_pointer + "/4", "pc": access_pointer + "/0"}
                    records.append(_make_record(field, access[4], source.source_id, locators))
        for field, value in (("DATA0196.low", generation["value"] & 255),
                             ("DATA0197", generation["value"] >> 8)):
            derivatives.append({"field": field, "value": value, "pc": 0x05EB,
                                "source_binding": source.public_binding(),
                                "snapshot_pointer": pointer + "/producerGeneration0196",
                                "source_cpu_session_group": case["scratch"], "phase": "producer-generation",
                                "classification": "StaticRomDerived_LittleEndianProjectionOfRecordedWord",
                                "not_a_separately_captured_flag_or_alias_observation": True})
        private_cases.append({"path": case["path"], "image": "OriginalAAsJoinedToSealedProof",
                              "corpus": case["corpus"], "source_binding": source.public_binding(),
                              "sequence_index": case["sequence_index"], "event_index": 0,
                              "source_cpu_machine_id": event["machineId"],
                              "source_cpu_session_group": {"scratchPattern": case["scratch"],
                                  "meaning": "SerializedSequenceGrouping_NotOsPidOrUuid"},
                              "raw_pointer": pointer, "old_proof_pointer": f"/proofs/{case['proof_index']}",
                              "native_pc_sequence": case["native_pc_sequence"], "stop_before": case["terminal"],
                              "generation_reconciliation": case["lineage"],
                              "same_value_suffix_writes": case["same_value_suffix_writes"],
                              "entry_snapshot": event["alternate"]["entry"],
                              "exit_snapshot": event["alternate"]["exit"],
                              "rom_bound_independent_model_join": case["independent_model_join"],
                              "data_state_before_is_pre_upstream_not_entry_state": True,
                              "same_cpu_bus_observation_continuity_reconciled": True,
                              "scheduler_seam": "ExplicitHarnessSchedule05EDto54F5_PCOnly"})
    derived_source = _derived_source("m2bs-current-architecture-projection", "ReviewedStaticSemantics", derivatives)
    sources.append(derived_source)
    for index, derivative in enumerate(derivatives):
        locators = {key: None for key in ("value", "machine_id", "session_id", "event_ordinal", "pc",
                                        "read_ordinal", "write_ordinal", "path")}
        locators.update(value=f"/{index}/value", pc=f"/{index}/pc")
        records.append(_make_record(derivative["field"], derivative["value"], derived_source.source_id,
                                    locators, native=False))
    attestations = []
    for role in ("slots", "below"):
        source = selected[role]
        observations = [{"field": record["field"], "locators": record["locators"],
                         "native_ownership": record["native_ownership"]}
                        for record in records if record["source_id"] == source.source_id]
        receipt = {"schema_version": 1, "classification": "HistoricalSourceCpuObservationVerification",
                   "passed": True, "observed_source_binding": source.public_binding(),
                   "validator_source_binding": current_source.public_binding(), "observations": observations,
                   "physical_execution": False, "model_only": False, "independent_expected_comparison": True}
        authority = _derived_source("m2bs-current-" + role + "-attestation",
                                     "HistoricalNativeVerificationReceipt", receipt)
        sources.append(authority)
        for record in records:
            if record["source_id"] == source.source_id:
                record["authority_id"] = authority.source_id
        attestations.append({"binding": authority.public_binding(), "document": receipt,
                             "construction": "DerivedVerifiedReceipt_CurrentReadOnlyReconciliation_NotHistoricalFile",
                             "reused_old_independent_proof_binding": selected["proof"].public_binding(),
                             "independent_comparison_kind": "ReusedOldIndependentCsharpProof_NotNewCsharpExecution"})
    matrix = build_context_matrix(records, sources)
    return {
        "passed": True,
        "privateEvidence": {
            "classification": "ActualSelectedHistoricalSourceCpuRecords_ReadOnlyReconciliation",
            "selected_sources": [{"binding": source.public_binding(), "private_path": source.private_path}
                                 for source in selected.values()],
            "prior_independent_proof_census": census, "fresh_reconciled_original_a_samples": private_cases,
            "original_rom_to_historical_raw_source_joins": rom_joins,
            "current_reader_binding": current_source.public_binding(),
            "current_derived_attestations": attestations, "architecture_derivatives": derivatives,
            "no_new_independent_csharp_execution": True,
        },
        "publicSummary": {
            "classification": "HistoricalSourceCpuEvidenceReconciled_NotPhysicalEcuExecution",
            "priorIndependentProofRows": 42, "priorStrictOriginalA": 33, "priorOneCellB": 6,
            "priorGateControls": 3, "freshReconciledOriginalASamples": 3,
            "freshReconciledPaths": ["A", "B", "D"], "historicalNativePathCWitnesses": 0,
            "nativeEntryPc": 0x556F, "continuationStopBeforePcs": [0x5596, 0x55C5],
            "sameSourceCpuBusContinuityReconciled": True, "writer05EBReaders54FA5578SameGeneration": True,
            "allNativeWriteOrdinalsReconciled": True, "equalValueGenerationEventsNotMerged": True,
            "actualRomIdentityJoinedToOldCsharpReports": True,
            "romBoundFullRawCheckpointProjectionComparisons": sum(join["whole_checkpoints_compared"] for join in rom_joins),
            "newOriginalRomExecutions": 0, "physicalEcuExecutions": 0,
            "newCsharpOrModelReplays": 0, "fullHistoricalCorpusReexecuted": False,
            "nativeSchedulerEstablished": False, "nativeStackSafetyEstablished": False,
            "physicalSFEstablished": False, "peripheralStateOwnershipEstablished": False,
            "firmwareReady": False,
        },
        "matrix": matrix,
    }
