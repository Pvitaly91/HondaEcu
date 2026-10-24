"""Closed M2bu per-case evidence ledger and idempotent resume orchestration.

This is not an emulator. The unchanged60-second one-process transport is reused;
the caller supplies independently frozen expectations and its actual comparator.
Only32 positive or2 branch-control cases are admitted. No build/network action
or automatic execution occurs at import. Partial observations are never erased.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import gzip
from hashlib import sha256
import os
from pathlib import Path
import re
import subprocess
import uuid

from original_rom_execution import verify as transport_api
from native_entry_continuity.checkpoint import canonical, atomic_json, read_checkpoint, local_path
from native_entry_continuity.build_guard import no_reparse

ROOT = Path(__file__).resolve().parents[3]
BASE = "7eb26571d8ee1f849efe5ffa619b0201008b267c"
BRANCH = "codex/p28-word0196-native-entry-continuity-m2bu"
MAX_JSON = 128 * 1024 * 1024
ARTIFACT_NAMES = frozenset({"sourcejoin.json", "pre-runtime-freeze.json", "canonical.jsonl.gz", "summary.json"})
BUDGETS = {"A": 16, "B": 18, "C": 19, "D": 21, "JbrAlternate": 1, "JneAlternate": 6}
PRIVATE_MODE = "OriginalRomBytes_TechnicalCallerToExitExecution"
PUBLIC_MODE = "PublicSyntheticEntryContinuityRegression"
UNRESOLVED = ("ActualHardwareEcuExecutionNotObserved", "RecoveredFullEcuSchedulerNotEstablished",
    "PhysicalSFNotEstablished", "NativeStackSafetyNotEstablished", "PeripheralStateOwnershipNotEstablished",
    "ActualNativeDownstreamRejoinNotEstablished", "SafeROMPlacementNotEstablished",
    "TargetProgramEquivalenceNotEstablished", "FirmwareIntegrationNotEstablished")
execute_case = transport_api.execute_case
process_identity = transport_api.process_identity
file_binding, publish_bytes = transport_api.file_binding, transport_api.publish_bytes
local_directory = transport_api.local_directory


class ResumeError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


class PauseRequested(ResumeError):
    def __init__(self):
        super().__init__("ExplicitUserPauseRequested_NoNewCaseStarted")


def require(condition, code):
    if condition is not True:
        raise ResumeError(code)


def digest(value):
    return sha256(canonical(value)).hexdigest()


def read_json(path):
    path = no_reparse(Path(path))
    before = file_binding(path)
    require(before["bytes"] <= MAX_JSON, "BoundedM2buMetadataRequired")
    raw = path.read_bytes()
    require(file_binding(path) == before, "M2buMetadataChangedDuringRead")
    value = transport_api.strict_json(raw)
    require(canonical(value) == raw, "CanonicalM2buReceiptRequired")
    return value


def check_source_join(value):
    fingerprint = transport_api.check_source_join(value)
    require(value.get("firmwareReady", False) is False, "SourceCannotPromoteFirmwareAuthority")
    return fingerprint


def verify_ack(ack, program_identity, public):
    fields = {"kind", "schemaVersion", "classification", "program_sha256", "entry_pc", "program_node_count",
              "native_generation_ownership", "physical_sf_known", "hardware_validated"}
    require(type(ack) is dict and set(ack) == fields and ack["kind"] == "program_admitted"
            and type(ack["schemaVersion"]) is int and ack["schemaVersion"] == 1
            and ack["classification"] == ("ExplicitInventedPublicEntryFixture" if public else PRIVATE_MODE)
            and ack["program_sha256"] == program_identity["program_sha256"]
            and type(ack["entry_pc"]) is int and ack["entry_pc"] == program_identity["program_base"]
            and type(ack["program_node_count"]) is int and ack["program_node_count"] == 24
            and ack["native_generation_ownership"] is False and ack["physical_sf_known"] is False
            and ack["hardware_validated"] is False, "ClosedM2buProgramAcknowledgementRequired")


class VerificationRun:
    """One source-frozen closed corpus; sibling modes retain separate progress."""
    def __init__(self, *, output, runner, source_join, source_supplier, cases, wire_cases,
                 expected, program, program_identity, compare, public, source_fence=lambda: True,
                 private_identity=None, historical=None, executor=execute_case, checkpoint_path=None,
                 global_checkpoint=None, preservation_binding=None, ack_validator=None, corpus_kind="positive"):
        require(corpus_kind in {"positive", "branch_controls"}, "ClosedM2buCorpusKindRequired")
        self.output = local_directory(output)
        self.state = local_directory(self.output.parent / (self.output.name + ".state"))
        self.runner = Path(runner).resolve(strict=True)
        self.runner_binding = file_binding(self.runner)
        self.join, self.source_supplier = source_join, source_supplier
        self.fingerprint = check_source_join(source_join)
        require(type(cases) is list and type(wire_cases) is list and type(expected) is list
                and len(cases) == len(wire_cases) == len(expected), "CompleteFrozenM2buCasesRequired")
        paths = Counter(case["path"] for case in cases)
        require(paths == (Counter({path: 8 for path in "ABCD"}) if corpus_kind == "positive"
                          else Counter({"JbrAlternate": 1, "JneAlternate": 1})), "ExactClosedM2buCorpusMembershipRequired")
        ids = [case["case_id"] for case in cases]
        require(len(ids) == len(set(ids)) and all(type(name) is str
                and re.fullmatch(r"[A-Za-z0-9_-]{1,160}", name) is not None for name in ids), "UniqueSafeM2buCaseIdsRequired")
        for case, wire in zip(cases, wire_cases):
            require(type(case["budget"]) is int and case["budget"] == BUDGETS[case["path"]]
                    and wire["case_id"] == case["case_id"] and wire["path"] == case["path"]
                    and type(wire["budget"]) is int and wire["budget"] == case["budget"], "ExactFrozenM2buPathBudgetRequired")
        require(type(public) is bool and program_identity["program_base"] == (0x6200 if public else 0x54F5),
                "ExplicitM2buProgramDomainRequired")
        require(transport_api.CASE_TIMEOUT_SECONDS == 60, "UnchangedBoundedOneCaseTransportRequired")
        self.cases, self.wires, self.expected = cases, wire_cases, expected
        self.program, self.program_identity, self.compare = program, program_identity, compare
        self.public, self.fence, self.executor = public, source_fence, executor
        self.private_identity, self.historical = private_identity, historical
        self.corpus_kind = corpus_kind
        self.mode = PUBLIC_MODE if public else PRIVATE_MODE
        self.mode_key = ("public" if public else "private") + ":" + corpus_kind
        require(global_checkpoint is None or checkpoint_path is None or Path(global_checkpoint) == Path(checkpoint_path),
                "ConflictingGlobalCheckpointPaths")
        selected = global_checkpoint if global_checkpoint is not None else checkpoint_path
        self.global_checkpoint = local_path(selected) if selected is not None else None
        self.local_checkpoint = self.state / "RESUME_STATE.json"
        self.preservation_binding = preservation_binding
        self.ack_validator = ack_validator or verify_ack
        self.corpus_digest = digest(cases)
        self.freeze = {"schemaVersion": 1, "milestone": "M2bu", "classification": self.mode,
            "baseSha": BASE, "corpusKind": corpus_kind, "sourceFingerprintSha256": self.fingerprint,
            "sourceBindings": source_join["sourceBindings"], "runnerBinding": self.runner_binding,
            "corpusSha256": self.corpus_digest, "cases": cases, "wireCases": wire_cases,
            "independentExpected": expected, "expectedSha256": digest(expected), "programIdentity": program_identity,
            "programSourceKind": program["kind"], "privateSourceIdentity": private_identity,
            "historicalObligations": historical, "expectedFrozenBeforeRuntime": True, "firmwareReady": False}
        self.records = []
        self.recovered_orphan_cases = 0

    def cache_path(self, index):
        return no_reparse(self.state / "cases" / f"{index:04d}-{self.cases[index]['case_id']}.json")

    def intent_path(self, index):
        return no_reparse(self.state / "intents" / f"{index:04d}-{self.cases[index]['case_id']}.json")

    def attempt_path(self, index):
        return no_reparse(self.state / "attempts" / f"{index:04d}-{self.cases[index]['case_id']}")

    def intent(self, index):
        return {"schemaVersion": 1, "milestone": "M2bu", "sourceFingerprint": self.fingerprint,
            "corpusSha256": self.corpus_digest, "corpusKind": self.corpus_kind, "caseIndex": index,
            "caseId": self.cases[index]["case_id"], "wireCaseSha256": digest(self.wires[index]),
            "expectedSha256": digest(self.expected[index]), "runnerBinding": self.runner_binding,
            "programIdentitySha256": digest(self.program_identity), "attempt": str(self.attempt_path(index))}

    @staticmethod
    def is_paused(state):
        return (state.get("pauseRequested") is True or state.get("phase") == "PAUSED"
                or state.get("currentPhase") == "PAUSED" or state.get("status") == "PAUSED")

    def pause_gate(self):
        # With a global controller, that one user-facing checkpoint is the
        # authority; a resumed user does not need to edit four local mirrors.
        path = self.global_checkpoint if self.global_checkpoint is not None else self.local_checkpoint
        path = local_path(path)
        if path.exists() and self.is_paused(read_checkpoint(path, fingerprint=self.fingerprint)):
            raise PauseRequested()

    def checkpoint(self, phase, *, active=None, blocker=None, summary=None):
        value = {"schemaVersion": 1, "milestone": "M2bu", "branch": BRANCH, "baseSha": BASE,
            "sourceFingerprint": self.fingerprint, "corpusSha256": self.corpus_digest,
            "executionMode": self.mode, "corpusKind": self.corpus_kind, "currentPhase": phase, "phase": phase,
            "completedSteps": ["SOURCE_VERIFIED", "PRE_RUNTIME_FREEZE"] + (["ROM_EXECUTION", "ORACLE_COMPARISON"] if summary else []),
            "lastCompletedCaseId": self.records[-1]["case"]["case_id"] if self.records else None,
            "canonicalRecordHashes": [digest(record) for record in self.records],
            "pendingCases": [case["case_id"] for case in self.cases[len(self.records):]],
            "activeProcess": active, "activeProcessIdentity": active, "blockers": [blocker] if blocker else [],
            "outputDirectory": str(self.output), "stateDirectory": str(self.state),
            "nextAction": "ContinueNextUnfinishedQaDeliveryAction" if summary else "ResumeFirstUncompletedCase",
            "updatedUtc": datetime.now(timezone.utc).isoformat()}
        if self.preservation_binding is not None:
            value["preservationException"] = self.preservation_binding
        if summary:
            value["summary"] = file_binding(self.output / "summary.json")
        value["lastSuccessfulReceipt"] = (value["summary"] if summary else
            file_binding(self.cache_path(len(self.records) - 1)) if self.records else
            file_binding(self.output / "pre-runtime-freeze.json"))
        if self.global_checkpoint is None and self.local_checkpoint.exists():
            previous = read_checkpoint(self.local_checkpoint, fingerprint=self.fingerprint)
            if self.is_paused(previous):
                value.update(phase="PAUSED", currentPhase="PAUSED", status="PAUSED")
                if "pauseRequested" in previous:
                    value["pauseRequested"] = previous["pauseRequested"]
        atomic_json(self.local_checkpoint, value, replace=True)
        if self.global_checkpoint is not None and self.global_checkpoint != self.local_checkpoint:
            global_state = read_checkpoint(self.global_checkpoint, fingerprint=self.fingerprint)
            paused = self.is_paused(global_state)
            require(self.preservation_binding is None or global_state.get("preservationException") == self.preservation_binding,
                    "InheritedPreservationExceptionChanged")
            modes = dict(global_state.get("runtimeModes", {}))
            modes[self.mode_key] = {key: value[key] for key in ("corpusSha256", "corpusKind", "outputDirectory",
                "stateDirectory", "lastCompletedCaseId", "canonicalRecordHashes", "pendingCases")}
            if summary:
                modes[self.mode_key]["summary"] = value["summary"]
            global_state.update({key: value[key] for key in ("phase", "currentPhase", "activeProcess", "activeProcessIdentity",
                "lastCompletedCaseId", "canonicalRecordHashes", "pendingCases", "blockers", "nextAction", "updatedUtc",
                "corpusSha256", "executionMode", "corpusKind", "lastSuccessfulReceipt")})
            required_modes = ["private:positive", "public:positive", "private:branch_controls", "public:branch_controls"]
            pending_modes = [key for key in required_modes if "summary" not in modes.get(key, {})]
            global_state.update(runtimeModes=modes, currentRuntimeMode=self.mode_key, verdict="NOT_ACCEPTED",
                pendingRuntimeModes=pending_modes,
                status="BLOCKED" if blocker else "RUNTIME_VERIFIED" if not pending_modes else "RUNTIME_IN_PROGRESS")
            if not blocker:
                global_state["nextAction"] = ("ExecuteOrResumeMode:" + pending_modes[0] if pending_modes else "FinalQAAndDelivery")
            global_state["completedSteps"] = list(dict.fromkeys(global_state.get("completedSteps", []) + value["completedSteps"]))
            if summary:
                global_state["completedSteps"] = list(dict.fromkeys(global_state["completedSteps"] +
                    [self.mode_key + ":ActualExecutionAndIndependentOracleComplete"]))
            if paused:
                global_state.update(phase="PAUSED", currentPhase="PAUSED", status="PAUSED",
                    nextAction="WaitForExplicitUserResume_NoNewCaseMayStart")
            atomic_json(self.global_checkpoint, global_state, replace=True)

    def transport_lines(self, transport, case_id):
        require(type(transport) is dict and set(transport) == {"schemaVersion", "runnerExitCode", "timedOut", "stdout", "stderr", "caseId", "oneRunnerProcessOneCase"}
                and type(transport["schemaVersion"]) is int and transport["schemaVersion"] == 1
                and type(transport.get("runnerExitCode")) is int and transport["runnerExitCode"] == 0 and transport.get("timedOut") is False
                and transport.get("oneRunnerProcessOneCase") is True and transport.get("caseId") == case_id,
                "CompleteActualM2buTransportRequired")
        for key in ("stdout", "stderr"):
            row = transport[key]
            path = Path(row["path"])
            require(path.is_absolute() and not str(path).startswith(("\\\\", "//"))
                    and path.is_relative_to(self.state), "TransportPathMustBeOwnedLocalBeforeRead")
            require(path == no_reparse(path) and file_binding(path) == row,
                    "TransportEvidenceEscapedOrChanged")
        require(transport["stderr"]["bytes"] == 0 and transport["stdout"]["bytes"] <= transport_api.MAX_RESPONSE,
                "BoundedSuccessfulM2buTransportRequired")
        raw = Path(transport["stdout"]["path"]).read_bytes()
        require(raw.endswith(b"\n") and len(raw.splitlines()) == 2, "TwoCompleteActualRunnerRecordsRequired")
        ack, actual = (transport_api.strict_json(line) for line in raw.splitlines())
        return ack, actual

    def check_transport(self, transport, record):
        ack, actual = self.transport_lines(transport, record["case"]["case_id"])
        require(ack == record["programAdmission"] and actual == record["actual"], "CanonicalObservationNotActualTransport")

    def check_record(self, index, record):
        require(type(record) is dict and set(record) == {"schemaVersion", "caseIndex", "case", "wireCase",
                "expected", "programAdmission", "actual", "comparison"}
                and type(record["schemaVersion"]) is int and record["schemaVersion"] == 1
                and type(record["caseIndex"]) is int and record["caseIndex"] == index
                and record["case"] == self.cases[index] and record["wireCase"] == self.wires[index]
                and record["expected"] == self.expected[index], "CompleteFrozenM2buRecordRequired")
        self.ack_validator(record["programAdmission"], self.program_identity, self.public)
        actual = record["actual"]
        require(actual.get("kind") == "entry_continuity_observation" and actual.get("accepted") is True,
                "ActualM2buObservationRequired")
        report = actual["report"]
        positive = self.corpus_kind == "positive"
        path = self.cases[index]["path"]
        terminal = (0x55C5 if path == "A" else 0x5596) if positive else (0x5533 if path == "JbrAlternate" else 0x5503)
        if self.public:
            terminal += 0x6200 - 0x54F5
        require(report["positive_completed"] is positive and report["boundary_only"] is (not positive)
                and report["actual_handoff_observed"] is positive and report["stop_before_pc"] == terminal
                and report["native_predecessor_retirements"] == (6 if positive else self.cases[index]["budget"])
                and report["algorithm_retirements"] == (self.cases[index]["budget"] - 6 if positive else 0)
                and actual["actual_successful_step_returns"] == self.cases[index]["budget"],
                "PositiveAndBoundaryOnlyActualContinuityMustRemainSeparate")
        compared = self.compare(self.cases[index], actual, program_identity=self.program_identity)
        require(compared["passed"] is True and compared["expected"] == self.expected[index]
                and compared["comparison"] == record["comparison"], "IndependentFrozenM2buComparisonMismatch")

    def make_record(self, index, ack, actual):
        compared = self.compare(self.cases[index], actual, program_identity=self.program_identity)
        require(compared["passed"] is True and compared["expected"] == self.expected[index], "IndependentExpectationChanged")
        value = {"schemaVersion": 1, "caseIndex": index, "case": self.cases[index], "wireCase": self.wires[index],
                 "expected": self.expected[index], "programAdmission": ack, "actual": actual, "comparison": compared["comparison"]}
        self.check_record(index, value)
        return value

    def publish_case(self, index, record, transport):
        self.check_record(index, record)
        self.check_transport(transport, record)
        atomic_json(self.cache_path(index), {"schemaVersion": 1, "milestone": "M2bu", "sourceFingerprint": self.fingerprint,
            "corpusSha256": self.corpus_digest, "corpusKind": self.corpus_kind,
            "record": record, "recordSha256": digest(record), "transport": transport})
        self.records.append(record)

    def recover_orphan(self, index):
        intent_path, attempt = self.intent_path(index), self.attempt_path(index)
        if not intent_path.exists():
            require(not attempt.exists(), "AttemptWithoutFrozenIntent")
            return False
        require(read_json(intent_path) == self.intent(index), "StaleOrChangedM2buAttemptIntent")
        if not attempt.exists():
            return False  # execute_case creates its directory before spawning.
        receipt = attempt / "transport.json"
        require(receipt.exists(), "OrphanOutcomeUnknown_PreservePartial_NoAutomaticRerun")
        transport = read_json(receipt)
        ack, actual = self.transport_lines(transport, self.cases[index]["case_id"])
        record = self.make_record(index, ack, actual)
        self.publish_case(index, record, transport)
        self.recovered_orphan_cases += 1
        return True

    def validate_saved_progress(self, previous):
        require(previous["corpusSha256"] == self.corpus_digest and previous["corpusKind"] == self.corpus_kind
                and previous["outputDirectory"] == str(self.output) and previous["stateDirectory"] == str(self.state),
                "SavedModeCorpusOrOutputChanged")
        hashes = previous["canonicalRecordHashes"]
        require(type(hashes) is list and hashes == [digest(value) for value in self.records[:len(hashes)]]
                and 0 <= len(self.records) - len(hashes) <= 1, "CheckpointCompletedRecordMismatch")
        require(previous["lastCompletedCaseId"] == (self.cases[len(hashes) - 1]["case_id"] if hashes else None)
                and previous["pendingCases"] == [case["case_id"] for case in self.cases[len(hashes):]],
                "CheckpointLastOrPendingCaseMismatch")
        if "summary" in previous:
            require(len(self.records) == len(self.cases) and file_binding(self.output / "summary.json") == previous["summary"],
                    "SavedCompletedModeReceiptMissingOrChanged")

    def prepare(self):
        self.pause_gate()
        # Disk receipts, not a retained Python list or checkpoint counter, are
        # the authority even when the same controller object is invoked again.
        self.records = []
        self.recovered_orphan_cases = 0
        self.output.mkdir(parents=True, exist_ok=True)
        self.state.mkdir(parents=True, exist_ok=True)
        require({path.name for path in self.output.iterdir()} <= ARTIFACT_NAMES, "UnexpectedArtifactMember")
        require(not (self.state / "first-mismatch.json").exists(), "PreservedFirstMismatchBlocksAcceptance")
        saved_mode = None
        if self.global_checkpoint is not None and self.global_checkpoint.exists():
            global_state = read_checkpoint(self.global_checkpoint, fingerprint=self.fingerprint)
            require(global_state.get("branch") == BRANCH and global_state.get("baseSha") == BASE,
                    "ExactM2buGlobalCheckpointBranchAndBaseRequired")
            transport_api.refuse_active(global_state.get("activeProcess") or global_state.get("activeProcessIdentity"))
            saved_mode = global_state.get("runtimeModes", {}).get(self.mode_key)
            require(saved_mode is None or saved_mode["outputDirectory"] == str(self.output), "ExistingModeOutputCannotBeReplaced")
        previous = None
        if self.local_checkpoint.exists():
            previous = read_checkpoint(self.local_checkpoint, fingerprint=self.fingerprint, corpus_sha256=self.corpus_digest)
            transport_api.refuse_active(previous.get("activeProcess"))
        self.fence()
        current_source = self.source_supplier()
        require(current_source["sourceBindings"] == self.join["sourceBindings"]
                and check_source_join(current_source) == self.fingerprint, "SourceChangedBeforeM2buRuntime")
        for name, expected in (("sourcejoin.json", self.join), ("pre-runtime-freeze.json", self.freeze)):
            path = self.output / name
            if path.exists():
                require(read_json(path) == expected, "FrozenM2buInputChanged")
            else:
                require(not any((self.state / "cases").glob("*.json")), "ObservationsWithoutFrozenInputs")
                atomic_json(path, expected)
        paths = set((self.state / "cases").glob("*.json"))
        require(paths <= {self.cache_path(index) for index in range(len(self.cases))}, "UnknownOrDuplicateCaseCache")
        gap = False
        for index in range(len(self.cases)):
            path = self.cache_path(index)
            if not path.exists():
                gap = True
                continue
            require(not gap, "NonprefixCompletedM2buCases")
            cached = read_json(path)
            require(set(cached) == {"schemaVersion", "milestone", "sourceFingerprint", "corpusSha256", "corpusKind", "record", "recordSha256", "transport"}
                    and cached["milestone"] == "M2bu" and type(cached["schemaVersion"]) is int and cached["schemaVersion"] == 1
                    and cached["sourceFingerprint"] == self.fingerprint and cached["corpusSha256"] == self.corpus_digest
                    and cached["corpusKind"] == self.corpus_kind and cached["recordSha256"] == digest(cached["record"]),
                    "CachedM2buIdentityOrChecksumMismatch")
            self.check_record(index, cached["record"])
            self.check_transport(cached["transport"], cached["record"])
            self.records.append(cached["record"])
        if previous is not None:
            require(previous.get("branch") == BRANCH and previous.get("baseSha") == BASE
                    and previous.get("executionMode") == self.mode, "ExactM2buLocalCheckpointDomainRequired")
            self.validate_saved_progress(previous)
        if saved_mode is not None:
            self.validate_saved_progress(saved_mode)
        if (self.output / "canonical.jsonl.gz").exists() or (self.output / "summary.json").exists():
            require(len(self.records) == len(self.cases), "FinalCanonicalWithoutCompleteActualCases")
        self.checkpoint("ROM_EXECUTION")

    def _run(self):
        self.prepare()
        for index in range(len(self.records), len(self.cases)):
            self.pause_gate()
            if self.recover_orphan(index):
                self.checkpoint("ROM_EXECUTION")
                continue
            intent_path = self.intent_path(index)
            if not intent_path.exists():
                atomic_json(intent_path, self.intent(index))
            active = {"controller": process_identity(os.getpid()), "child": None,
                      "caseId": self.cases[index]["case_id"], "attempt": str(self.attempt_path(index))}
            self.checkpoint("ROM_EXECUTION", active=active)
            ack = actual = None
            try:
                require(file_binding(self.runner) == self.runner_binding, "RunnerChangedAfterFreeze")
                def started(identity):
                    active["child"] = identity
                    self.checkpoint("ROM_EXECUTION", active=active)
                ack, actual, transport = self.executor(self.runner, self.program, self.wires[index], self.attempt_path(index), started)
                record = self.make_record(index, ack, actual)
                self.publish_case(index, record, transport)
                self.checkpoint("ROM_EXECUTION")
            except (ValueError, OSError, subprocess.SubprocessError) as error:
                code = getattr(error, "code", type(error).__name__)
                atomic_json(self.state / "first-mismatch.json", {"schemaVersion": 1, "milestone": "M2bu",
                    "sourceFingerprint": self.fingerprint, "corpusSha256": self.corpus_digest, "caseIndex": index,
                    "caseId": self.cases[index]["case_id"], "diagnosticClass": code,
                    "expected": self.expected[index], "actual": actual, "programAdmission": ack,
                    "detail": str(error)[:4096], "attemptDirectory": str(self.attempt_path(index)),
                    "passed": False, "expectationsChanged": False})
                self.checkpoint("ROM_EXECUTION", blocker=code)
                raise
        self.pause_gate()
        self.fence()
        current_source = self.source_supplier()
        require(current_source["sourceBindings"] == self.join["sourceBindings"]
                and check_source_join(current_source) == self.fingerprint
                and file_binding(self.runner) == self.runner_binding, "SourceOrRunnerChangedAcrossM2buRuntime")
        raw = b"".join(canonical(record) for record in self.records)
        require(len(raw) <= MAX_JSON, "BoundedM2buCanonicalStreamRequired")
        path = self.output / "canonical.jsonl.gz"
        if path.exists():
            with gzip.open(path, "rb") as stream:
                require(stream.read(MAX_JSON + 1) == raw, "RetainedCanonicalBytesChanged")
        else:
            publish_bytes(path, gzip.compress(raw, mtime=0))
        with gzip.open(path, "rb") as stream:
            require(stream.read(MAX_JSON + 1) == raw, "CanonicalFullEofCrcRoundtripFailed")
        summary = {"schemaVersion": 1, "milestone": "M2bu", "passed": True, "classification": self.mode,
            "corpusKind": self.corpus_kind, "sourceFingerprintSha256": self.fingerprint, "corpusSha256": self.corpus_digest,
            "cases": len(self.records), "positiveCases": len(self.records) if self.corpus_kind == "positive" else 0,
            "branchBoundaryControls": len(self.records) if self.corpus_kind == "branch_controls" else 0,
            "paths": dict(Counter(case["path"] for case in self.cases)), "retiredInstructions": sum(case["budget"] for case in self.cases),
            "firstMismatch": None, "independentOracle": "PASS", "canonicalDecompressedBytes": len(raw),
            "canonicalSha256": sha256(raw).hexdigest(), "expectedSha256": digest(self.expected),
            "fullActualObservationsRetained": True, "canonicalFieldExclusions": [], "firmwareReady": False,
            "NativeExitBoundaryReached": not self.public and self.corpus_kind == "positive",
            "PublicEquivalentExitBoundaryReached": self.public and self.corpus_kind == "positive",
            "BoundedPredecessorBranchBoundaryObserved": self.corpus_kind == "branch_controls",
            "unresolvedStatuses": list(UNRESOLVED)}
        path = self.output / "summary.json"
        if path.exists():
            require(read_json(path) == summary, "RetainedSummaryChanged")
        else:
            atomic_json(path, summary)
        self.checkpoint("ORACLE_COMPARISON", summary=summary)
        return summary

    def run(self):
        self.pause_gate()
        self.state.mkdir(parents=True, exist_ok=True)
        if self.global_checkpoint is not None:
            global_state = read_checkpoint(self.global_checkpoint, fingerprint=self.fingerprint)
            require(global_state.get("branch") == BRANCH and global_state.get("baseSha") == BASE,
                    "ExactM2buGlobalCheckpointBranchAndBaseRequired")
            lock = local_path(self.global_checkpoint.parent / ".m2bu-runtime.lock.json")
        else:
            lock = no_reparse(self.state / "runtime.lock.json")
        if lock.exists():
            saved = read_json(lock)
            require(saved["milestone"] == "M2bu" and saved["sourceFingerprint"] == self.fingerprint
                    and (self.global_checkpoint is not None or saved["corpusSha256"] == self.corpus_digest),
                    "StaleRuntimeLockSourceOrCorpus")
            transport_api.refuse_active({"controller": saved["controller"]})
            retired = lock.parent / "retired-locks" / (sha256(lock.read_bytes()).hexdigest() + "-" + uuid.uuid4().hex + ".json")
            retired.parent.mkdir(parents=True, exist_ok=True)
            require(not retired.exists(), "RetiredLockCollision")
            lock.rename(retired)  # Preserve stale ownership evidence; do not delete it.
        owner = {"schemaVersion": 1, "milestone": "M2bu", "sourceFingerprint": self.fingerprint,
                 "corpusSha256": self.corpus_digest, "modeKey": self.mode_key,
                 "outputDirectory": str(self.output), "controller": process_identity(os.getpid())}
        with lock.open("xb") as stream:
            stream.write(canonical(owner)); stream.flush(); os.fsync(stream.fileno())
        try:
            return self._run()
        except (ValueError, OSError, subprocess.SubprocessError) as error:
            code = getattr(error, "code", type(error).__name__)
            if code not in {"SameRuntimeStillActive_NoDuplicateStarted", "ActiveRuntimeIdentityUncertain_NoDuplicateStarted",
                            "ExplicitUserPauseRequested_NoNewCaseStarted"}:
                # A refusal must not truncate an older checkpoint's verified
                # prefix merely because validation stopped at a corrupt row.
                for path in dict.fromkeys((self.local_checkpoint, self.global_checkpoint)):
                    if path is not None and path.exists():
                        saved = read_checkpoint(path)
                        if (saved.get("sourceFingerprint") == self.fingerprint
                                and saved.get("branch") == BRANCH and saved.get("baseSha") == BASE):
                            saved.update(status="BLOCKED", blockers=[code],
                                nextAction="InspectPreservedM2buEvidence_NoAutomaticRuntimeRepeat",
                                updatedUtc=datetime.now(timezone.utc).isoformat())
                            atomic_json(path, saved, replace=True)
            raise
        finally:
            require(read_json(lock) == owner, "OwnedRuntimeLockChanged")
            lock.unlink()  # Only this invocation's ephemeral mutex, never case evidence.
