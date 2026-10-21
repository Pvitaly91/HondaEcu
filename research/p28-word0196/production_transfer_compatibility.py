"""M2br version-explicit compatibility, not a historical-validator source alias.

The active engine is observed through the unchanged default, M2bp one-step and
M2bq composite probes. Complete old/new records are retained in paired streams.
Only exact, independently frozen source-header identities may differ. The old
validators themselves run only in their pinned trees. Import starts no process.
"""
from __future__ import annotations
import argparse
from copy import deepcopy
import gzip
from hashlib import sha256
import importlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

sys.dont_write_bytecode = True
from production_transfer_common import binding, bounded_json, canonical, first_difference, require
import production_transfer_analysis as analysis

RESEARCH = "research/p28-word0196/"
COMPOSITE_INPUT = RESEARCH + "rust-production-composite/closed_inputs.json"
LIMIT = 16 * 1024**2
STREAM_LIMIT = 8 * 1024**3
RESERVE = 4 * 1024**3
CHANGED_BP_HEADERS = frozenset(("rust/p28-slice-runner/src/audit.rs", "rust/p28-slice-runner/src/audit_bus.rs"))
CHANGED_BQ_HEADERS = CHANGED_BP_HEADERS | {"rust/p28-slice-runner/src/audit_composite.rs"}
FAMILIES = (
    ("m2bi", "validate_composite_emission_eligibility_contract.py", "composite_emission_eligibility_tests.py"),
    ("m2bh", "validate_static_composition_contract.py", "static_composition_tests.py"),
    ("m2bg", "validate_direct_j_contract.py", "direct_j_tests.py"),
    ("m2bf", "validate_external_continuation_contract.py", "continuation_transfer_tests.py"),
    ("m2be", "validate_layout_feasibility_contract.py", "layout_feasibility_tests.py"),
    ("m2bd", "validate_typed_lowering_contract.py", "typed_lowering_tests.py"),
    ("m2bc", "validate_independent_decode_encode_contract.py", "independent_decoder_tests.py"),
    ("m2bb", "validate_independent_encoder_contract.py", "independent_encoder_tests.py"),
    ("m2ba-provenance", "validate_doc_contribution.py", "doc_contribution_tests.py"),
    ("m2ba-encoder", "validate_independent_encoder_design.py", "independent_encoder_design_tests.py"),
    ("m2az", "validate_asm662_original_release.py", "asm662_original_release_tests.py"),
    ("m2ay", "validate_asm662_source.py", "asm662_source_tests.py"),
    ("m2ax", "validate_toolchain_provenance.py", "toolchain_provenance_tests.py"),
    ("m2aw", "validate_target_contract.py", "target_contract_tests.py"),
)
SCHEMA = {"version": 1, "scopeRecords": {"historical-pinned": 14, "default": 493,
          "one-step": 583, "composite": 5478, "source-transition": 1},
          "pairedRecords": "CompletePinnedAndCompleteActiveObjects_NoFieldRemoval",
          "canonicalFieldsExcluded": [], "platformExclusions": [],
          "sourceVersions": "EachCompleteHeaderMustEqualItsOwnPreCpuFrozenHeader",
          "historicalSemantics": "FullMachineJsonAndExit_TransportPidPathsTimesAndUnittestProgressAreSeparate",
          "historicalDefaultReference": "ExactPinnedM2bqActualRegressionReference_NotManufacturerOrIsaOracle",
          "activeCompatibilityIsNotNewTransferExecution": True}


def own(root, supplied, role="evidence"):
    root = Path(root).resolve(); fragment = Path(supplied)
    require(".." not in fragment.parts, "NoOwnedParentTraversal")
    path = fragment if fragment.is_absolute() else root / fragment
    path = path.absolute()
    prefix = root / ".tmp/m2br-owned" / ("public-evidence/compatibility" if role == "evidence" else "targets/compatibility")
    require(path == prefix or path.is_relative_to(prefix), "ExactNewCompatibilityOwnedRole")
    for ancestor in (path, *path.parents):
        if ancestor == root:
            break
        require(not ancestor.is_symlink() and (not ancestor.exists() or not getattr(ancestor.stat(), "st_file_attributes", 0) & 0x400),
                "NoOwnedReparseAncestor")
    require(path.resolve() == path, "NoOwnedPathAlias")
    return path


def bound(root, path):
    return binding(root, Path(path).relative_to(root).as_posix())


def write_new(path, value):
    with Path(path).open("xb") as output:
        output.write(canonical(value) + b"\n")
        output.flush(); os.fsync(output.fileno())


def load_helpers(root, pinned_bq, pinned_bp, legacy):
    proof, contract = analysis.source_checks(root, pinned_bq, pinned_bp, legacy)
    # Complete four-tree source checks precede reuse of any old definitions.
    names = ("default_mode_compatibility", "validate_production_optin_capabilities",
             "production_composite_compatibility", "validate_production_composite",
             "production_composite_corpus", "production_composite_records", "production_composite_projection",
             "production_composite_negative", "production_composite_stream", "production_composite_emission")
    old = {row["path"]: row for row in proof["pinnedM2bqSources"]}
    helpers = {}
    for name in names:
        relative = RESEARCH + name + ".py"
        require(binding(root, relative) == old[relative], "UnchangedSourceBoundDefinition:" + name)
        module = importlib.import_module(name)
        require(Path(module.__file__).resolve() == root / relative, "NoHistoricalModulePathAlias:" + name)
        helpers[name] = module
    return proof, contract, helpers


def checked_json(root, path, limit=32 * 1024**2):
    row = bound(root, path)
    require(row["bytes"] <= limit, "BoundedCompatibilityMetadata")
    value = bounded_json(Path(path).read_bytes(), limit)
    require(bound(root, path) == row, "CompatibilityMetadataChangedWhileParsing")
    return value, row


def checked_host_json(root, path):
    """Native timings may be finite floats; observation JSON remains integer-only."""
    row = bound(root, path)
    require(row["bytes"] <= 4 * 1024**2, "BoundedNativeReceiptMetadata")
    def pairs(items):
        result = {}
        for key, item in items:
            require(key not in result, "DuplicateHostReceiptKey")
            result[key] = item
        return result
    def finite(text):
        value = float(text); require(math.isfinite(value), "FiniteHostTimingMetadata")
        return value
    value = json.loads(Path(path).read_bytes(), object_pairs_hook=pairs, parse_float=finite,
                       parse_constant=lambda _: (_ for _ in ()).throw(ValueError("NonfiniteHostMetadata")))
    require(bound(root, path) == row, "HostNativeReceiptChangedDuringParse")
    return value, row


class Writer:
    def __init__(self, root, path, codec=None):
        self.root, self.path, self.codec = root, Path(path), codec
        self.raw = self.path.open("xb")
        try:
            self.output = gzip.GzipFile(filename="", fileobj=self.raw, mode="wb", mtime=0)
        except BaseException:
            self.raw.close(); raise
        self.records = self.bytes = self.maximum = 0
        self.digest = sha256(); self.result = None

    def put(self, value):
        if self.codec is not None:
            projected = self.codec.project(value)
            require(first_difference(value, self.codec.restore(projected)) is None, "EveryPairedFieldRoundTrips")
        else:
            projected = value
        line = canonical(projected) + b"\n"
        require(len(line) <= LIMIT and self.bytes + len(line) <= STREAM_LIMIT, "BoundedCompleteCompatibilityRecord")
        self.output.write(line); self.digest.update(line)
        self.records += 1; self.bytes += len(line); self.maximum = max(self.maximum, len(line))

    def close(self):
        if self.result is None:
            try: self.output.close()
            finally: self.raw.close()
            self.result = {"records": self.records, "bytes": self.bytes, "sha256": self.digest.hexdigest(),
                           "maxRowBytes": self.maximum, "expectedCompressed": bound(self.root, self.path)}
        return self.result


def rows(path, codec=None):
    total = 0
    with gzip.open(path, "rb") as source:
        while line := source.readline(LIMIT + 1):
            require(len(line) <= LIMIT and line.endswith(b"\n"), "FullBoundedCompatibilityRow")
            total += len(line); require(total <= STREAM_LIMIT, "CompatibilityFullStreamBound")
            value = bounded_json(line, LIMIT)
            require(canonical(value) + b"\n" == line, "OriginalCanonicalEncodingRetained")
            yield codec.restore(value) if codec else value


def full_compare(root, left, right, expected):
    before = [bound(root, left), bound(root, right)]; digest = sha256(); total = chunks = 0
    with gzip.open(left, "rb") as a, gzip.open(right, "rb") as b:
        while True:
            x, y = a.read(1024**2), b.read(1024**2)
            require(total + max(len(x), len(y)) <= expected["bytes"] + 1024**2, "FrozenFullStreamBound")
            require(x == y, "FirstWholeCompatibilityByteMismatch:" + str(total))
            if not x: break
            digest.update(x); total += len(x); chunks += 1
    require(total == expected["bytes"] and digest.hexdigest() == expected["sha256"]
            and before == [bound(root, left), bound(root, right)], "WholeEofCrcAndFrozenDigest")
    return {"passed": True, "everyDecompressedByteCompared": True, "shaOnlyComparison": False,
            "bytes": total, "sha256": digest.hexdigest(), "chunks": chunks, "chunkBytes": 1024**2,
            "fullEofAndCrcChecked": True, "firstMismatch": None, "canonicalFieldsExcluded": [],
            "leftCompressed": before[0], "rightCompressed": before[1]}


def native(root, cwd, output, label, arguments, expected=0, timeout=1800, input_bytes=None):
    require(re.fullmatch(r"[a-z0-9][a-z0-9-]{0,100}", label) is not None, "ClosedFreshNativeLabel")
    require(shutil.disk_usage(output).free >= RESERVE, "FourGiBReserve_NoCleanup")
    stdout, stderr = output / (label + ".stdout.log"), output / (label + ".stderr.log")
    started = time.time_ns(); child = None; code = None; observed = killed = False; failure = None; cleanup = None
    with stdout.open("xb") as out, stderr.open("xb") as err:
        try:
            child = subprocess.Popen(list(map(str, arguments)), cwd=cwd,
                                     stdin=subprocess.PIPE if input_bytes is not None else subprocess.DEVNULL,
                                     stdout=out, stderr=err, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            write_new(output / (label + ".start.json"), {"pid": child.pid, "arguments": list(map(str, arguments)),
                      "cwd": str(cwd), "startedUnixNs": started, "programStdinPersisted": False})
            if input_bytes is not None:
                child.communicate(input=input_bytes, timeout=timeout)
                code = child.returncode
            else: code = child.wait(timeout=timeout)
            observed = True
        except BaseException as error:
            failure = error
            if child is not None:
                try:
                    if child.poll() is None: child.kill(); killed = True
                    code = child.wait(timeout=30); observed = True
                except BaseException as cleanup_error: cleanup = type(cleanup_error).__name__
    receipt = {"pid": child.pid if child else None, "arguments": list(map(str, arguments)), "cwd": str(cwd),
               "exitCode": code, "expectedExit": expected, "passed": failure is None and observed and code == expected,
               "actualExitObserved": observed, "startedUnixNs": started, "finishedUnixNs": time.time_ns(),
               "stdout": bound(root, stdout), "stderr": bound(root, stderr), "ownedChildKilledAfterFailure": killed,
               "failureClass": type(failure).__name__ if failure else None, "cleanupDiagnostic": cleanup,
               "childMayStillBeRunning": child is not None and child.poll() is None,
               "descendantCleanup": "NotEstablishedAfterInterruptedCargo" if failure and "cargo" in str(arguments[0]) else "NoForeignProcessesInspectedOrKilled",
               "automaticRetry": False}
    path = output / (label + ".command.json"); write_new(path, receipt)
    require(receipt["passed"] is True, "ActualCompatibilityNativeFailure:" + label)
    return {"receipt": bound(root, path), "start": bound(root, output / (label + ".start.json")), **receipt}


def historical_controls(root, legacy, output):
    output.mkdir()
    results, commands = [], []
    for identity, validator, tests in FAMILIES:
        semantic = []
        for index, filename in enumerate((validator, tests)):
            tail = []
            if identity == "m2ax": tail = ["research/p28-word0196/toolchain_provenance_contract.json" if index == 0 else "research/p28-word0196"]
            if identity == "m2aw": tail = ["research/p28-word0196/target_abi_contract.json"]
            command = native(root, legacy, output, identity + "-" + str(index),
                             [sys.executable, "-B", legacy / RESEARCH / filename, *tail])
            commands.append(command)
            text = (root / command["stdout"]["path"]).read_text(encoding="utf-8-sig")
            machine = []; non_json = []
            for line in text.splitlines():
                if not line.strip(): continue
                try: value = bounded_json(line.encode("utf-8"), LIMIT)
                except (ValueError, AssertionError): non_json.append(line)
                else:
                    require(type(value) is dict, "WholeHistoricalMachineJsonObject")
                    machine.append(value)
            require(len(machine) > 0 and not non_json, "EveryHistoricalStdoutRecordIsCompleteMachineJson")
            for value in machine:
                require(value.get("passed", True) is True and value.get("failures", 0) == 0
                        and value.get("skipped", 0) == 0, "HistoricalPureControlMustActuallyPassWithoutSkips")
            err = (root / command["stderr"]["path"]).read_text(encoding="utf-8-sig")
            if identity == "m2ax" and index == 1:
                match = re.fullmatch(r"[.\r\n]+-+\r?\nRan ([0-9]+) tests in [0-9.]+s\r?\n\r?\nOK\r?\n?", err)
                require(match is not None and len(machine) == 1 and machine[0]["tests"] == int(match[1]),
                        "DeclaredUnittestProgressTransportOnly_MachineJsonCountsRetained")
            else: require(err == "", "UnexpectedHistoricalPureStderr")
            semantic.append({"source": binding(legacy, RESEARCH + filename), "exitCode": command["exitCode"],
                             "machineJsonRecords": machine, "nonJsonStdoutLines": [], "failedOrSkipped": False})
        results.append({"kind": "historical_pinned_research_semantics", "family": identity,
                        "exactHistoricalBase": analysis.PINNED_BO, "scope": "ActualPureHistoricalResearchControls_NoTargetCpu",
                        "commands": semantic, "targetCpuExecutions": 0})
    require(len(results) == 14, "AllFourteenHistoricalFamilies")
    return results, commands


def header_pair(old, active, allowed):
    left = {row["path"]: row for row in old["source_bindings"]}
    right = {row["path"]: row for row in active["source_bindings"]}
    changed = {name for name in left if left[name] != right.get(name)}
    require(set(left) == set(right) and changed <= allowed and CHANGED_BP_HEADERS <= changed,
            "OnlyExplicitFrozenHeaderSourceRows")
    copied = deepcopy(active); copied["source_bindings"] = old["source_bindings"]
    require(first_difference(old, copied) is None, "EveryNonSourceHeaderFieldMustRemainExact")
    return {"pinned": old, "active": active, "changedSourceRows":
            [{"path": name, "old": left[name], "new": right[name]} for name in sorted(changed)]}


def paired(root, old_path, active_path, output, expected_count, codec=None, transition=None, bp=None, pinned=None):
    writer = Writer(root, output, codec); first = iter(rows(old_path, codec)); second = iter(rows(active_path, codec)); count = 0
    try:
        while True:
            left, right = next(first, None), next(second, None)
            if left is None or right is None:
                require(left is right is None, "ExactEqualChildRecordInventory"); break
            if transition and left.get("kind") in ("optin_header", "composite_header"):
                require(first_difference(left, transition["pinned"]) is None
                        and first_difference(right, transition["active"]) is None, "TwoCompleteIndependentlyFrozenHeaders")
            elif transition and left.get("kind") == "arbitrary_operation_refusal":
                require(bp is not None and first_difference(left, bp.expected_arbitrary(pinned)) is None
                        and first_difference(right, bp.expected_arbitrary(root)) is None, "CompleteNestedVersionedHeaderAndRefusal")
            else: require(first_difference(left, right) is None, "EveryCompleteObservationFieldEqual:" + str(count))
            writer.put({"record": count, "pinned": left, "active": right,
                        "comparison": "CompleteRecord_NoArchitecturalOrObservationFieldsExcluded"}); count += 1
        require(count == expected_count, "FrozenExactCompatibilityRecordCount")
    finally:
        first.close(); second.close()
        result = writer.close()
    return result


def expected_records(root, output, records, codec=None):
    writer = Writer(root, output, codec)
    try:
        for record in records: writer.put(record)
    finally: result = writer.close()
    return result


def expected_default_totals(oracle, micro):
    from collections import Counter
    return {"positive_cases": 468, "positive_cpu_instances": 468, "positive_bus_instances": 468,
            "positive_step_calls": 468, "positive_successful_step_calls": 468, "positive_failed_step_calls": 0,
            "positive_instruction_counter_delta": 468, "capability_cases": 2, "capability_cpu_instances": 2,
            "capability_bus_instances": 2, "capability_step_calls": 2, "capability_successful_step_calls": 0,
            "capability_failed_step_calls": 2, "capability_instruction_counter_delta": 1, "admission_refusals": 0,
            "observed_decoded_forms": dict(sorted(Counter(oracle.expected_decode(row)["mnemonic"] for row in micro).items()))}


def build_default(root, baseline, target, output, helpers, *, baseline_only=False):
    shared = helpers["default_mode_compatibility"]; commands = []; binaries = {}
    roles = (("baseline", baseline),) if baseline_only else (("baseline", baseline), ("active", root))
    for label, tree in roles:
        production_target, probe_target = target / label / "production", target / label / "probe"
        for kind, manifest, destination in (("production", tree / "rust/p28-slice-runner/Cargo.toml", production_target),
                                           ("probe", target / "staging" / label / "Cargo.toml", probe_target)):
            commands.append(native(root, tree, output, label + "-" + kind,
                ["cargo", "+1.85.1", "build", "--release", "--locked", "--offline", "--jobs", "1",
                 "--no-default-features", "--manifest-path", manifest, "--target-dir", destination]))
        suffix = ".exe" if os.name == "nt" else ""
        binaries[label] = {"production": production_target / "release" / ("p28-slice-runner" + suffix),
                           "probe": probe_target / "release" / ("m2bp-default-compatibility" + suffix)}
    if baseline_only:
        binaries["active"] = binaries["baseline"]
    return binaries, commands


def run_default(root, tree, binary, output, frozen, helpers):
    """Whole old default protocol; BO supplies only the immutable micro oracle."""
    shared = helpers["default_mode_compatibility"]
    corpus, oracle = shared.load_references(Path(frozen["referenceRoot"]))
    micro, protocols = corpus.build_corpus(), shared.protocol_cases()
    require(first_difference(shared.input_projection(micro, protocols, oracle), frozen["inputs"]) is None,
            "IndependentOldDefaultInputsUnchanged")
    from production_transfer_stream import Harness
    output.mkdir(); writer = Writer(root, output / "canonical.jsonl.gz"); process = None; commands = []
    count = 0
    def put(value):
        nonlocal count
        writer.put(value); count += 1
    try:
        process = Harness([str(binary["probe"])], tree, output)
        header = process.receive()
        require(header["kind"] == "default_compatibility_identity" and header["cpu_instances"] == 0,
                "ActualDefaultProbeIdentityBeforeCpu")
        shared.check_identity(header["identity"], frozen["independentIdentity"]); put(header)
        for request in micro:
            process.send({"kind": "micro", "request": request}); actual = process.receive()
            require(oracle.compare(oracle.expected_case(request), actual) is None, "IndependentDefaultMicroStateMismatch")
            put(actual)
        process.send({"kind": "capabilities", "request": micro[0]}); actual = process.receive()
        require(oracle.compare({"kind": "capability_observations", "records": frozen["capabilityExpected"]}, actual) is None,
                "ActualDefaultCapabilityFaultsUnchanged"); put(actual)
        process.send({"kind": "finish"}); actual = process.receive()
        require(first_difference(actual["totals"], frozen["expectedProbeTotals"]) is None
                and actual["production_composite_executions"] == 0, "ActualDefaultProbeCountersComplete")
        observed_totals = actual["totals"]; put(actual); process.finish()
        for index, case in enumerate(protocols):
            command = native(root, tree, output, "protocol-" + str(index), [binary["production"]],
                             expected=case["expected_exit"], timeout=180, input_bytes=canonical(case["request"]))
            commands.append(command)
            raw = (root / command["stdout"]["path"]).read_bytes()
            err = (root / command["stderr"]["path"]).read_bytes()
            if command["exitCode"] == 0:
                response = bounded_json(raw, LIMIT); shared.check_identity(response, frozen["independentIdentity"])
                require(response["operation"] == case["request"]["operation"], "OriginalProtocolOperationNotRelabeled")
                for path, expected in case["assertions"]:
                    require(first_difference(shared.lookup(response, path), expected) is None, "OldProtocolAssertionUnchanged")
                actual = {"kind": "legacy_protocol_observation", "case_id": case["case_id"],
                          "exitCode": 0, "response": response, "stderr": err.decode("utf-8")}
            else:
                actual = {"kind": "legacy_protocol_refusal", "case_id": case["case_id"],
                          "exitCode": command["exitCode"], "stdout": raw.decode("utf-8"), "stderr": err.decode("utf-8")}
            put(actual)
        require(count == 493 and len(commands) == 22, "CompleteDefault493And22ActualProtocolProcesses")
    finally:
        if process is not None and not process.finished: process.abort()
        result = writer.close()
    return {"canonical": result, "actualProbeTotals": observed_totals,
            "actualCpuInstancesInProbe": observed_totals["positive_cpu_instances"] + observed_totals["capability_cpu_instances"],
            "actualBusInstancesInProbe": observed_totals["positive_bus_instances"] + observed_totals["capability_bus_instances"],
            "protocolProcesses": len(commands), "commands": commands,
            "probeRuntimeStart": bound(root, output / "runtime.start.json"),
            "probeRuntimeEnd": bound(root, output / "runtime.end.json"),
            "firstMismatch": None}


def expectation_lock(root, path, source):
    fixed = root / ".tmp/m2br-owned/public-evidence/transfer/independent-expectation-lock.json"
    require(Path(path).resolve() == fixed, "OnlyTheDeclaredIndependentTransferExpectationLock")
    value, row = checked_json(root, fixed)
    require(value["milestone"] == "M2br" and first_difference(value["sourceState"]["sourceProof"], source) is None,
            "IndependentTransferOracleAndCompleteSourceGraphLockedBeforeAnyHistoricalCpu")
    require(set(value["canonicalLanes"]) == {"admission", "positive", "negative"}, "AllThreeTransferExpectedLanesLockedFirst")
    for lane in value["canonicalLanes"].values():
        require(type(lane["records"]) is int and lane["records"] > 0 and type(lane["bytes"]) is int
                and lane["bytes"] > 0 and type(lane["maxRowBytes"]) is int and 0 < lane["maxRowBytes"] <= LIMIT,
                "IndependentExpectedTransferRowAndWholeStreamBounds")
        require(binding(root, lane["expectedCompressed"]["path"]) == lane["expectedCompressed"],
                "ActualLockedIndependentExpectedStreamIdentity")
    return value, row


def freeze(root, bq, bp_root, bo, output, target, lock_path):
    require(not output.exists() and not target.exists(), "FreshCompatibilityFreezeAndBuildRoots")
    proof, _, helpers = load_helpers(root, bq, bp_root, bo)
    lock, lock_binding = expectation_lock(root, lock_path, proof)
    output.mkdir(parents=True); target.mkdir(parents=True)
    shared = helpers["default_mode_compatibility"]; bp = helpers["validate_production_optin_capabilities"]
    comp = helpers["validate_production_composite"]; codec = helpers["production_composite_projection"]
    historical, historical_commands = historical_controls(root, bo, output / "historical-freeze")
    lanes = {}; expected_dir = output / "expected"; expected_dir.mkdir()
    lanes["historical-pinned"] = expected_records(root, expected_dir / "historical-pinned.jsonl.gz", historical)
    corpus, oracle = shared.load_references(bo); micro = corpus.build_corpus(); protocols = shared.protocol_cases()
    default = {"referenceRoot": str(bo), "inputs": shared.input_projection(micro, protocols, oracle),
               "independentIdentity": shared.independent_identity(bo), "capabilityExpected": oracle.expected_capabilities(),
               "expectedProbeTotals": expected_default_totals(oracle, micro)}
    staging = shared.generate_staging(root, bq, target / "default", root / shared.CRATE)
    baseline_build_dir = output / "default-baseline-build"; baseline_build_dir.mkdir()
    binaries, baseline_builds = build_default(root, bq, target / "default", baseline_build_dir, helpers, baseline_only=True)
    baseline_actual = run_default(root, bq, binaries["baseline"], output / "default-baseline-reference", default, helpers)
    baseline_stream = output / "default-baseline-reference/canonical.jsonl.gz"
    lanes["default"] = paired(root, baseline_stream, baseline_stream, expected_dir / "default.jsonl.gz", 493)
    one = output / "one-step"; one.mkdir()
    active_one, pinned_one = one / "expected-active.jsonl.gz", one / "expected-pinned.jsonl.gz"
    one_expected = {}
    for tree, path, role in ((root, active_one, "active"), (bq, pinned_one, "pinned")):
        cases, patterns, mutations = bp.inputs_and_patterns(tree)
        one_expected[role] = expected_records(root, path, bp.expected_records(tree, cases, patterns, mutations))
    one_header = header_pair(bp.expected_header(bq), bp.expected_header(root), CHANGED_BP_HEADERS)
    lanes["one-step"] = paired(root, pinned_one, active_one, expected_dir / "one-step.jsonl.gz", 583,
                                transition=one_header, bp=bp, pinned=bq)
    generated = bp.generated_disabled_crate(root, target / "one-step")
    generated_bindings = [bound(root, generated / name) for name in ("Cargo.toml", "Cargo.lock", "src/main.rs")]
    composite = output / "composite"; composite.mkdir()
    active_positive = composite / "expected-active-positive.jsonl.gz"
    pinned_positive = composite / "expected-pinned-positive.jsonl.gz"
    active_negative = composite / "expected-active-negative.jsonl.gz"
    negative = helpers["production_composite_negative"]; records_module = helpers["production_composite_records"]
    positive_expected = {}
    positive_expected["active"] = expected_records(root, active_positive, comp.positive_expectations(root), codec)
    def pinned_positive_records():
        # Four-tree proof already established byte-identical old oracle,
        # corpus, topology, codec and Rust probe sources. Functional expected
        # records are source-independent pure values. Generate them through
        # that ONE verified definition role, not a second sys.modules alias.
        generated_rows = iter(comp.positive_expectations(root))
        require(first_difference(next(generated_rows), records_module.header(root)) is None,
                "ActualExpectedActiveHeaderBeforeExactPinnedHeaderConstruction")
        yield records_module.header(bq)
        yield from generated_rows
    positive_expected["pinned"] = expected_records(root, pinned_positive, pinned_positive_records(), codec)
    negative_expected = expected_records(root, active_negative,
                     [records_module.header(root), *negative.expected_negative_records(root)], codec)
    composite_header = header_pair(records_module.header(bq), records_module.header(root), CHANGED_BQ_HEADERS)
    lanes["composite"] = paired(root, pinned_positive, active_positive, expected_dir / "composite.jsonl.gz", 5478,
                                codec=codec, transition=composite_header)
    source_record = {"kind": "complete_four_version_source_transition", "scope": "StaticSourceIo_NotCpuOrQaAcceptance",
                     "sourceProof": proof, "normalizationWrites": 0, "targetCpuExecutions": 0}
    lanes["source-transition"] = expected_records(root, expected_dir / "source-transition.jsonl.gz", [source_record])
    reference_execution = {"scope": "PinnedM2bqDefaultProbeMicroAndCapabilitiesOnly_ProtocolConstructionsNotExposed",
        "probeCpuInstances": baseline_actual["actualCpuInstancesInProbe"], "probeBusInstances": baseline_actual["actualBusInstancesInProbe"],
        "probePositiveExecutions": baseline_actual["actualProbeTotals"]["positive_cases"],
        "probeCapabilityAttempts": baseline_actual["actualProbeTotals"]["capability_step_calls"],
        "protocolProcesses": baseline_actual["protocolProcesses"], "protocolCpuConstructionCount": None,
        "protocolBusConstructionCount": None, "protocolConstructionCountStatus": "NotExposedByLegacyProtocol",
        "actualNativeReceipts": [row["receipt"] for row in baseline_builds + baseline_actual["commands"]],
        "actualProbeRuntimeStart": baseline_actual["probeRuntimeStart"], "actualProbeRuntimeEnd": baseline_actual["probeRuntimeEnd"],
        "independentTransferExpectationLockPredatesHistoricalReference": lock_binding,
        "manufacturerOrInstructionSemanticsOracleClaimed": False}
    require(reference_execution["probeCpuInstances"] == reference_execution["probeBusInstances"] == 470
            and reference_execution["probePositiveExecutions"] == 468 and reference_execution["probeCapabilityAttempts"] == 2,
            "ActualKnownHistoricalProbeCounters_NotGlobalCpuZero")
    composite_freeze = {"milestone": "M2br", "classification": "IndependentOldCompositeCompatibilityExpectationFreeze_NotRuntime",
        "sourceState": {"sourceProof": proof}, "sourceHeaderTransition": composite_header,
        "expectedActivePositive": bound(root, active_positive), "expectedPinnedPositive": bound(root, pinned_positive),
        "expectedActiveNegative": bound(root, active_negative), "positiveCases": 5470, "smokeCases": 4,
        "activePositiveExpectation": positive_expected["active"], "pinnedPositiveExpectation": positive_expected["pinned"],
        "activeNegativeExpectation": negative_expected,
        "canonicalLane": lanes["composite"], "independentTransferExpectationLock": lock_binding,
        "historicalReferenceExecution": reference_execution, "newCpuExecutionScope": "ActiveM2brTransferOnly",
        "newCpuExecutionsBeforeThisFreeze": 0, "newTransferCpuInstancesBeforeThisFreeze": 0, "firmwareReady": False}
    write_new(composite / "pre-runtime-freeze.json", composite_freeze)
    frozen = {"milestone": "M2br", "classification": "VersionExplicitCompatibilityFreeze_WithHistoricalReference_NotGlobalCpuZero",
        "schema": SCHEMA, "sourceState": {"sourceProof": proof}, "canonicalLanes": lanes,
        "independentTransferExpectationLock": lock_binding, "historicalPureCommands": historical_commands,
        "historicalReferenceExecution": reference_execution, "defaultProtocol": default,
        "defaultGeneratedCrates": staging, "defaultBaselineCanonical": bound(root, baseline_stream),
        "oneStepHeaderTransition": one_header, "oneStepGeneratedFeatureOff": generated_bindings,
        "oneStepExpectedActive": bound(root, active_one), "oneStepExpectedPinned": bound(root, pinned_one),
        "oneStepExpectations": one_expected,
        "compositeFreeze": bound(root, composite / "pre-runtime-freeze.json"), "composite": composite_freeze,
        "newCpuExecutionsBeforeThisFreeze": 0, "newCpuExecutionScope": "ActiveM2brTransferOnly",
        "newActiveTreeCpuInstancesBeforeThisFreeze": 0, "historicalPurePythonPairsActuallyRun": 14,
        "historicalControlsAreNotNoSubprocessOrNoTestClaim": True,
        "compatibilityDoesNotEstablishNewCallerOrContinuationInstructionSemantics": True,
        "outputRelative": output.relative_to(root).as_posix(), "targetRelative": target.relative_to(root).as_posix(),
        "originalRomExecutions": 0, "persistentProgramPayloads": 0, "firmwareReady": False}
    require(first_difference(analysis.source_checks(root, bq, bp_root, bo)[0], proof) is None,
            "AllFourSourceGraphsUnchangedDuringFreeze")
    for key, lane in lanes.items(): require(lane["records"] == SCHEMA["scopeRecords"][key], "EveryExpectedScopeCountFrozen")
    write_new(output / "pre-runtime-freeze.json", frozen)
    return frozen


def revalidate(root, bq, bp_root, bo, output, target, frozen):
    proof, _, helpers = load_helpers(root, bq, bp_root, bo)
    require(frozen["milestone"] == "M2br" and frozen["schema"] == SCHEMA
            and first_difference(frozen["sourceState"]["sourceProof"], proof) is None
            and frozen["newCpuExecutionScope"] == "ActiveM2brTransferOnly"
            and frozen["outputRelative"] == output.relative_to(root).as_posix()
            and frozen["targetRelative"] == target.relative_to(root).as_posix(), "ExactNewCompatibilityFreezeAndSourceRoles")
    _, lock_binding = expectation_lock(root, root / frozen["independentTransferExpectationLock"]["path"], proof)
    require(lock_binding == frozen["independentTransferExpectationLock"], "IndependentTransferLockNeverRegenerated")
    for lane in frozen["canonicalLanes"].values():
        require(binding(root, lane["expectedCompressed"]["path"]) == lane["expectedCompressed"], "FrozenExpectedScopeFileImmutable")
    for row in [frozen["defaultBaselineCanonical"], frozen["compositeFreeze"],
                frozen["oneStepExpectedActive"], frozen["oneStepExpectedPinned"], *frozen["oneStepGeneratedFeatureOff"]]:
        require(binding(root, row["path"]) == row, "FrozenCompatibilityDependencyImmutable")
    for row in frozen["defaultGeneratedCrates"]:
        require(binding(root, row["path"]) == {key: row[key] for key in ("path", "bytes", "sha256")},
                "GeneratedDefaultProbeSourcesNeverRevised")
    for row in frozen["composite"].values():
        if type(row) is dict and set(row) == {"path", "bytes", "sha256"}:
            require(binding(root, row["path"]) == row, "CompositePeerExpectedInputsImmutable")
    return proof, helpers


def build_audit(root, crate, binary_name, target, output, role):
    manifest = root / RESEARCH / crate / "Cargo.toml"
    metadata = native(root, root, output, role + "-resolved-feature-graph",
                      ["cargo", "+1.85.1", "metadata", "--format-version", "1", "--locked", "--offline", "--manifest-path", manifest])
    graph, _ = checked_json(root, root / metadata["stdout"]["path"])
    packages = [row for row in graph["packages"] if row["name"] == "p28-slice-runner"]
    require(len(packages) == 1 and Path(packages[0]["manifest_path"]).resolve() == root / "rust/p28-slice-runner/Cargo.toml",
            "ActualCurrentProductionResolvedDependency")
    nodes = [row for row in graph["resolve"]["nodes"] if row["id"] == packages[0]["id"]]
    require(len(nodes) == 1 and "p28-word0196-audit" in nodes[0]["features"]
            and set(nodes[0]["features"]) <= {"default", "p28-word0196-audit"}, "OnlyExplicitDefaultOffAuditFeature")
    build = native(root, root, output, role + "-build",
                   ["cargo", "+1.85.1", "build", "--release", "--locked", "--offline", "--jobs", "1",
                    "--manifest-path", manifest, "--target-dir", target])
    binary = target / "release" / (binary_name + (".exe" if os.name == "nt" else ""))
    require(binary.is_file(), "ActualSourceBoundCompatibilityBinary")
    return binary, [metadata, build]


def pinned_joins(root, bq, pinned_compat, pinned_composite, frozen):
    expected_compat = bq / ".tmp/m2bq-public-evidence/compatibility"
    expected_composite = bq / ".tmp/m2bq-public-evidence/composite"
    require(pinned_compat == expected_compat and pinned_composite == expected_composite, "ExactFreshPinnedBqValidatorOwnedOutputs")
    compatibility, cb = checked_json(root, pinned_compat / "summary.json")
    cfreeze, cf = checked_json(root, pinned_compat / "pre-runtime-freeze.json")
    composite, pb = checked_json(root, pinned_composite / "summary.json")
    pfreeze, pf = checked_json(root, pinned_composite / "pre-runtime-freeze.json")
    require(compatibility["milestone"] == "M2bq" and compatibility["passed"] is True
            and compatibility["LegacyDefaultBehaviorUnchanged"] is True and compatibility["M2bpSingleStepBehaviorUnchanged"] is True
            and compatibility["freeze"] == {key: cf[key] for key in ("bytes", "sha256")}
            and first_difference(cfreeze["sourceState"], frozen["sourceState"]["sourceProof"]["pinnedM2bqProof"]) is None,
            "OldCompatibilityValidatorActuallyPassedOnlyOnExactPinnedBq")
    require(composite["milestone"] == "M2bq" and composite["passed"] is True and composite["firstMismatch"] is None
            and composite["preRuntimeFreeze"] == {key: pf[key] for key in ("bytes", "sha256")}
            and first_difference(pfreeze["sourceState"]["sourceProof"], frozen["sourceState"]["sourceProof"]["pinnedM2bqProof"]) is None
            and composite["actualPositiveCounters"]["positiveCompositeExecutions"] == 5470
            and composite["actualPositiveCounters"]["successfulRetirements"] == 73784
            and composite["actualSmokeCounters"]["executions"] == 4,
            "ActualCompletePinnedBqCompositeReportsAndFreeze")
    one_path, positive_path = pinned_compat / "one-step/canonical.jsonl.gz", pinned_composite / "positive-canonical.jsonl.gz"
    require(bound(root, one_path) == {"path": one_path.relative_to(root).as_posix(), **compatibility["activeOneStep"]["canonical"]}
            and bound(root, positive_path) == {"path": positive_path.relative_to(root).as_posix(), **composite["positiveCanonical"]["compressed"]},
            "ComparedPinnedActualCanonicalFilesJoinActualValidatorSummaries")
    command_receipts = []
    require(type(compatibility["commands"]) is list and len(compatibility["commands"]) > 0,
            "ActualPinnedOneStepCommandInventory")
    for row in compatibility["commands"]:
        require(type(row["path"]) is str and Path(row["path"]).name == row["path"]
                and row["path"].endswith(".command.json"), "OnlyPinnedOneStepContainedCommandBasenames")
        path = pinned_compat / "one-step" / row["path"]
        actual, actual_binding = checked_host_json(root, path)
        require({key: actual_binding[key] for key in ("bytes", "sha256")} == {key: row[key] for key in ("bytes", "sha256")}
                and actual["exitCode"] == 0 and Path(actual["cwd"]).resolve() == bq,
                "ActualSuccessfulPinnedOneStepNativeCommandAtExactTree")
        label = row["path"].removesuffix(".command.json")
        logs = {}
        for suffix in ("stdout", "stderr"):
            logs[suffix] = bound(root, path.parent / (label + "." + suffix + ".log"))
            require({key: logs[suffix][key] for key in ("bytes", "sha256")} == actual[suffix],
                    "PinnedOneStepNativeRawLogIdentity")
        if row["path"] == "optin-production-build.command.json":
            argv = actual["arguments"]
            manifest = Path(argv[argv.index("--manifest-path") + 1]).resolve()
            require(manifest == bq / RESEARCH / "rust-production-optin-audit/Cargo.toml", "ActualPinnedOneStepManifest")
            target = Path(argv[argv.index("--target-dir") + 1]).resolve()
            binary = target / "release" / ("m2bp-production-optin-audit" + (".exe" if os.name == "nt" else ""))
            require(target.is_relative_to(bq / ".tmp/m2bq-optin-target"), "FreshPinnedOneStepTargetOnly")
            logs["binary"] = bound(root, binary)
        command_receipts.append({"receipt": actual_binding, "rawLogs": logs, "arguments": actual["arguments"]})
    require(sum(Path(row["receipt"]["path"]).name == "optin-production-build.command.json" for row in command_receipts) == 1,
            "ExactlyOneActualPinnedOneStepProductionBuild")
    build_start, build_start_binding = checked_host_json(root, pinned_composite / "build.start.json")
    build_end, build_end_binding = checked_host_json(root, pinned_composite / "build.end.json")
    require(first_difference(build_end, composite["actualBuild"]) is None and build_end["exitCode"] == 0
            and build_end["actualExitObserved"] is True and build_end["ownedCargoKilledAfterFailure"] is False
            and build_end["originalWaitFailure"] is build_end["cleanupDiagnostic"] is None
            and build_start["pid"] == build_end["pid"] and type(build_end["pid"]) is int and build_end["pid"] > 0
            and build_start["startedUnixNs"] == build_end["startedUnixNs"] <= build_end["finishedUnixNs"]
            and Path(build_start["cwd"]).resolve() == bq, "ActualPinnedCompositeBuildPidExitTimesAndNoCleanup")
    argv = build_start["command"]
    require(argv[:8] == ["cargo", "+1.85.1", "build", "--locked", "--offline", "--release", "--jobs", "1"]
            and argv[8:10] == ["--manifest-path", "research/p28-word0196/rust-production-composite/Cargo.toml"]
            and argv[10] == "--target-dir" and len(argv) == 12, "ExactPinnedCompositeBuildArguments")
    build_target = Path(argv[11]).resolve()
    require(build_target == bq / ".tmp/m2bq-runtime-target", "ExactPinnedCompositeBuildTarget")
    composite_binary = build_target / "release" / ("m2bq-production-composite" + (".exe" if os.name == "nt" else ""))
    binary_binding = bound(root, composite_binary)
    require({key: binary_binding[key] for key in ("bytes", "sha256")} == composite["actualExecutable"], "ActualPinnedCompositeBinary")
    build_logs = {}
    for suffix in ("stdout", "stderr"):
        build_logs[suffix] = bound(root, pinned_composite / ("build." + suffix + ".log"))
        require({key: build_logs[suffix][key] for key in ("bytes", "sha256")} == build_end[suffix], "ActualPinnedCompositeBuildLogs")
    runtime_start, runtime_start_binding = checked_host_json(root, pinned_composite / "runtime.start.json")
    runtime_end, runtime_end_binding = checked_host_json(root, pinned_composite / "runtime.end.json")
    require({key: runtime_start_binding[key] for key in ("bytes", "sha256")} == composite["runtimeStart"]
            and {key: runtime_end_binding[key] for key in ("bytes", "sha256")} == composite["runtimeEnd"]
            and runtime_start["pid"] == runtime_end["pid"] and type(runtime_end["pid"]) is int and runtime_end["pid"] > 0
            and runtime_start["command"] == [str(composite_binary)] and Path(runtime_start["cwd"]).resolve() == bq
            and runtime_start["startedUnixNs"] == runtime_end["startedUnixNs"] <= runtime_end["finishedUnixNs"]
            and runtime_end["actualExitObserved"] is True and runtime_end["exitCode"] == 0
            and runtime_end["ownedChildKilledAfterFailure"] is False and runtime_end["ownedStreamThreadsFinished"] is True
            and runtime_end["trailingStdoutWasEof"] is True, "ActualPinnedCompositeRuntimePidCommandExitAndEof")
    runtime_stderr = bound(root, pinned_composite / "runtime.stderr.log")
    require(runtime_stderr["bytes"] == 0 and {key: runtime_stderr[key] for key in ("bytes", "sha256")} == runtime_end["stderr"],
            "ActualPinnedCompositeEmptyStderrBinding")
    return {"compatibilitySummary": cb, "compatibilityFreeze": cf, "compositeSummary": pb, "compositeFreeze": pf,
            "oneStepCanonical": bound(root, one_path), "positiveCanonical": bound(root, positive_path),
            "oneStepNativeCommands": command_receipts, "compositeActualBinary": binary_binding,
            "compositeBuildStart": build_start_binding, "compositeBuildEnd": build_end_binding,
            "compositeBuildLogs": build_logs, "compositeRuntimeStart": runtime_start_binding,
            "compositeRuntimeEnd": runtime_end_binding, "compositeRuntimeStderr": runtime_stderr}


def execute_composite(root, output, target, frozen, helpers):
    """Unchanged BQ Rust harness, new source-bound wrapper, no old source pin edits."""
    from production_transfer_stream import Harness
    comp = helpers["validate_production_composite"]; codec = helpers["production_composite_projection"]
    corpus = helpers["production_composite_corpus"]; negative = helpers["production_composite_negative"]
    emitted = helpers["production_composite_emission"]
    binary, commands = build_audit(root, "rust-production-composite", "m2bq-production-composite", target, output, "old-composite")
    binary_binding = bound(root, binary)
    positive = refused = expected_positive = expected_negative = process = None
    last_wire = None; actual_cases = actual_smokes = 0; cpu = bus = retired = 0; smoke_retired = 0
    def observe(actual, writer, expected):
        nonlocal last_wire
        last_wire = {"scope": "OldM2bqApiCompatibility", "actualWire": actual,
                     "source": "BoundedParsedActualStdout_NeverProgramStdin"}
        difference = first_difference(next(expected), actual)
        writer.put(actual)
        require(difference is None, "CompleteIndependentOldCompositeObservationMustMatch")
    try:
        positive = Writer(root, output / "active-positive-canonical.jsonl.gz", codec)
        refused = Writer(root, output / "active-negative-capabilities.jsonl.gz", codec)
        expected_positive = iter(rows(root / frozen["expectedActivePositive"]["path"], codec))
        expected_negative = iter(rows(root / frozen["expectedActiveNegative"]["path"], codec))
        process = Harness([str(binary)], root, output)
        actual = process.receive(); observe(actual, positive, expected_positive); observe(actual, refused, expected_negative)
        program, emission = emitted.emitted_program(root)
        process.send(program); del program
        observe(process.receive(), positive, expected_positive)
        process.send({"kind": "psw_sweep"}); observe(process.receive(), positive, expected_positive)
        for index, path in enumerate("ABCD", 1):
            process.send({"kind": "smoke", "input": negative.control_seeds(root)[path]})
            actual = process.receive(); observe(actual, positive, expected_positive)
            actual_smokes += actual["full_production_composite_executions"]
            smoke_retired += actual["report"]["audit"]["successful_retirements"]
        for request in corpus.iter_cases(root):
            process.send(request); actual = process.receive(); observe(actual, positive, expected_positive)
            actual_cases += actual["full_production_composite_executions"]
            cpu += actual["cpu_instances"]; bus += actual["bus_instances"]
            retired += actual["report"]["audit"]["successful_retirements"]
        process.send({"kind": "capabilities"})
        for _ in range(33): observe(process.receive(), refused, expected_negative)
        require(next(expected_negative, None) is None, "AllOldCapabilityRecordsConsumedInFull")
        process.send({"kind": "finish"}); observe(process.receive(), positive, expected_positive)
        require(next(expected_positive, None) is None, "All5478PositiveRowsConsumedThroughEof")
        process.finish()
    except BaseException as failure:
        partial, diagnostics = {}, []
        if process is not None:
            try: process.abort()
            except BaseException as cleanup_error: diagnostics.append({"role": "owned-child", "class": type(cleanup_error).__name__})
        for label, writer in (("positive", positive), ("negative", refused)):
            if writer is not None:
                try: partial[label] = writer.close()
                except BaseException as cleanup_error: diagnostics.append({"role": label, "class": type(cleanup_error).__name__})
        write_new(output / "FIRST_FAILURE.json", {"milestone": "M2br", "passed": False,
                  "classification": "FirstOldApiCompatibilityFailure_PartialEffectsRetained_NoRetry",
                  "diagnosticClass": type(failure).__name__, "lastBoundedActualWireBeforeFailure": last_wire,
                  "partialCanonicalStreams": partial, "cleanupDiagnostics": diagnostics,
                  "actualCompletedCases": actual_cases, "actualCompletedSmokes": actual_smokes,
                  "expectationsNotRevised": True, "automaticRetry": False})
        raise
    finally:
        for reader in (expected_positive, expected_negative):
            if reader is not None: reader.close()
    positive_result, negative_result = positive.close(), refused.close()
    require(actual_cases == cpu == bus == 5470 and actual_smokes == 4 and retired == 73784 and smoke_retired == 54,
            "ActualOldApiFull5470AndSeparateFourSmokeCounters")
    require(bound(root, binary) == binary_binding, "ActualOldApiCompatibilityBinaryUnchanged")
    comparison = full_compare(root, root / frozen["expectedActivePositive"]["path"], output / "active-positive-canonical.jsonl.gz",
                              frozen["activePositiveExpectation"])
    negative_comparison = full_compare(root, root / frozen["expectedActiveNegative"]["path"], output / "active-negative-capabilities.jsonl.gz",
                                       frozen["activeNegativeExpectation"])
    result = {"milestone": "M2br", "passed": True, "classification": "ActualUnchangedM2bqApiAgainstNewProductionGraph_NotTransferExecution",
        "sourceState": frozen["sourceState"], "positiveCases": actual_cases, "smokeCases": actual_smokes,
        "positiveCpuInstances": cpu, "positiveBusInstances": bus, "positiveRetirements": retired,
        "smokeRetirements": smoke_retired, "actualOldCapabilityRecords": 33,
        "activePositiveCanonical": bound(root, output / "active-positive-canonical.jsonl.gz"),
        "preRuntimeFreeze": bound(root, output / "pre-runtime-freeze.json"),
        "positiveCanonical": positive_result, "negativeCanonical": negative_result,
        "positiveWholeStreamComparison": comparison, "negativeWholeStreamComparison": negative_comparison,
        "actualExecutable": binary_binding, "commands": commands, "actualEmitterReceipt": emission,
        "runtimeStart": bound(root, output / "runtime.start.json"), "runtimeEnd": bound(root, output / "runtime.end.json"),
        "fullNewTransferExecutions": 0, "firstMismatch": None, "originalRomExecutions": 0, "firmwareReady": False}
    write_new(output / "summary.json", result)
    return result


def execute(root, bq, bp_root, bo, output, target, pinned_compat, pinned_composite):
    frozen, freeze_binding = checked_json(root, output / "pre-runtime-freeze.json")
    require(not (output / "summary.json").exists() and not (output / "FIRST_FAILURE.json").exists(), "OneCompatibilityAttemptOnly")
    proof, helpers = revalidate(root, bq, bp_root, bo, output, target, frozen)
    shared = helpers["default_mode_compatibility"]; bp = helpers["validate_production_optin_capabilities"]
    codec = helpers["production_composite_projection"]
    historical, historical_commands = historical_controls(root, bo, output / "historical-actual")
    actual_lanes = {}
    actual_lanes["historical-pinned"] = expected_records(root, output / "historical-pinned-canonical.jsonl.gz", historical)
    runtime = output / "default-execute-build"; runtime.mkdir()
    binaries, default_builds = build_default(root, bq, target / "default", runtime, helpers)
    default_actual = {}
    for role, tree in (("baseline", bq), ("active", root)):
        default_actual[role] = run_default(root, tree, binaries[role], output / ("default-actual-" + role), frozen["defaultProtocol"], helpers)
    (output / "default").mkdir()
    actual_lanes["default"] = paired(root, output / "default-actual-baseline/canonical.jsonl.gz",
                                     output / "default-actual-active/canonical.jsonl.gz", output / "default/canonical.jsonl.gz", 493)
    pinned = pinned_joins(root, bq, pinned_compat, pinned_composite, frozen)
    one = output / "one-step"; one_active = one / "active"; one_active.mkdir()
    binary, one_builds = build_audit(root, "rust-production-optin-audit", "m2bp-production-optin-audit", target / "one-step/production-optin", one_active, "old-one-step")
    expected = frozen["oneStepExpectations"]["active"]
    # The unchanged runtime expects this basename. Copying source-bound
    # expectation bytes is not a mutable old-source identity alias.
    with (one_active / "expected.canonical.jsonl.gz").open("xb") as destination, (root / frozen["oneStepExpectedActive"]["path"]).open("rb") as source:
        shutil.copyfileobj(source, destination, 1024**2)
    require(bound(root, one_active / "expected.canonical.jsonl.gz")["sha256"] == frozen["oneStepExpectedActive"]["sha256"], "ExactFrozenExpectedByteCopy")
    one_frozen = {"sourceState": frozen["sourceState"], "expectedCanonical":
                  {"bytes": expected["bytes"], "sha256": expected["sha256"]}}
    cases, patterns, mutations = bp.inputs_and_patterns(root)
    active_one = bp.runtime(root, binary, target / "one-step", one_active, one_frozen, cases, patterns, mutations)
    pinned_one_path = root / pinned["oneStepCanonical"]["path"]
    pinned_one_comparison = full_compare(root, root / frozen["oneStepExpectedPinned"]["path"], pinned_one_path,
                                         frozen["oneStepExpectations"]["pinned"])
    actual_lanes["one-step"] = paired(root, pinned_one_path, one_active / "canonical.jsonl.gz", one / "canonical.jsonl.gz", 583,
                                       transition=frozen["oneStepHeaderTransition"], bp=bp, pinned=bq)
    # The user-facing scope name is fixed; the unpaired actual child remains
    # active/canonical.jsonl.gz for the unchanged BP runtime's checks/receipts.
    composite = execute_composite(root, output / "composite", target / "composite", frozen["composite"], helpers)
    pinned_positive = root / pinned["positiveCanonical"]["path"]
    pinned_comparison = full_compare(root, root / frozen["composite"]["expectedPinnedPositive"]["path"], pinned_positive,
                                      frozen["composite"]["pinnedPositiveExpectation"])
    actual_lanes["composite"] = paired(root, pinned_positive, output / "composite/active-positive-canonical.jsonl.gz",
                                       output / "composite/canonical.jsonl.gz", 5478, codec, frozen["composite"]["sourceHeaderTransition"])
    actual_lanes["source-transition"] = expected_records(root, output / "source-transition-canonical.jsonl.gz",
        [{"kind": "complete_four_version_source_transition", "scope": "StaticSourceIo_NotCpuOrQaAcceptance",
          "sourceProof": analysis.source_checks(root, bq, bp_root, bo)[0], "normalizationWrites": 0, "targetCpuExecutions": 0}])
    comparisons = {}
    for name, actual in actual_lanes.items():
        comparisons[name] = full_compare(root, root / frozen["canonicalLanes"][name]["expectedCompressed"]["path"],
                                        root / actual["expectedCompressed"]["path"], frozen["canonicalLanes"][name])
    revalidate(root, bq, bp_root, bo, output, target, frozen)
    result = {"milestone": "M2br", "passed": True, "classification": "ActualFourVersionCompatibility_NotNewTransferExecution",
        "sourceState": frozen["sourceState"], "preRuntimeFreeze": freeze_binding, "schema": SCHEMA,
        "canonicalLanes": actual_lanes, "wholeExpectedComparisons": comparisons,
        "historicalPureCommands": historical_commands, "historicalReferenceExecution": frozen["historicalReferenceExecution"],
        "defaultBuildCommands": default_builds, "default": default_actual, "oneStepBuildCommands": one_builds,
        "activeOneStep": active_one, "pinnedActual": pinned, "pinnedOneStepExpectedComparison": pinned_one_comparison,
        "composite": composite, "pinnedCompositeExpectedComparison": pinned_comparison,
        "allFullRecordsRetained": True, "canonicalFieldsExcluded": [], "firstMismatch": None,
        "activeNewTransferExecutions": 0, "originalRomExecutions": 0, "persistentProgramPayloads": 0, "firmwareReady": False}
    write_new(output / "summary.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("pinned-root", "pinned-m2bp-root", "historical-root", "output-dir", "target-dir",
                 "pinned-compatibility-output", "pinned-composite-output", "transfer-expectation-lock"):
        parser.add_argument("--" + name, required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--freeze-only", action="store_true"); mode.add_argument("--execute-freeze", action="store_true")
    args = parser.parse_args(); root = Path.cwd().resolve()
    require(not (root / "private/reports/m2br/FINAL_REPORT_UK.md").exists(), "MilestoneAlreadyClosed_Stop")
    bq, bp_root, bo = (Path(value).resolve() for value in (args.pinned_root, args.pinned_m2bp_root, args.historical_root))
    output, target = own(root, args.output_dir), own(root, args.target_dir, "target")
    failure = output / "FIRST_FAILURE.json"
    require(not failure.exists(), "NoRetryAfterFirstCompatibilityFailure")
    try:
        if args.freeze_only:
            result = freeze(root, bq, bp_root, bo, output, target, Path(args.transfer_expectation_lock).resolve())
            summary = {"milestone": "M2br", "classification": result["classification"],
                       "preRuntimeFreeze": bound(root, output / "pre-runtime-freeze.json"),
                       "newCpuExecutionScope": "ActiveM2brTransferOnly", "newTransferCpuInstances": 0}
        else:
            result = execute(root, bq, bp_root, bo, output, target, Path(args.pinned_compatibility_output).resolve(),
                             Path(args.pinned_composite_output).resolve())
            summary = {"milestone": "M2br", "passed": True, "summary": bound(root, output / "summary.json"), "firstMismatch": None}
        print(canonical(summary).decode("ascii")); return 0
    except BaseException as error:
        if output.exists() and not failure.exists():
            write_new(failure, {"milestone": "M2br", "passed": False, "classification": "FirstCompatibilityAttemptFailure_NoRetry",
                      "diagnosticClass": type(error).__name__, "diagnostic": str(error),
                      "expectationsNotRevised": True, "automaticRetry": False, "firmwareReady": False})
        print(canonical({"milestone": "M2br", "passed": False, "diagnosticClass": type(error).__name__}).decode("ascii")); return 1


if __name__ == "__main__":
    raise SystemExit(main())

