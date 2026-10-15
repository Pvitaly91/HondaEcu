#!/usr/bin/env python3
"""M2bm actual Rust orchestration and independent result verification.

Pinned contracts and independently sealed expectations are verified before
actual sequential Cargo build/tests. Importing this module does not run Cargo
or CPU probes. A contract contains obligations, never a PASS.
"""

from __future__ import annotations

import argparse
import base64
from copy import deepcopy
from hashlib import sha256
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import subprocess
import sys
import time
import tomllib


BASE = "7c37185a104348685d7604b74bf885057a95149d"
BRANCH = "codex/p28-word0196-rust-synthetic-adapter-m2bm"
CRATE = "research/p28-word0196/rust-synthetic-adapter"
CONTRACT = "research/p28-word0196/synthetic_rust_adapter_contract.json"
VALIDATOR = "research/p28-word0196/validate_synthetic_rust_adapter_contract.py"
DOCUMENT = "docs/M2BM_WORD0196_RUST_SYNTHETIC_ADAPTER.md"
FIXTURE = CRATE + "/tests/fixtures/microprobe_expectations.json"
ORACLE = "research/p28-word0196/synthetic_adapter_feasibility_oracle.py"
ORACLE_SHA = "4414f6de4fe705f4b097a00c7aed3fac951d5951f050589f3276b21e4c406268"
# Raw public fixture bytes may use LF while the private projection used CRLF.
# Its final raw-byte pin is mandatory in the reviewed contract; expectations are
# still the independent pre-result projection, not inferred from Rust output.
COMPOSITE_SHA = "91ffb46922def91764f5d4da166ef2cfc9834ed0effcc051d3f97246fa147ab1"
PROVENANCE = "InventedOnly_NoNativeGenerationOwner"
SF_UNKNOWN = {"status": "SFMeaningStorageNotEstablished", "value": None,
              "meaning": None, "storage": None, "width_bits": None}
LEVELS = ["ModelVerified", "RustImplementationCompiled", "RustUnitTestsPassed",
          "MicroprobeRuntimeObserved", "ProductionCpuIntegrated",
          "FullCompositeExecutionObserved"]
MARKERS = ("M2BM_RUNTIME_JSON", "M2BM_COMPONENT_JSON")
FORM_IDENTITY = {
    "lb-a-page": ("LB A, off N8", ["F4", "N8"], "R"),
    "sllb-a": ("SLLB A", ["53"], "0"),
    "rolb-page": ("ROLB off N8", ["C4", "N8", "B7"], "U"),
    "lb-a-r0": ("LB A, r0", ["78"], "R"),
    "andb-a-page": ("ANDB A, off N8", ["D7", "N8"], "0"),
    "cmp-page-imm16": ("CMP off N8, #N16", ["B4", "N8", "C0", "NL", "NH"], "U"),
    "jlt-rel8": ("JLT rel8", ["CA", "rel8"], "U"),
    "movb-r1-page": ("MOVB r1, off N8", ["C4", "N8", "49"], "U"),
    "andb-page-a": ("ANDB off N8, A", ["C4", "N8", "D1"], "U"),
    "jbs-page-bit7": ("JBS off N8.7, rel8", ["EF", "N8", "rel8"], "U"),
    "jbs-page-bit5": ("JBS off N8.5, rel8", ["ED", "N8", "rel8"], "U"),
    "orb-page-imm8": ("ORB off N'8, #N8", ["C4", "N'8", "E0", "N8"], "U"),
    "orb-a-imm8": ("ORB A, #N8", ["E6", "N8"], "0"),
    "lb-a-imm8": ("LB A, #N8", ["77", "N8"], "R"),
    "stb-a-page": ("STB A, off N8", ["D4", "N8"], "0"),
    "j-address": ("J addr16", ["03", "addrl", "addrh"], "U"),
}
# Labels are actual Rust component case identities, not counts inferred from JSON.
CATEGORIES = [
    "ProgramOutOfRange", "ProgramDataConfusion", "FakePadding", "WrongBase",
    "WrongSha", "WrongNodeIdentity", "WrongFormId", "UnsupportedMnemonic",
    "DirectJTargetSwapped", "MissingEntryField", "IncompletePointingBanks",
    "WrongRegisterAlias", "UnauthorizedDataRead", "UnauthorizedDataWrite",
    "WrongWidth", "WrongLe16", "SameValueWriteDeduplication", "RmwWriteWithoutRead",
    "DiagnosticReadMixedIntoFunctionalJournal", "DecoderLookaheadMislabeledAsRetired",
    "OutOfRangePeekNotZero", "ExtraProgramReadAfterExit", "ZeroStepExitAccepted",
    "MultipleDirectJ", "IncompatiblePswSilentlyNormalized", "OtherPswOverwritesCf",
    "WrongScb", "SfSilentlyDefaulted", "MissingSfIndependenceEvidence",
    "SourceMismatch", "ActualM2bjStreamShapeAdmission", "OriginalRomAdmission",
    "FirmwareReadyPromotion",
]
CATEGORY_LABELS = [
    "PROGRAM out-of-range", "PROGRAM/DATA confusion", "Fake padding", "Wrong base",
    "Wrong SHA", "Wrong node identity", "Wrong FormId", "Unsupported mnemonic admitted",
    "Direct J target swapped", "Missing entry field", "Incomplete pointing banks",
    "Wrong register alias", "Unauthorized DATA read", "Unauthorized DATA write", "Wrong width",
    "Wrong LE16", "Same-value write deduplication", "RMW write without read",
    "Diagnostic read mixed into functional journal", "Decoder lookahead mislabeled as retired",
    "Out-of-range peek returns zero", "Extra PROGRAM read after exit", "Zero-step exit accepted",
    "Multiple direct J", "Incompatible PSW silently normalized", "OtherPSW overwrites CF",
    "Wrong SCB", "SF silently defaulted", "Missing SF independence evidence", "Source mismatch",
    "Actual M2bj bytes accidentally admitted", "Original ROM admitted", "FirmwareReady promotion",
]
EXPECTED_ERRORS = dict(zip(CATEGORIES, [
    "ProgramOutOfRange", "ProgramOutOfRange", "SegmentIdentityMismatch", "SegmentIdentityMismatch",
    "WrongContentDigest", "NodeIdentityMismatch", "MicrofixtureBindingMismatch", "WrongExactForm",
    "MicrofixtureBindingMismatch", "MissingOrUnknownEntryField", "MissingOrUnknownEntryField",
    "ConflictingLocalAliases", "UnauthorizedDataRead", "UnauthorizedDataWrite", "UnauthorizedDataRead",
    "FunctionalJournalMismatch", "FunctionalJournalMismatch", "RmwReadRequired", "FunctionalJournalMismatch",
    "WrongSelectedExtent", "ProgramOutOfRange", "FetchAfterRetirement", "UnprovedExternalExit",
    "ExtraRetirementOrTransfer", "NotRepresentableByCurrentCanonicalRustCpu", "ConflictingCpuAliases",
    "ConflictingCpuAliases", "SfUncertaintyRequired", "MissingSfIndependenceEvidence", "SourceBindingMismatch",
    "ForbiddenProgramInput", "ForbiddenProgramInput", "MissingOrUnknownEntryField",
]))
EXPECTED_ERRORS.update(DataJournalAddressOverflow="FunctionalJournalMismatch",
                       DataJournalAfterFault="RmwReadRequired",
                       ProductionDecoderOutOfRangeSentinel="ProgramOutOfRange")
METADATA_CASES = {"FakePadding", "WrongBase", "WrongNodeIdentity", "WrongFormId", "UnsupportedMnemonic",
                  "MissingEntryField", "IncompletePointingBanks", "WrongRegisterAlias", "OtherPswOverwritesCf",
                  "WrongScb", "SfSilentlyDefaulted", "MissingSfIndependenceEvidence", "OriginalRomAdmission",
                  "FirmwareReadyPromotion"}
PRODUCTION_NAMES = ["cpu.rs", "bus.rs", "decoder.rs", "full_decoder.rs", "exec.rs",
                    "runner.rs", "operand.rs", "lib.rs", "Cargo.toml", "protocol.rs", "main.rs"]
# Final immutable production Cargo.toml/Cargo.lock bindings are filled from the
# already captured preflight below; no new M2bm source pins are fabricated here.
PRODUCTION_MANIFEST_PINS = {
    "rust/p28-slice-runner/Cargo.toml": {
        "bytes": 250,
        "sha256": "62a898777d81271760d1adb88b38cc021170b84872b14791a97028989fcb82ff"
    },
    "rust/p28-slice-runner/Cargo.lock": {
        "bytes": 2412,
        "sha256": "93ec94839f19ff2954cc95d0892940128459f17e84d409af0623da8be9fa9efe"
    },
    "rust/p28-slice-runner/src/cpu.rs": {
        "bytes": 5281,
        "sha256": "b12a0b3388a7d34201888a0a6f948263dcf1c7bebca1801056e176d871184d3b"
    },
    "rust/p28-slice-runner/src/bus.rs": {
        "bytes": 35151,
        "sha256": "556dceff088ecdfac7f05469a03251896c81fdb1979394bdbae4c59e1b30445a"
    },
    "rust/p28-slice-runner/src/decoder.rs": {
        "bytes": 9735,
        "sha256": "1120cc37cee9ec23f1f596c72ff8dd5bf372204495d2b5e00cc044dfe2ea3aa4"
    },
    "rust/p28-slice-runner/src/full_decoder.rs": {
        "bytes": 240468,
        "sha256": "77697d4b0e3c90372326156bf1a8544486d07f4aa8f93c67cf9e5f2af6c7eff1"
    },
    "rust/p28-slice-runner/src/exec.rs": {
        "bytes": 77117,
        "sha256": "e7ef7d04fb28c838b20c52f352c89fc7ea8780d5a2e1d19f7178dec5109324aa"
    },
    "rust/p28-slice-runner/src/runner.rs": {
        "bytes": 43177,
        "sha256": "c93026e5d1152bdb8196d9a67a6dc071fd704000351b13db668eab1bff255727"
    },
    "rust/p28-slice-runner/src/operand.rs": {
        "bytes": 7079,
        "sha256": "c3e7b418b81b4fa0becfa2ec2be741a4b0929994831ebb89e829698d289bb48f"
    },
    "rust/p28-slice-runner/src/lib.rs": {
        "bytes": 1986,
        "sha256": "80b141f1d2e17852ab4691515d645245881bd2fad30dd94a795f5d22aee3e376"
    },
    "rust/p28-slice-runner/src/protocol.rs": {
        "bytes": 14537,
        "sha256": "2be02025de40df2336e3c442a68924d98539ecc57147317b01808200c42a023c"
    },
    "rust/p28-slice-runner/src/main.rs": {
        "bytes": 2347,
        "sha256": "be5a42edf56fa9cdd798b865b8cd81b8c602be329ca9fadc49f6865535ab561f"
    }
}


class ValidationFailure(Exception):
    def __init__(self, scope, message, expected=None, actual=None):
        super().__init__(f"{scope}: {message}")
        self.record = {"scope": scope, "message": message,
                       "expected": expected, "actual": actual}


def require(condition, scope, message, expected=None, actual=None):
    if not condition:
        raise ValidationFailure(scope, message, expected, actual)


def equal(actual, expected, scope):
    # Python bool/int equality is intentionally insufficient for JSON evidence.
    if type(actual) is not type(expected):
        raise ValidationFailure(scope, "JSON type mismatch", type(expected).__name__, type(actual).__name__)
    if isinstance(expected, dict):
        require(actual.keys() == expected.keys(), scope, "closed object field mismatch",
                sorted(expected), sorted(actual))
        for key in expected:
            equal(actual[key], expected[key], f"{scope}.{key}")
    elif isinstance(expected, list):
        require(len(actual) == len(expected), scope, "array length mismatch", len(expected), len(actual))
        for index, (left, right) in enumerate(zip(actual, expected)):
            equal(left, right, f"{scope}[{index}]")
    else:
        if isinstance(expected, set):
            require(actual == expected, scope, "set mismatch", sorted(expected), sorted(actual))
            return
        require(actual == expected, scope, "value mismatch", expected, actual)


def uint(value, maximum, scope):
    require(type(value) is int and 0 <= value <= maximum, scope, "unsigned integer required")
    return value


def no_duplicates(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "JSON", "duplicate object key", actual=key)
        result[key] = value
    return result


def strict_json(text):
    def refused(value):
        raise ValidationFailure("JSON", "noninteger/nonfinite JSON number", actual=value)
    value = json.loads(text, object_pairs_hook=no_duplicates, parse_float=refused, parse_constant=refused)
    def bounded(node, depth=0):
        require(depth <= 64, "JSON", "excessive depth")
        if type(node) is int:
            require(-(1 << 63) <= node <= (1 << 64) - 1, "JSON", "integer outside evidence range")
        elif isinstance(node, dict):
            for item in node.values():
                bounded(item, depth + 1)
        elif isinstance(node, list):
            for item in node:
                bounded(item, depth + 1)
    bounded(value)
    return value


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")


def repo_root():
    for directory in Path(__file__).resolve().parents:
        if (directory / "rust/p28-slice-runner/src/cpu.rs").is_file() and (directory / ".git").exists():
            return directory
    raise ValidationFailure("Repository", "workspace root absent")


def public_path(root, relative):
    require(type(relative) is str and "\\" not in relative, "SourcePath", "canonical relative public path required")
    parts = PurePosixPath(relative)
    require(not parts.is_absolute() and parts.parts and all(p not in (".", "..") for p in parts.parts),
            "SourcePath", "unsafe relative path", actual=relative)
    path = root.joinpath(*parts.parts)
    require(path.resolve().is_relative_to(root.resolve()) and not path.is_symlink(), "SourcePath", "symlink/outside workspace")
    return path


def binding(root, relative):
    path = public_path(root, relative)
    before = path.stat()
    digest = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    after = path.stat()
    require((before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns),
            "SourceBinding", "file changed while hashing", actual=relative)
    return {"path": relative, "bytes": after.st_size, "sha256": digest.hexdigest()}


def verify_bindings(root, rows, expected_count=None):
    require(type(rows) is list and rows, "SourceBinding", "nonempty reviewed bindings required")
    if expected_count is not None:
        equal(len(rows), expected_count, "SourceBinding.count")
    seen = set()
    actual = []
    for row in rows:
        require(type(row) is dict and set(row) == {"path", "bytes", "sha256"}, "SourceBinding", "closed binding object required")
        require(row["path"] not in seen and re.fullmatch(r"[0-9a-f]{64}", row["sha256"] or ""), "SourceBinding", "duplicate/missing exact SHA")
        uint(row["bytes"], 1 << 40, "SourceBinding.bytes")
        seen.add(row["path"])
        observed = binding(root, row["path"])
        equal(observed, row, "SourceBinding." + row["path"])
        actual.append(observed)
    return actual


def validate_contract(contract):
    for name in ("passed", "actualResults", "actualStatus", "finalSha"):
        require(name not in contract, "Contract", "obligations must not declare actual outcome", actual=name)
    for key, value in (("schemaVersion", 1), ("milestone", "M2bm"), ("exactBase", BASE), ("branch", BRANCH)):
        equal(contract.get(key), value, "Contract." + key)
    require(type(contract.get("scope")) is str and contract["scope"], "Contract", "explicit scope required")
    architecture = contract.get("architecture", {})
    for key, value in (("route", "B"), ("productionCpuStateAndDecoder", True),
                       ("productionBus", False), ("productionExecStep", False),
                       ("productionRunner", False), ("productionSourceChangesAllowed", False)):
        equal(architecture.get(key), value, "Contract.architecture." + key)
    for name, count in (("expectedUnitTestCount", 35), ("expectedIntegrationTestCount", 1),
                        ("expectedRustTestCount", 36)):
        equal(contract.get(name), count, "Contract." + name)
    categories = contract.get("mandatoryNegativeCategories")
    require(type(categories) is list and len(categories) == 33, "Contract", "all33 required categories required")
    actual_categories = [row if type(row) is str else row.get("rustCategory", row.get("id", row.get("label"))) for row in categories]
    labels = dict(zip(CATEGORIES, CATEGORY_LABELS))
    actual_categories = [labels.get(value, value) for value in actual_categories]
    equal(sorted(actual_categories), sorted(CATEGORY_LABELS), "Contract.mandatoryNegativeCategories")
    capabilities = contract.get("capabilities")
    require(type(capabilities) is list and len(capabilities) == 6, "Contract", "six capability obligations required")
    equal(sorted(row.get("id") for row in capabilities), list("ABCDEF"), "Contract.capabilityIds")
    equal(contract.get("evidenceLevelNames"), LEVELS, "Contract.evidenceLevelNames")
    for capability in capabilities:
        require("passed" not in capability and "actualResults" not in capability, "Contract", "capability metadata cannot declare PASS")
    for name, value in (("inputs", 65536), ("representableLow12", 128), ("incompatibleLow12", 3968),
                        ("representableFull", 2048), ("incompatibleFull", 63488)):
        equal(contract.get("psw", {}).get(name), value, "Contract.psw." + name)
    equal(contract.get("sfStatus"), "SFMeaningStorageNotEstablished", "Contract.sfStatus")
    for name, value in (("m2bjCompositeExecutions", 0), ("actualROMExecutions", 0),
                        ("targetObjects", 0), ("targetHEX", 0), ("FirmwareBIN", 0),
                        ("FirmwareReady", False), ("nativeExitIsolationEstablished", False)):
        equal(contract.get("runtimeExclusions", {}).get(name), value, "Contract.runtimeExclusions." + name)
    require(type(contract.get("newSourceBindings")) is list and contract["newSourceBindings"],
            "Contract", "final reviewed new-source pins absent; refuse unreviewed draft execution")
    require(all(row["path"] != CONTRACT for row in contract["newSourceBindings"]), "Contract", "contract cannot bind its own hash")
    paths = {row["path"] for row in contract["newSourceBindings"]}
    require({VALIDATOR, DOCUMENT, FIXTURE, CRATE + "/Cargo.toml", CRATE + "/Cargo.lock",
             CRATE + "/src/lib.rs", CRATE + "/tests/independent_expectations.rs"} <= paths,
            "Contract", "all new implementation/fixture/validator/doc pins required")
    require(all(path.startswith(CRATE + "/") or path in (VALIDATOR, DOCUMENT) for path in paths),
            "Contract", "new binding outside exact current public scope")


def rust_tokens(text):
    """Small strict lexical policy pass, not a general Rust sandbox/parser."""
    result = []
    index = 0
    while index < len(text):
        if text[index].isspace():
            index += 1
        elif text.startswith("//", index):
            end = text.find("\n", index)
            index = len(text) if end < 0 else end + 1
        elif text.startswith("/*", index):
            depth = 1
            index += 2
            while depth:
                require(index < len(text), "RustPolicy", "unterminated comment")
                if text.startswith("/*", index):
                    depth += 1; index += 2
                elif text.startswith("*/", index):
                    depth -= 1; index += 2
                else:
                    index += 1
        else:
            raw = re.match(r'(?:br|r)(#*)"', text[index:])
            if raw:
                start = index + raw.end()
                end = text.find('"' + raw.group(1), start)
                require(end >= 0, "RustPolicy", "unterminated raw string")
                result.append(("string", text[start:end])); index = end + 1 + len(raw.group(1))
                continue
            if text[index] == '"':
                start = index; index += 1
                while index < len(text) and text[index] != '"':
                    index += 2 if text[index] == "\\" else 1
                require(index < len(text), "RustPolicy", "unterminated string")
                value = text[start + 1:index]
                result.append(("string", value)); index += 1
                continue
            char = re.match(r"'(?:\\.|[^'\\\n])'", text[index:])
            if char:
                result.append(("char", char.group())); index += char.end(); continue
            identifier = re.match(r"[A-Za-z_][A-Za-z_0-9]*", text[index:])
            if identifier:
                result.append(("identifier", identifier.group())); index += identifier.end()
            else:
                require(ord(text[index]) < 128, "RustPolicy", "non-ASCII executable token not reviewed")
                result.append(("punctuation", text[index])); index += 1
    return result


def source_policy(root, contract):
    new_rows = contract["newSourceBindings"]
    pinned = {row["path"] for row in new_rows}
    crate_path = public_path(root, CRATE)
    actual_files = {path.relative_to(root).as_posix() for path in crate_path.rglob("*") if path.is_file()}
    require(actual_files == {path for path in pinned if path.startswith(CRATE + "/")}, "RustPolicy", "new crate file inventory differs from reviewed pins")
    require(not any(path.endswith("/main.rs") or path.endswith("/build.rs") or "/examples/" in path or "/benches/" in path for path in actual_files), "RustPolicy", "library-only crate; no executable/build script/benchmark/example")
    manifest = tomllib.loads((crate_path / "Cargo.toml").read_text(encoding="utf-8"))
    require(set(manifest) <= {"package", "dependencies", "profile"}, "RustPolicy", "unreviewed Cargo configuration")
    package = manifest["package"]
    for name, value in (("name", "p28-research-synthetic-adapter"), ("edition", "2021"), ("rust-version", "1.85.1"), ("publish", False)):
        equal(package.get(name), value, "RustPolicy.package." + name)
    require(not set(package).intersection({"build", "links", "default-run", "autobins"}), "RustPolicy", "package build/entry hook prohibited")
    equal(manifest.get("dependencies"), {
        "p28-slice-runner": {"path": "../../../rust/p28-slice-runner"},
        "serde": {"version": "=1.0.219", "features": ["derive"]},
        "serde_json": "=1.0.140"}, "RustPolicy.dependencies")
    equal(manifest.get("profile", {}).get("release", {}).get("overflow-checks"), True, "RustPolicy.overflowChecks")
    allowed_include = {public_path(root, "rust/p28-slice-runner/" + (name if name == "Cargo.toml" else "src/" + name)).resolve() for name in PRODUCTION_NAMES}
    allowed_include.add(public_path(root, FIXTURE).resolve())
    blocked_ids = {"unsafe", "extern", "asm", "global_asm", "Command", "OpenOptions", "File", "TcpStream", "TcpListener", "UdpSocket", "Bus", "fs", "process", "net", "ffi", "env", "read_to_string", "read_to_end", "write_all"}
    # Assemble policy sentinels so whole-file leak checks do not mistake the
    # checker's own deny vocabulary for leaked input. Exact checks are unchanged.
    deny = ("original" + "Hex", "private/" + "oracle/", "baseline-" + "binding.json", "label_" + "556f:")
    checked = []
    for relative in sorted(actual_files):
        path = public_path(root, relative)
        require(path.suffix in (".rs", ".json", ".toml", ".lock"), "RustPolicy", "unexpected crate artifact", actual=relative)
        text = path.read_text(encoding="utf-8")
        require(not re.search(r"(?:ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|-----BEGIN [^-]*PRIVATE KEY-----|[A-Z]:[\\/]Users[\\/])", text), "Privacy", "credential/local-user marker", actual=relative)
        require(not any(token in text for token in deny), "Privacy", "private/OEM input marker", actual=relative)
        if path.suffix != ".rs":
            continue
        tokens = rust_tokens(text)
        identifiers = {value for kind, value in tokens if kind == "identifier"}
        require(not identifiers.intersection(blocked_ids), "RustPolicy", "forbidden execution/unsafe/FS/network primitive", actual=relative)
        code = " ".join(value if kind != "string" else "STRING_LITERAL" for kind, value in tokens)
        require(not re.search(r"\bstd\s*:\s*:\s*(?:fs|process|net|ffi|os|env)\b|\bp28_slice_runner\s*:\s*:\s*(?:exec|bus|runner|protocol)\b|\bexec\s*:\s*:\s*step\b|#\s*\[\s*path\b", code), "RustPolicy", "FS/process/ROM loader/production executor/module bypass", actual=relative)
        for use in re.finditer(r"\buse\s+([^;]+);", code):
            declaration = use.group(1)
            if "p28_slice_runner" in declaration:
                require(not re.search(r"\b(exec|bus|runner|protocol|main)\b|\*", declaration), "RustPolicy", "unreviewed production import", actual=relative)
        for index, (kind, value) in enumerate(tokens):
            if kind == "identifier" and value in ("include", "include_bytes"):
                raise ValidationFailure("RustPolicy", "unreviewed source/ROM inclusion macro", actual=relative)
            if kind == "identifier" and value == "include_str":
                following = tokens[index + 1:index + 5]
                require(len(following) == 4 and [item[1] for item in following[:2]] == ["!", "("] and following[2][0] == "string" and following[3][1] == ")", "RustPolicy", "literal include_str only")
                target = (path.parent / following[2][1]).resolve()
                require(target in allowed_include, "RustPolicy", "unreviewed include_str target", actual=following[2][1])
        checked.append(relative)
    require("# ! [ forbid ( unsafe_code ) ]" in " ".join(value for _, value in rust_tokens((crate_path / "src/lib.rs").read_text(encoding="utf-8"))), "RustPolicy", "crate forbid unsafe_code attribute required")
    return {"classification": "LexicalDefenseInDepthForPinnedReviewedSources_NotGeneralRustSandbox", "checkedRustFiles": checked,
            "productionExecStepUsed": False, "runtimeFsProcessLoaderAllowed": False}


def hex_value(value):
    require(type(value) is str and re.fullmatch(r"[0-9A-Fa-f]{1,4}", value), "Fixture", "literal hexadecimal value required")
    return int(value, 16)


def expand_cases(fixture):
    equal(fixture.get("total_positive_contexts"), 51, "Fixture.contexts")
    equal(fixture.get("total_positive_instances"), 102, "Fixture.instances")
    equal(fixture.get("internal_sf_variants"), [False, True], "Fixture.sfVariants")
    equal(len(fixture["main_cases"]), 16, "Fixture.mainCases")
    equal(len(fixture["control_cases"]), 23, "Fixture.controls")
    equal(len(fixture["dd_cases"]), 12, "Fixture.ddCases")
    equal(len(fixture["dd_refusals"]), 4, "Fixture.ddRefusals")
    cases = deepcopy(fixture["main_cases"] + fixture["control_cases"])
    main = {row["id"]: row for row in fixture["main_cases"]}
    for dd in fixture["dd_cases"]:
        case = deepcopy(main[dd["baseCase"]])
        case["id"] = dd["id"]
        case["entryOverride"]["psw"] = dd["beforePsw"]
        case["expected"]["psw"] = dd["afterPsw"]
        cases.append(case)
    require(len(cases) == len({row["id"] for row in cases}) == 51, "Fixture", "exact51 unique contexts required")
    equal(sorted({row["form"] for row in cases}), sorted(FORM_IDENTITY), "Fixture.formCoverage")
    return cases


def state_owners(entry, a, psw, data):
    entry.update(a=a, al=a & 255, ah=a >> 8, psw=psw, other_psw=psw & 4095, scb=psw & 7)
    for name, mask in (("cf", 32768), ("zf", 16384), ("hc", 8192), ("dd", 4096)):
        entry[name] = bool(psw & mask)
    entry["local_r"] = [data[str(0x108 + n)] for n in range(8)]
    entry["local_er"] = [entry["local_r"][2*n] + 256*entry["local_r"][2*n+1] for n in range(4)]


def expected_request(fixture, case, sf):
    common = fixture["common_entry"]
    data = {str(int(address, 16)): hex_value(value) for address, value in fixture["common_data"].items()}
    data.update({str(int(address, 16)): hex_value(value) for address, value in case["dataOverride"].items()})
    entry = {name: hex_value(common[name]) for name in ("pc", "a", "al", "ah", "psw", "lrb", "ssp")}
    entry.update(pointing_banks=[{name.lower(): hex_value(bank[name]) for name in ("X1", "X2", "DP", "USP")} for bank in common["pointingBanks"]],
                 halted=False, provenance=PROVENANCE, sf=deepcopy(SF_UNKNOWN))
    state_owners(entry, hex_value(case["entryOverride"].get("a", common["a"])),
                 hex_value(case["entryOverride"].get("psw", common["psw"])), data)
    instruction = [hex_value(byte) for byte in case["bytesHex"]]
    require(1 <= len(instruction) <= 5 and len(instruction) == case["length"], "Fixture", "one short instruction required")
    guards = [0xA5 if n % 2 == 0 else 0x5A for n in range(6 - len(instruction))]
    return {"case_id": case["id"], "form": case["form"], "bytes": instruction, "guards": guards,
            "content_digest": sha256(bytes(instruction + guards)).hexdigest(), "entry": entry,
            "data": data, "path": "A" if case["form"] == "stb-a-page" else "D", "internal_sf": sf, "budget": 1}


def expected_data_journals(case):
    logical, raw = [], []
    for read in case["expected"]["reads"]:
        address, width, value, constituents = hex_value(read[0]), read[1], hex_value(read[2]), list(map(hex_value, read[3]))
        ordinal = len(logical) + 1
        raw_start = len(raw)
        raw.extend({"ordinal": raw_start + n + 1, "logical_ordinal": ordinal, "address": address + n,
                    "operation": "Read", "value": byte} for n, byte in enumerate(constituents))
        logical.append({"ordinal": ordinal, "phase": "ExecutedFunctionalDataAccess", "pc": 4096,
                        "address": address, "width": width, "operation": "Read", "value": value,
                        "old_value": None, "write_ordinal": None, "kind": None, "same_value": False,
                        "constituents": constituents})
    for write in case["expected"]["writes"]:
        address, old, value, write_ordinal, kind, same = write
        address, old, value = hex_value(address), hex_value(old), hex_value(value)
        ordinal = len(logical) + 1
        raw.append({"ordinal": len(raw) + 1, "logical_ordinal": ordinal, "address": address,
                    "operation": "Write", "value": value})
        logical.append({"ordinal": ordinal, "phase": "ExecutedFunctionalDataAccess", "pc": 4096,
                        "address": address, "width": 8, "operation": "Write", "value": value,
                        "old_value": old, "write_ordinal": write_ordinal, "kind": kind,
                        "same_value": same, "constituents": [value]})
    return logical, raw


def opcode_rows(root):
    source = public_path(root, "rust/p28-slice-runner/src/full_decoder.rs").read_text(encoding="utf-8")
    pattern = r'OpcodePattern\s*\{\s*mnemonic:\s*"([^"\n]+)",\s*dd_mode:\s*\x27([01RUS])\x27,\s*bytes_pat:\s*&\[([^\]]*)\]\s*\}'
    rows = [(mnemonic, re.findall(r'"([^"\n]*)"', byte_text), dd) for mnemonic, dd, byte_text in re.findall(pattern, source)]
    equal(len(rows), 2623, "PrimaryPatternTable.count")
    return rows


def expected_auxiliary_journals(request, case, after_data):
    # Independently reviewed instrumentation acquisition protocol: sixteen seed
    # bytes, thirty-two setup words, complete before/after diagnostic snapshots,
    # and explicit diagnostic old-value acquisitions for functional writes.
    seed = []
    for address, value in sorted(request["data"].items(), key=lambda row: int(row[0])):
        seed.append({"ordinal": len(seed) + 1, "phase": "SeedInitializationAccess",
                     "address": int(address), "width": 8, "value": value})
    pointing_bytes = {}
    for bank, values in enumerate(request["entry"]["pointing_banks"]):
        for slot, name in enumerate(("x1", "x2", "dp", "usp")):
            address, value = 0x80 + bank * 8 + slot * 2, values[name]
            seed.append({"ordinal": len(seed) + 1, "phase": "SeedInitializationAccess",
                         "address": address, "width": 16, "value": value})
            pointing_bytes[address] = value & 255
            pointing_bytes[address + 1] = value >> 8
    diagnostics = []
    def diagnostic(address, value):
        diagnostics.append({"ordinal": len(diagnostics) + 1, "phase": "DiagnosticSnapshotRead",
                            "address": address, "width": 8, "value": value})
    def snapshot(data):
        for address in range(0x80, 0xC0): diagnostic(address, pointing_bytes[address])
        for address in range(0x108, 0x110): diagnostic(address, data[str(address)])
        for address in sorted(map(int, data)): diagnostic(address, data[str(address)])
    snapshot(request["data"])
    for address, old, *_ in case["expected"]["writes"]:
        diagnostic(hex_value(address), hex_value(old))
    snapshot(after_data)
    return seed, diagnostics


def compare_observation(root, request, case, actual, patterns, observed_production):
    scope = f"Microprobe.{case['id']}.sf={request['internal_sf']}"
    require(actual.get("first_mismatch") is None, scope, "Rust first mismatch must not be promoted", actual=actual.get("first_mismatch"))
    after_data = deepcopy(request["data"])
    for address, _, value, *_ in case["expected"]["writes"]:
        after_data[str(hex_value(address))] = hex_value(value)
    after = deepcopy(request["entry"])
    state_owners(after, hex_value(case["expected"]["a"]), hex_value(case["expected"]["psw"]), after_data)
    after["pc"] = hex_value(case["expected"]["pc"])
    logical, raw = expected_data_journals(case)
    expected = {"case_id": case["id"], "provenance": PROVENANCE,
                "scope": "MicroprobeScope_NotCompositePathReachability", "before": request["entry"],
                "after": after, "before_data": request["data"], "after_data": after_data,
                "all_program_bytes": request["bytes"] + request["guards"],
                "immutable_content_digest": request["content_digest"], "selected_bytes": request["bytes"],
                "data_journal": logical, "raw_data_journal": raw, "retired_instructions": 1,
                "cpu_instances": 1, "instructions": 1, "production_exec_integrated": False,
                "m2bj_composite_executions": 0, "original_rom_executions": 0, "first_mismatch": None,
                "internal_sf_before": request["internal_sf"], "internal_sf_after": request["internal_sf"],
                "branch_taken": case["expected"]["branchTaken"],
                "external_transfer": after["pc"] if case["expected"]["external"] else None,
                "retirements": [{"ordinal": 1, "pc": 4096, "next_pc": after["pc"], "form": case["form"],
                                 "external_transfer": case["expected"]["external"]}]}
    fields = {"n8": 0, "n8_alt": 0, "n16": 0, "addr16": 0, "rel8": 0}
    instruction = request["bytes"]
    mnemonic, pattern, dd = FORM_IDENTITY[case["form"]]
    for token, byte in zip(pattern, instruction):
        if token == "N8": fields["n8"] = byte
        elif token == "N'8": fields["n8_alt"] = byte
        elif token == "NL": fields["n16"] |= byte
        elif token == "NH": fields["n16"] |= byte << 8
        elif token == "addrl": fields["addr16"] |= byte
        elif token == "addrh": fields["addr16"] |= byte << 8
        elif token == "rel8": fields["rel8"] = byte if byte < 128 else byte - 256
        else: equal(byte, int(token, 16), scope + ".primaryFixedByte")
    identities = [index for index, row in enumerate(patterns) if row == (mnemonic, pattern, dd)]
    equal(len(identities), 1, scope + ".uniquePrimaryIndex")
    expected["decode"] = {"form": case["form"], "mnemonic": mnemonic, "index": identities[0],
                          "len": len(instruction), "dd_before": request["entry"]["dd"],
                          "dd_after": after["dd"], **fields}
    for key, value in expected.items():
        equal(actual.get(key), value, scope + "." + key)
    uint(actual.get("cycles"), (1 << 64) - 1, scope + ".cycles")
    require(actual["cycles"] > 0, scope, "actual instruction cycle accounting absent")
    equal(actual.get("source_bindings"), observed_production, scope + ".compiledProductionSources")
    probes = actual.get("raw_program")
    require(type(probes) is list and probes, scope, "actual raw PROGRAM observations absent")
    selected, decoder_count, selected_phase = [], 0, False
    content = bytes(request["bytes"] + request["guards"])
    for index, event in enumerate(probes):
        equal(set(event), {"ordinal", "address", "offset", "acquired_purpose", "purpose", "value", "fault"}, scope + ".programEventFields")
        offset = uint(event["offset"], len(content) - 1, scope + ".programOffset")
        equal(event["ordinal"], index + 1, scope + ".programOrdinal")
        equal(event["address"], 4096 + offset, scope + ".programAddress")
        equal(event["value"], content[offset], scope + ".programByte")
        equal(event["fault"], None, scope + ".programFault")
        if event["acquired_purpose"] == "DecoderProbe":
            require(not selected_phase, scope, "decoder read after selected phase")
            equal(event["purpose"], "DecoderProbe" if offset < len(instruction) else "DecoderLookahead", scope + ".lookaheadPurpose")
            if not decoder_count: equal(offset, 0, scope + ".firstDecoderOffset")
            decoder_count += 1
        elif event["acquired_purpose"] == "ArchitecturalSelectedFetch":
            selected_phase = True
            equal(event["purpose"], "ArchitecturalSelectedFetch", scope + ".selectedPurpose")
            selected.append(offset)
        else:
            raise ValidationFailure(scope, "unreviewed successful acquisition purpose", actual=event["acquired_purpose"])
    require(decoder_count > 0, scope, "actual production decoder observations absent")
    equal(selected, list(range(len(instruction))), scope + ".selectedOffsets")
    for name, phase in (("seed_journal", "SeedInitializationAccess"), ("diagnostic_journal", "DiagnosticSnapshotRead")):
        events = actual.get(name)
        require(type(events) is list and events, scope, "actual auxiliary journal absent", actual=name)
        for index, event in enumerate(events):
            equal(set(event), {"ordinal", "phase", "address", "width", "value"}, scope + "." + name + ".fields")
            equal(event["ordinal"], index + 1, scope + "." + name + ".ordinal")
            equal(event["phase"], phase, scope + "." + name + ".phase")
            uint(event["address"], 65535, scope + ".auxiliaryAddress")
            uint(event["value"], 65535, scope + ".auxiliaryValue")
    expected_seed, expected_diagnostics = expected_auxiliary_journals(request, case, after_data)
    equal(actual["seed_journal"], expected_seed, scope + ".completeSetupAcquisitions")
    equal(actual["diagnostic_journal"], expected_diagnostics, scope + ".completeDiagnosticAcquisitions")
    equal(set(actual), set(expected) | {"cycles", "source_bindings", "raw_program", "seed_journal", "diagnostic_journal"}, scope + ".closedObservationFields")


def compare_runtime(root, fixture, runtime, observed_production, fixture_sha):
    require(runtime.get("first_mismatch") is None, "RustRuntime", "preserve original Rust first mismatch", actual=runtime.get("first_mismatch"))
    for name, value in (("schema_version", 1), ("positive_microprobe_contexts", 51), ("positive_cpu_instances", 102),
                        ("positive_retired_instructions", 102), ("psw_inputs_observed", 65536),
                        ("psw_cpu_instances", 65536), ("psw_observe_raw_calls", 65536),
                        ("psw_checked_calls", 65536), ("psw_retired_instructions", 0),
                        ("m2bj_composite_executions", 0), ("original_rom_executions", 0), ("firmware_ready", False),
                        ("sf_status", "SFMeaningStorageNotEstablished"),
                        ("sf_runtime_comparison", "PairedInternalBooleanVariantsOnly_NoNativeBooleanClaim")):
        equal(runtime.get(name), value, "RustRuntime." + name)
    equal(runtime.get("oracle_fixture_sha256"), fixture_sha, "RustRuntime.fixtureSha")
    equal(runtime.get("oracle_seals"), fixture["oracle_seals"], "RustRuntime.oracleSeals")
    cases = expand_cases(fixture)
    observations = runtime.get("microprobe_observations")
    require(type(observations) is list and len(observations) == 102, "RustRuntime", "exact102 actual observations required")
    patterns = opcode_rows(root)
    for index, case in enumerate(cases):
        pair = []
        for variant, sf in enumerate((False, True)):
            record = observations[2 * index + variant]
            require(set(record) == {"case_id", "internal_sf", "request", "actual", "comparison"}, "RustRuntime", "closed success observation wrapper required")
            equal(record["case_id"], case["id"], "RustRuntime.caseId")
            equal(record["internal_sf"], sf, "RustRuntime.sfVariant")
            equal(record["comparison"], "Pass", "RustRuntime.comparison")
            request = expected_request(fixture, case, sf)
            equal(record["request"], request, "RustRuntime.independentRequest")
            compare_observation(root, request, case, record["actual"], patterns, observed_production)
            actual = deepcopy(record["actual"])
            del actual["internal_sf_before"], actual["internal_sf_after"]
            pair.append(actual)
        equal(pair[0], pair[1], "RustRuntime.WholeSfPair." + case["id"])
    refusals = runtime.get("wrong_dd_refusals")
    require(type(refusals) is list and len(refusals) == 4, "RustRuntime", "four actual DD refusals required")
    all_cases = {case["id"]: case for case in cases}
    for expected, actual in zip(fixture["dd_refusals"], refusals):
        case = deepcopy(all_cases[expected["baseCase"]])
        case["entryOverride"]["psw"] = expected["beforePsw"]
        equal(actual.get("request"), expected_request(fixture, case, False), "RustRuntime.DdRefusal.request")
        equal(actual.get("base_case"), expected["baseCase"], "RustRuntime.DdRefusal.baseCase")
        equal(actual.get("caller_request_unchanged"), True, "RustRuntime.DdRefusal.atomicity")
        equal(actual.get("comparison"), "Pass", "RustRuntime.DdRefusal.comparison")
        equal(actual.get("actual_refusal", {}).get("code"), "WrongDdAdmission", "RustRuntime.DdRefusal.actualError")
    return {"contexts": 51, "cpuInstances": 102, "retiredInstructions": 102, "sfPairs": 51,
            "ddRefusals": 4, "externalJInstances": sum(row["actual"]["external_transfer"] is not None for row in observations)}


def compare_psw(root, runtime):
    equal(binding(root, ORACLE)["sha256"], ORACLE_SHA, "PswOracle.hashBeforeImport")
    spec = importlib.util.spec_from_file_location("_m2bm_pinned_unchanged_m2bl_oracle", public_path(root, ORACLE))
    require(spec is not None and spec.loader is not None, "PswOracle", "pinned module unavailable")
    module = importlib.util.module_from_spec(spec)
    sys.dont_write_bytecode = True
    spec.loader.exec_module(module)
    records = runtime.get("psw_round_trip_records")
    require(type(records) is list and len(records) == 65536, "PswRuntime", "all65536 actual tuples required")
    equal(runtime.get("psw_record_fields"), ["lossless_input_u16", "actual_canonical_output_u16"], "PswRuntime.recordFields")
    representable_low, representable_full = 0, 0
    expected_digest = sha256()
    for word, actual in enumerate(records):
        require(type(actual) is list and len(actual) == 2, "PswRuntime", "compact two-tuple required")
        equal(actual[0], word, "PswRuntime.losslessInput")
        uint(actual[1], 65535, "PswRuntime.actualCanonicalOutput")
        flags = {name: int(bool(word & mask)) for name, mask in (("cf", 32768), ("zf", 16384), ("hc", 8192), ("dd", 4096))}
        expected = module.check_psw_round_trip(word & 4095, flags)
        equal(expected["requestedPsw"], word, "PswOracle.requestedInput")
        equal(actual[1], expected["encodedPsw"], f"PswRuntime.word{word:04X}")
        compatible = expected["representable"]
        representable_full += int(compatible)
        representable_low += int(word < 4096 and compatible)
        expected_digest.update(canonical(expected))
    for name, value in (("psw_representable_low12", 128), ("psw_incompatible_low12", 3968),
                        ("psw_representable_full", 2048), ("psw_incompatible_full", 63488)):
        equal(runtime.get(name), value, "PswRuntime." + name)
    equal([representable_low, representable_full], [128, 2048], "PswOracle.actualClassificationCounts")
    equal(binding(root, ORACLE)["sha256"], ORACLE_SHA, "PswOracle.hashAfterComparison")
    return {"actualWordTuples": 65536, "representableLow12": 128, "incompatibleLow12": 3968,
            "representableFull": 2048, "incompatibleFull": 63488,
            "independentOracleRecordDigest": expected_digest.hexdigest(),
            "digestOrder": "ActualInputWordAscending0000ThroughFFFF_NotOldOtherThenFlagLoopOrder",
            "upstreamM2bkDomainChanged": False}


def compare_component_inventory(root, component):
    # M2bl nodes are opaque reviewed metadata. This comparison does not emit,
    # assemble, concatenate or load their51-byte executable representation.
    upstream = strict_json(public_path(root, "research/p28-word0196/synthetic_adapter_feasibility_contract.json").read_text(encoding="utf-8"))
    expected = []
    kinds = {"PageOffset8": "Page", "EvenPageOffset8": "EvenPage",
             "Immediate8": "Immediate8", "Immediate16": "Immediate16",
             "ProgramTarget16": "Target", "TargetPC16": "Target"}
    for node in upstream["nodes"]:
        operands = []
        for operand in node["typedOperands"]:
            kind, fields = operand["kind"], operand["fields"]
            if kind == "AccumulatorA": operands.append({"kind": "Accumulator"})
            elif kind in ("Register0", "Register1"):
                operands.append({"kind": "LocalRegister", "value": fields["value"]})
            elif kind in ("PageBit5", "PageBit7"):
                operands.append({"kind": "PageBit", "value": {"offset": fields["offset"], "bit": fields["bit"]}})
            else:
                require(kind in kinds, "AdmissionInventory", "unreviewed typed operand kind")
                operands.append({"kind": kinds[kind], "value": fields["value"]})
        node_id = node["nodeId"] if type(node["nodeId"]) is str else f"{node['nodeId']:04X}"
        expected.append({"pc": node["syntheticPc"], "node_identity": node_id,
                         "form": node["formId"], "length": node["length"],
                         "architectural_dd": [bool(value) for value in node["documentedIncomingDD"]],
                         "reachable_dd": [bool(value) for value in node["plannedIncomingDD"]],
                         "operands": operands, "successors": node["successors"],
                         "primary_pdf_page": node["primaryEvidence"]["pdfPage"],
                         "primary_pattern": FORM_IDENTITY[node["formId"]][1],
                         "manual_sha256": "f6e423ac0bd15378754e30c35ed426415ec219e360c68e817ab451df72142271",
                         "source_identity": "M2bjVerifiedSyntheticComposite_20Nodes_51Bytes",
                         "source_sha256": COMPOSITE_SHA})
    equal(len(expected), 20, "AdmissionInventory.nodeCount")
    equal(component.get("admission_inventory"), expected, "AdmissionInventory.whole20MetadataRecords")


def compare_permission_matrix(root, component):
    upstream = strict_json(public_path(root, "research/p28-word0196/synthetic_adapter_feasibility_contract.json").read_text(encoding="utf-8"))
    inventory = upstream["dataPolicy"]["inventory"]
    equal(len(inventory), 16, "Permissions.inventoryCount")
    expected = []
    for path in "ABCD":
        for item in inventory:
            address = item["address"]
            for width in (8, 16):
                if width == 16:
                    readable, writable, kind = address == 0x196, False, None
                else:
                    # 0196/0197 authorize one complete LE16 operation, never two
                    # independently admitted functional byte reads.
                    readable = path in item["readPaths"] and address not in (0x196, 0x197)
                    writable = path in item["writePaths"]
                    kind = None
                    if writable:
                        kind = "LocalRegisterStore" if address == 0x109 else "Store" if path == "A" and address in (0x117, 0x18F) else "RMW"
                expected.append({"path": path, "address": address, "width": width,
                                 "read_allowed": readable, "write_allowed": writable,
                                 "write_kind": kind})
    equal(component.get("permission_matrix"), expected, "Permissions.whole128IndependentRows")


def compare_components(root, component, observed_production):
    require(component.get("first_mismatch") is None, "RustComponents", "preserve original Rust first mismatch", actual=component.get("first_mismatch"))
    for name, value in (("schema_version", 1), ("instruction_executions", 0),
                        ("m2bj_composite_executions", 0), ("original_rom_executions", 0),
                        ("component_cpu_instances", 9), ("decoder_only_calls", 1)):
        equal(component.get(name), value, "RustComponents." + name)
    equal(component.get("classification"), "ActualRustComponentRuntimeObserved_NoInstructionExecution", "RustComponents.classification")
    equal(component.get("source_bindings"), observed_production, "RustComponents.productionSources")
    mapping = [{"pc": 4096 + n, "offset": n, "opaque": f"InventedOpaqueOffsetIdentity-{n}"} for n in range(51)]
    equal(component.get("mapping"), mapping, "RustComponents.actual51Mapping")
    snapshots = component.get("entry_snapshots")
    require(type(snapshots) is list and len(snapshots) == 8, "RustComponents", "all8 SCB snapshots required")
    for scb, row in enumerate(snapshots):
        equal(row.get("scb"), scb, "RustComponents.scb")
        equal(row.get("preserved"), True, "RustComponents.snapshotPreserved")
        equal(row.get("actual_cpu_instructions"), 0, "RustComponents.snapshotInstructions")
        equal(row.get("functional_events"), 0, "RustComponents.seedFunctionalEvents")
        snapshot = row.get("snapshot", {})
        expected = {"pc": 4096, "a": 0xA581, "al": 0x81, "ah": 0xA5,
                    "psw": (0xECCB & ~7) | scb, "lrb": 0x21, "ssp": 0x37A1,
                    "pointing_banks": [{name: 0x1001 + bank * 0x100 + slot for slot, name in enumerate(("x1", "x2", "dp", "usp"))} for bank in range(8)],
                    "halted": False, "provenance": PROVENANCE, "sf": deepcopy(SF_UNKNOWN)}
        state_owners(expected, 0xA581, expected["psw"], {str(0x108 + n): 8 + n for n in range(8)})
        equal(snapshot, expected, "RustComponents.completeScbSnapshot")
    compare_component_inventory(root, component)
    compare_permission_matrix(root, component)
    cases = component.get("cases")
    require(type(cases) is list and cases, "RustComponents", "actual component case records required")
    present, counts = set(), {"negativeRefusals": 0, "positiveInvariants": 0,
                              "componentRuntimeCases": 0, "metadataPolicyRuntimeCases": 0}
    for row in cases:
        fields = {"id", "category", "operation", "kind", "evidence_level", "passed", "error", "observed"}
        if row.get("kind") == "NegativeRefusal": fields.add("input")
        equal(set(row), fields, "RustComponents.caseFields")
        equal(row["passed"], True, "RustComponents.casePassed")
        require(type(row["id"]) is str and row["id"] not in present, "RustComponents", "duplicate/missing case identity")
        present.add(row["id"])
        equal(row["category"], dict(zip(CATEGORIES, CATEGORY_LABELS)).get(row["id"], row["id"]), "RustComponents.promptCategory")
        require(type(row["operation"]) is str and row["operation"], "RustComponents", "actual operation missing")
        if row["kind"] == "NegativeRefusal":
            require(type(row["error"]) is dict and set(row["error"]) == {"code", "detail"} and all(type(v) is str and v for v in row["error"].values()), "RustComponents", "actual typed Rust refusal required")
            require(row["id"] in EXPECTED_ERRORS, "RustComponents", "unreviewed negative case identity", actual=row["id"])
            equal(row["error"]["code"], EXPECTED_ERRORS[row["id"]], "RustComponents.exactRefusalReason." + row["id"])
            equal(row["input"], row["operation"], "RustComponents.actualOperationDescriptor")
            equal(row["evidence_level"], "MetadataPolicyRuntimeObserved" if row["id"] in METADATA_CASES else "ComponentRuntimeObserved", "RustComponents.separateMetadataScope")
            counts["negativeRefusals"] += 1
        elif row["kind"] == "PositiveInvariant":
            equal(row["error"], None, "RustComponents.invariantError")
            require(row["observed"] is not None, "RustComponents", "actual invariant observation missing")
            counts["positiveInvariants"] += 1
        else: raise ValidationFailure("RustComponents", "unreviewed case kind")
        if row["evidence_level"] == "ComponentRuntimeObserved": counts["componentRuntimeCases"] += 1
        elif row["evidence_level"] == "MetadataPolicyRuntimeObserved": counts["metadataPolicyRuntimeCases"] += 1
        else: raise ValidationFailure("RustComponents", "unreviewed component evidence level")
    require(set(CATEGORIES) <= present, "RustComponents", "mandatory33 coverage missing", actual=sorted(set(CATEGORIES) - present))
    equal(counts, {"negativeRefusals": 36, "positiveInvariants": 6,
                   "componentRuntimeCases": 28, "metadataPolicyRuntimeCases": 14}, "RustComponents.preplannedExactAccounting")
    return {"coveredMandatoryCategories": 33, "actualCases": len(cases), **counts,
            "componentCpuInstancesInReceipt": 9, "decoderOnlyCalls": 1,
            "metadataRefusalsAreNotCpuInstructions": True}


def emit_chunks(record):
    payload = canonical(record)
    encoded = base64.b64encode(payload).decode("ascii")
    size = 7200
    count = (len(encoded) + size - 1) // size
    digest = sha256(payload).hexdigest()
    for index in range(count):
        envelope = {"schemaVersion": 1, "recordKind": "ValidatorFullRuntimeEvidence",
                    "encoding": "base64-utf8", "index": index, "count": count,
                    "decodedBytes": len(payload), "sha256": digest,
                    "data": encoded[index * size:(index + 1) * size]}
        line = "M2BM_RUNTIME_CHUNK_JSON=" + canonical(envelope).decode("ascii")
        require(len(line.encode("ascii")) <= 8192, "EvidenceChunks", "chunk exceeds8KiB")
        print(line, flush=True)
    return {"sha256": digest, "decodedBytes": len(payload), "chunks": count}


def marker_records(stdout):
    records = {}
    filtered = []
    for line in stdout.decode("utf-8", errors="strict").splitlines():
        marker = next((name for name in MARKERS if name in line), None)
        if marker is None:
            filtered.append(line)
            continue
        position = line.index(marker)
        prefix = line[:position]
        require(not prefix or re.fullmatch(r"test [A-Za-z_0-9:.-]+ \.\.\.\s*", prefix), "RustMarker", "unexpected marker prefix")
        require(marker not in records, "RustMarker", "duplicate actual marker", actual=marker)
        body = line[position + len(marker):]
        require(body.startswith("=") or body.startswith(" "), "RustMarker", "marker separator missing")
        records[marker] = strict_json(body[1:].strip())
    return records, filtered


def write_new(path, content):
    with path.open("xb") as stream:
        stream.write(content)


def receipt_directory(root, value):
    if value is None: return None
    path = (root / value).resolve() if not Path(value).is_absolute() else Path(value).resolve()
    private = (root / "private/reports/m2bm").resolve()
    temporary = (root / ".tmp").resolve()
    require(path != private and (path.is_relative_to(private) or (path.is_relative_to(temporary) and path.relative_to(temporary).parts[0].startswith("m2bm-"))), "ReceiptPath", "new current private subdirectory or .tmp/m2bm-* required")
    require(not (private / "FINAL_REPORT_UK.md").exists(), "ReceiptPath", "M2bm final report exists: STOP")
    path.mkdir(parents=True, exist_ok=True)
    require(not any((path / name).exists() for name in ("build.stdout.log", "build.stderr.log", "test.stdout.log", "test.stderr.log", "fmt.stdout.log", "fmt.stderr.log", "validator-result.json")), "ReceiptPath", "refuse receipt overwrite/retry")
    return path


def run_command(root, phase, arguments, receipt_dir, commands):
    started = time.monotonic()
    completed = subprocess.run(arguments, cwd=root, stdin=subprocess.DEVNULL,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False, check=False)
    row = {"id": phase, "command": arguments, "exitCode": completed.returncode,
           "durationSeconds": round(time.monotonic() - started, 6),
           "stdoutBytes": len(completed.stdout), "stdoutSha256": sha256(completed.stdout).hexdigest(),
           "stderrBytes": len(completed.stderr), "stderrSha256": sha256(completed.stderr).hexdigest()}
    commands.append(row)
    if receipt_dir:
        write_new(receipt_dir / f"{phase}.stdout.log", completed.stdout)
        write_new(receipt_dir / f"{phase}.stderr.log", completed.stderr)
    records, filtered = marker_records(completed.stdout)
    for line in filtered:
        print(line, flush=True)
    for line in completed.stderr.decode("utf-8", errors="strict").splitlines():
        require(not any(name in line for name in MARKERS), "RustMarker", "actual evidence unexpectedly on stderr")
        print(line, file=sys.stderr, flush=True)
    return row, records, completed.stdout.decode("utf-8", errors="strict")


def production_observed_rows(root):
    rows = []
    for name in PRODUCTION_NAMES:
        relative = "rust/p28-slice-runner/" + (name if name == "Cargo.toml" else "src/" + name)
        row = binding(root, relative)
        row["path"] = name
        rows.append(row)
    return rows


def declared_rust_test_inventory(root):
    inventory = []
    for path in sorted(public_path(root, CRATE).rglob("*.rs")):
        tokens = rust_tokens(path.read_text(encoding="utf-8"))
        code = " ".join(value if kind != "string" else "STRING_LITERAL" for kind, value in tokens)
        for name in re.findall(r"#\s*\[\s*test\s*\]\s*fn\s+([A-Za-z_0-9]+)\s*\(", code):
            inventory.append({"path": path.relative_to(root).as_posix(), "name": name})
    require(len(inventory) == 36, "RustTestInventory", "reviewed planned35unit+1integration source inventory required", actual=len(inventory))
    return inventory


def capability_levels():
    # These levels are produced only after actual compiled tests and independent
    # comparisons succeed. The closed20-node metadata policy stays distinct from
    # the separately joined invented one-instruction microfixture admission.
    qualifications = {
        "A": "ActualCpuPcAndProductionDecoderThroughCheckedInventedProgramMapping",
        "B": "MicrofixtureAdmissionJoinedToCpuDecoder_Closed20NodePolicyMetadataOnly",
        "C": "ActualCpuFieldsAndIndependentResearchDataSnapshot_NotProductionEntryApi",
        "D": "ActualResearchExecutorDataCalls_NotProductionBusIntegration",
        "E": "ActualProductionDecoderAndInventedDirectJResearchTrap_NotNativeHandoff",
        "F": "ActualUnchangedCpuPswMethodsAll65536Words_CanonicalDomainOnly",
    }
    return [{"id": name, "ModelVerified": "InheritedM2blIndependentModel_NotNewRustCoverage",
             "RustImplementationCompiled": True, "RustUnitTestsPassed": True,
             "MicroprobeRuntimeObserved": "ActualBoundedResearchComponentObservations",
             "ProductionCpuIntegrated": qualifications[name],
             "FullCompositeExecutionObserved": "NotRun"} for name in "ABCDEF"]


def validate(args):
    root = repo_root()
    require(not (root / "private/reports/m2bm/FINAL_REPORT_UK.md").exists(), "Lifecycle", "final report exists: STOP")
    contract_binding = binding(root, CONTRACT)
    contract = strict_json(public_path(root, CONTRACT).read_text(encoding="utf-8"))
    validate_contract(contract)
    require(PRODUCTION_MANIFEST_PINS, "SourceBinding", "preflight production manifest pins not filled in draft")
    production_manifest_rows = [{"path": path, **value} for path, value in PRODUCTION_MANIFEST_PINS.items()]
    sources_before = verify_bindings(root, contract["sourceBindings"], 175)
    new_before = verify_bindings(root, contract["newSourceBindings"])
    manifest_before = verify_bindings(root, production_manifest_rows)
    equal(contract.get("fixtureBinding"), next((row for row in new_before if row["path"] == FIXTURE), None), "Fixture.reviewedBinding")
    fixture = strict_json(public_path(root, FIXTURE).read_text(encoding="utf-8"))
    policy = source_policy(root, contract)
    test_inventory = declared_rust_test_inventory(root)
    equal(len(test_inventory), contract["expectedRustTestCount"], "Contract.plannedTestCountAgainstPinnedSource")
    equal(sum("/tests/" in row["path"] for row in test_inventory), 1, "Contract.integrationTestDeclarations")
    observed_production = production_observed_rows(root)
    pinned_existing = {row["path"]: row for row in sources_before + manifest_before}
    for row in observed_production:
        relative = "rust/p28-slice-runner/" + (row["path"] if row["path"] == "Cargo.toml" else "src/" + row["path"])
        require(relative in pinned_existing, "SourceBinding", "required production source not frozen", actual=relative)
        equal({**row, "path": relative}, pinned_existing[relative], "SourceBinding.productionReuse")
    receipts = receipt_directory(root, args.receipt_dir)
    target = public_path(root, ".tmp/m2bm-rust-synthetic-adapter-target")
    manifest = str(public_path(root, CRATE + "/Cargo.toml"))
    commands, rust_records = [], {}
    cargo_base = ["cargo", "+1.85.1"]
    build = cargo_base + ["build", "--release", "--locked", "--jobs", "1", "--manifest-path", manifest, "--target-dir", str(target)]
    tests = cargo_base + ["test", "--release", "--locked", "--jobs", "1", "--manifest-path", manifest, "--target-dir", str(target), "--", "--nocapture", "--test-threads=1"]
    fmt = cargo_base + ["fmt", "--check", "--manifest-path", manifest]
    evidence = {"schemaVersion": 1, "milestone": "M2bm", "passed": False,
                "firstMismatch": None, "commands": commands, "contractBinding": contract_binding,
                "actualHost": {"sysPlatform": sys.platform, "machine": platform.machine(),
                               "pythonVersion": platform.python_version(),
                               "scope": "ObservedValidatorHost_ExcludedFromCrossOsSemanticRecord"}}
    try:
        row, records, _ = run_command(root, "build", build, receipts, commands)
        require(not records and row["exitCode"] == 0, "CargoBuild", "actual new-crate build failed", actual=row["exitCode"])
        row, records, test_stdout = run_command(root, "test", tests, receipts, commands)
        rust_records.update(records)
        # Emit and preserve the original failed Rust record before any promotion.
        for name, record in rust_records.items():
            if record.get("first_mismatch") is not None:
                evidence["originalRustFirstMismatch"] = {"marker": name, "value": record["first_mismatch"]}
        require(row["exitCode"] == 0, "CargoTests", "actual new-crate test command failed", actual=row["exitCode"])
        require(set(records) == set(MARKERS), "RustMarker", "exactly one runtime and one component record required")
        totals = re.findall(r"test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored; (\d+) measured; (\d+) filtered out", test_stdout)
        require(totals, "CargoTests", "actual complete Rust test summaries absent")
        require(all(all(int(value) == 0 for value in counts[1:]) for counts in totals), "CargoTests", "failed/ignored/measured/filtered Rust cases forbidden")
        test_count = sum(int(counts[0]) for counts in totals)
        equal(test_count, contract["expectedRustTestCount"], "CargoTests.actualPlannedCount")
        equal([int(counts[0]) for counts in totals],
              [contract["expectedUnitTestCount"], contract["expectedIntegrationTestCount"], 0],
              "CargoTests.separateUnitIntegrationAndDocCounts")
        runtime, component = records["M2BM_RUNTIME_JSON"], records["M2BM_COMPONENT_JSON"]
        micro = compare_runtime(root, fixture, runtime, observed_production, contract["fixtureBinding"]["sha256"])
        psw = compare_psw(root, runtime)
        components = compare_components(root, component, observed_production)
        row, fmt_records, _ = run_command(root, "fmt", fmt, receipts, commands)
        require(not fmt_records and row["exitCode"] == 0, "CargoFormatting", "actual formatting check failed", actual=row["exitCode"])
        sources_after = verify_bindings(root, contract["sourceBindings"], 175)
        new_after = verify_bindings(root, contract["newSourceBindings"])
        manifest_after = verify_bindings(root, production_manifest_rows)
        equal(binding(root, CONTRACT), contract_binding, "Contract.unchangedDuringExecution")
        equal(sources_after, sources_before, "SourceBinding.prePostExisting")
        equal(new_after, new_before, "SourceBinding.prePostNew")
        equal(manifest_after, manifest_before, "SourceBinding.prePostProductionManifests")
        stable = {"schemaVersion": 1, "milestone": "M2bm", "runtime": runtime, "components": component,
                  "sourceBindings": sources_after, "newSourceBindings": new_after,
                  "productionManifestBindings": manifest_after, "contractBinding": contract_binding,
                  "independentFixtureBinding": contract["fixtureBinding"], "microprobeComparison": micro,
                  "pswComparison": psw, "componentComparison": components,
                  "actualRustTestCount": test_count, "actualRustUnitTestCount": int(totals[0][0]),
                  "actualRustIntegrationTestCount": int(totals[1][0]), "sourcePolicy": policy,
                  "executedPinnedRustTestInventory": test_inventory, "capabilities": capability_levels(),
                  "componentCpuInstanceAccounting": {
                      "receiptFunctionObserved": 9, "otherExecutedUnitFunctions": 9, "wholeComponentSuite": 18,
                      "otherFunctions": [{"name": "entry_roundtrips_all8_scb_and32_pointing_canaries_without_functional_effects", "instances": 8},
                                         {"name": "incompatible_psw_is_refused_before_cpu_mutation_and_expected_is_lossless", "instances": 1}],
                      "basis": "AllPinnedUnitFunctionsExecutedWithoutFiltering_SourceReviewedExplicitCpuConstructionCounts",
                      "componentRetiredInstructions": 0, "microprobeInstancesSeparate": 102,
                      "pswInstancesSeparate": 65536},
                  "fullCompositeExecutionObserved": "NotRun", "productionCpuIntegration": "ActualCpuAndProductionDecoderWithResearch16FormExecutor",
                  "productionBusIntegrated": False, "productionExecStepIntegrated": False, "productionRunnerIntegrated": False,
                  "sfArchitecturalStatus": "SFMeaningStorageNotEstablished", "nativeExitIsolationEstablished": False,
                  "m2bjCompositeExecutions": 0, "actualROMExecutions": 0, "FirmwareReady": False,
                  "firstMismatch": None, "passed": True}
        chunks = emit_chunks(stable)
        evidence.update(passed=True, actualRustTestCount=test_count,
                        actualRustUnitTestCount=int(totals[0][0]), actualRustIntegrationTestCount=int(totals[1][0]),
                        microprobes=micro, psw=psw,
                        componentCoverage=components, fullEvidence=chunks,
                        sourceBindingCount=len(sources_after), newSourceBindingCount=len(new_after),
                        sourceBindingsSha256=sha256(canonical(sources_after)).hexdigest(),
                        newSourceBindingsSha256=sha256(canonical(new_after)).hexdigest(),
                        compiledProductionSourceBindings=observed_production,
                        m2bjCompositeExecutions=0, actualROMExecutions=0, FirmwareReady=False)
    except Exception as error:
        evidence["firstMismatch"] = error.record if isinstance(error, ValidationFailure) else {"scope": "Orchestration", "message": str(error), "type": type(error).__name__}
        evidence["passed"] = False
        try:
            failure_sources = {
                "existing": verify_bindings(root, contract["sourceBindings"], 175),
                "new": verify_bindings(root, contract["newSourceBindings"]),
                "production": verify_bindings(root, production_manifest_rows)}
            evidence["failureSourceBindingsAfter"] = {
                name: {"count": len(rows), "sha256": sha256(canonical(rows)).hexdigest()}
                for name, rows in failure_sources.items()}
            equal(binding(root, CONTRACT), contract_binding, "FailureSourceFence.contract")
        except Exception as source_error:
            evidence["additionalSourceFenceFailure"] = source_error.record if isinstance(source_error, ValidationFailure) else str(source_error)
        if rust_records:
            evidence["failedRustRecords"] = emit_chunks({"schemaVersion": 1, "milestone": "M2bm", "passed": False, "originalRustRecords": rust_records, "firstMismatch": evidence["firstMismatch"]})
        if receipts:
            write_new(receipts / "validator-result.json", canonical(evidence) + b"\n")
        print("M2BM_EVIDENCE_JSON=" + canonical(evidence).decode("ascii"), flush=True)
        error.m2bm_evidence_emitted = True
        raise
    if receipts:
        write_new(receipts / "validator-result.json", canonical(evidence) + b"\n")
    # The small marker names digests/counts; the full Rust records occur only in
    # the bounded encoded chunk stream above, never echoed as giant marker lines.
    print("M2BM_EVIDENCE_JSON=" + canonical(evidence).decode("ascii"), flush=True)
    return evidence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt-dir", help="optional new current-private or .tmp/m2bm-* directory; no default private CI writes")
    args = parser.parse_args()
    try:
        validate(args)
        return 0
    except Exception as error:
        if not getattr(error, "m2bm_evidence_emitted", False):
            first = error.record if isinstance(error, ValidationFailure) else {"scope": "PreExecutionOrchestration", "message": str(error), "type": type(error).__name__}
            print("M2BM_EVIDENCE_JSON=" + canonical({"schemaVersion": 1, "milestone": "M2bm", "passed": False,
                  "firstMismatch": first, "actualRustBuildAndTests": "NotEstablished", "noOutcomeInferredFromContract": True,
                  "actualHost": {"sysPlatform": sys.platform, "machine": platform.machine()}}).decode("ascii"), flush=True)
        print(f"M2bm validator failed: {error}", file=sys.stderr, flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
