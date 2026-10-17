"""Closed invented M2bp inputs. Generation performs no Cpu execution.

The exact 468 M2bo requests are retained. Stronger predicate-derived permissions
reject 84 old microcontexts; those are explicit refusals, not skipped positives.
Separate D-compatible controls cover their forms without changing old requests.
"""
from collections import Counter
from copy import deepcopy
from hashlib import sha256
import json

import production_exec_parity_corpus as historical
import production_exec_parity_oracle as reference

BASE = "1ceec589ee8586727fb16a39fd15875444d6feab"
PROVENANCE = historical.PROVENANCE
READS = {
    "A": [(0x108, 8), (0x18e, 8), (0x196, 16)],
    "B": [(0x108, 8), (0x18e, 8), (0x196, 16), (0x117, 8), (0x12a, 8), (0x18f, 8)],
    "C": [(0x108, 8), (0x18e, 8), (0x196, 16), (0x117, 8), (0x12a, 8), (0x18f, 8), (0x124, 8)],
    "D": [(0x108, 8), (0x18e, 8), (0x196, 16), (0x117, 8), (0x12a, 8), (0x18f, 8), (0x124, 8)],
}
WRITES = {"A": [0x18e, 0x117, 0x18f], "B": [0x18e, 0x109, 0x117],
          "C": [0x18e, 0x109, 0x117], "D": [0x18e, 0x109, 0x117, 0x12a, 0x18f]}
RMW_FORMS = frozenset(("rolb-page", "andb-page-a", "orb-page-imm8"))


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def derived_profile(request):
    data = request["data"]
    word = data[str(0x196)] | data[str(0x197)] << 8
    return ("A" if word < 0xc0 else "B" if data[str(0x12a)] & 0x80
            else "C" if data[str(0x124)] & 0x20 else "D")


def independent_incompatibility(request):
    """Reference effect inventory only; no production decode or Cpu is called."""
    profile = derived_profile(request)
    effects = reference.reference_effect(request)
    denied = []
    for address, width, *_ in effects["reads"]:
        if (int(address, 16), width) not in READS[profile]:
            denied.append({"operation": "read", "address": int(address, 16), "width": width})
    for address, *_ in effects["writes"]:
        if int(address, 16) not in WRITES[profile]:
            denied.append({"operation": "write", "address": int(address, 16), "width": 8})
    return denied


def build_corpus():
    rows = []
    original = historical.build_corpus()
    assert len(original) == 468
    for request in original:
        reference.validate_request(request)
        denied = independent_incompatibility(request)
        rows.append({"request": deepcopy(request), "profile": derived_profile(request),
                     "source_family": "ExactM2boFrozenContext",
                     "source_case_id": request["case_id"],
                     "expected_admission": "StricterPermissionContextIncompatible" if denied else "Accepted",
                     "denied_effects": denied})
    assert sum(bool(row["denied_effects"]) for row in rows) == 84
    for row in list(rows):
        if not row["denied_effects"]:
            continue
        request = deepcopy(row["request"])
        request["case_id"] = "m2bp-predicate-D-" + request["case_id"]
        request["family"] = "m2bp-predicate-compatible-D"
        # Explicit independent NEW inputs, not a mutation/replacement of old
        # evidence. Instruction, flags, accumulator, aliases and all pointing
        # contexts stay unchanged. No composite reachability is asserted.
        request["data"][str(0x196)] = 0xc0
        request["data"][str(0x197)] = 0
        request["data"][str(0x12a)] &= 0x7f
        request["data"][str(0x124)] &= 0xdf
        assert derived_profile(request) == "D" and not independent_incompatibility(request)
        rows.append({"request": request, "profile": "D",
                     "source_family": "NewExplicitPredicateCompatibleControl",
                     "source_case_id": row["request"]["case_id"],
                     "expected_admission": "Accepted", "denied_effects": []})
    assert len(rows) == 552 and len({row["request"]["case_id"] for row in rows}) == 552
    assert sum(row["expected_admission"] == "Accepted" for row in rows) == 468
    assert len({row["request"]["form"] for row in rows if row["expected_admission"] == "Accepted"}) == 16
    # Neither original M2bo input digest nor a single original byte is changed.
    assert [row["request"] for row in rows[:468]] == original
    return rows


def coverage(rows=None):
    rows = build_corpus() if rows is None else rows
    accepted = [row for row in rows if row["expected_admission"] == "Accepted"]
    return {"originalM2boContexts": 468, "unchangedCompatibleM2boContexts": 384,
            "unchangedIncompatibleM2boAdmissionControls": 84,
            "newPredicateCompatibleControls": 84, "positiveExecutions": 468,
            "totalClosedInputs": 552, "internalSfPositivePairs": 234,
            "positiveForms": dict(sorted(Counter(row["request"]["form"] for row in accepted).items())),
            "positiveProfiles": dict(sorted(Counter(row["profile"] for row in accepted).items())),
            "physicalEntryPc": 4096, "logicalEntryPc": 4096, "relocation": False,
            "oneStepPerPositive": True, "compositeReachabilityClaimed": False,
            "originalM2boRequestsSha256": sha256(b"".join(canonical(row["request"]) + b"\n"
                                                          for row in rows[:468])).hexdigest(),
            "closedInputsSha256": sha256(canonical(rows)).hexdigest(),
            "cpuExecutionsDuringGeneration": 0}


def admission_mutations(rows=None):
    """Exact finite malformed/admission inputs, not expected status mutations."""
    rows = build_corpus() if rows is None else rows
    template = deepcopy(next(row for row in rows if row["expected_admission"] == "Accepted"))
    result = []

    def add(identifier, code, detail, mutate, *, metadata_only=False):
        item = deepcopy(template)
        mutate(item)
        result.append({"id": identifier, "input": item, "metadata_only": metadata_only,
                       "expected": {"kind": "admission_refusal", "case_id": item["request"]["case_id"],
                                    "accepted": False, "error": {"code": code, "detail": detail},
                                    "cpu_instances": 0, "bus_instances": 0, "actual_step_calls": 0}})

    shape = "historical input identity; actual opt-in PC1000/budget1/scratchA5"
    aliases = "A/PSW/named flags/OtherPSW/SCB"
    frozen = "full typed input must match immutable allowlist"
    add("wrong-entry-pc", "WrongOneStepScope", shape, lambda row: row["request"]["entry"].update(pc=0))
    add("wrong-historical-relocation-metadata", "WrongOneStepScope", shape,
        lambda row: row["request"].update(physical_entry_pc=4096), metadata_only=True)
    add("wrong-budget", "WrongOneStepScope", shape, lambda row: row["request"].update(budget=16))
    add("wrong-invented-scratch", "WrongOneStepScope", shape, lambda row: row["request"].update(scratch=0))
    add("forged-path-profile", "ForgedPermissionProfile", "profile differs from validated entry predicate",
        lambda row: row.update(profile="A"))
    add("conflicting-al", "ConflictingCpuAliases", aliases, lambda row: row["request"]["entry"].update(al=0))
    add("conflicting-ah", "ConflictingCpuAliases", aliases, lambda row: row["request"]["entry"].update(ah=0))
    add("conflicting-scb", "ConflictingCpuAliases", aliases, lambda row: row["request"]["entry"].update(scb=7))
    add("conflicting-other-psw", "ConflictingCpuAliases", aliases, lambda row: row["request"]["entry"].update(other_psw=0))
    add("conflicting-local-r", "ConflictingLocalAliases", "rN and DATA0108..010F",
        lambda row: row["request"]["entry"]["local_r"].__setitem__(0, row["request"]["entry"]["local_r"][0] ^ 1))
    add("conflicting-local-er", "ConflictingLocalAliases", "erN and r pair",
        lambda row: row["request"]["entry"]["local_er"].__setitem__(0, row["request"]["entry"]["local_er"][0] ^ 256))
    add("wrong-lrb", "InvalidEntryScope", "explicit PC1000/LRB0021/nonhalted/invented snapshot required",
        lambda row: row["request"]["entry"].update(lrb=0))
    add("missing-data", "IncompleteDataInventory", "exact inventoried sixteen bytes",
        lambda row: row["request"]["data"].pop(str(0x117)))
    add("unknown-microfixture", "UnknownMicrofixture", "sealed invented fixture ID required",
        lambda row: row["request"].update(fixture_id="not-reviewed"))
    add("wrong-content-digest", "WrongContentDigest", "immutable actual invented content SHA256",
        lambda row: row["request"].update(content_digest="0" * 64))
    add("wrong-length", "WrongInstructionLength", "one exact instruction plus explicit six-byte total guard extent",
        lambda row: row["request"].update(expected_length=5))
    add("wrong-decoded-index", "FrozenInputMismatch", frozen,
        lambda row: row["request"].update(expected_decoded_index=748))
    add("unknown-closed-case", "UnknownClosedCase", "no arbitrary instruction/ROM/input admission",
        lambda row: row["request"].update(case_id="not-in-closed-corpus"))
    add("unknown-form", "MalformedRequest", "closed typed input schema refused",
        lambda row: row["request"].update(form="arbitrary-opcode-form"))
    add("undeclared-ssP-context", "FrozenInputMismatch", frozen,
        lambda row: row["request"]["entry"].update(ssp=row["request"]["entry"]["ssp"] ^ 2))
    add("forged-source-classification", "FrozenInputMismatch", frozen,
        lambda row: row.update(source_family="ActualOriginalRom"), metadata_only=True)
    add("arbitrary-program-length", "WrongInstructionLength", "one exact instruction plus explicit six-byte total guard extent",
        lambda row: row["request"].update(bytes=[0xa5] * 51, guards=[], expected_length=51))
    psw = template["request"]["entry"]["psw"] & ~8
    add("incompatible-canonical-psw", "NotRepresentableByCurrentCanonicalRustCpu", f"preserve expected {psw:04X}",
        lambda row: historical.own_aliases(row["request"]["entry"], row["request"]["data"], psw=psw))
    add("invented-hardware-sf-value", "SfUncertaintyRequired", "architectural SF remains opaque unknown",
        lambda row: row["request"]["entry"]["sf"].update(value=True))
    add("invented-hardware-sf-meaning", "SfUncertaintyRequired", "architectural SF remains opaque unknown",
        lambda row: row["request"]["entry"]["sf"].update(meaning="invented-physical-flag"))
    assert len(result) == 25 and sum(row["metadata_only"] for row in result) == 2
    return result
