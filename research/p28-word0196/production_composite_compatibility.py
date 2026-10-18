"""M2bq default and unchanged M2bp one-step compatibility, separate from composites.

Old contracts, main entry points and evidence are never modified. Reused pure
reference/runtime functions stay source-bound by the new three-tree manifest.
Full one-step observations must match; the only permitted unequal bytes are
exact old/new source identities in the two independently validated headers.
Those complete headers remain in the comparison stream, not removed fields.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import gzip
from hashlib import sha256
from pathlib import Path
import os
import re
import sys
from types import SimpleNamespace

sys.dont_write_bytecode = True
import default_mode_compatibility as shared
import validate_production_optin_capabilities as bp
import production_composite_analysis as analysis

canonical, strict, require = shared.canonical, shared.strict, shared.require
write_new, binding = shared.write_new, shared.binding
HEADER_CHANGED_PATHS = frozenset(("rust/p28-slice-runner/src/audit.rs",
                                  "rust/p28-slice-runner/src/audit_bus.rs"))
SCHEMA = {
    "version": 1, "oneStepRecords": 583, "defaultRecords": 493,
    "comparison": "EveryCompleteRecordAgainstIndependentExpectationsAndPinnedActual",
    "sourceMetadataDifference": "OnlyTwoExactFrozenSourceIdentityRowsInHeaderAndNestedArbitraryHeader",
    "architecturalOrObservationFieldsExcluded": [],
    "pairedCanonical": "FullPinnedRecordAndFullActiveRecordPreserved_NoNormalization",
    "scope": "OldDefaultAndM2bpOneStepOnly_NotCompositeCoverage",
}


def owned_path(root, supplied):
    """Only this milestone's two exact fresh ownership roots, never old M2bp."""
    supplied = Path(supplied)
    require(".." not in supplied.parts, "NoParentTraversalInM2bqOwnedPath")
    path = (root / supplied).resolve()
    require(path.is_relative_to(root), "M2bqOutputMustStayInsideActiveRepository")
    parts = path.relative_to(root).parts
    require(len(parts) >= 2 and parts[0] == ".tmp" and parts[1] in
            ("m2bq-public-evidence", "m2bq-optin-target"), "OnlyExactNewM2bqCompatibilityRoots")
    for parent in (path, *path.parents):
        if parent == root:
            break
        require(not parent.is_symlink(), "NoSymlinkOwnedOutput")
    return path


def identity_transition(active, pinned):
    old, new = bp.expected_header(pinned), bp.expected_header(active)
    old_rows = {row["path"]: row for row in old["source_bindings"]}
    new_rows = {row["path"]: row for row in new["source_bindings"]}
    require(set(old_rows) == set(new_rows) and
            {name for name in old_rows if old_rows[name] != new_rows[name]} == HEADER_CHANGED_PATHS,
            "OnlyExactTwoAuditHeaderSourceTransitionsAllowed")
    projected = deepcopy(new)
    projected["source_bindings"] = old["source_bindings"]
    require(projected == old, "NoOtherHeaderFieldMayChange")
    return {"old": old, "new": new,
            "sourceRows": [{"path": name, "old": old_rows[name], "new": new_rows[name]}
                           for name in sorted(HEADER_CHANGED_PATHS)],
            "oldHeaderSha256": sha256(canonical(old)).hexdigest(),
            "newHeaderSha256": sha256(canonical(new)).hexdigest()}


def expected_stream(root, output):
    rows, patterns, mutations = bp.inputs_and_patterns(root)
    digest, size, count = sha256(), 0, 0
    with output.open("xb") as raw, gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as stream:
        for row in bp.expected_records(root, rows, patterns, mutations):
            line = canonical(row) + b"\n"
            stream.write(line)
            digest.update(line)
            size += len(line)
            count += 1
    require(count == SCHEMA["oneStepRecords"], "CompleteOneStepExpectedInventory")
    return {"records": count, "bytes": size, "sha256": digest.hexdigest(),
            "compressed": binding(output)}


def freeze(root, pinned, legacy, output, target, composite_freeze):
    source, _ = analysis.source_checks(root, pinned, legacy)
    composite = strict(composite_freeze.read_bytes())
    require(composite["milestone"] == "M2bq"
            and composite["newCompositeExecutionsBeforeFreeze"] == 0,
            "EarlierFullIndependentCompositeFreezeRequired")
    require(not output.exists() and not target.exists(), "FreshCompatibilityPathsRequired")
    output.mkdir(parents=True)
    default_output, step_output = output / "default", output / "one-step"
    default_output.mkdir()
    step_output.mkdir()
    corpus, oracle = shared.load_references(legacy)
    default, _, _ = shared.preparation(SimpleNamespace(), root, legacy,
                                       default_output, target / "default",
                                       root / shared.CRATE, corpus, oracle)
    require(bp.oracle.reproduce_historical_literals() is None,
            "AllHistoricalIndependentLiteralsMustReproduceBeforeRuntime")
    generated_stage = bp.generated_disabled_crate(root, target / "one-step")
    generated = [{"path": path.relative_to(root).as_posix(), **binding(path)} for path in
                 (generated_stage / "Cargo.toml", generated_stage / "Cargo.lock", generated_stage / "src/main.rs")]
    active_expected = expected_stream(root, step_output / "expected.canonical.jsonl.gz")
    pinned_expected = expected_stream(pinned, step_output / "pinned.expected.canonical.jsonl.gz")
    frozen = {"milestone": "M2bq", "classification": "DefaultAndOneStepCompatibilityFrozenBeforeRuntime",
              "sourceState": source, "schema": SCHEMA,
              "sourceHeaderTransition": identity_transition(root, pinned),
              "newCompositeFreeze": {"path": composite_freeze.relative_to(root).as_posix(), **binding(composite_freeze)},
              "defaultFreeze": binding(default_output / "pre-runtime-freeze.json"),
              "generatedFeatureOffCrate": generated,
              "expectedCanonical": active_expected, "pinnedExpectedCanonical": pinned_expected,
              "newCpuExecutionsBeforeThisCompatibilityFreeze": 0,
              "fullProductionCompositeExecutionsByThisDriver": 0, "firmwareReady": False}
    write_new(output / "pre-runtime-freeze.json", frozen)
    return frozen


def revalidate(root, pinned, legacy, output, frozen):
    source, _ = analysis.source_checks(root, pinned, legacy)
    require(source == frozen["sourceState"] and frozen["schema"] == SCHEMA
            and frozen["sourceHeaderTransition"] == identity_transition(root, pinned),
            "CompatibilitySourcesOrProjectionChangedAfterFreeze")
    step = output / "one-step"
    for name, key in (("expected.canonical.jsonl.gz", "expectedCanonical"),
                      ("pinned.expected.canonical.jsonl.gz", "pinnedExpectedCanonical")):
        require(binding(step / name) == frozen[key]["compressed"], "ExpectedOneStepStreamChanged")
    require(binding(output / "default/pre-runtime-freeze.json") == frozen["defaultFreeze"],
            "DefaultFreezeChanged")
    for row in frozen["generatedFeatureOffCrate"]:
        require(binding(root / row["path"]) == {key: row[key] for key in ("bytes", "sha256")},
                "FeatureOffNegativeSourceChanged")
    item = frozen["newCompositeFreeze"]
    require(binding(root / item["path"]) == {key: item[key] for key in ("bytes", "sha256")},
            "IndependentCompositeFreezeChanged")


def compare_pinned_actual(root, pinned, old_stream, active_stream, output, frozen):
    transition = frozen["sourceHeaderTransition"]
    count, header_differences, digest, size = 0, 0, sha256(), 0
    pair_path = output / "canonical.jsonl.gz"
    with gzip.open(old_stream, "rb") as old, gzip.open(active_stream, "rb") as active, \
            (pair_path).open("xb") as raw, gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as writer:
        while True:
            left, right = old.readline(4 * 1024**2), active.readline(4 * 1024**2)
            if not left and not right:
                break
            require(left.endswith(b"\n") and right.endswith(b"\n"), "CompleteEqualOneStepRecordInventory")
            a, b = strict(left), strict(right)
            require(canonical(a) + b"\n" == left and canonical(b) + b"\n" == right,
                    "OriginalCanonicalEncodingMustBePreserved")
            if a.get("kind") == "optin_header":
                require(a == transition["old"] and b == transition["new"], "ExactCompleteVersionedHeaderPair")
                header_differences += 1
            elif a.get("kind") == "arbitrary_operation_refusal":
                require(a == bp.expected_arbitrary(pinned) and b == bp.expected_arbitrary(root),
                        "FullVersionedArbitraryRefusalIncludingAllActualFields")
                header_differences += 1
            elif left != right:
                write_new(output / "first-mismatch.json", {"record": count, "pinned": a, "active": b,
                                                           "expectationsNotRevised": True})
                raise AssertionError("M2bpSingleStepBehaviorChanged:" + str(count))
            line = canonical({"record": count, "pinned": a, "active": b,
                              "observationScope": "M2bpSingleStepOnly"}) + b"\n"
            writer.write(line)
            digest.update(line)
            size += len(line)
            count += 1
    require(count == 583 and header_differences == 2, "All583RecordsAndExactlyTwoVersionedHeaders")
    return {"records": count, "wholeRecordBytesReadAndCompared": True, "sourceVersionHeaders": header_differences,
            "architecturalOrObservationFieldsExcluded": [], "allUnequalMetadataBoundExplicitly": True,
            "canonical": binding(pair_path), "decompressedBytes": size, "sha256": digest.hexdigest(),
            "firstMismatch": None}


def pinned_runtime_join(pinned, legacy, output):
    summary = strict((output / "summary.json").read_bytes())
    require(summary["milestone"] == "M2bp" and summary["passed"] is True
            and summary["runtime"]["records"] == 583,
            "ActualPinnedM2bpValidatorPassRequired")
    frozen_path = output / "pre-runtime-freeze.json"
    require(binding(frozen_path) == summary["preRuntimeFreeze"], "PinnedActualSummaryFreezeBinding")
    frozen = strict(frozen_path.read_bytes())
    require(frozen["sourceState"] == bp.source_state(pinned, legacy)
            and frozen["schema"] == bp.SCHEMA and frozen["newCpuExecutionsBeforeFreeze"] == 0,
            "PinnedRuntimeMustBindActualExactM2bpAndM2boSources")
    require(summary["sourceTransition"] == frozen["sourceState"]["sourceChecks"],
            "PinnedActualSummarySourceApplicability")
    require(binding(output / "canonical.jsonl.gz") == summary["runtime"]["canonical"],
            "PinnedActualSummaryMustBindComparedCanonicalFile")
    commands = []
    for row in summary["commands"]:
        require(Path(row["path"]).name == row["path"] and row["path"].endswith(".command.json"),
                "PinnedCommandReceiptMustBeContainedBasename")
        receipt_path = output / row["path"]
        require(binding(receipt_path) == {key: row[key] for key in ("bytes", "sha256")},
                "PinnedNativeCommandBinding")
        receipt = strict(receipt_path.read_bytes())
        require(receipt["exitCode"] == 0 and Path(receipt["cwd"]).resolve() == pinned,
                "PinnedCommandMustActuallyRunSuccessfullyInPinnedTree")
        stem = row["path"].removesuffix(".command.json")
        for suffix in ("stdout", "stderr"):
            require(binding(output / (stem + "." + suffix + ".log")) == receipt[suffix],
                    "PinnedNativeCommandActualLogsChanged")
        commands.append({"receipt": row, "arguments": receipt["arguments"]})
    build = [row for row in commands if row["receipt"]["path"] == "optin-production-build.command.json"]
    require(len(commands) == 6 and len(build) == 1, "CompleteSixPinnedActualCommands")
    arguments = build[0]["arguments"]
    manifest = Path(arguments[arguments.index("--manifest-path") + 1]).resolve()
    require(manifest == pinned / bp.CRATE / "Cargo.toml", "ActualBuildMustUsePinnedOneStepCrate")
    target = Path(arguments[arguments.index("--target-dir") + 1]).resolve()
    binary = target / "release" / ("m2bp-production-optin-audit" + (".exe" if os.name == "nt" else ""))
    require(binding(binary) == summary["compiledBinary"], "ActualPinnedCompiledBinaryBinding")
    return {"summary": binding(output / "summary.json"), "freeze": binding(frozen_path),
            "canonical": binding(output / "canonical.jsonl.gz"), "compiledBinary": binding(binary),
            "actualSourceBoundCommands": commands}


def actual_composite_component_tests(output):
    """Join required guard names to the real unfiltered Rust test log.

    A source list or negative-protocol JSON cannot establish that these private
    component tests were actually discovered and executed by the Rust runner.
    """
    from production_composite_negative import COMPONENT_TESTS
    path = output / "optin-production-tests.stdout.log"
    before = binding(path)
    text = path.read_text(encoding="utf-8")
    summaries = re.findall(r"^test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored; "
                           r"(\d+) measured; (\d+) filtered out;", text, re.MULTILINE)
    require(summaries and sum(int(row[0]) for row in summaries) == 333 + len(COMPONENT_TESTS)
            and len(COMPONENT_TESTS) == 13
            and all(all(int(value) == 0 for value in row[1:]) for row in summaries),
            "ActualFull346OptInTestsWithAll13NewGuardsAndNoSkipsRequired")
    observed = []
    for name in COMPONENT_TESTS:
        matches = re.findall(r"^test (?:[^\s]+::)?" + re.escape(name) + r" \.\.\. ok$", text, re.MULTILINE)
        require(len(matches) == 1, "ActualNamedComponentGuardMissingOrDuplicated:" + name)
        observed.append(name)
    require(binding(path) == before, "ActualComponentTestLogChangedDuringRead")
    return {"classification": "ActualNamedRustComponentGuards_NotCompositeCpuExecutions",
            "stdout": before, "actualOptInTests": sum(int(row[0]) for row in summaries),
            "actualComponentGuardTests": len(observed), "observedNames": observed,
            "failed": 0, "ignored": 0, "filteredOut": 0, "compositeCpuExecutionsByTheseGuards": 0}


def execute(root, pinned, legacy, output, target, pinned_optin, frozen):
    revalidate(root, pinned, legacy, output, frozen)
    require(not (output / "summary.json").exists(), "NeverRepeatCompletedCompatibilityAttempt")
    corpus, oracle = shared.load_references(legacy)
    default_output, step_output = output / "default", output / "one-step"
    default = strict((default_output / "pre-runtime-freeze.json").read_bytes())
    micro, protocols = shared.revalidate(default, root, legacy, target / "default", root / shared.CRATE, corpus, oracle)
    commands, binaries = shared.build_pair(root, legacy, target / "default", default_output)
    default_result = shared.runtime_pair(default, micro, protocols, oracle, binaries, default_output)
    shared.revalidate(default, root, legacy, target / "default", root / shared.CRATE, corpus, oracle)
    write_new(default_output / "summary.json", {"milestone": "M2bq", "passed": True,
              "classification": "ActiveDefaultModeActualDifferential", "runtime": default_result,
              "commands": commands, "fullProductionCompositeExecutionsByThisLane": 0})
    pinned_join = pinned_runtime_join(pinned, legacy, pinned_optin)
    pinned_comparison = shared.compare_streams(step_output / "pinned.expected.canonical.jsonl.gz",
                                              pinned_optin / "canonical.jsonl.gz")
    require(pinned_comparison["canonicalSha256"] == frozen["pinnedExpectedCanonical"]["sha256"],
            "PinnedActualMustEqualIndependentFrozenOldExpectations")
    rows, patterns, mutations = bp.inputs_and_patterns(root)
    pure_commands = bp.pure_test_receipts(root, step_output, execute=True)
    binary, build_commands = bp.actual_build(root, target / "one-step", step_output)
    component_tests = actual_composite_component_tests(step_output)
    observed = bp.runtime(root, binary, target / "one-step", step_output, frozen, rows, patterns, mutations)
    compatibility = compare_pinned_actual(root, pinned, pinned_optin / "canonical.jsonl.gz",
                                          step_output / "canonical.jsonl.gz", output, frozen)
    revalidate(root, pinned, legacy, output, frozen)
    result = {"milestone": "M2bq", "passed": True, "LegacyDefaultBehaviorUnchanged": True,
              "M2bpSingleStepBehaviorUnchanged": True, "default": default_result,
              "actualCompositeComponentTests": component_tests,
              "activeOneStep": observed, "pinnedOneStep": {"actualRuntimeJoin": pinned_join,
              "wholeExpectedComparison": pinned_comparison}, "oneStepCompatibility": compatibility,
              "commands": pure_commands + build_commands, "freeze": binding(output / "pre-runtime-freeze.json"),
              "firstMismatch": None, "fullProductionCompositeExecutionsByThisDriver": 0,
              "originalRomExecutions": 0, "firmwareReady": False}
    write_new(output / "summary.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("pinned-root", "historical-root", "output-dir", "target-dir", "composite-freeze", "pinned-optin-output"):
        parser.add_argument("--" + name, required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--freeze-only", action="store_true")
    mode.add_argument("--execute-freeze", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    require(not (root / "private/reports/m2bq/FINAL_REPORT_UK.md").exists(),
            "M2bqDeliveryClosed_ReadOnlyOnly")
    pinned, legacy = Path(args.pinned_root).resolve(), Path(args.historical_root).resolve()
    output, target = owned_path(root, args.output_dir), owned_path(root, args.target_dir)
    try:
        if args.freeze_only:
            result = freeze(root, pinned, legacy, output, target, Path(args.composite_freeze).resolve())
            print(canonical({"passed": True, "classification": "CompatibilityFreezeOnly_NoRuntime",
                             "freeze": binding(output / "pre-runtime-freeze.json")}).decode())
        else:
            result = execute(root, pinned, legacy, output, target, Path(args.pinned_optin_output).resolve(),
                             strict((output / "pre-runtime-freeze.json").read_bytes()))
            print(canonical({"passed": True, "firstMismatch": result["firstMismatch"],
                             "summary": binding(output / "summary.json")}).decode())
        return 0
    except Exception as error:
        if output.exists() and not (output / "failure.json").exists():
            write_new(output / "failure.json", {"milestone": "M2bq", "passed": False,
                      "diagnostic": str(error), "automaticRetry": False, "expectationsNotRevised": True})
        print(canonical({"passed": False, "diagnostic": str(error)}).decode())
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
