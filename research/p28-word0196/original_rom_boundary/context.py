"""Closed, evidence-bound M2bs context classifications; never a CPU executor.

This module deliberately separates a recorded historical *source CPU* observation
from a physical ECU observation.  ``ObservedNative`` can describe the former only
when both the original observation and an independently selected successful
verification receipt bind the exact source bytes, field and JSON locators.
Numerical equality, a JSON category, a synthetic transfer ticket and an offline
reference state are not native ownership authorities.

``select_source`` is an explicit read-only selection, not an archive search.  Its
private path is never included in ``build_context_matrix``'s public-safe result.
Historical evidence with a different schema needs an explicitly reviewed adapter;
there is no permissive fallback that infers an observation from missing fields.
"""

from __future__ import annotations

from dataclasses import dataclass, field as dataclass_field
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Mapping, Sequence


CLASSIFICATIONS = (
    "ObservedNative", "StaticRomDerived", "HistoricalReplay", "SyntheticOnly", "Unknown"
)
SOURCE_KINDS = (
    "VerifiedOriginalRomSourceReceipt", "ReviewedStaticSemantics",
    "HistoricalSourceCpuObservations", "HistoricalOfflineModel",
    "SyntheticTestResults", "HistoricalNativeVerificationReceipt",
    "ReviewedHistoricalValidator",
)
_SCALAR_WIDTHS = {
    "PC": 16, "A": 16, "AL": 8, "AH": 8,
    "CF": 1, "ZF": 1, "HC": 1, "DD": 1,
    "PSW": 16, "OtherPSW": 16, "LRB": 16, "SCB": 3, "SSP": 16,
    "X1": 16, "X2": 16, "DP": 16, "USP": 16,
    **{f"pointingBank{bank}.{reg}": 16 for bank in range(8)
       for reg in ("X1", "X2", "DP", "USP")},
    **{f"r{number}": 8 for number in range(8)},
    **{f"er{number}": 16 for number in range(4)},
    **{f"DATA{address:04X}": 8 for address in
       (0x0117, 0x0124, 0x0128, 0x012A, 0x018E, 0x018F, 0x0197)},
    "DATA0196": 16, "DATA0196.low": 8,
}
_UNKNOWN_ONLY_FIELDS = (
    "SF", "P2", "RelevantDownstreamSFR", "NativeStackFrame",
    "InterruptContext", "PeripheralContext", "NativeScheduler",
)
FIELD_NAMES = tuple(_SCALAR_WIDTHS) + _UNKNOWN_ONLY_FIELDS
_PROTECTED_OWNERSHIP_FIELDS = frozenset(_UNKNOWN_ONLY_FIELDS + ("SSP",))
_LOCATOR_NAMES = (
    "value", "machine_id", "session_id", "event_ordinal", "pc",
    "read_ordinal", "write_ordinal", "path",
)
_RECORD_KEYS = {
    "field", "classification", "value", "source_id", "locators",
    "execution_domain", "native_ownership", "physical_execution", "authority_id",
}
_DOMAINS = {
    "ObservedNative": "HistoricalSourceCpuOnly",
    "StaticRomDerived": "ReadOnlyStaticRomSemantics",
    "HistoricalReplay": "HistoricalOfflineModelOnly",
    "SyntheticOnly": "InventedSyntheticOnly",
}
_SOURCE_FOR_CLASS = {
    "ObservedNative": {"HistoricalSourceCpuObservations"},
    "StaticRomDerived": {"VerifiedOriginalRomSourceReceipt", "ReviewedStaticSemantics"},
    "HistoricalReplay": {"HistoricalOfflineModel"},
    "SyntheticOnly": {"SyntheticTestResults"},
}
_IDENTITY = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,95}\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")

# These are documentary software obligations, not captured incoming values or
# proof of physical/native ownership.  The read-only caller separately binds the
# reviewed architecture/IR sources and actual selected ROM extents.
ARCHITECTURAL_OBLIGATIONS = {
    "classification": "DocumentedArchitectureAndReviewedSoftwareObligations_NotObservedState",
    "sources": ["docs/M2AW_NX8_200_TARGET_ABI_CONTRACT.md",
                "docs/M2BF_WORD0196_EXTERNAL_CONTINUATION_EVIDENCE.md"],
    "entry_pc": 0x556F,
    "stop_before_pcs": [0x5596, 0x55C5],
    "program_and_data_are_distinct_spaces": True,
    "accumulator_alias": "A = AL | (AH << 8)",
    "psw_bits": {"CF": 15, "ZF": 14, "HC": 13, "DD": 12},
    "other_psw_rule": "OtherPSW = PSW & 0x0FFF; preserved",
    "scb_rule": "SCB = PSW & 7; retained from incoming PSW",
    "lrb_precondition": 0x0021,
    "current_page_rule": "((LRB & 0x1FE0) << 3) & 0xFFFF",
    "local_bank_rule": "((LRB & 0x1FFF) << 3) & 0xFFFF",
    "pointing_bank_rule": "DATA(0x0080 + 8*SCB + offset); X1/X2/DP/USP offsets0/2/4/6",
    "all_pointing_banks_preserved": True,
    "local_alias_rule": "erN = r(2*N) | (r(2*N+1) << 8); r0 low/r1 high of er0",
    "local_preservation": "r0/r2..r7 retained; r1 written only NotBelow",
    "ah_hc_other_psw_preserved": True,
    "ssp_rule": "Retain actual incoming SSP; no scoped stack writer; safe frame not established",
    "data0196_word_rule": "DATA0196.low | (DATA0197 << 8); even little-endian16 read only",
    "immediate_00c0_is_not_a_data_read": True,
    "below_terminal": {"pc": 0x55C5, "AL": 0x0F, "CF": True, "ZF": False, "DD": False},
    "not_below_terminal": {"pc": 0x5596, "AL_rule": "FinalDATA018F OR 0xF0",
                           "CF": False, "ZF": False, "DD": False},
    "physical_sf_meaning_or_storage": "Unknown",
    "native_scheduler_stack_peripheral_ownership": "Unknown",
}


class ContextError(ValueError):
    """A closed context/evidence relation was refused; never a catch-and-pass."""


def _closed(value: Any, keys: set[str], label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != keys:
        raise ContextError(f"{label}: closed schema mismatch")
    return value


def _integer(value: Any, low: int, high: int, label: str) -> int:
    if type(value) is not int or not low <= value <= high:
        raise ContextError(f"{label}: integer outside the admitted domain")
    return value


def _identity(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _IDENTITY.fullmatch(value):
        raise ContextError(f"{label}: public-safe identity required")
    return value


def _object_without_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ContextError("selected source: duplicate JSON key")
        result[key] = value
    return result


@dataclass(frozen=True)
class SelectedSource:
    """A pinned, actually read JSON source, explicitly selected by the caller."""

    source_id: str
    kind: str
    sha256: str
    size_bytes: int
    document: Any = dataclass_field(repr=False, compare=False)
    private_path: str = dataclass_field(repr=False, compare=False)

    def public_binding(self) -> dict[str, Any]:
        return {"source_id": self.source_id, "kind": self.kind,
                "sha256": self.sha256, "size_bytes": self.size_bytes}


def select_source(path: str | Path, source_id: str, expected_sha256: str,
                  expected_bytes: int, kind: str) -> SelectedSource:
    """Read exactly one selected JSON source and verify its immutable identity.

    No source discovery, remote access, writes, execution or authority promotion
    occurs.  A source kind is an admission restriction, not proof by itself.
    """
    _identity(source_id, "source_id")
    if kind not in SOURCE_KINDS or not isinstance(expected_sha256, str) \
            or not _SHA256.fullmatch(expected_sha256):
        raise ContextError("selected source: unsupported kind or SHA-256")
    _integer(expected_bytes, 1, 64 * 1024 * 1024, "selected source bytes")
    candidate = Path(path)
    try:
        before = candidate.stat()
        if not candidate.is_file() or before.st_size != expected_bytes:
            raise ContextError("selected source: file or length mismatch")
        with candidate.open("rb") as handle:
            payload = handle.read(expected_bytes + 1)
        after = candidate.stat()
    except OSError as error:
        raise ContextError("selected source unavailable") from error
    if len(payload) != expected_bytes or hashlib.sha256(payload).hexdigest() != expected_sha256:
        raise ContextError("selected source: SHA-256 or complete-read mismatch")
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise ContextError("selected source: changed during read")
    try:
        text = payload.decode("utf-8-sig")
        document = None if kind == "ReviewedHistoricalValidator" else json.loads(text,
                              object_pairs_hook=_object_without_duplicate_keys,
                              parse_constant=lambda _: (_ for _ in ()).throw(
                                  ContextError("selected source: nonfinite JSON number")))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise ContextError("selected source: malformed JSON") from error
    return SelectedSource(source_id, kind, expected_sha256, expected_bytes,
                          document, str(candidate.resolve()))


def _at_pointer(document: Any, pointer: Any) -> Any:
    if not isinstance(pointer, str) or (pointer and not pointer.startswith("/")):
        raise ContextError("evidence locator: JSON pointer required")
    current = document
    for token in pointer.split("/")[1:] if pointer else ():
        if re.search(r"~(?![01])", token):
            raise ContextError("evidence locator: invalid JSON pointer escape")
        part = token.replace("~1", "/").replace("~0", "~")
        try:
            if isinstance(current, list):
                if not re.fullmatch(r"0|[1-9][0-9]*", part):
                    raise ContextError("evidence locator: noncanonical array index")
                current = current[int(part)]
            elif isinstance(current, Mapping):
                current = current[part]
            else:
                raise ContextError("evidence locator: scalar is not a container")
        except (KeyError, IndexError) as error:
            raise ContextError("evidence locator: missing actual observation") from error
    return current


def _source_table(sources: Sequence[SelectedSource]) -> dict[str, SelectedSource]:
    result = {}
    for source in sources:
        if not isinstance(source, SelectedSource) or source.source_id in result:
            raise ContextError("selected sources: invalid or duplicate source")
        result[source.source_id] = source
    return result


def _bind_native_authority(record: Mapping[str, Any], observed: SelectedSource,
                           sources: Mapping[str, SelectedSource]) -> None:
    try:
        authority = sources[record["authority_id"]]
    except (KeyError, TypeError) as error:
        raise ContextError("native evidence: separate selected verification receipt required") from error
    if authority.kind != "HistoricalNativeVerificationReceipt":
        raise ContextError("native evidence: synthetic/model/static receipt cannot authorize it")
    receipt = _closed(authority.document, {
        "schema_version", "classification", "passed", "observed_source_binding",
        "validator_source_binding", "observations", "physical_execution",
        "model_only", "independent_expected_comparison",
    }, "native verification receipt")
    if type(receipt["schema_version"]) is not int or receipt["schema_version"] != 1 \
            or receipt["classification"] != "HistoricalSourceCpuObservationVerification" \
            or receipt["passed"] is not True or receipt["physical_execution"] is not False \
            or receipt["model_only"] is not False \
            or receipt["independent_expected_comparison"] is not True:
        raise ContextError("native evidence: receipt does not attest independent actual observations")
    if receipt["observed_source_binding"] != observed.public_binding():
        raise ContextError("native evidence: receipt does not bind this actual source")
    validator_binding = receipt["validator_source_binding"]
    if not isinstance(validator_binding, Mapping):
        raise ContextError("native evidence: selected independent validator identity required")
    validator = sources.get(validator_binding.get("source_id"))
    if validator is None or validator.kind != "ReviewedHistoricalValidator" \
            or validator.public_binding() != validator_binding:
        raise ContextError("native evidence: independent validator binding mismatch")
    observations = receipt["observations"]
    if not isinstance(observations, list) or not observations:
        raise ContextError("native evidence: no actual observation admission")
    admitted = []
    for item in observations:
        _closed(item, {"field", "locators", "native_ownership"}, "native observation admission")
        if item["field"] not in FIELD_NAMES or type(item["native_ownership"]) is not bool:
            raise ContextError("native evidence: malformed observation admission")
        _closed(item["locators"], set(_LOCATOR_NAMES), "native observation locators")
        admitted.append(item)
    relation = {"field": record["field"], "locators": record["locators"],
                "native_ownership": record["native_ownership"]}
    if admitted.count(relation) != 1:
        raise ContextError("native evidence: exact field/locator/ownership admission missing or duplicated")


def validate_evidence_record(record: Mapping[str, Any],
                             sources: Sequence[SelectedSource]) -> dict[str, Any]:
    """Validate one evidence relation against selected bytes, not caller labels.

    Every locator is a JSON pointer into the selected actual observation.  Static
    facts need no machine/session; runtime observations do.  The returned mapping
    excludes private paths and contains no executable instruction bytes.
    """
    record = _closed(record, _RECORD_KEYS, "context evidence")
    name = record["field"]
    classification = record["classification"]
    if name not in FIELD_NAMES or classification not in _DOMAINS:
        raise ContextError("context evidence: unknown field or unsupported classification")
    if name in _UNKNOWN_ONLY_FIELDS:
        raise ContextError("context evidence: unresolved SF/stack/peripheral/scheduler field cannot be assigned")
    value = record["value"]
    width = _SCALAR_WIDTHS[name]
    if width == 1:
        if type(value) is not bool:
            raise ContextError("context evidence: a documented flag requires a boolean")
    else:
        _integer(value, 0, (1 << width) - 1, name)
    if record["execution_domain"] != _DOMAINS[classification] \
            or record["physical_execution"] is not False \
            or type(record["native_ownership"]) is not bool:
        raise ContextError("context evidence: authority-domain or physical-execution promotion")
    if record["native_ownership"] and (classification != "ObservedNative"
                                       or name in _PROTECTED_OWNERSHIP_FIELDS):
        raise ContextError("context evidence: false native ownership")
    selected = _source_table(sources)
    try:
        source = selected[record["source_id"]]
    except (KeyError, TypeError) as error:
        raise ContextError("context evidence: actual selected source required") from error
    if source.kind not in _SOURCE_FOR_CLASS[classification]:
        raise ContextError("context evidence: source class promotion refused")
    locators = _closed(record["locators"], set(_LOCATOR_NAMES), "context evidence locators")
    if locators["value"] is None or _at_pointer(source.document, locators["value"]) != value \
            or type(_at_pointer(source.document, locators["value"])) is not type(value):
        raise ContextError("context evidence: value differs from the actual source")
    observation = {key: None if pointer is None else _at_pointer(source.document, pointer)
                   for key, pointer in locators.items() if key != "value"}
    if classification in ("ObservedNative", "HistoricalReplay"):
        for key in ("machine_id", "session_id"):
            identity = observation[key]
            if type(identity) is int:
                _integer(identity, 0, (1 << 63) - 1, key)
            else:
                _identity(identity, key)
        for key in ("event_ordinal", "pc"):
            _integer(observation[key], 0, 0xFFFF if key == "pc" else (1 << 63) - 1, key)
    elif any(observation[key] is not None for key in ("machine_id", "session_id")):
        raise ContextError("context evidence: static/synthetic fact cannot borrow native machine identity")
    for key in ("read_ordinal", "write_ordinal"):
        if observation[key] is not None:
            _integer(observation[key], 0, (1 << 63) - 1, key)
    path = observation["path"]
    if path is not None and path not in ("A", "B", "C", "D"):
        raise ContextError("context evidence: fabricated path")
    if classification == "ObservedNative":
        if path == "C":
            raise ContextError("context evidence: path C has no historical native witness")
        _bind_native_authority(record, source, selected)
    elif record["authority_id"] is not None:
        raise ContextError("context evidence: non-native fact cannot borrow a native authority")
    return {**dict(record), "source_binding": source.public_binding(),
            "actual_observation": observation,
            "ownership_scope": "HistoricalSourceCpuOnly" if record["native_ownership"] else "NotEstablished",
            "physical_ownership_established": False}


def build_context_matrix(records: Sequence[Mapping[str, Any]] = (),
                          sources: Sequence[SelectedSource] = ()) -> dict[str, Any]:
    """Return a full typed matrix; absent evidence stays Unknown, never zero.

    Multiple observations retain their separate source/generation identities.
    Classification is a list of actually present evidence domains, not a strongest
    evidence ranking: a historical replay is not overwritten by a synthetic value.
    """
    _source_table(sources)
    rows = {name: {
        "field": name, "width_bits": _SCALAR_WIDTHS.get(name),
        "classifications": ["Unknown"], "actual_value": None,
        "native_ownership_established": False, "physical_ownership_established": False,
        "observations": [],
    } for name in FIELD_NAMES}
    seen = set()
    for record in records:
        validated = validate_evidence_record(record, sources)
        identity = json.dumps(record, sort_keys=True, separators=(",", ":"), allow_nan=False)
        if identity in seen:
            raise ContextError("context matrix: duplicate observation identity")
        seen.add(identity)
        row = rows[validated["field"]]
        row["observations"].append(validated)
        row["classifications"] = [item for item in CLASSIFICATIONS if item != "Unknown"
                                  and any(obs["classification"] == item for obs in row["observations"])]
        row["native_ownership_established"] |= validated["native_ownership"]
    return {
        "schema_version": 1, "classification": "EvidenceBoundContextMatrix_NoExecution",
        "field_count": len(rows), "fields": list(rows.values()),
        "source_bindings": [source.public_binding() for source in sources],
        "architectural_obligations": ARCHITECTURAL_OBLIGATIONS,
        "classification_is_not_a_strength_ranking": True,
        "actual_value_without_a_single_selected_session_is_unknown": True,
        "same_value_generation_events_are_not_deduplicated": True,
        "new_original_rom_executions": 0, "physical_ecu_executions": 0,
        "firmware_ready": False,
        "unresolved": ["NativeSchedulerNotEstablished", "PhysicalSFNotEstablished",
                       "NativeStackSafetyNotEstablished", "PeripheralStateOwnershipNotEstablished",
                       "ActualNativeDownstreamRejoinNotEstablished"],
    }


def verify_data0196_lineage(journal: Mapping[str, Any]) -> dict[str, Any]:
    """Check a complete selected historical journal's producer/reader relation.

    This pure reconciliation is not a source selector and grants no ObservedNative
    status by itself.  Caller must separately bind the journal to selected actual
    evidence.  ``ordinal`` is total functional DATA-access order; ``write_ordinal``
    is the zero-based ordinal among *all* native writes, not just0196 writers.
    """
    journal = _closed(journal, {"machine_id", "session_id", "event_ordinal",
                                "complete_event_writes", "accesses"}, "DATA0196 journal")
    if journal["complete_event_writes"] is not True or not isinstance(journal["accesses"], list):
        raise ContextError("DATA0196 lineage: complete event-wide journal required")
    _identity(str(journal["machine_id"]), "journal machine")
    _identity(str(journal["session_id"]), "journal session")
    _integer(journal["event_ordinal"], 0, (1 << 63) - 1, "journal event")
    previous_access = -1
    next_write = 0
    current_generation = None
    reader_generations = []
    event_writes = []
    for access in journal["accesses"]:
        access = _closed(access, {"ordinal", "kind", "pc", "address", "width", "value",
                                  "write_ordinal", "generation_write_ordinal", "origin"}, "DATA access")
        ordinal = _integer(access["ordinal"], 0, (1 << 63) - 1, "access ordinal")
        if ordinal <= previous_access:
            raise ContextError("DATA0196 lineage: access order is missing or duplicated")
        previous_access = ordinal
        pc = _integer(access["pc"], 0, 0xFFFF, "access PC")
        address = _integer(access["address"], 0, 0xFFFF, "DATA address")
        width = access["width"]
        if width not in (8, 16) or type(width) is not int:
            raise ContextError("DATA0196 lineage: unsupported DATA width")
        _integer(access["value"], 0, (1 << width) - 1, "DATA value")
        if access["origin"] != "HistoricalSourceCpuOnly" or access["kind"] not in ("read", "write"):
            raise ContextError("DATA0196 lineage: host seed, diagnostic or synthetic event is not a native access")
        aligned = address & 0xFFFE if width == 16 else address
        overlap = aligned <= 0x0197 and aligned + width // 8 > 0x0196
        if access["kind"] == "write":
            if access["write_ordinal"] != next_write or type(access["write_ordinal"]) is not int \
                    or access["generation_write_ordinal"] is not None:
                raise ContextError("DATA0196 lineage: all-native-write ordinal mismatch")
            next_write += 1
            event_writes.append({"pc": pc, "write_ordinal": access["write_ordinal"],
                                 "address": address, "width": width, "value": access["value"]})
            if overlap:
                if pc == 0x05EB and address == 0x0196 and width == 16:
                    current_generation = {"writer_pc": pc, "write_ordinal": access["write_ordinal"],
                                          "value": access["value"]}
                else:
                    current_generation = None
        elif access["write_ordinal"] is not None:
            raise ContextError("DATA0196 lineage: read cannot be a new writer")
        elif pc in (0x54FA, 0x5578):
            _integer(access["generation_write_ordinal"], 0, (1 << 63) - 1,
                     "reader generation ordinal")
            if address != 0x0196 or width != 16 or current_generation is None \
                    or access["value"] != current_generation["value"] \
                    or access["generation_write_ordinal"] != current_generation["write_ordinal"]:
                raise ContextError("DATA0196 lineage: current exact05EB generation not read")
            reader_generations.append({"reader_pc": pc, "read_ordinal": ordinal,
                                       **current_generation})
        elif access["generation_write_ordinal"] is not None:
            raise ContextError("DATA0196 lineage: unrelated read cannot claim0196 ownership")
    if [item["reader_pc"] for item in reader_generations] != [0x54FA, 0x5578] \
            or reader_generations[0]["write_ordinal"] != reader_generations[1]["write_ordinal"]:
        raise ContextError("DATA0196 lineage: exact ordered54FA/5578 same-generation pair required")
    return {"passed": True, "classification": "SelectedJournalRelationOnly_NoNewRuntimeObservation",
            "machine_id": journal["machine_id"], "session_id": journal["session_id"],
            "event_ordinal": journal["event_ordinal"], "readers": reader_generations,
            "all_native_writes": event_writes, "generation_identity": {
                "machine_id": journal["machine_id"], "session_id": journal["session_id"],
                "event_ordinal": journal["event_ordinal"], **reader_generations[0]},
            "same_value_writes_retained": True, "indirect_alias_absence_established": False,
            "recovered_scheduler_established": False, "physical_execution_claimed": False}
