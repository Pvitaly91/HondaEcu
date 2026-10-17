"""M2bp actual opt-in capabilities, separate from historical/default QA.

Freeze every source/input/oracle/projection before the first build or observed
Bus call. Never revise expected records from runtime. A mismatch is retained
and ends this attempt; a new reviewed source requires a new attempt directory.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import gzip
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import threading

sys.dont_write_bytecode = True
import default_mode_compatibility as shared
import production_optin_analysis as analysis
import production_optin_corpus as corpus
import production_optin_oracle as oracle
import production_optin_capability_oracle as capabilities

BASE = analysis.BASE
RESEARCH = "research/p28-word0196/"
CRATE = RESEARCH + "rust-production-optin-audit/"
HEADER_PATHS = tuple("rust/p28-slice-runner/src/" + name for name in
                     ("cpu.rs", "bus.rs", "decoder.rs", "exec.rs", "audit.rs", "audit_bus.rs",
                      "audit_sha256.rs", "audit_tests.rs", "lib.rs", "operand.rs", "full_decoder.rs",
                      "runner.rs")) + ("rust/p28-slice-runner/Cargo.toml", "rust/p28-slice-runner/Cargo.lock",
                                      "rust/p28-slice-runner/src/protocol.rs", "rust/p28-slice-runner/src/main.rs") + tuple(
                                          CRATE + name for name in ("Cargo.toml", "Cargo.lock", "src/main.rs",
                                                                   "src/capabilities.rs", "closed_inputs.json"))
DISABLED_SOURCE = b"use p28_slice_runner::audit::ProgramSegment;\nfn main() {}\n"
SCHEMA = {
    "version": 1, "encoding": "ASCII_SortedKeys_CompactJson_OneLfPerRecord",
    "recordOrder": ["compiled_header", "552_closed_inputs", "25_admission_mutations",
                    "65536_admission_only_psw", "35_actual_capabilities_wrapper", "actual_summary",
                    "feature_off_api_compile_refusal", "arbitrary_operation_process_refusal"],
    "records": 583, "comparison": oracle.PROJECTION,
    "featureOffProjection": {"included": ["actual_exit_success", "actual_rust_error_codes",
                                          "actual_import_unresolved", "actual_cfg_gate_note", "resolved_features"],
                             "outOfBandOnly": ["compiler_rendered_diagnostics", "host_paths", "command_durations",
                                               "compiled_binary_digests"]},
    "arbitraryOperation": "OneActualProcess_ActualHeaderAndFullFixedStderr_Exit1_NoCpu",
    "noCanonicalPlatformNormalization": True,
    "separateInternalSfPairCheck": {"onlyVariantFields": ["case_id_suffix_sf0_sf1", "source_case_id_suffix_sf0_sf1",
                                                           "before.cpu.sf", "after.cpu.sf"],
                                   "canonicalRecordsUnmodified": True, "physicalSfClaim": False},
}
require = shared.require
canonical = shared.canonical
strict = shared.strict
write_new = shared.write_new


def expected_header(root):
    return {"kind": "optin_header", "schema_version": 1, "historical_exact_sha": BASE,
            "source_bindings": [analysis.identity(root, path) for path in HEADER_PATHS],
            "closed_inputs_sha256": shared.binding(root / CRATE / "closed_inputs.json")["sha256"],
            "mechanism": "ProductionBusStrictDecoder_SharedExecuteDecoded_OneStepOnly",
            "feature": "p28-word0196-audit", "default_enabled": False,
            "cpu_instances": 0, "bus_instances": 0, "actual_step_calls": 0,
            "full_production_composite_executions": 0, "original_rom_executions": 0, "firmware_ready": False}


def expected_psw():
    raw = b"".join(value.to_bytes(2, "little") + bytes([value & 0xcc8 == 0xcc8])
                   for value in range(65536))
    return {"kind": "psw_sweep", "inputs": 65536, "representable": 2048, "incompatible": 63488,
            "classification_sha256": sha256(raw).hexdigest(), "cpu_instances": 0,
            "bus_instances": 0, "actual_step_calls": 0}


def expected_summary():
    return {"kind": "optin_summary", "positive_successful_steps": 468, "admission_refusals": 109,
            "positive_cpu_instances": 468, "positive_bus_instances": 468,
            "psw_sweep_observed": True, "capabilities_observed": True,
            "full_production_composite_executions": 0, "original_rom_executions": 0, "firmware_ready": False}


def expected_disabled():
    return {"kind": "feature_off_api_refusal", "actual_exit_success": False,
            "actual_rust_error_codes": ["E0432"], "actual_import_unresolved": True,
            "actual_cfg_gate_note": True, "resolved_features": [],
            "cpu_instances": 0, "bus_instances": 0, "actual_step_calls": 0}


def expected_arbitrary(root):
    return {"kind": "arbitrary_operation_refusal", "exitCode": 1, "header": expected_header(root),
            "extra_stdout": "", "stderr": "M2BP_HARNESS_ERROR=Unknown closed operation; arbitrary ROM/executor not admitted\n",
            "cpu_instances": 0, "bus_instances": 0, "actual_step_calls": 0,
            "original_rom_bytes_supplied": 0}


def inputs_and_patterns(root):
    rows = corpus.build_corpus()
    actual = strict((root / CRATE / "closed_inputs.json").read_bytes())
    require(oracle.difference(rows, actual) is None, "CompiledClosedInputsMustEqualIndependentFrozenGenerator")
    patterns = oracle.instrumentation.load_instrumentation_patterns(root)
    require(len(patterns) == 2623, "UnchangedCompleteProductionPatternInventoryRequired")
    mutations = corpus.admission_mutations(rows)
    require(len(mutations) == 25 and sum(row["metadata_only"] for row in mutations) == 2,
            "Separate23MeaningfulAnd2MetadataAdmissionControlsRequired")
    return rows, patterns, mutations


def expected_records(root, rows, patterns, mutations):
    yield expected_header(root)
    for row in rows:
        yield oracle.expected_case(row, patterns)
    for row in mutations:
        yield row["expected"]
    yield expected_psw()
    yield capabilities.expected_capabilities(rows, patterns)
    yield expected_summary()
    yield expected_disabled()
    yield expected_arbitrary(root)


def generated_disabled_crate(root, target):
    stage = target / "feature-off-api-refusal"
    require(not stage.exists(), "FreshDisabledFeatureCrateRequired")
    (stage / "src").mkdir(parents=True)
    dependency = (root / "rust/p28-slice-runner").as_posix()
    manifest = ('[package]\nname = "m2bp-feature-off-refusal"\nversion = "0.1.0"\nedition = "2021"\n'
                '[workspace]\n[dependencies]\np28-slice-runner = { path = ' + json.dumps(dependency) +
                ', default-features = false }\n')
    lock = (root / "rust/p28-slice-runner/Cargo.lock").read_bytes()
    needle = b'\n[[package]]\nname = "p28-slice-runner"\n'
    require(lock.count(needle) == 1, "ExactPinnedDependencyGraphRequiredForFeatureOffNegative")
    lock = lock.replace(needle, b'\n[[package]]\nname = "m2bp-feature-off-refusal"\nversion = "0.1.0"\ndependencies = [\n "p28-slice-runner",\n]\n' + needle)
    for name, content in (("Cargo.toml", manifest.encode()), ("Cargo.lock", lock), ("src/main.rs", DISABLED_SOURCE)):
        with (stage / name).open("xb") as stream:
            stream.write(content)
    # Exact retained dependency versions/checksums, not a cache-sensitive
    # resolution or a compiler call before the formal freeze.
    return stage


def source_state(root, baseline):
    checked, contract = analysis.source_checks(root, baseline)
    paths = [row["path"] for row in checked["newSourceBindings"]]
    paths += [row["path"] for row in checked["authorizedModifiedFiles"]]
    paths += [analysis.MANIFEST, analysis.CONTRACT]
    return {"sourceChecks": checked, "contract": contract,
            "completeActiveM2bpSources": [analysis.identity(root, path) for path in sorted(set(paths))]}


def prepare(root, baseline, output, target, peer_freeze):
    source = source_state(root, baseline)
    rows, patterns, mutations = inputs_and_patterns(root)
    # Reproduce all historical literal architectural records without target CPU.
    literals = oracle.reproduce_historical_literals()
    require(literals is None, "IndependentHistoricalLiteralReproductionFailed:" + canonical(literals).decode())
    stage = generated_disabled_crate(root, target)
    generated = [{"path": path.relative_to(root).as_posix(), **shared.binding(path)} for path in
                 (stage / "Cargo.toml", stage / "Cargo.lock", stage / "src/main.rs")]
    raw = (output / "expected.canonical.jsonl.gz").open("xb")
    digest, byte_count, count = sha256(), 0, 0
    with raw, gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as writer:
        for value in expected_records(root, rows, patterns, mutations):
            line = canonical(value) + b"\n"
            writer.write(line)
            digest.update(line)
            byte_count += len(line)
            count += 1
    require(count == SCHEMA["records"], "CompleteBeforeRuntimeExpectedRecordInventoryRequired")
    seeds = [{**{key: value for key, value in row.items() if key != "request"},
              "request": {key: value for key, value in row["request"].items() if key not in ("bytes", "guards")}}
             for row in rows]
    frozen = {"milestone": "M2bp", "classification": "InputsExpectedRecordsAndSourcesFrozenBeforeNewObservation",
              "sourceState": source, "coverage": corpus.coverage(rows), "schema": SCHEMA,
              "closedSeedsWithoutRawInstructionPayload": seeds,
              "admissionMutationsSha256": sha256(canonical(mutations)).hexdigest(),
              "admissionMeaningful": 23, "admissionMetadataOnly": 2,
              "capabilityIds": list(capabilities.CAPABILITY_IDS), "historicalLiteralReproduction": literals,
              "generatedFeatureOffCrate": generated,
              "separateDefaultFreeze": {"path": peer_freeze.relative_to(root).as_posix(), **shared.binding(peer_freeze)},
              "expectedCanonical": {"records": count, "bytes": byte_count, "sha256": digest.hexdigest(),
                                    "compressed": shared.binding(output / "expected.canonical.jsonl.gz")},
              "metadataProjection": "OnlySchemaDeclaredHostCommandsPathsDurationsAndCompilerDetailsOutOfBand",
              "newCpuExecutionsBeforeFreeze": 0, "newBusObservationsBeforeFreeze": 0,
              "fullProductionCompositeExecutions": 0, "originalRomExecutions": 0, "firmwareReady": False}
    write_new(output / "pre-runtime-freeze.json", frozen)
    return frozen, rows, patterns, mutations


def revalidate(root, baseline, output, frozen):
    require(source_state(root, baseline) == frozen["sourceState"], "CompleteSourcesChangedAfterFormalFreeze")
    rows, patterns, mutations = inputs_and_patterns(root)
    require(corpus.coverage(rows) == frozen["coverage"] and SCHEMA == frozen["schema"]
            and sha256(canonical(mutations)).hexdigest() == frozen["admissionMutationsSha256"],
            "InputsOrProjectionChangedAfterFormalFreeze")
    require(shared.binding(output / "expected.canonical.jsonl.gz") == frozen["expectedCanonical"]["compressed"],
            "ImmutableBeforeRuntimeExpectedRecordFileChanged")
    for row in frozen["generatedFeatureOffCrate"]:
        require(shared.binding(root / row["path"]) == {key: row[key] for key in ("bytes", "sha256")},
                "FeatureOffNegativeSourceChangedAfterFreeze")
    peer_row = frozen["separateDefaultFreeze"]
    peer_path = root / peer_row["path"]
    require(shared.binding(peer_path) == {key: peer_row[key] for key in ("bytes", "sha256")},
            "SeparateEarlierDefaultFreezeMustStayImmutable")
    peer = strict(peer_path.read_bytes())
    require(peer["exactLegacyBase"] == BASE and peer["newCpuExecutionsBeforeFreeze"] == 0,
            "SeparateDefaultFreezeMustPrecedeEveryNewOptInObservation")
    peer_sources = {row["path"]: row for row in peer["sourceBindings"]["active"]}
    for row in frozen["sourceState"]["completeActiveM2bpSources"]:
        if row["path"].startswith("rust/p28-slice-runner/"):
            require(peer_sources.get(row["path"]) == row, "DefaultAndOptInFreezeMustBindSameProductionVersion")
    return rows, patterns, mutations


def pure_test_receipts(root, output, *, execute):
    result = []
    for name, expected_count in (("production_optin_protocol_tests.py", 10), ("production_optin_comparator_tests.py", 5)):
        label = name.removesuffix(".py").replace("_", "-")
        if execute:
            result.append(shared.actual_command([sys.executable, "-B", root / RESEARCH / name], root, output, label))
        else:
            path = output / (label + ".command.json")
            receipt = strict(path.read_bytes())
            require(receipt["exitCode"] == 0 and receipt["arguments"] ==
                    [sys.executable, "-B", str(root / RESEARCH / name)] and receipt["cwd"] == str(root),
                    "ActualExactPreRuntimePureTestCommandMustPass")
            for suffix in ("stdout", "stderr"):
                require(shared.binding(output / (label + "." + suffix + ".log")) == receipt[suffix],
                        "ImmutablePureTestLogRequired")
            result.append({"path": label + ".command.json", **shared.binding(path)})
        stderr = (output / (label + ".stderr.log")).read_text(encoding="utf-8")
        require(re.search(r"Ran " + str(expected_count) + r" tests? in ", stderr) is not None
                and stderr.rstrip().endswith("OK") and "skipped=" not in stderr,
                "ActualCompletePureProtocolTestsWithoutSkipsRequired:" + label)
    return result


def actual_build(root, target, output):
    manifest = root / CRATE / "Cargo.toml"
    formatting = shared.actual_command(["cargo", "+1.85.1", "fmt", "--check", "--manifest-path", manifest],
                                       root, output, "optin-research-format")
    metadata = shared.actual_command(["cargo", "+1.85.1", "metadata", "--format-version", "1", "--locked",
                                      "--manifest-path", manifest], root, output, "optin-resolved-feature-graph")
    graph = strict((output / "optin-resolved-feature-graph.stdout.log").read_bytes())
    packages = [p for p in graph["packages"] if p["name"] == "p28-slice-runner"]
    require(len(packages) == 1 and Path(packages[0]["manifest_path"]).resolve() == root / "rust/p28-slice-runner/Cargo.toml",
            "ActualOptInProductionDependencyRequired")
    nodes = [p for p in graph["resolve"]["nodes"] if p["id"] == packages[0]["id"]]
    require(len(nodes) == 1 and "p28-word0196-audit" in nodes[0]["features"]
            and set(nodes[0]["features"]) <= {"default", "p28-word0196-audit"},
            "ActualExplicitAuditFeatureOnlyRequired")
    build = shared.actual_command(["cargo", "+1.85.1", "build", "--release", "--locked", "--jobs", "1",
                                   "--manifest-path", manifest, "--target-dir", target / "production-optin"],
                                  root, output, "optin-production-build")
    binary = target / "production-optin/release" / ("m2bp-production-optin-audit" + (".exe" if os.name == "nt" else ""))
    require(binary.is_file(), "ActualCompiledOptInHarnessRequired")
    tests = shared.actual_command(["cargo", "+1.85.1", "test", "--release", "--locked", "--jobs", "1",
                                   "--no-default-features", "--features", "p28-word0196-audit",
                                   "--manifest-path", root / "rust/p28-slice-runner/Cargo.toml",
                                   "--target-dir", target / "optin-tests"], root, output, "optin-production-tests")
    summaries = re.findall(r"test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored; (\d+) measured; (\d+) filtered out;",
                           (output / "optin-production-tests.stdout.log").read_text(encoding="utf-8"))
    require(summaries and sum(int(row[0]) for row in summaries) >= 333
            and all(all(int(value) == 0 for value in row[1:]) for row in summaries),
            "All321HistoricalAnd12NewProductionTests_UnfilteredWithoutSkipsRequired")
    return binary, [formatting, metadata, build, tests]


def actual_disabled(root, target, output):
    stage = target / "feature-off-api-refusal"
    shared.actual_command(["cargo", "+1.85.1", "metadata", "--format-version", "1", "--locked", "--no-default-features",
                           "--manifest-path", stage / "Cargo.toml"], root, output, "disabled-api-feature-graph")
    graph = strict((output / "disabled-api-feature-graph.stdout.log").read_bytes())
    packages = [p for p in graph["packages"] if p["name"] == "p28-slice-runner"]
    require(len(packages) == 1 and Path(packages[0]["manifest_path"]).resolve() == root / "rust/p28-slice-runner/Cargo.toml",
            "FeatureOffNegativeMustResolveActualActiveProduction")
    nodes = [p for p in graph["resolve"]["nodes"] if p["id"] == packages[0]["id"]]
    require(len(nodes) == 1, "ActualFeatureOffGraphRequired")
    command = ["cargo", "+1.85.1", "check", "--locked", "--jobs", "1", "--no-default-features", "--message-format=json",
               "--manifest-path", str(stage / "Cargo.toml"), "--target-dir", str(target / "feature-off-compile")]
    with (output / "disabled-api-compiler.stdout.log").open("xb") as stdout, (output / "disabled-api-compiler.stderr.log").open("xb") as stderr:
        completed = subprocess.run(command, cwd=root, stdout=stdout, stderr=stderr, check=False, timeout=1800)
    messages = []
    for raw in (output / "disabled-api-compiler.stdout.log").read_bytes().splitlines():
        value = strict(raw)
        if value.get("reason") == "compiler-message" and value["message"].get("level") == "error":
            messages.append(value["message"])
    codes = sorted({m["code"]["code"] for m in messages if m.get("code")})
    rendered = "\n".join(m.get("rendered") or "" for m in messages)
    result = {"kind": "feature_off_api_refusal", "actual_exit_success": completed.returncode == 0,
              "actual_rust_error_codes": codes,
              "actual_import_unresolved": any("unresolved import `p28_slice_runner::audit`" in m["message"] for m in messages),
              "actual_cfg_gate_note": "p28-word0196-audit" in rendered and "gated behind" in rendered,
              "resolved_features": nodes[0]["features"], "cpu_instances": 0, "bus_instances": 0, "actual_step_calls": 0}
    write_new(output / "disabled-api-compiler.receipt.json", {"arguments": command, "exitCode": completed.returncode,
              "stdout": shared.binding(output / "disabled-api-compiler.stdout.log"),
              "stderr": shared.binding(output / "disabled-api-compiler.stderr.log"),
              "projection": SCHEMA["featureOffProjection"], "actualProjectedRecord": result})
    return result


def mutation_checks(expected, actual):
    """Prove comparator sensitivity using actual matched observations, no CPU.

    One scalar of each complete schema path (array index wildcarded), plus each
    ordered-array reversal/omission. Actual equality is required first. Every
    field/value in the unmodified runtime is compared independently beforehand.
    """
    require(oracle.difference(expected, actual) is None, "SensitivityRequiresAlreadyIndependentMatchedActualRecord")
    representatives = {}
    arrays = {}

    def visit(value, path=(), schema=()):
        if isinstance(value, dict):
            for key, child in value.items():
                visit(child, path + (key,), schema + (key,))
        elif isinstance(value, list):
            if value:
                arrays.setdefault(schema, path)
                # Discover every heterogeneous nested event/capability schema;
                # only homogeneous scalar arrays use bounded position probes.
                indices = (range(len(value)) if any(isinstance(child, (dict, list)) for child in value)
                           else sorted({0, len(value) // 2, len(value) - 1}))
                for index in indices:
                    visit(value[index], path + (index,), schema + ("*",))
        else:
            representatives.setdefault(schema, path)

    def at(value, path):
        for key in path:
            value = value[key]
        return value

    visit(actual)
    count = 0
    for path in representatives.values():
        changed = deepcopy(actual)
        parent, key = at(changed, path[:-1]), path[-1]
        value = parent[key]
        parent[key] = (not value if type(value) is bool else value + 1 if type(value) is int
                       else value + "_MUTATED" if type(value) is str else "MUTATED_NULL")
        require(oracle.difference(expected, changed) is not None, "UndetectedMeaningfulScalarMutation:" + str(path))
        count += 1
    for path in arrays.values():
        changed = deepcopy(actual)
        values = at(changed, path)
        values.pop()
        require(oracle.difference(expected, changed) is not None, "UndetectedOrderedEventOrStateOmission:" + str(path))
        count += 1
        original = at(actual, path)
        if len(original) > 1 and original != list(reversed(original)):
            changed = deepcopy(actual)
            at(changed, path).reverse()
            require(oracle.difference(expected, changed) is not None, "UndetectedOrderedArrayReversal:" + str(path))
            count += 1
    return count


def runtime(root, binary, target, output, frozen, rows, patterns, mutations):
    expected_path = output / "expected.canonical.jsonl.gz"
    actual_path = output / "canonical.jsonl.gz"
    count, mutations_detected = 0, 0
    tested_forms = set()
    sf_pairs, paired = {}, 0
    actual_totals = {"cpu": 0, "bus": 0, "steps": 0, "shared": 0, "retirements": 0,
                     "positives": 0, "admissionRefusals": 0}
    cap_totals = None
    stdout_stderr = (output / "optin-runtime.stderr.log").open("xb")
    writer_raw = actual_path.open("xb")
    writer = gzip.GzipFile(filename="", mode="wb", fileobj=writer_raw, mtime=0)
    expected_stream = gzip.open(expected_path, "rb")
    try:
        process = subprocess.Popen([str(binary)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=stdout_stderr)
    except Exception:
        expected_stream.close()
        writer.close()
        writer_raw.close()
        stdout_stderr.close()
        raise
    timer = threading.Timer(600, process.kill)  # Only this harness child, never a foreign process.

    def record(actual, context, *, sensitivity=False):
        nonlocal count, mutations_detected
        expected_line = expected_stream.readline(4 * 1024**2)
        require(expected_line.endswith(b"\n"), "FrozenExpectedRecordMissing")
        expected = strict(expected_line)
        actual_line = canonical(actual) + b"\n"
        writer.write(actual_line)
        writer.flush()
        mismatch = oracle.difference(expected, actual)
        if mismatch is not None or actual_line != expected_line:
            write_new(output / "first-mismatch.json", {"context": context, "record": count,
                "firstMismatch": mismatch or "CanonicalBytesDiffer", "expected": expected, "actual": actual,
                "sourceStateAtFreeze": frozen["sourceState"], "expectationsNotRevised": True})
            raise AssertionError("FirstOptInRuntimeMismatch:" + context)
        count += 1
        if sensitivity:
            mutations_detected += mutation_checks(expected, actual)

    def exchange(command=None):
        if command is not None:
            process.stdin.write(canonical(command) + b"\n")
            process.stdin.flush()
        line = process.stdout.readline(4 * 1024**2)
        require(line.endswith(b"\n"), "BoundedActualOptInRecordRequired")
        return strict(line)

    try:
        timer.start()
        record(exchange(), "actual-compiled-header", sensitivity=True)
        for item in rows:
            actual = exchange({"kind": "case", "input": item})
            form = item["request"]["form"]
            sensitivity = item["expected_admission"] == "Accepted" and form not in tested_forms
            record(actual, item["request"]["case_id"], sensitivity=sensitivity)
            if actual["kind"] == "optin_observation":
                actual_totals["positives"] += 1
                for name, value in (("cpu", actual["cpu_instances"]), ("bus", actual["bus_instances"]),
                                    ("steps", actual["audit"]["step_calls"]),
                                    ("shared", actual["audit"]["shared_execution_calls"]),
                                    ("retirements", actual["audit"]["successful_retirements"])):
                    actual_totals[name] += value
                normalized = deepcopy(actual)
                for name in ("case_id", "source_case_id"):
                    require(normalized[name].endswith(("-sf0", "-sf1")), "ClosedSfVariantIdentityRequired")
                    normalized[name] = normalized[name][:-4]
                for name in ("before", "after"):
                    require(normalized[name]["cpu"]["sf"] is item["request"]["internal_sf"], "ActualInternalSfPreservationRequired")
                    normalized[name]["cpu"]["sf"] = False
                key = normalized["case_id"]
                if key in sf_pairs:
                    require(oracle.difference(sf_pairs.pop(key), normalized) is None, "ActualInternalSfPairEffectMismatch:" + key)
                    paired += 1
                else:
                    sf_pairs[key] = normalized
            else:
                actual_totals["admissionRefusals"] += 1
            if sensitivity:
                tested_forms.add(form)
        for item in mutations:
            record(exchange({"kind": "admit", "input": item["input"]}), item["id"], sensitivity=True)
            actual_totals["admissionRefusals"] += 1
        record(exchange({"kind": "psw_sweep"}), "all-65536-psw-admission", sensitivity=True)
        observed_capabilities = exchange({"kind": "capabilities"})
        record(observed_capabilities, "all-35-actual-capability-records", sensitivity=True)
        cap_rows = observed_capabilities["records"]
        cap_totals = {"cases": len(cap_rows), "cpu": sum(row["cpu_instances"] for row in cap_rows),
                      "bus": sum(row["bus_instances"] for row in cap_rows),
                      "steps": sum(row["audit"]["step_calls"] for row in cap_rows if "audit" in row),
                      "shared": sum(row["audit"]["shared_execution_calls"] for row in cap_rows if "audit" in row),
                      "retirements": sum(row["audit"]["successful_retirements"] for row in cap_rows if "audit" in row)}
        record(exchange({"kind": "finish"}), "actual-runtime-summary", sensitivity=True)
        process.stdin.close()
        require(process.wait(timeout=30) == 0 and process.stdout.read() == b"", "ExactOptInFinishRequired")
        timer.cancel()
        require((output / "optin-runtime.stderr.log").stat().st_size == 0, "UnexpectedActualOptInStderr")
        record(actual_disabled(root, target, output), "actual-disabled-feature-api-compile-refusal", sensitivity=True)
        arbitrary = subprocess.run([str(binary)], input=canonical({"kind": "arbitrary_rom"}) + b"\n",
                                   capture_output=True, check=False, timeout=30)
        lines = arbitrary.stdout.splitlines(keepends=True)
        actual = {"kind": "arbitrary_operation_refusal", "exitCode": arbitrary.returncode,
                  "header": strict(lines[0]) if lines else None,
                  "extra_stdout": b"".join(lines[1:]).decode("utf-8"), "stderr": arbitrary.stderr.decode("utf-8"),
                  "cpu_instances": 0, "bus_instances": 0, "actual_step_calls": 0, "original_rom_bytes_supplied": 0}
        record(actual, "actual-arbitrary-operation-process-refusal", sensitivity=True)
        require(expected_stream.read() == b"" and count == SCHEMA["records"] and len(tested_forms) == 16
                and paired == 234 and not sf_pairs,
                "CompleteFrozenCoverageRequired")
    finally:
        timer.cancel()
        if process.poll() is None:
            process.kill()
            process.wait(timeout=30)
        process.stdout.close()
        stdout_stderr.close()
        writer.close()
        writer_raw.close()
        expected_stream.close()
    comparison = shared.compare_streams(expected_path, actual_path)
    require(comparison["comparedBytes"] == frozen["expectedCanonical"]["bytes"]
            and comparison["canonicalSha256"] == frozen["expectedCanonical"]["sha256"], "ExactFrozenCanonicalDigestRequired")
    require(actual_totals == {"cpu": 468, "bus": 468, "steps": 468, "shared": 468,
                             "retirements": 468, "positives": 468, "admissionRefusals": 109}
            and cap_totals == {"cases": 35, "cpu": 27, "bus": 27, "steps": 10, "shared": 4, "retirements": 3},
            "CountersDerivedFromEveryMatchedActualRecordMustMatchFrozenCoverage")
    return {"records": count, "positiveSuccessfulSingleSteps": actual_totals["positives"], "observedForms": len(tested_forms),
            "positiveInternalSfPairs": paired, "actualPositiveCounters": actual_totals,
            "actualCapabilityCounters": cap_totals, "unchangedM2boAdmissionRefusals": 84,
            "extraAdmissionRefusals": 25, "extraMeaningfulAdmissionRefusals": 23, "metadataOnlyAdmissionRefusals": 2,
            "capabilityCases": cap_totals["cases"], "capabilityCpuInstances": cap_totals["cpu"], "capabilityBusInstances": cap_totals["bus"],
            "capabilityActualStepAttempts": cap_totals["steps"], "capabilitySharedExecutionCalls": cap_totals["shared"],
            "capabilitySuccessfulRetirements": cap_totals["retirements"],
            "cpuInstancesWithinThisHarness": actual_totals["cpu"] + cap_totals["cpu"],
            "busInstancesWithinThisHarness": actual_totals["bus"] + cap_totals["bus"],
            "actualStepAttemptsWithinThisHarness": actual_totals["steps"] + cap_totals["steps"],
            "sharedExecutionCallsWithinThisHarness": actual_totals["shared"] + cap_totals["shared"],
            "successfulRetirementsWithinThisHarness": actual_totals["retirements"] + cap_totals["retirements"],
            "pswInputsAdmissionOnly": 65536,
            "meaningfulMatchedActualRecordMutationsDetected": mutations_detected,
            "featureOffApiActuallyRefused": True, "arbitraryOperationActuallyRefused": True,
            "canonical": shared.binding(actual_path), "wholeStreamComparison": comparison, "firstMismatch": None,
            "allDeclaredActualFieldsCompared": True, "canonicalPlatformExclusions": [],
            "fullProductionCompositeExecutions": 0, "originalRomExecutions": 0, "firmwareReady": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--historical-root", required=True)
    parser.add_argument("--output-dir", default=".tmp/m2bp-public-evidence/optin")
    parser.add_argument("--target-dir", default=".tmp/m2bp-optin-target")
    parser.add_argument("--default-freeze", default=".tmp/m2bp-public-evidence/default/pre-runtime-freeze.json")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--freeze-only", action="store_true")
    mode.add_argument("--execute-freeze", action="store_true")
    args = parser.parse_args()
    root, baseline = Path(__file__).resolve().parents[2], Path(args.historical_root).resolve()
    output, target = shared.owned(root, args.output_dir), shared.owned(root, args.target_dir)
    peer_freeze = shared.owned(root, args.default_freeze)
    require(root != baseline and not (root / "private/reports/m2bp/FINAL_REPORT_UK.md").exists(),
            "OpenM2bpLifecycleAndSeparateExactBaselineRequired")
    try:
        if args.execute_freeze:
            frozen = strict((output / "pre-runtime-freeze.json").read_bytes())
            require(not (output / "summary.json").exists() and not (output / "optin-production-build.command.json").exists(),
                    "NoAutomaticRetryOrEvidenceOverwrite")
            rows, patterns, mutations = revalidate(root, baseline, output, frozen)
        else:
            require(not output.exists() and not target.exists(), "FreshOwnedOptInAttemptPathsRequired")
            output.mkdir(parents=True)
            peer = strict(peer_freeze.read_bytes())
            require(peer["exactLegacyBase"] == BASE and peer["newCpuExecutionsBeforeFreeze"] == 0,
                    "EarlierDefaultFreezeRequiredBeforeOptInFreeze")
            frozen, rows, patterns, mutations = prepare(root, baseline, output, target, peer_freeze)
            revalidate(root, baseline, output, frozen)
            pure_test_receipts(root, output, execute=True)
        if args.freeze_only:
            print(canonical({"passed": True, "classification": "BeforeRuntimeFreezeOnly", "cpuExecutions": 0,
                             "freeze": shared.binding(output / "pre-runtime-freeze.json")}).decode(), flush=True)
            return 0
        commands = pure_test_receipts(root, output, execute=False)
        revalidate(root, baseline, output, frozen)
        binary, build_commands = actual_build(root, target, output)
        commands.extend(build_commands)
        observed = runtime(root, binary, target, output, frozen, rows, patterns, mutations)
        revalidate(root, baseline, output, frozen)
        write_new(output / "summary.json", {"milestone": "M2bp", "passed": True,
            "classification": "ActiveTreeOptInCapabilityQA_NotWholeMilestoneAcceptance",
            "preRuntimeFreeze": shared.binding(output / "pre-runtime-freeze.json"),
            "sourceTransition": frozen["sourceState"]["sourceChecks"], "commands": commands,
            "compiledBinary": shared.binding(binary), "runtime": observed, "firstMismatch": None,
            "HistoricalPinnedBaselineQA": "SeparateGate", "ActiveTreeDefaultModeQA": "SeparateGate",
            "crossPlatformCanonicalComparison": "SeparateFullByteGate", "milestoneAccepted": False,
            "fullProductionCompositeExecutions": 0, "originalRomExecutions": 0, "firmwareReady": False})
        print(canonical({"passed": True, "summary": shared.binding(output / "summary.json"), "runtime": observed}).decode(), flush=True)
        return 0
    except Exception as error:
        if output.exists() and not (output / "failure.json").exists():
            write_new(output / "failure.json", {"passed": False, "diagnostic": str(error), "automaticRetry": False,
                                               "allOriginalEvidenceRetained": True, "milestoneAccepted": False})
        print(canonical({"passed": False, "diagnostic": str(error)}).decode(), flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
