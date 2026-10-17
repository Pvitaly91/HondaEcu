"""M2bo: real production single-step execution and independent comparison.

Only sealed invented microfixtures reach production exec. The full M2bj
composite is never CPU input. Missing Bus observations stay unavailable.
"""
from __future__ import annotations

import argparse
from collections import Counter
import copy
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import threading
import time

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CONTRACT = HERE / "production_exec_parity_contract.json"
BASE = "50dfe6b0ee814caddb69eaaa9c01936d9894bed5"
RESERVE = 4 * 1024**3


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def strict(text):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "DuplicateJsonKey:" + key)
            result[key] = value
        return result
    return json.loads(text, object_pairs_hook=pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError("NonfiniteJson")))


def identity(path):
    path = Path(path).resolve()
    require(path.is_relative_to(ROOT), "RepositoryRelativeSourceRequired")
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
            size += len(chunk)
    return {"path": path.relative_to(ROOT).as_posix(), "bytes": size,
            "sha256": digest.hexdigest()}


def write_new(path, value):
    with Path(path).open("xb") as output:
        output.write(canonical(value) + b"\n")


def disk(stage):
    value = {"stage": stage, "freeBytes": shutil.disk_usage(ROOT).free}
    require(value["freeBytes"] >= RESERVE, "LowDiskReserve_NoCleanup:" + stage)
    return value


def source_checks():
    import production_exec_parity_analysis as analysis
    import production_exec_parity_oracle as oracle
    contract = strict(CONTRACT.read_text(encoding="utf-8"))
    require(contract["milestone"] == "M2bo" and contract["exactBase"] == BASE,
            "ExactResearchScopeAndBaseRequired")
    require(contract["positiveBaseContexts"] == 234
            and contract["positiveExecutions"] == 468
            and contract["capabilityOnlyStepAttempts"] == 2,
            "FinitePredeclaredCorpusRequired")
    require(contract["projection"] == oracle.PROJECTION_RULES,
            "PredeterminedCanonicalProjectionRequired")
    require(contract["productionSourceChangesAllowed"] is False
            and contract["fullProductionCompositeAuthorized"] is False,
            "NoProductionMutationOrCompositeAuthority")
    require(contract["productionMechanism"] == "p28_slice_runner::exec::step"
            and contract["historicalM2bmM2bnChanged"] is False
            and contract["rustPureModelTests"] == 6
            and contract["negativeChecks"]["actualAdmissionMutations"] == 24,
            "UnchangedProductionAndFiniteResearchChecksRequired")
    require(contract["runtimeAuthority"] == {
        "originalRomExecutions": 0, "nativeDownstreamRejoins": 0,
        "productionCompositeExecutions": 0, "targetBIN": 0, "targetObjects": 0,
        "targetHEX": 0, "FirmwareBIN": 0, "FirmwareReady": False},
        "NoExecutionOrFirmwareAuthorityPromotion")
    bindings = []
    seen = set()
    for expected in contract["sourceBindings"]:
        require(expected["path"] not in seen, "DuplicateSourceBinding")
        seen.add(expected["path"])
        actual = identity(ROOT / expected["path"])
        require(actual == expected, "SourceIdentityMismatch:" + expected["path"])
        bindings.append(actual)
    require(len(bindings) >= 175, "CompleteHistoricalAndNewSourceBindingsRequired")
    for path in contract["newSourcePaths"]:
        require(path in seen, "NewSourceMissingBinding:" + path)
    return contract, bindings, analysis.source_audit()


def freeze_expectations(directory, contract, bindings):
    import production_exec_parity_corpus as corpus
    import production_exec_parity_oracle as oracle
    cases = corpus.build_corpus()
    require(len(cases) == 468 and len({case["case_id"] for case in cases}) == 468,
            "ExactUniqueFiniteCorpusRequired")
    coverage = corpus.coverage(cases)
    request_hash, expected_hash = hashlib.sha256(), hashlib.sha256()
    requests_path = directory / "requests.jsonl.gz"
    expected_path = directory / "expected-architecture.jsonl.gz"
    with requests_path.open("xb") as request_raw, expected_path.open("xb") as expected_raw:
        with gzip.GzipFile(fileobj=request_raw, mode="wb", mtime=0, filename="") as requests:
            with gzip.GzipFile(fileobj=expected_raw, mode="wb", mtime=0, filename="") as expectations:
                for request in cases:
                    expected = oracle.expected_case(request)
                    request_line = canonical(request) + b"\n"
                    expected_line = canonical(expected) + b"\n"
                    request_hash.update(request_line)
                    expected_hash.update(expected_line)
                    requests.write(request_line)
                    expectations.write(expected_line)
    frozen = {"milestone": "M2bo", "classification": "IndependentBeforeProductionExecution",
              "exactBase": BASE, "positiveBaseContexts": 234, "positiveExecutions": 468,
              "requestSemanticSha256": request_hash.hexdigest(),
              "expectedSemanticSha256": expected_hash.hexdigest(),
              "requests": identity(requests_path), "expectedArchitecture": identity(expected_path),
              "coverage": coverage, "projection": oracle.PROJECTION_RULES,
              "sourceBindings": bindings, "contract": identity(CONTRACT),
              "capabilityExpected": oracle.expected_capabilities(),
              "expectedHeader": expected_header(),
              "expectedAdmissionSweep": expected_admission_sweep(),
              "admissionMutations": oracle.admission_mutations(cases),
              "expectedRuntimeSummary": expected_runtime_summary(cases),
              "physicalEntryPc": 0, "logicalEntryPc": 4096,
              "actualProductionExecCallsBeforeFreeze": 0,
              "productionCompositeExecution": "NotRun", "firmwareReady": False}
    write_new(directory / "pre-runtime-freeze.json", frozen)
    return frozen, cases


def run_command(command, directory, label, timeout=600):
    before = disk(label + "-before")
    started = time.monotonic()
    with (directory / (label + ".stdout.log")).open("xb") as out:
        with (directory / (label + ".stderr.log")).open("xb") as err:
            result = subprocess.run(command, cwd=ROOT, stdout=out, stderr=err,
                                    timeout=timeout, check=False)
    receipt = {"command": command, "exitCode": result.returncode,
               "durationSeconds": time.monotonic() - started,
               "diskBefore": before, "diskAfter": disk(label + "-after"),
               "stdout": identity(directory / (label + ".stdout.log")),
               "stderr": identity(directory / (label + ".stderr.log"))}
    write_new(directory / (label + ".command.json"), receipt)
    require(result.returncode == 0, "ActualCommandFailed:" + label)
    return receipt


def exchange(process, request):
    process.stdin.write(canonical(request) + b"\n")
    process.stdin.flush()
    line = process.stdout.readline(2 * 1024 * 1024)
    require(line.endswith(b"\n"), "MissingOrOversizedRuntimeRecord")
    return strict(line.decode("utf-8"))


def authority_checks():
    import production_exec_parity_analysis as analysis
    valid = {"executionMechanism": "p28_slice_runner::exec::step",
             "actualProductionStepCalls": 468,
             "hiddenProgramProbes": "ObservationNotAvailable",
             "hiddenDataJournal": "ObservationNotAvailable",
             "sameValueStoreOccurrence": "ObservationNotAvailable",
             "productionCompositeIntegration": "NotEstablished",
             "originalRomExecutions": 0, "nativeRejoins": 0,
             "targetArtifacts": 0, "firmwareReady": False}
    require(analysis.validate_authority_claims(valid), "ValidRestrictedClaimRejected")
    tests = []
    for field, value in (("executionMechanism", "decoder-only"),
                         ("actualProductionStepCalls", 0),
                         ("hiddenProgramProbes", "ReconstructedObserved"),
                         ("hiddenDataJournal", "InferredObserved"),
                         ("sameValueStoreOccurrence", "ObservedFromFinalSnapshot"),
                         ("productionCompositeIntegration", "Verified"),
                         ("originalRomExecutions", 1), ("nativeRejoins", 1),
                         ("targetArtifacts", 1), ("firmwareReady", True)):
        altered = {**valid, field: value}
        error = None
        try:
            analysis.validate_authority_claims(altered)
        except AssertionError as caught:
            error = str(caught)
        require(error is not None, "AuthorityMutationNotRejected:" + field)
        tests.append({"field": field, "actualRefusal": error})
    return {"passed": True, "checks": tests, "actualProductionExecCalls": 0}


def expected_header():
    production_names = ("cpu.rs", "bus.rs", "decoder.rs", "full_decoder.rs",
                        "exec.rs", "runner.rs", "operand.rs", "lib.rs",
                        "Cargo.toml", "protocol.rs", "main.rs")
    research_names = ("Cargo.toml", "Cargo.lock", "src/lib.rs", "src/admission.rs",
                      "src/state.rs", "src/execution.rs", "src/capabilities.rs",
                      "src/source.rs", "src/main.rs", "src/tests.rs")
    production = []
    for name in production_names:
        relative = "rust/p28-slice-runner/" + (name if name == "Cargo.toml" else "src/" + name)
        production.append({**identity(ROOT / relative), "path": name})
    research = [{**identity(HERE / "rust-production-exec-parity" / name), "path": name}
                for name in research_names]
    return {"kind": "production_header", "schema_version": 1,
            "scope": "ResearchOnly_ProductionExecSingleStep_NotComposite",
            "production_source_bindings": production,
            "research_source_bindings": research,
            "sealed_m2bm_fixture_sha256": "7535b5edc203b759d8049a5905328695e0591a7cb7d874519d3f73a8646db343",
            "production_execution": "Unchanged_p28_slice_runner::exec::step",
            "research_effects_called": False, "cpu_instances": 0,
            "bus_instances": 0, "production_step_calls": 0,
            "production_bus_composite_integration": "NotEstablished",
            "original_rom_executions": 0, "firmware_ready": False}


def expected_admission_sweep():
    digest = hashlib.sha256()
    for word in range(65536):
        digest.update(word.to_bytes(2, "little") + bytes([int(word & 0x0CC8 == 0x0CC8)]))
    return {"kind": "admission_summary", "inputs": 65536, "representable": 2048,
            "incompatible": 63488, "low12_representable": 128,
            "low12_incompatible": 3968,
            "classification_record_encoding": "ForU16Ascending_ThreeBytes_LittleEndianInputThenAdmitted0or1",
            "classification_sha256": digest.hexdigest(), "cpu_instances": 0,
            "bus_instances": 0, "production_step_calls": 0,
            "caller_request_unchanged": True}


def expected_runtime_summary(cases):
    import production_exec_parity_oracle as oracle
    forms = dict(sorted(Counter(oracle.expected_decode(row)["mnemonic"] for row in cases).items()))
    totals = {"positive_cases": 468, "positive_cpu_instances": 468,
              "positive_bus_instances": 468, "positive_step_calls": 468,
              "positive_successful_step_calls": 468, "positive_failed_step_calls": 0,
              "positive_instruction_counter_delta": 468, "capability_cases": 2,
              "capability_cpu_instances": 2, "capability_bus_instances": 2,
              "capability_step_calls": 2, "capability_successful_step_calls": 0,
              "capability_failed_step_calls": 2, "capability_instruction_counter_delta": 1,
              "admission_refusals": len(oracle.admission_mutations(cases)),
              "observed_decoded_forms": forms}
    return {"kind": "production_run_summary", "totals": totals,
            "admission_sweep_observed": True, "capabilities_observed": True,
            "production_step_calls": 470, "cpu_instances": 470, "bus_instances": 470,
            "successful_step_calls": 468, "failed_step_calls": 2,
            "production_exec_architectural_parity": "RequiresIndependentComparator",
            "production_bus_composite_integration": "NotEstablished",
            "production_composite_executions": 0, "original_rom_executions": 0,
            "firmware_ready": False}


def actual_runtime(directory, target, frozen, cases, contract):
    import production_exec_parity_oracle as oracle
    executable = target / "release" / ("m2bo-production-exec.exe" if os.name == "nt" else "m2bo-production-exec")
    require(executable.is_file(), "ActualCompiledProductionHarnessRequired")
    counts = Counter()
    forms = Counter()
    record_hash = hashlib.sha256()
    record_bytes = 0
    records = 0
    sensitivities = []
    sensitivity_keys = set()
    before_disk = disk("actual-production-before")
    process = None
    watchdog = None
    with (directory / "runtime.stderr.log").open("xb") as runtime_errors:
        with (directory / "canonical.jsonl.gz").open("xb") as compressed:
            with gzip.GzipFile(fileobj=compressed, mode="wb", mtime=0, filename="") as output:
                def record(value):
                    nonlocal record_bytes, records
                    line = canonical(value) + b"\n"
                    output.write(line)
                    record_hash.update(line)
                    record_bytes += len(line)
                    records += 1

                def compare_all(expected, actual, label, request=None):
                    mismatch = oracle.compare(expected, actual)
                    if mismatch is not None:
                        path = directory / "first-mismatch.json"
                        if not path.exists():
                            write_new(path, {"classification": label, "request": request,
                                             "firstMismatch": mismatch,
                                             "expected": expected, "actual": actual})
                        raise AssertionError("IndependentProductionComparatorMismatch:" + label)

                try:
                    process = subprocess.Popen([str(executable)], cwd=ROOT, stdin=subprocess.PIPE,
                                               stdout=subprocess.PIPE, stderr=runtime_errors)
                    watchdog = threading.Timer(180, process.kill)
                    watchdog.start()
                    line = process.stdout.readline(2 * 1024 * 1024)
                    require(line.endswith(b"\n"), "MissingActualCompiledSourceHeader")
                    header = strict(line.decode("utf-8"))
                    compare_all(frozen["expectedHeader"], header, "CompiledSourceHeader")
                    record(header)
                    sweep = exchange(process, {"kind": "admission_sweep", "request": cases[0]})
                    compare_all(frozen["expectedAdmissionSweep"], sweep, "FullPswAdmissionDomain")
                    record(sweep)
                    for negative in frozen["admissionMutations"]:
                        actual = exchange(process, {"kind": "admit", "request": negative["request"]})
                        # Preserve the full actual refusal before asserting its
                        # independently frozen semantic/error-code projection.
                        record(actual)
                        expected_negative = {
                            "case_id": negative["request"]["case_id"],
                            "kind": "admission_refusal", "accepted": False,
                            "error_code": negative["expected_error_code"],
                            "cpu_instances": 0, "bus_instances": 0,
                            "production_step_calls": 0,
                            "production_exec_runtime_observed": False,
                            "production_bus_composite_integration": "NotEstablished"}
                        projected = {name: actual.get(name) for name in expected_negative
                                     if name != "error_code"}
                        projected["error_code"] = actual.get("error", {}).get("code")
                        compare_all(expected_negative, projected,
                                    "ActualAdmissionNegative:" + negative["id"], negative["request"])
                        require(set(actual) == (set(expected_negative) - {"error_code"}) | {"error"}
                                and set(actual["error"]) == {"code", "detail"}
                                and type(actual["error"]["detail"]) is str,
                                "UnexpectedNegativeObservationShape:" + negative["id"])
                        counts["admissionRefusals"] += 1
                    prior_pair = None
                    for index, request in enumerate(cases):
                        actual = exchange(process, {"kind": "case", "request": request})
                        expected = oracle.expected_case(request)
                        compare_all(expected, actual, "PositiveArchitecturalParity", request)
                        if not request["internal_sf"]:
                            prior_pair = copy.deepcopy(actual)
                        else:
                            left, right = prior_pair, copy.deepcopy(actual)
                            for item in (left, right):
                                item["case_id"] = "SameFrozenContextInternalSfPair"
                                item["internal_sf_before"] = item["internal_sf_after"] = False
                                item["cpu_before"]["sf"] = item["cpu_after"]["sf"] = False
                            compare_all(left, right, "InternalSfArchitecturalNoninterference", request)
                        record(actual)
                        counts["positiveExecutions"] += 1
                        counts["positiveCpuInstances"] += actual["cpu_instances"]
                        counts["positiveBusInstances"] += actual["bus_instances"]
                        counts["positiveStepCalls"] += actual["step_calls"]
                        counts["successfulPositiveSteps"] += actual["successful_step_calls"]
                        counts["failedPositiveSteps"] += actual["failed_step_calls"]
                        forms[actual["form"]] += 1
                        sensitivity_key = (actual["form"], actual["branch_taken"])
                        if sensitivity_key not in sensitivity_keys:
                            sensitivity_keys.add(sensitivity_key)
                            sensitivities.append({"case_id": request["case_id"], "form": actual["form"],
                                                  "checks": oracle.semantic_mutations(request, actual),
                                                  "actualExtraProductionSteps": 0})
                        if index % 100 == 0:
                            disk("production-case-" + str(index))
                            print("M2bo actual production steps:", index + 1, "/468", flush=True)
                    # Only after complete positive parity: independent integration
                    # boundary observations, not full composite execution.
                    capabilities = exchange(process, {"kind": "capabilities", "request": cases[0]})
                    compare_all({"kind": "capability_observations", "records": frozen["capabilityExpected"]},
                                capabilities, "SeparateProductionBoundaryFailures")
                    record(capabilities)
                    final = exchange(process, {"kind": "finish"})
                    compare_all(frozen["expectedRuntimeSummary"], final, "ActualCompletedLifecycleCounters")
                    record(final)
                    process.stdin.close()
                    require(process.wait(timeout=30) == 0 and process.stdout.read() == b"",
                            "RuntimeFailedOrProducedExtraRecords")
                finally:
                    if watchdog is not None:
                        watchdog.cancel()
                    if process is not None and process.poll() is None:
                        process.kill()
                        process.wait(timeout=30)
    require(counts["positiveExecutions"] == counts["positiveCpuInstances"]
            == counts["positiveBusInstances"] == counts["positiveStepCalls"]
            == counts["successfulPositiveSteps"] == 468
            and counts["failedPositiveSteps"] == 0 and len(forms) == 16,
            "AllDeclaredProductionExecutionsMustActuallyComplete")
    write_new(directory / "actual-comparator-sensitivity.json", {"passed": True,
              "actualRecordsMutated": len(sensitivities),
              "checks": sum(len(row["checks"]) for row in sensitivities),
              "records": sensitivities, "extraProductionStepCalls": 0})
    return {"actualPositiveExecutions": counts["positiveExecutions"],
            "actualPositiveStepCalls": counts["positiveStepCalls"],
            "actualPositiveCpuInstances": counts["positiveCpuInstances"],
            "actualPositiveBusInstances": counts["positiveBusInstances"],
            "successfulPositiveSteps": counts["successfulPositiveSteps"],
            "failedOrBlockedPositiveSteps": counts["failedPositiveSteps"],
            "capabilityStepCalls": final["totals"]["capability_step_calls"],
            "capabilityFailedSteps": final["totals"]["capability_failed_step_calls"],
            "actualTotalProductionStepCalls": final["production_step_calls"],
            "actualTotalCpuInstances": final["cpu_instances"],
            "actualTotalBusInstances": final["bus_instances"],
            "perFormPositiveExecutions": dict(sorted(forms.items())),
            "admissionRefusals": counts["admissionRefusals"],
            "representablePswWords": 2048, "incompatiblePswWords": 63488,
            "internalSfPairs": 234, "canonicalRecords": records,
            "canonicalBytes": record_bytes, "canonicalSha256": record_hash.hexdigest(),
            "compressedRecord": identity(directory / "canonical.jsonl.gz"),
            "compiledHarness": identity(executable), "firstMismatch": None,
            "observationCapabilities": oracle.CAPABILITIES,
            "productionCompositeIntegration": "NotEstablished",
            "productionCompositeExecutions": 0, "originalRomExecutions": 0,
            "diskBefore": before_disk, "diskAfter": disk("actual-production-after")}


def validate(args):
    require(not (ROOT / "private/reports/m2bo/FINAL_REPORT_UK.md").exists(),
            "FinalReportAlreadyWritten_Stop")
    directory = (ROOT / args.output_dir).resolve()
    target = (ROOT / args.target_dir).resolve()
    owned_output = directory.is_relative_to(ROOT / "private/reports/m2bo") or (
        directory.is_relative_to(ROOT / ".tmp")
        and directory.relative_to(ROOT / ".tmp").parts[0].startswith("m2bo-"))
    require(owned_output and target.is_relative_to(ROOT / ".tmp")
            and target.relative_to(ROOT / ".tmp").parts[0].startswith("m2bo-"),
            "NewM2boOwnedOutputsRequired")
    require(not directory.exists(), "NeverOverwriteAttemptEvidence")
    directory.mkdir(parents=True)
    args.created_output_dir = True
    contract, bindings, audit = source_checks()
    write_new(directory / "source-capability-audit.json", audit)
    import production_exec_parity_oracle_tests as reference_tests
    static = reference_tests.static_checks()
    require(static["passed"] is True and static["productionExecCalls"] == 0,
            "IndependentPreRuntimeStaticProofRequired")
    write_new(directory / "static-oracle-checks.json", static)
    write_new(directory / "authority-checks.json", authority_checks())
    frozen, cases = freeze_expectations(directory, contract, bindings)
    if args.freeze_only:
        print("M2BO_PRE_RUNTIME_FREEZE_JSON=" + canonical({
            "passed": True, "positiveExecutions": frozen["positiveExecutions"],
            "requestSemanticSha256": frozen["requestSemanticSha256"],
            "expectedSemanticSha256": frozen["expectedSemanticSha256"],
            "sourceBindings": len(bindings), "productionExecCalls": 0,
            "freeze": identity(directory / "pre-runtime-freeze.json")}).decode(), flush=True)
        return
    commands = []
    manifest = HERE / "rust-production-exec-parity/Cargo.toml"
    for label, arguments in (("build", ["build", "--release", "--locked", "--jobs", "1"]),
                             ("tests", ["test", "--release", "--locked", "--jobs", "1"]),
                             ("fmt", ["fmt", "--check"])):
        command = ["cargo", "+1.85.1"] + arguments + ["--manifest-path", str(manifest)]
        if label != "fmt":
            command += ["--target-dir", str(target)]
        commands.append(run_command(command, directory, label))
    test_text = (directory / "tests.stdout.log").read_text(encoding="utf-8")
    results = re.findall(r"test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored; (\d+) measured; (\d+) filtered out", test_text)
    require(results and all(all(int(n) == 0 for n in row[1:]) for row in results),
            "AllRustTestsRequiredWithoutSkipsOrFilters")
    require(sum(int(row[0]) for row in results) == 6,
            "AllSixPureRustModelAndTransportTestsRequired")
    runtime = actual_runtime(directory, target, frozen, cases, contract)
    _, after_bindings, after_audit = source_checks()
    require(after_bindings == bindings and after_audit == audit,
            "SourcesChangedDuringProductionExecution")
    summary = {"milestone": "M2bo", "exactBase": BASE, "passed": True,
               "commands": commands, "actualRustTests": sum(int(row[0]) for row in results),
               "preRuntimeFreeze": identity(directory / "pre-runtime-freeze.json"),
               "runtime": runtime, "sourceBindings": bindings, "hostPlatform": sys.platform,
               "ProductionExecRuntimeObserved": True,
               "ProductionExecArchitecturalParityVerified": True,
               "ProductionBusCompositeIntegrationVerified": "NotEstablished",
               "SFMeaningStorageNotEstablished": True, "testedPswDomainRestricted": True,
               "originalRomExecutions": 0, "nativeDownstreamRejoins": 0,
               "targetBIN": 0, "targetObjects": 0, "targetHEX": 0,
               "FirmwareBIN": 0, "FirmwareReady": False}
    write_new(directory / "summary.json", summary)
    print("M2BO_EVIDENCE_JSON=" + canonical({"milestone": "M2bo", "passed": True,
        "actualPositiveExecutions": runtime["actualPositiveExecutions"],
        "actualTotalProductionStepCalls": runtime["actualTotalProductionStepCalls"],
        "firstMismatch": runtime["firstMismatch"],
        "canonicalSha256": runtime["canonicalSha256"],
        "summary": identity(directory / "summary.json")}).decode(), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default=".tmp/m2bo-public-evidence")
    parser.add_argument("--target-dir", default=".tmp/m2bo-cargo-target")
    parser.add_argument("--freeze-only", action="store_true")
    args = parser.parse_args()
    try:
        validate(args)
        return 0
    except Exception as error:
        directory = (ROOT / args.output_dir).resolve()
        owned = directory.is_relative_to(ROOT / "private/reports/m2bo") or (
            directory.is_relative_to(ROOT / ".tmp")
            and directory.relative_to(ROOT / ".tmp").parts[0].startswith("m2bo-"))
        if (getattr(args, "created_output_dir", False) and owned and directory.is_dir()
                and not (directory / "failure.json").exists()):
            write_new(directory / "failure.json", {"passed": False, "diagnostic": str(error),
                                                   "automaticRetry": False,
                                                   "historicalEvidenceUnchanged": True})
        print("M2BO_FAILURE_JSON=" + canonical({"passed": False, "diagnostic": str(error)}).decode(), flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
