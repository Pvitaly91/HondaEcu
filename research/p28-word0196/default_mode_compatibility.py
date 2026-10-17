"""M2bp source-bound actual default-mode differential.

Two source-bound builds run the SAME unchanged M2bo probe library against the
legacy and active production engine. Historical source-pin validators are NOT
run on, or claimed to have passed on, the active tree. No module import runs CPU.
"""
from __future__ import annotations

import argparse
import copy
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import threading
import time
import tomllib

sys.dont_write_bytecode = True
BASE = "1ceec589ee8586727fb16a39fd15875444d6feab"
RESEARCH = "research/p28-word0196"
CRATE = RESEARCH + "/rust-default-compatibility"
RESERVE = 4 * 1024**3
REQUEST_SHA = "0d185fb533a9503ff88eee381d7617f7e1548aba06aa9d306d2afca90b1ff091"
EXPECTED_SHA = "482425591db0b354a35e9a2b5ad0190e3a33d459120b22c9997ce0ac100181c6"
FIXTURE_SOURCES = ("synthetic_runner.rs", "checksum_runner.rs", "producer_runner.rs",
                   "acquisition_runner.rs", "stateful_runner.rs", "basic_prefix_runner.rs")


def require(condition, label):
    if not condition:
        raise AssertionError(label)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                      allow_nan=False).encode("ascii")


def strict(raw):
    def pairs(items):
        result = {}
        for key, item in items:
            require(key not in result, "DuplicateJsonKey:" + key)
            result[key] = item
        return result
    return json.loads(raw, object_pairs_hook=pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


def binding(path):
    path = Path(path).resolve()
    start, digest, size = path.stat(), hashlib.sha256(), 0
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024**2), b""):
            size += len(block)
            digest.update(block)
    end = path.stat()
    require((start.st_size, start.st_mtime_ns) == (end.st_size, end.st_mtime_ns), "FileChangedDuringHash")
    return {"bytes": size, "sha256": digest.hexdigest()}


def write_new(path, value):
    with Path(path).open("xb") as stream:
        stream.write(canonical(value) + b"\n")


def git(root, *arguments):
    result = subprocess.run(["git", "-C", str(root), *arguments], capture_output=True, check=False)
    require(result.returncode == 0, "ReadOnlyGitCommandFailed:" + " ".join(arguments))
    return result.stdout.decode("utf-8").strip()


def owned(root, supplied, must_not_exist=False):
    result = Path(supplied)
    result = (root / result).resolve() if not result.is_absolute() else result.resolve()
    private = root / "private/reports/m2bp"
    temporary = root / ".tmp"
    require(result != private and (result.is_relative_to(private) or
            (result.is_relative_to(temporary) and result.relative_to(temporary).parts[0].startswith("m2bp-"))),
            "M2bpOwnedOutputRequired")
    require(not result.is_symlink() and (not must_not_exist or not result.exists()), "FreshOwnedPathRequired")
    return result


def load_references(baseline):
    # Bind the actual files before importing any generator/oracle code. These
    # pure historical functions do not call production CPU or source validators.
    directory = baseline / RESEARCH
    contract = strict((directory / "production_exec_parity_contract.json").read_bytes())
    pinned = {row["path"]: row for row in contract["sourceBindings"]}
    for name in ("production_exec_parity_corpus.py", "production_exec_parity_oracle.py"):
        relative = RESEARCH + "/" + name
        require(binding(baseline / relative) == {key: pinned[relative][key] for key in ("bytes", "sha256")},
                "HistoricalReferenceSourceIdentityChanged:" + name)
        module_name = name[:-3]
        spec = importlib.util.spec_from_file_location(module_name, directory / name)
        require(spec is not None and spec.loader is not None, "HistoricalReferenceModuleMissing")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
    return sys.modules["production_exec_parity_corpus"], sys.modules["production_exec_parity_oracle"]


def independent_identity(baseline):
    # Independent retained C# test literals, never the production builder output.
    text = (baseline / "tests/HondaEcu.Core.Tests/IntCycleRunnerIdentityTests.cs").read_text(encoding="utf-8")
    initial = re.search(r"Historical040Fixes\s*=\s*\[(.*?)\];", text, re.S)
    require(initial is not None, "IndependentHistoricalIdentityLiteralMissing")
    fixes = re.findall(r'"([^"\n]+)"', initial.group(1))
    require(len(fixes) == 34, "IndependentHistorical040InventoryMustHave34")
    for name in ("SllbSemanticFix", "DecDpSemanticFix", "DecDpCycleFix", "SllbCycleFix"):
        found = re.findall(r"const string " + name + r'\s*=\s*"([^"\n]+)";', text)
        require(len(found) == 1, "IndependentIdentityConstantMissing:" + name)
        fixes.append(found[0])
    require(len(fixes) == len(set(fixes)) == 38, "All38OrderedDistinctIdentitiesRequired")
    return {"protocolVersion": 1, "runnerVersion": "0.43.0",
            "upstreamCommit": "85b30752473ca9979e4ad9b307ea05a30c0b3d1e", "localSemanticFixes": fixes}


def protocol_cases():
    """Pure inputs reconstructed from the six pinned, invented-only Rust tests."""
    result = []

    def add(identity, request, assertions=(), exit_code=0):
        result.append({"case_id": identity, "request": request, "expected_exit": exit_code,
                       "assertions": [[list(path), value] for path, value in assertions]})

    def request(operation, rom, synthetic=None, scratch=(0,), image_id="synthetic"):
        value = {"protocolVersion": 1, "operation": operation,
                 "images": [{"id": image_id, "rom": rom}], "allowAssumptions": [],
                 "scratchPatterns": list(scratch)}
        if synthetic is not None:
            value["synthetic"] = synthetic
        return value

    def synthetic(exit_pc):
        return {"entryPc": 0, "exitPcs": [exit_pc], "allowedCodeRanges": [[0, exit_pc]],
                "psw": 0x0101, "lrb": 0x40, "usp": 0x180, "instructionBudget": 16,
                "dataSeeds": [], "outputAddresses": [0xC4]}

    base = request("synthetic", [0x77, 42, 0xD5, 0xC4], synthetic(4))
    add("synthetic-lb-store", base, [(("syntheticResult", "status"), 0), (("syntheticResult", "outputs"), [42])])
    changed = copy.deepcopy(base)
    changed["images"][0]["rom"][0] = 0xE5
    add("synthetic-opcode-sfr-fault", changed, [(("syntheticResult", "status"), 2)])
    for constant in (42, 43):
        rom = [0] * 0x102
        rom[:7] = [0x62, 0, 1, 0x92, 0xA8, 0xD5, 0xC4]
        rom[0x100] = constant
        scope = synthetic(7)
        scope["dataSeeds"] = [[0x100, 99], [0x101, 88]]
        add("synthetic-program-data-" + str(constant), request("synthetic", rom, scope),
            [(("syntheticResult", "status"), 0), (("syntheticResult", "outputs"), [constant])])
    for permitted in (False, True):
        scope = synthetic(2)
        scope.update(psw=0x1101, dataSeeds=[[6, 1], [7, 0], [0x206, 2], [0x207, 0]], outputAddresses=[0x206, 0x207])
        value = request("synthetic", [0x47, 0x81], scope)
        value["allowAssumptions"] = ["oki.add-er3-a"] if permitted else []
        add("synthetic-add-er3-" + str(int(permitted)), value,
            [(("syntheticResult", "status"), 0 if permitted else 1),
             (("syntheticResult", "outputs"), [3, 0] if permitted else [2, 0])])
    for constant, expected in ((1, 8), (4, 11)):
        rom = [0] * 0x122
        rom[:11] = [0x90, 0xA8, 0xC5, 7, 0x82, 0x20, 0x81, 0x78, 0xD1, 0xA0, 3]
        rom[0x120:0x122] = [constant, 2]
        scope = {"entryPc": 0, "exitPcs": [11], "allowedCodeRanges": [[0, 11]], "psw": 256,
                 "lrb": 65, "usp": 384, "instructionBudget": 16,
                 "dataSeeds": [[128, 32], [129, 1], [130, 0], [131, 0], [520, 5], [288, 99], [289, 88]],
                 "outputAddresses": [520, 928]}
        add("checksum-program-data-" + str(constant), request("checksumSynthetic", rom, scope, (170,), "toy"),
            [(("syntheticResult", "status"), 0), (("syntheticResult", "outputs"), [expected, expected]),
             (("syntheticResult", "programReads"), [288, 289])])

    def producer_program(g_add=False, f_add=False):
        rom = [0] * 32768
        g = [0xF9, 0x50, 0xE0, 0x60, 3] + ([0x45, 0x81] if g_add else [])
        g += [0xB5, 0xC4, 0x10, 3, 0xA5, 7]
        f = ([0x47, 0x81] if f_add else []) + [0xF5, 0xC4, 0xD3, 0xB3, 0xCB, 0x53 if f_add else 0x55]
        rom[0x772:0x772 + len(g)] = g
        rom[0x7C7:0x7C7 + len(f)] = f
        rom[0x122C:0x122E] = [0xCB, 0x3F]
        return rom

    for value in (42, 43):
        q = request("producerBatch", producer_program(), scratch=(0, 85, 170), image_id="baseline")
        q["producerCases"] = [[0, 0, value, 2, 3, 4, 5, 6, 123, 0, 0, 0, 0, 0]]
        add("producer-input-" + str(value), q, [(("producerRows", 0, 2), 0), (("producerRows", 0, 5), value),
                                             (("producerRows", 0, 18), value)])
    for name, permissions, g_status, f_status in (("strict", [], 1, 4), ("unrelated", ["oki.add-er3-a"], 1, 4),
            ("only-g", ["oki.add-er1-a"], 0, 1), ("both", ["oki.add-er1-a", "oki.add-er3-a"], 0, 0)):
        q = request("producerBatch", producer_program(True, True), scratch=(0, 85, 170), image_id="baseline")
        q.update(producerCases=[[0, 0, 42, 2, 3, 4, 5, 6, 123, 0, 0, 0, 0, 0]], allowAssumptions=permissions)
        add("producer-permissions-" + name, q, [(("producerRows", 0, 2), g_status), (("producerRows", 0, 15), f_status)])
    for compose in (False, True):
        rom = producer_program()
        acquire = [0xF5, 0xA2, 0x53, 0xF8, 0x50, 0xE5, 0x3A, 0x8B, 0xD5, 0xEE, 0xD0, 0x60, 3, 0xF9, 0xC9]
        acquire.append((0x5719 - (0x56BE + len(acquire) + 1)) & 255)
        rom[0x56BE:0x56BE + len(acquire)] = acquire
        q = request("acquisitionSequence", rom, scratch=(0, 85, 170), image_id="baseline")
        q["acquisitionSequence"] = {"formatVersion": 1, "composition": "scheduled-g-f-threshold" if compose else "acquisition-only",
            "initialState": {"previousTimestamp": 65000, "samples": [42, 100, 200, 300, 400, 500], "data0128": 8,
                             "data00AE": 7, "data00B6": 32, "data011F": 0, "previousT": 321, "data0217": 0,
                             "data0231": 0, "data0136": 4321},
            "observations": [{"index": 0, "tmr2": 42, "irqh": 1, "tcon2": 4, "slot": 0, "compose": compose,
                              "thresholdContext": 0, "thresholdPriorBits": 2, "thresholdEnabled": False},
                             {"index": 1, "tmr2": 73, "irqh": 0, "tcon2": 0, "slot": 4, "compose": compose,
                              "thresholdContext": 1, "thresholdPriorBits": 1, "thresholdEnabled": True}],
            "traceObservationIndexes": [0]}
        if compose:
            derived = copy.deepcopy(rom)
            derived[0x775] = 0x62
            q["images"].append({"id": "derived", "rom": derived})
        add("acquisition-" + str(int(compose)), q)
    images = []
    for increment, image_id in ((1, "baseline"), (2, "derived")):
        rom = [0] * 32768
        rom[0x122C:0x122C + 9] = [0xF4, 0x31, 0x86, increment, 0xD4, 0x31, 3, 0xFC, 0x12]
        images.append({"id": image_id, "rom": rom})
    q = request("statefulVtec", images[0]["rom"], scratch=(0, 85, 170), image_id="baseline")
    q["images"] = images
    q["statefulVtec"] = {"formatVersion": 1,
        "initialState": {"data0131": 4, "data0127": 6, "data0198": 79, "data01D8": 3, "data01D9": 7,
                         "data01DF": 19, "data00F3": 254, "p1OutputData": 69},
        "calls": [{"index": i, "compactCode": 80 + i, "context": i % 2, "enabled": i != 1, "raw00CC": 0,
                   "raw00D9": 0, "snapshot011A": 0, "snapshot011C": 0, "snapshot0119": 0, "raw0132": 0,
                   "raw0199": 0, "fastTicks": 0, "slowTicks": 0} for i in range(4)], "traceCallIndexes": [1]}
    add("stateful-two-images-four-calls", q)
    for operation in ("vtecThresholdPrefix", "vtecThresholdControl"):
        rom = [0] * 32768
        rom[0x122C:0x122F] = [3, 0x6D, 0x12]
        rom[0x7C7] = 9
        q = {"protocolVersion": 1, "operation": operation, "images": [{"id": n, "rom": rom} for n in "ABC"],
             "scratchPatterns": [0, 85, 170], "allowAssumptions": []}
        add("threshold-" + operation, q)
    for identity, field, value in (("protocol-version-refusal", "protocolVersion", 2),
                                   ("unknown-operation-refusal", "operation", "m2bpUnsupportedOperation"),
                                   ("unknown-field-refusal", "notInProtocol", True)):
        q = copy.deepcopy(base)
        q[field] = value
        add(identity, q, exit_code=2)
    require(len(result) == len({row["case_id"] for row in result}) == 22, "Closed22ProtocolFixtureCases")
    return result


def source_inventory(root):
    paths = {"rust/p28-slice-runner/Cargo.toml", "rust/p28-slice-runner/Cargo.lock"}
    for directory in ("rust/p28-slice-runner/src", "rust/p28-slice-runner/tests",
                      RESEARCH + "/rust-production-exec-parity", RESEARCH + "/rust-synthetic-adapter"):
        for path in (root / directory).rglob("*"):
            if path.is_file() and path.suffix in (".rs", ".toml", ".lock", ".json"):
                paths.add(path.relative_to(root).as_posix())
    paths.update(RESEARCH + "/" + name for name in ("production_exec_parity_corpus.py",
        "production_exec_parity_oracle.py", "production_exec_parity_contract.json"))
    paths.add("tests/HondaEcu.Core.Tests/IntCycleRunnerIdentityTests.cs")
    paths.update("rust/p28-slice-runner/tests/" + name for name in FIXTURE_SOURCES)
    return [{"path": relative, **binding(root / relative)} for relative in sorted(paths)]


def input_projection(micro, protocol, oracle):
    request_hash, expected_hash = hashlib.sha256(), hashlib.sha256()
    for request in micro:
        request_hash.update(canonical(request) + b"\n")
        expected_hash.update(canonical(oracle.expected_case(request)) + b"\n")
    require(len(micro) == 468 and request_hash.hexdigest() == REQUEST_SHA
            and expected_hash.hexdigest() == EXPECTED_SHA, "OriginalM2boInputsAndExpectationsMustRemainExact")
    protocol_manifest = [{"case_id": row["case_id"], "requestSha256": hashlib.sha256(canonical(row["request"])).hexdigest(),
                          "requestBytes": len(canonical(row["request"])), "expected_exit": row["expected_exit"],
                          "assertions": row["assertions"],
                          "inventedInputSeeds": {**{key: value for key, value in row["request"].items() if key != "images"},
                              "images": [{"id": image["id"], "programBytes": len(image["rom"]),
                                          "programSha256": hashlib.sha256(bytes(image["rom"])).hexdigest()}
                                         for image in row["request"]["images"]]}}
                         for row in protocol]
    return {"microCases": 468, "capabilitySteps": 2, "requestSemanticSha256": REQUEST_SHA,
            "expectedSemanticSha256": EXPECTED_SHA, "protocolCases": protocol_manifest,
            "microCaseSeeds": [{**{key: value for key, value in row.items() if key not in ("bytes", "guards")},
                                 "instructionLength": len(row["bytes"]), "guardLength": len(row["guards"])} for row in micro],
            "protocolManifestSha256": hashlib.sha256(canonical(protocol_manifest)).hexdigest(),
            "microProgramScope": "ExistingSixByteGuardedSingleInstructions_NeverComposite",
            "protocolProgramScope": "ExistingInventedLegacyRunnerFixtures_NotOptInMappingEvidence",
            "fullProgramBytesPersisted": False}


def generate_staging(active, baseline, target, template):
    manifest_text = (template / "Cargo.toml").read_text(encoding="utf-8")
    main_bytes, lock_bytes = (template / "src/main.rs").read_bytes(), (template / "Cargo.lock").read_bytes()
    paths = []
    for label, root in (("baseline", baseline), ("active", active)):
        stage = target / "staging" / label
        require(not stage.exists(), "FreshGeneratedProbeCrateRequired")
        (stage / "src").mkdir(parents=True)
        manifest = manifest_text
        for old, replacement in (("../../../rust/p28-slice-runner", root / "rust/p28-slice-runner"),
                                 ("../rust-production-exec-parity", root / RESEARCH / "rust-production-exec-parity")):
            require(manifest.count('path = "' + old + '"') == 1, "ExactDependencyPathSubstitutionRequired")
            manifest = manifest.replace('path = "' + old + '"', 'path = ' + json.dumps(replacement.as_posix()))
        for name, content in (("Cargo.toml", manifest.encode("utf-8")), ("Cargo.lock", lock_bytes), ("src/main.rs", main_bytes)):
            with (stage / name).open("xb") as stream:
                stream.write(content)
            paths.append({"tree": label, "path": (stage / name).relative_to(active).as_posix(), **binding(stage / name)})
    return paths


def preparation(args, active, baseline, output, target, template, corpus, oracle):
    require(git(baseline, "rev-parse", "HEAD") == BASE, "HistoricalCheckoutMustBeExactM2bo")
    require(git(baseline, "diff", "--name-only") == "" and git(baseline, "diff", "--cached", "--name-only") == "",
            "HistoricalTrackedCheckoutMustBeUnmodified")
    for root in (baseline, active):
        package = tomllib.loads((root / "rust/p28-slice-runner/Cargo.toml").read_text(encoding="utf-8"))
        require(package.get("features", {}).get("default", []) == [], "AuditMustNotBeEnabledByProductionDefaultFeatures")
    baseline_sources, active_sources = source_inventory(baseline), source_inventory(active)
    old = {row["path"]: row for row in baseline_sources}
    new = {row["path"]: row for row in active_sources}
    for name in old:
        if not name.startswith("rust/p28-slice-runner/"):
            require(new.get(name) == old[name], "HistoricalLibraryReferenceOrFixtureChanged:" + name)
    transition = [{"path": name, "old": old.get(name), "new": new.get(name)}
                  for name in sorted(set(old) | set(new))
                  if name.startswith("rust/p28-slice-runner/") and old.get(name) != new.get(name)]
    micro, protocol = corpus.build_corpus(), protocol_cases()
    inputs = input_projection(micro, protocol, oracle)
    generated = generate_staging(active, baseline, target, template)
    expected_totals = {"positive_cases": 468, "positive_cpu_instances": 468, "positive_bus_instances": 468,
        "positive_step_calls": 468, "positive_successful_step_calls": 468, "positive_failed_step_calls": 0,
        "positive_instruction_counter_delta": 468, "capability_cases": 2, "capability_cpu_instances": 2,
        "capability_bus_instances": 2, "capability_step_calls": 2, "capability_successful_step_calls": 0,
        "capability_failed_step_calls": 2, "capability_instruction_counter_delta": 1, "admission_refusals": 0,
        "observed_decoded_forms": dict(sorted(__import__("collections").Counter(oracle.expected_decode(row)["mnemonic"] for row in micro).items()))}
    frozen = {"milestone": "M2bp", "classification": "DefaultCompatibilityInputsFrozenBeforeBuildOrCpu",
        "exactLegacyBase": BASE, "baselineHead": git(baseline, "rev-parse", "HEAD"),
        "activeHeadAtFreeze": git(active, "rev-parse", "HEAD"), "sourceBindings": {"baseline": baseline_sources, "active": active_sources},
        "productionSourceTransition": transition, "historicalPureLibrariesAndFixturesUnchanged": True,
        "generatorSource": binding(Path(__file__)), "probeMainSource": binding(template / "src/main.rs"),
        "generatedCrates": generated, "inputs": inputs, "independentIdentity": independent_identity(baseline),
        "capabilityExpected": oracle.expected_capabilities(), "expectedProbeTotals": expected_totals,
        "newCpuExecutionsBeforeFreeze": 0, "featureSelection": "NoOptInFeatureRequested_NoDefaultFeaturesOnDirectDependencies",
        "projection": {"canonicalFieldsExcluded": [], "fullResponseStateAndTraceCompared": True,
                       "hostCommandsPathsDurationsAndBinaryDigestsAreSeparateReceipts": True},
        "historicalValidatorPassedOnActiveTreeClaimed": False, "fullProductionCompositeExecutions": 0,
        "originalRomExecutions": 0, "firmwareReady": False}
    write_new(output / "pre-runtime-freeze.json", frozen)
    return frozen, micro, protocol


def revalidate(frozen, active, baseline, target, template, corpus, oracle):
    require(frozen["baselineHead"] == git(baseline, "rev-parse", "HEAD") == BASE, "LegacyHeadChangedAfterFreeze")
    require(source_inventory(baseline) == frozen["sourceBindings"]["baseline"]
            and source_inventory(active) == frozen["sourceBindings"]["active"], "SourceGraphChangedAfterFreeze")
    require(binding(Path(__file__)) == frozen["generatorSource"]
            and binding(template / "src/main.rs") == frozen["probeMainSource"], "NewHarnessSourceChangedAfterFreeze")
    for row in frozen["generatedCrates"]:
        require(binding(active / row["path"]) == {key: row[key] for key in ("bytes", "sha256")}, "GeneratedManifestChangedAfterFreeze")
    micro, protocol = corpus.build_corpus(), protocol_cases()
    require(input_projection(micro, protocol, oracle) == frozen["inputs"], "FrozenDefaultInputCorpusChanged")
    return micro, protocol


def actual_command(arguments, cwd, output, label):
    require(shutil.disk_usage(output).free >= RESERVE, "LowDiskReserve_NoCleanup")
    start = time.monotonic()
    with (output / (label + ".stdout.log")).open("xb") as stdout, (output / (label + ".stderr.log")).open("xb") as stderr:
        completed = subprocess.run(list(map(str, arguments)), cwd=cwd, stdout=stdout, stderr=stderr, check=False, timeout=1800)
    receipt = {"arguments": list(map(str, arguments)), "cwd": str(cwd), "exitCode": completed.returncode,
               "durationSeconds": time.monotonic() - start,
               "stdout": binding(output / (label + ".stdout.log")), "stderr": binding(output / (label + ".stderr.log"))}
    write_new(output / (label + ".command.json"), receipt)
    require(completed.returncode == 0, "ActualDefaultBuildFailed:" + label)
    return {"path": label + ".command.json", **binding(output / (label + ".command.json"))}


def build_pair(active, baseline, target, output):
    commands, binaries = [], {}
    commands.append(actual_command(["cargo", "+1.85.1", "fmt", "--check", "--manifest-path",
                                    active / CRATE / "Cargo.toml"], active, output, "default-research-format"))
    for label, root in (("baseline", baseline), ("active", active)):
        production_target = target / label / "production"
        probe_target = target / label / "probe"
        for kind, manifest, build_target in (("production", root / "rust/p28-slice-runner/Cargo.toml", production_target),
                                           ("probe", target / "staging" / label / "Cargo.toml", probe_target)):
            if kind == "probe":
                metadata_label = label + "-default-feature-graph"
                commands.append(actual_command(["cargo", "+1.85.1", "metadata", "--format-version", "1", "--locked",
                    "--no-default-features", "--manifest-path", manifest], root, output, metadata_label))
                metadata = strict((output / (metadata_label + ".stdout.log")).read_bytes())
                packages = [row for row in metadata["packages"] if row["name"] == "p28-slice-runner"]
                require(len(packages) == 1 and Path(packages[0]["manifest_path"]).resolve() == root / "rust/p28-slice-runner/Cargo.toml",
                        "ActualResolvedProductionDependencyTreeRequired")
                nodes = [row for row in metadata["resolve"]["nodes"] if row["id"] == packages[0]["id"]]
                require(len(nodes) == 1 and set(nodes[0]["features"]) <= {"default"},
                        "ActualDefaultDependencyMustHaveNoEnabledAuditFeature")
                for name, relative in (("p28-research-production-exec-parity", RESEARCH + "/rust-production-exec-parity/Cargo.toml"),
                                       ("p28-research-synthetic-adapter", RESEARCH + "/rust-synthetic-adapter/Cargo.toml")):
                    dependencies = [row for row in metadata["packages"] if row["name"] == name]
                    require(len(dependencies) == 1 and Path(dependencies[0]["manifest_path"]).resolve() == root / relative,
                            "ActualHistoricalProbeLibraryDependencyTreeRequired:" + name)
            commands.append(actual_command(["cargo", "+1.85.1", "build", "--release", "--locked", "--jobs", "1",
                "--no-default-features", "--manifest-path", manifest, "--target-dir", build_target], root, output, label + "-" + kind))
        suffix = ".exe" if os.name == "nt" else ""
        binaries[label] = {"production": production_target / "release" / ("p28-slice-runner" + suffix),
                           "probe": probe_target / "release" / ("m2bp-default-compatibility" + suffix)}
    return commands, binaries


def lookup(value, path):
    for part in path:
        value = value[part]
    return value


def check_identity(actual, expected):
    for name, value in expected.items():
        require(type(actual.get(name)) is type(value) and actual[name] == value, "LegacyIdentityChanged:" + name)


def compare_streams(first, second):
    digest, size, chunks = hashlib.sha256(), 0, 0
    with gzip.open(first, "rb") as left, gzip.open(second, "rb") as right:
        while True:
            a, b = left.read(1024**2), right.read(1024**2)
            require(a == b, "WholeDefaultCanonicalByteMismatchAt:" + str(size))
            if not a:
                break
            digest.update(a)
            size += len(a)
            chunks += 1
    return {"everyDecompressedCanonicalByteCompared": True, "shaOnlyComparison": False,
            "comparedBytes": size, "chunks": chunks, "chunkSize": 1024**2,
            "canonicalSha256": digest.hexdigest(), "firstMismatch": None}


def runtime_pair(frozen, micro, protocol, oracle, binaries, output):
    processes, timers, handles = {}, [], []
    records = 0
    stdout_files = {name: output / (name + ".canonical.jsonl.gz") for name in ("baseline", "active")}
    try:
        writers = {}
        for label in ("baseline", "active"):
            stderr = (output / (label + "-probe.runtime.stderr.log")).open("xb")
            handles.append(stderr)
            process = subprocess.Popen([str(binaries[label]["probe"])], stdin=subprocess.PIPE,
                                       stdout=subprocess.PIPE, stderr=stderr)
            processes[label] = process
            timer = threading.Timer(300, process.kill)
            timer.start()
            timers.append(timer)
            raw = stdout_files[label].open("xb")
            handles.append(raw)
            writers[label] = gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0)
            handles.append(writers[label])

        def exchange(label, value=None):
            process = processes[label]
            if value is not None:
                process.stdin.write(canonical(value) + b"\n")
                process.stdin.flush()
            line = process.stdout.readline(4 * 1024**2)
            require(line.endswith(b"\n"), "MissingBoundedActualProbeRecord:" + label)
            return strict(line)

        def record(actual, context):
            nonlocal records
            left, right = canonical(actual["baseline"]) + b"\n", canonical(actual["active"]) + b"\n"
            if left != right:
                write_new(output / "first-mismatch.json", {"context": context, "baseline": actual["baseline"],
                                                           "active": actual["active"], "comparison": "WholeActualRecord"})
                raise AssertionError("LegacyDefaultRuntimeMismatch:" + context)
            for label, raw in (("baseline", left), ("active", right)):
                writers[label].write(raw)
            records += 1

        headers = {label: exchange(label) for label in processes}
        for header in headers.values():
            require(header["kind"] == "default_compatibility_identity" and header["cpu_instances"] == 0,
                    "ActualDefaultCompiledIdentityHeaderRequired")
            check_identity(header["identity"], frozen["independentIdentity"])
        record(headers, "compiled-default-identity")
        for request in micro:
            actual = {label: exchange(label, {"kind": "micro", "request": request}) for label in processes}
            expected = oracle.expected_case(request)
            for label, value in actual.items():
                mismatch = oracle.compare(expected, value)
                if mismatch is not None:
                    write_new(output / "first-mismatch.json", {"context": request["case_id"], "tree": label,
                        "firstMismatch": mismatch, "expected": expected, "actual": value})
                    raise AssertionError("HistoricalIndependentArchitecturalMismatch:" + label)
            record(actual, request["case_id"])
        actual = {label: exchange(label, {"kind": "capabilities", "request": micro[0]}) for label in processes}
        expected = {"kind": "capability_observations", "records": frozen["capabilityExpected"]}
        require(all(oracle.compare(expected, value) is None for value in actual.values()), "LegacyCapabilityBehaviorChanged")
        record(actual, "two-legacy-capability-faults")
        actual = {label: exchange(label, {"kind": "finish"}) for label in processes}
        for value in actual.values():
            require(value["totals"] == frozen["expectedProbeTotals"] and value["production_composite_executions"] == 0,
                    "ActualDefaultProbeLifecycleCountersChanged")
        record(actual, "default-probe-summary")
        for label, process in processes.items():
            process.stdin.close()
            require(process.wait(timeout=30) == 0 and process.stdout.read() == b"", "ProbeDidNotFinishExactly:" + label)
        for case in protocol:
            actual = {}
            supplied = canonical(case["request"])
            for label in ("baseline", "active"):
                completed = subprocess.run([str(binaries[label]["production"])], input=supplied,
                    capture_output=True, check=False, timeout=180)
                require(completed.returncode == case["expected_exit"], "LegacyProtocolExitChanged:" + case["case_id"])
                if completed.returncode == 0:
                    response = strict(completed.stdout)
                    check_identity(response, frozen["independentIdentity"])
                    require(response["operation"] == case["request"]["operation"], "ProtocolOperationRelabeled")
                    for field, expected in case["assertions"]:
                        require(lookup(response, field) == expected, "HistoricalProtocolFixtureAssertion:" + case["case_id"])
                    actual[label] = {"kind": "legacy_protocol_observation", "case_id": case["case_id"],
                                     "exitCode": 0, "response": response, "stderr": completed.stderr.decode("utf-8")}
                else:
                    actual[label] = {"kind": "legacy_protocol_refusal", "case_id": case["case_id"],
                                     "exitCode": completed.returncode, "stdout": completed.stdout.decode("utf-8"),
                                     "stderr": completed.stderr.decode("utf-8")}
            record(actual, case["case_id"])
    finally:
        for timer in timers:
            timer.cancel()
        for process in processes.values():
            if process.poll() is None:
                process.kill()
                process.wait(timeout=30)
        for handle in reversed(handles):
            handle.close()
    comparison = compare_streams(stdout_files["baseline"], stdout_files["active"])
    require(records == 493, "Complete471ProbePlus22ProtocolRecordsRequired")
    with stdout_files["baseline"].open("rb") as source, (output / "canonical.jsonl.gz").open("xb") as destination:
        shutil.copyfileobj(source, destination, 1024**2)
    return {"records": records, "actualMicroExecutionsPerTree": 468, "actualCapabilityStepAttemptsPerTree": 2,
            "actualProductionStepCallsPerTree": 470, "actualProtocolProcessesPerTree": len(protocol),
            "actualDefaultProtocolIdentityStrings": 38, "firstMismatch": None,
            "canonical": binding(output / "canonical.jsonl.gz"), "wholeStreamComparison": comparison,
            "baselineCanonical": binding(stdout_files["baseline"]), "activeCanonical": binding(stdout_files["active"]),
            "canonicalByteExclusions": [], "allActualResponseStateAndTraceFieldsCompared": True,
            "historicalPinValidatorsRunOnActiveTree": False, "fullProductionCompositeExecutions": 0,
            "originalRomExecutions": 0, "firmwareReady": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-root", required=True)
    parser.add_argument("--active-root", default=str(Path(__file__).resolve().parents[2]))
    parser.add_argument("--output-dir", default=".tmp/m2bp-public-evidence/default")
    parser.add_argument("--target-dir", default=".tmp/m2bp-default-target")
    parser.add_argument("--freeze-only", action="store_true")
    parser.add_argument("--execute-freeze", action="store_true")
    args = parser.parse_args()
    active, baseline = Path(args.active_root).resolve(), Path(args.baseline_root).resolve()
    output, target = owned(active, args.output_dir), owned(active, args.target_dir)
    template = active / CRATE
    require(active != baseline and not (active / "private/reports/m2bp/FINAL_REPORT_UK.md").exists(), "SeparateBaselineAndOpenM2bpLifecycleRequired")
    corpus, oracle = load_references(baseline)
    try:
        if args.execute_freeze:
            frozen = strict((output / "pre-runtime-freeze.json").read_bytes())
            require(not (output / "summary.json").exists() and not (output / "baseline-production.command.json").exists(),
                    "NeverRepeatOrOverwriteActualDefaultAttempt")
            micro, protocol = revalidate(frozen, active, baseline, target, template, corpus, oracle)
        else:
            require(not output.exists() and not target.exists(), "FreshDefaultAttemptPathsRequired")
            output.mkdir(parents=True)
            frozen, micro, protocol = preparation(args, active, baseline, output, target, template, corpus, oracle)
        if args.freeze_only:
            print(canonical({"passed": True, "classification": "BeforeRuntimeFreezeOnly", "cpuExecutions": 0,
                             "freeze": binding(output / "pre-runtime-freeze.json")}).decode())
            return 0
        commands, binaries = build_pair(active, baseline, target, output)
        runtime = runtime_pair(frozen, micro, protocol, oracle, binaries, output)
        revalidate(frozen, active, baseline, target, template, corpus, oracle)
        summary = {"milestone": "M2bp", "scope": "ActiveTreeDefaultModeCompatibility_NotOptInCapabilityEvidence",
            "passed": True, "LegacyDefaultBehaviorUnchanged": True, "HistoricalPinnedBaselineQA": "SeparateGate",
            "OldSourcePinConflictExpectedAfterVersionTransition": bool(frozen["productionSourceTransition"]), "baselineSha": BASE,
            "preRuntimeFreeze": binding(output / "pre-runtime-freeze.json"), "commands": commands,
            "compiledBinaries": {label: {kind: binding(path) for kind, path in paths.items()} for label, paths in binaries.items()},
            "runtime": runtime, "firstMismatch": None, "fullProductionCompositeExecutions": 0,
            "originalRomExecutions": 0, "firmwareReady": False}
        write_new(output / "summary.json", summary)
        print(canonical({"passed": True, "LegacyDefaultBehaviorUnchanged": True,
                         "summary": binding(output / "summary.json"), "runtime": runtime}).decode(), flush=True)
        return 0
    except Exception as error:
        if output.exists() and not (output / "failure.json").exists():
            write_new(output / "failure.json", {"passed": False, "diagnostic": str(error), "automaticRetry": False,
                                                "originalEvidenceRetained": True, "defaultCompatibilityEstablished": False})
        print(canonical({"passed": False, "diagnostic": str(error)}).decode(), flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
