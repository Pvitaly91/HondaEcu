"""Closed M2bw per-case evidence ledger and idempotent resume orchestration.

This is not an emulator. The unchanged60-second one-process transport is reused;
the caller supplies independently frozen expectations and its actual comparator.
Only32 positive cases with one P2 instruction and the closed post-P2 tail are admitted. No build/network action
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
from native_post_p2_control.checkpoint import canonical, atomic_json, read_checkpoint, local_path
from original_rom_execution.build_guard import no_reparse

ROOT = Path(__file__).resolve().parents[3]
BASE = "b67ea436870fe591f6ae4daca307341806d6f8eb"
BRANCH = "codex/p28-word0196-post-p2-control-continuity-m2bw"
MAX_JSON = 128 * 1024 * 1024
ARTIFACT_NAMES = frozenset({"sourcejoin.json", "pre-runtime-freeze.json", "canonical.jsonl.gz", "summary.json"})
BUDGETS = {"A": 21, "B": 20, "C": 21, "D": 23}
PRIVATE_MODE = "OriginalRomBytes_TechnicalPostP2ControlExecution"
PUBLIC_MODE = "PublicSyntheticPostP2ControlRegression"
from native_post_p2_control.oracle import CYCLE_ACCOUNTING
UNRESOLVED = ("ActualHardwareEcuExecutionNotObserved", "RecoveredFullEcuSchedulerNotEstablished",
    "PhysicalSFNotEstablished", "NativeStackSafetyNotEstablished", "NativeP2InitialOwnershipNotEstablished",
    "NativeTCON0InitialOwnershipNotEstablished", "NativeTRNSITInitialOwnershipNotEstablished",
    "TimerEvolutionNotModeled", "IRQDeliveryNotInjected", "PhysicalTimingEquivalenceNotEstablished",
    "ElectricalOutputNotObserved", "ActualNativeDownstreamRejoinNotEstablished", "SafeROMPlacementNotEstablished",
    "TargetProgramEquivalenceNotEstablished", "FirmwareIntegrationNotEstablished",
    "DiagnosticCycleTimingEquivalenceNotEstablished")

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
    require(before["bytes"] <= MAX_JSON, "BoundedM2bwMetadataRequired")
    raw = path.read_bytes()
    require(file_binding(path) == before, "M2bwMetadataChangedDuringRead")
    value = transport_api.strict_json(raw)
    require(canonical(value) == raw, "CanonicalM2bwReceiptRequired")
    return value


def check_source_join(value):
    fingerprint = transport_api.check_source_join(value)
    require(value.get("milestone") == "M2bw" and value.get("exactBase") == BASE
            and value.get("firmwareReady", False) is False, "ExactM2bwSourceCannotPromoteFirmwareAuthority")
    return fingerprint


def verify_ack(ack, program_identity, public):
    fields = {"kind", "schemaVersion", "classification", "program_sha256", "entry_pc", "program_node_count",
              "native_generation_ownership", "physical_sf_known", "hardware_validated"}
    require(type(ack) is dict and set(ack) == fields and ack["kind"] == "program_admitted"
            and type(ack["schemaVersion"]) is int and ack["schemaVersion"] == 1
            and ack["classification"] == ("ExplicitInventedPublicPostP2ControlFixture" if public else PRIVATE_MODE)
            and ack["program_sha256"] == program_identity["program_sha256"]
            and type(ack["entry_pc"]) is int and ack["entry_pc"] == program_identity["program_base"]
            and type(ack["program_node_count"]) is int and ack["program_node_count"] == 31
            and ack["native_generation_ownership"] is False and ack["physical_sf_known"] is False
            and ack["hardware_validated"] is False, "ClosedM2bwProgramAcknowledgementRequired")


class VerificationRun:
    """One source-frozen closed corpus; sibling modes retain separate progress."""
    def __init__(self, *, output, runner, source_join, source_supplier, cases, wire_cases,
                 expected, program, program_identity, compare, public, source_fence=lambda: True,
                 private_identity=None, historical=None, executor=execute_case, checkpoint_path=None,
                 global_checkpoint=None, preservation_binding=None, ack_validator=None, corpus_kind="positive"):
        require(corpus_kind == "positive", "ClosedM2bwPositiveCorpusKindRequired")
        self.output = local_directory(output)
        self.state = local_directory(self.output.parent / (self.output.name + ".state"))
        self.runner = Path(runner).resolve(strict=True)
        self.runner_binding = file_binding(self.runner)
        self.join, self.source_supplier = source_join, source_supplier
        self.fingerprint = check_source_join(source_join)
        require(type(cases) is list and type(wire_cases) is list and type(expected) is list
                and len(cases) == len(wire_cases) == len(expected), "CompleteFrozenM2bwCasesRequired")
        paths = Counter(case["path"] for case in cases)
        require(paths == Counter({path: 8 for path in "ABCD"}), "ExactClosedM2bwCorpusMembershipRequired")
        ids = [case["case_id"] for case in cases]
        require(len(ids) == len(set(ids)) and all(type(name) is str
                and re.fullmatch(r"[A-Za-z0-9_-]{1,160}", name) is not None for name in ids), "UniqueSafeM2bwCaseIdsRequired")
        for case, wire, frozen_expected in zip(cases, wire_cases, expected):
            require(type(case["budget"]) is int and case["budget"] == BUDGETS[case["path"]]
                    and wire["case_id"] == case["case_id"] and wire["path"] == case["path"]
                    and type(wire["budget"]) is int and wire["budget"] == case["budget"], "ExactFrozenM2bwPathBudgetRequired")
            snapshot = case.get("p2_snapshot")
            require(type(snapshot) is dict and set(snapshot) == {"value", "p2io", "p2sf", "provenance"}
                    and type(snapshot["value"]) is int and 0 <= snapshot["value"] <= 255
                    and type(snapshot["p2io"]) is int and snapshot["p2io"] == 255
                    and type(snapshot["p2sf"]) is int and snapshot["p2sf"] == 7
                    and snapshot["provenance"] == "TechnicalArchitecturalP2LatchSnapshot_NoNativeWriterGeneration"
                    and wire.get("p2_snapshot") == snapshot, "ExactOnceInitialTechnicalP2SnapshotRequired")
            require(type(frozen_expected.get("initial_p2")) is int and frozen_expected["initial_p2"] == snapshot["value"]
                    and type(frozen_expected.get("final_p2")) is int and 0 <= frozen_expected["final_p2"] <= 255
                    and type(frozen_expected.get("same_value_p2_write")) is bool
                    and type(frozen_expected.get("final_p2_zf")) is bool, "FrozenIndependentP2StateRequired")
            control = case.get("control_snapshot")
            require(type(control) is dict and set(control) == {"tcon0", "trnsit_implemented_flags", "provenance"}
                    and type(control["tcon0"]) is int and control["tcon0"] in (0x83, 0x87, 0x8B, 0x8F)
                    and type(control["trnsit_implemented_flags"]) is int and 0 <= control["trnsit_implemented_flags"] <= 15
                    and control["provenance"] == "TechnicalArchitecturalControlSnapshot_NoNativeWriterGeneration"
                    and wire.get("control_snapshot") == control, "ExactOnceInitialTechnicalControlSnapshotRequired")
            require(frozen_expected.get("control_initial") == [control["tcon0"], control["trnsit_implemented_flags"]]
                    and frozen_expected.get("control_instruction_retirements") == (4 if case["path"] == "A" else 1),
                    "FrozenIndependentControlStateRequired")
        require(type(public) is bool and program_identity["program_base"] == (0x6400 if public else 0x54F5),
                "ExplicitM2bwProgramDomainRequired")
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
        self.freeze = {"schemaVersion": 1, "milestone": "M2bw", "classification": self.mode,
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
        return {"schemaVersion": 1, "milestone": "M2bw", "sourceFingerprint": self.fingerprint,
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
        value = {"schemaVersion": 1, "milestone": "M2bw", "branch": BRANCH, "baseSha": BASE,
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
            required_modes = ["private:positive", "public:positive"]
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
                "CompleteActualM2bwTransportRequired")
        for key in ("stdout", "stderr"):
            row = transport[key]
            path = Path(row["path"])
            require(path.is_absolute() and not str(path).startswith(("\\\\", "//"))
                    and path.is_relative_to(self.state), "TransportPathMustBeOwnedLocalBeforeRead")
            require(path == no_reparse(path) and file_binding(path) == row,
                    "TransportEvidenceEscapedOrChanged")
        require(transport["stderr"]["bytes"] == 0 and transport["stdout"]["bytes"] <= transport_api.MAX_RESPONSE,
                "BoundedSuccessfulM2bwTransportRequired")
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
                and record["expected"] == self.expected[index], "CompleteFrozenM2bwRecordRequired")
        self.ack_validator(record["programAdmission"], self.program_identity, self.public)
        actual = record["actual"]
        require(actual.get("kind") == "post_p2_control_observation" and actual.get("accepted") is True,
                "ActualM2bwObservationRequired")
        report = actual["report"]
        path = self.cases[index]["path"]
        terminal = 0x55D2 if path == "A" else 0x559D
        if self.public:
            terminal += 0x6400 - 0x54F5
        require(report["positive_completed"] is True and report["boundary_only"] is False
                and report["actual_handoff_observed"] is True and report["stop_before_pc"] == terminal
                and type(report["native_predecessor_retirements"]) is int and report["native_predecessor_retirements"] == 6
                and type(report["algorithm_retirements"]) is int and report["algorithm_retirements"] == self.cases[index]["budget"] - 7 - (4 if path == "A" else 1)
                and type(report["p2_instruction_retirements"]) is int and report["p2_instruction_retirements"] == 1
                and type(actual["actual_successful_step_returns"]) is int
                and actual["actual_successful_step_returns"] == self.cases[index]["budget"],
                "ExactlyOneActualP2InstructionAfterContinuousPrefixAndAlgorithmRequired")
        journal = report.get("peripheral_p2_journal")
        require(type(journal) is list and len(journal) == 2
                and all(type(row) is dict and type(row.get("address")) is int and row["address"] == 36
                        and type(row.get("width")) is int and row["width"] == 8
                        and row.get("space") == "PeripheralP2" for row in journal)
                and [row.get("operation") for row in journal] == ["Read", "Write"],
                "ExactlyOneFunctionalPeripheralP2ReadBeforeWriteRequired")
        require(report.get("control_instruction_retirements") == (4 if path == "A" else 1),
                "ExactClosedPostP2RetirementsRequired")
        control = report.get("peripheral_control_journal")
        require(type(control) is list and len(control) == (3 if path == "A" else 2)
                and [event.get("operation") for event in control] == (["Read", "Read", "Write"] if path == "A" else ["Read", "Write"])
                and all(event.get("address") == (64 if path == "A" else 70)
                    and event.get("width") == 8 and event.get("space") == "PeripheralControl" for event in control),
                "ClosedControlReadBeforeWriteJournalRequired")
        compared = self.compare(self.cases[index], actual, program_identity=self.program_identity)
        require(compared["passed"] is True and compared["expected"] == self.expected[index]
                and compared["comparison"] == record["comparison"], "IndependentFrozenM2bwComparisonMismatch")

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
        atomic_json(self.cache_path(index), {"schemaVersion": 1, "milestone": "M2bw", "sourceFingerprint": self.fingerprint,
            "corpusSha256": self.corpus_digest, "corpusKind": self.corpus_kind,
            "record": record, "recordSha256": digest(record), "transport": transport})
        self.records.append(record)

    def recover_orphan(self, index):
        intent_path, attempt = self.intent_path(index), self.attempt_path(index)
        if not intent_path.exists():
            require(not attempt.exists(), "AttemptWithoutFrozenIntent")
            return False
        require(read_json(intent_path) == self.intent(index), "StaleOrChangedM2bwAttemptIntent")
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
                    "ExactM2bwGlobalCheckpointBranchAndBaseRequired")
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
                and check_source_join(current_source) == self.fingerprint, "SourceChangedBeforeM2bwRuntime")
        for name, expected in (("sourcejoin.json", self.join), ("pre-runtime-freeze.json", self.freeze)):
            path = self.output / name
            if path.exists():
                require(read_json(path) == expected, "FrozenM2bwInputChanged")
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
            require(not gap, "NonprefixCompletedM2bwCases")
            cached = read_json(path)
            require(set(cached) == {"schemaVersion", "milestone", "sourceFingerprint", "corpusSha256", "corpusKind", "record", "recordSha256", "transport"}
                    and cached["milestone"] == "M2bw" and type(cached["schemaVersion"]) is int and cached["schemaVersion"] == 1
                    and cached["sourceFingerprint"] == self.fingerprint and cached["corpusSha256"] == self.corpus_digest
                    and cached["corpusKind"] == self.corpus_kind and cached["recordSha256"] == digest(cached["record"]),
                    "CachedM2bwIdentityOrChecksumMismatch")
            self.check_record(index, cached["record"])
            self.check_transport(cached["transport"], cached["record"])
            self.records.append(cached["record"])
        if previous is not None:
            require(previous.get("branch") == BRANCH and previous.get("baseSha") == BASE
                    and previous.get("executionMode") == self.mode, "ExactM2bwLocalCheckpointDomainRequired")
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
                atomic_json(self.state / "first-mismatch.json", {"schemaVersion": 1, "milestone": "M2bw",
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
                and file_binding(self.runner) == self.runner_binding, "SourceOrRunnerChangedAcrossM2bwRuntime")
        raw = b"".join(canonical(record) for record in self.records)
        require(len(raw) <= MAX_JSON, "BoundedM2bwCanonicalStreamRequired")
        path = self.output / "canonical.jsonl.gz"
        if path.exists():
            with gzip.open(path, "rb") as stream:
                require(stream.read(MAX_JSON + 1) == raw, "RetainedCanonicalBytesChanged")
        else:
            publish_bytes(path, gzip.compress(raw, mtime=0))
        with gzip.open(path, "rb") as stream:
            require(stream.read(MAX_JSON + 1) == raw, "CanonicalFullEofCrcRoundtripFailed")
        require(len(self.records) == 32
                and sum(record["actual"]["actual_successful_step_returns"] for record in self.records) == 680,
                "ExactlyThirtyTwoActualP2CasesAnd680RetirementsRequired")
        peripheral = [row for record in self.records for row in record["actual"]["report"]["peripheral_p2_journal"]]
        control = [row for record in self.records for row in record["actual"]["report"]["peripheral_control_journal"]]
        summary = {"schemaVersion": 1, "milestone": "M2bw", "passed": True, "classification": self.mode,
            "corpusKind": self.corpus_kind, "sourceFingerprintSha256": self.fingerprint, "corpusSha256": self.corpus_digest,
            "cases": len(self.records), "positiveCases": len(self.records),
            "paths": dict(Counter(case["path"] for case in self.cases)),
            "retiredInstructions": sum(record["actual"]["actual_successful_step_returns"] for record in self.records),
            "p2Retirements": sum(record["actual"]["report"]["p2_instruction_retirements"] for record in self.records),
            "functionalPeripheralP2Reads": sum(row["operation"] == "Read" for row in peripheral),
            "functionalPeripheralP2Writes": sum(row["operation"] == "Write" for row in peripheral),
            "sameValueP2Writes": sum(row["same_value"] for row in peripheral if row["operation"] == "Write"),
            "zeroResultP2Writes": sum(record["actual"]["report"]["p2_final"] == 0 for record in self.records),
            "controlRetirements": sum(record["actual"]["report"]["control_instruction_retirements"] for record in self.records),
            "functionalPeripheralControlReads": sum(row["operation"] == "Read" for row in control),
            "functionalPeripheralControlWrites": sum(row["operation"] == "Write" for row in control),
            "sameValueControlWrites": sum(row["same_value"] for row in control if row["operation"] == "Write"),
            "TechnicalPostP2ControlContinuityVerified": True, "initialNativeControlOwnerEstablished": False,
            "timerEvolutionModeled": False, "irqDeliveryInjected": False,
            "firstMismatch": None, "independentOracle": "PASS", "canonicalDecompressedBytes": len(raw),
            "canonicalSha256": sha256(raw).hexdigest(), "expectedSha256": digest(self.expected),
            "fullActualObservationsRetained": True, "canonicalFieldExclusions": [], "firmwareReady": False,
            "TechnicalP2HandoffVerified": True, "OriginalRomP2HandoffObserved": not self.public,
            "PublicEquivalentP2HandoffVerified": self.public,
            "initialNativeP2OwnerEstablished": False, "physicalP2ElectricalEffectNotEstablished": True,
            "P2InitialSource": "TechnicalArchitecturalSnapshot", "P2InitialNativeOwner": "NotEstablished",
            "P2RmwWriter": "ActualProductionInstruction", "P2FinalGeneration": "VerifiedWithinTechnicalSession",
            "PhysicalP2Owner": "NotEstablished", "PhysicalOutputEffect": "NotObserved",
            "cycleAccounting": dict(CYCLE_ACCOUNTING),
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
                    "ExactM2bwGlobalCheckpointBranchAndBaseRequired")
            lock = local_path(self.global_checkpoint.parent / ".m2bw-runtime.lock.json")
        else:
            lock = no_reparse(self.state / "runtime.lock.json")
        if lock.exists():
            saved = read_json(lock)
            require(saved["milestone"] == "M2bw" and saved["sourceFingerprint"] == self.fingerprint
                    and (self.global_checkpoint is not None or saved["corpusSha256"] == self.corpus_digest),
                    "StaleRuntimeLockSourceOrCorpus")
            transport_api.refuse_active({"controller": saved["controller"]})
            retired = lock.parent / "retired-locks" / (sha256(lock.read_bytes()).hexdigest() + "-" + uuid.uuid4().hex + ".json")
            retired.parent.mkdir(parents=True, exist_ok=True)
            require(not retired.exists(), "RetiredLockCollision")
            lock.rename(retired)  # Preserve stale ownership evidence; do not delete it.
        owner = {"schemaVersion": 1, "milestone": "M2bw", "sourceFingerprint": self.fingerprint,
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
                                nextAction="InspectPreservedM2bwEvidence_NoAutomaticRuntimeRepeat",
                                updatedUtc=datetime.now(timezone.utc).isoformat())
                            atomic_json(path, saved, replace=True)
            raise
        finally:
            require(read_json(lock) == owner, "OwnedRuntimeLockChanged")
            lock.unlink()  # Only this invocation's ephemeral mutex, never case evidence.
