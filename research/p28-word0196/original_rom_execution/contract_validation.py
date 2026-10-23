"""Validate the closed M2bt declaration and its supplied active source join.

No CPU/process/private-input interface is present. A static contract is never
runtime evidence or authorization for a preservation exception. Current hashes
arrive from the complete independently checked source join, avoiding self-hash
cycles inside this declaration.
"""
from __future__ import annotations

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
import re

from . import corpus

CONTRACT_PATH = Path(__file__).with_name("contract.json")
CONTRACT_CANONICAL_SHA256 = "36eb382451e2b1921ce3bf3b1f4b46d2584c53b071ad2fec8f7ed6530ce9216c"
BASE = "4196153c6bcda3da5b164db752a8be4011c4e598"
FROZEN_DIRECTORY_PLACEHOLDERS = frozenset({
    "private/oracle/.gitkeep", "private/reports/.gitkeep", "private/roms/.gitkeep",
})
FROZEN_INPUTS = (
    {"path": "research/p28-word0196/original_rom_boundary/contract.json", "bytes": 17557,
     "sha256": "b8a1a482dfa8f48f310db89d291014d1f4ebf83f51022cf7f70fb1dea0c1da30"},
    {"path": "research/p28-word0196/word0196_ir.json", "bytes": 32188,
     "sha256": "4fdbd6b7dbdd8f48d5a43e123ca93a33a003c22556a0c40b5296d5f409e085c4"},
    {"path": "research/p28-word0196/word0196_equivalent.c", "bytes": 8507,
     "sha256": "4b189d4ed3e97e0d197f6c558755cf056a89c1dc7122653c5c557e7ab62d76d3"},
)
PACKAGE = "research/p28-word0196/original_rom_execution/"
REQUIRED_CURRENT_PATHS = frozenset(row["path"] for row in FROZEN_INPUTS) | frozenset({
    "AGENTS.md", "rust/p28-slice-runner/Cargo.toml",
    "rust/p28-slice-runner/src/cpu.rs", "rust/p28-slice-runner/src/bus.rs",
    "rust/p28-slice-runner/src/decoder.rs", "rust/p28-slice-runner/src/exec.rs",
    "rust/p28-slice-runner/src/audit.rs", "rust/p28-slice-runner/src/audit_bus.rs",
    "rust/p28-slice-runner/src/audit_original_rom.rs",
    "rust/p28-slice-runner/src/audit_original_rom_tests.rs",
    "rust/p28-slice-runner/src/bin/m2bt_original_rom.rs",
    "research/p28-word0196/validate_original_rom_execution.py",
}) | frozenset(PACKAGE + name for name in (
    "__init__.py", "admission.py", "binding.py", "build_guard.py", "checkpoint.py",
    "corpus.py", "oracle.py", "verify.py", "source_guard.py", "contract.json",
    "contract_validation.py",
))


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                      allow_nan=False).encode("ascii") + b"\n"


def need(condition, rule):
    if condition is not True:
        raise ValueError(rule)


def load_contract():
    def unique(items):
        result = {}
        for key, value in items:
            need(key not in result, "DuplicateContractKey")
            result[key] = value
        return result
    raw = CONTRACT_PATH.read_bytes()
    need(len(raw) <= 65536, "BoundedContractRequired")
    return json.loads(raw.decode("utf-8", "strict"), object_pairs_hook=unique,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError("NonfiniteContractValue")))


def validate_source_bindings(rows):
    need(type(rows) is list and 934 <= len(rows) <= 10000, "CompleteActiveSourceJoinRequired")
    names, by_name = [], {}
    for row in rows:
        need(type(row) is dict and set(row) == {"path", "mode", "bytes", "sha256"},
             "ClosedSourceBindingRow")
        name = row["path"]
        need(type(name) is str and bool(name) and "\\" not in name and ":" not in name
             and not any(ord(character) < 32 for character in name), "CanonicalSourceBindingPath")
        path = PurePosixPath(name)
        need(not path.is_absolute() and path.as_posix() == name and ".." not in path.parts,
             "CanonicalSourceBindingPath")
        if name.startswith(("private/", "artifacts/")):
            # These three one-LF directory placeholders are already tracked in
            # the exact M2bs base. No private payload or new path is admitted.
            need(name in FROZEN_DIRECTORY_PLACEHOLDERS and row["mode"] == "100644"
                 and type(row["bytes"]) is int and row["bytes"] == 1
                 and row["sha256"] == sha256(b"\n").hexdigest(), "CanonicalSourceBindingPath")
        need(row["mode"] in ("100644", "100755") and type(row["bytes"]) is int
             and row["bytes"] >= 0 and type(row["sha256"]) is str
             and re.fullmatch(r"[0-9a-f]{64}", row["sha256"]) is not None,
             "SourceBindingDomain")
        names.append(name)
        need(name not in by_name, "DuplicateSourceBindingPath")
        by_name[name] = row
    need(names == sorted(names), "OrderedSourceBindingsRequired")
    need(REQUIRED_CURRENT_PATHS <= set(by_name), "RequiredExecutionSourceBindingMissing")
    for frozen in FROZEN_INPUTS:
        row = by_name[frozen["path"]]
        need({key: row[key] for key in frozen} == frozen and row["mode"] == "100644",
             "FrozenIndependentSourceIdentityChanged:" + frozen["path"])
    return {"sourceBindingsVerified": True, "sourceBindingCount": len(rows),
            # Active Git/source joins deliberately hash canonical JSON without
            # the publication LF. Contract-document digests use their own LF.
            "sourceFingerprintSha256": sha256(canonical(rows)[:-1]).hexdigest()}


def validate_contract(contract=None, *, source_bindings=None):
    declaration = load_contract() if contract is None else contract
    need(type(declaration) is dict, "ClosedContractObjectRequired")
    need(sha256(canonical(declaration)).hexdigest() == CONTRACT_CANONICAL_SHA256,
         "ReviewedClosedProtocolDeclarationChanged")
    need(type(declaration["schemaVersion"]) is int and declaration["schemaVersion"] == 1
         and declaration["milestone"] == "M2bt" and declaration["baseCommit"] == BASE,
         "ExactM2btBaseContractRequired")
    need(declaration["sourceBindings"] == list(FROZEN_INPUTS), "FrozenIndependentInputsRequired")
    cases = list(corpus.iter_cases())
    need(len(cases) == declaration["corpus"]["publicCases"] == 64, "ClosedPublicCorpusCount")
    need(len({case["case_id"] for case in cases}) == 64, "UniquePublicCaseIdsRequired")
    need(set(case["path"] for case in cases) == {"A", "B", "C", "D"}, "FourPathCoverageRequired")
    need(Counter(case["family"] for case in cases) == Counter({
        name: count * 2 for name, count in declaration["corpus"]["familyBaseCounts"].items()}),
        "ClosedCorpusFamilyCounts")
    pairs = {}
    for case in cases:
        corpus.validate_case(case)
        need(case["budget"] == declaration["paths"][case["path"]]["retirements"],
             "ExactOriginalInstructionBudgetRequired")
        stem = case["case_id"].rsplit("-sf", 1)[0]
        pairs.setdefault(stem, []).append(case["internal_sf"])
    need(len(pairs) == 32 and all(values == [False, True] for values in pairs.values()),
         "PairedInternalHostSfExperimentsRequired")
    join = {"sourceBindingsVerified": False, "sourceBindingCount": None,
            "sourceFingerprintSha256": None}
    if source_bindings is not None:
        join = validate_source_bindings(source_bindings)
    return {"passed": True, "classification": "StaticProtocolAndSourceJoin_NotRuntimeEvidence",
            "contractCanonicalSha256": CONTRACT_CANONICAL_SHA256, "baseCommit": BASE,
            "publicCasesSpecifiedAndMathematicallyChecked": 64, "privateCasesSpecified": 70,
            "privateHistoricalCompletionsVerifiedByThisFunction": False,
            "originalSites": 18, "pathInstructionCounts": {"A": 10, "B": 12, "C": 13, "D": 15},
            "stopBeforePcs": [0x5596, 0x55C5], "actualCpuExecutions": 0,
            "originalRomIdentityVerifiedByThisFunction": False,
            "preservationExceptionAuthorizedByThisContract": False,
            "firmwareReady": False, **join}
