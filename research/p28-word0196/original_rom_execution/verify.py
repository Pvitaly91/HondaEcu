"""Source-frozen, resumable bounded production-runner orchestration.

Private original bytes and public invented fixtures use separate admissions.
Expected values are sealed before a runner starts. Immutable per-case actual
observations and process receipts live outside the four-file artifact directory.
This module never builds a runner, searches for a ROM, or accesses a network.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import gzip
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import uuid

from original_rom_execution.checkpoint import atomic_json, canonical, read_checkpoint

ROOT = Path(__file__).resolve().parents[3]
BASE = "4196153c6bcda3da5b164db752a8be4011c4e598"
BRANCH = "codex/p28-word0196-original-rom-execution-m2bt"
PUBLIC_MODE = "PublicSyntheticExecutionRegression"
PRIVATE_MODE = "OriginalRomBytes_TechnicalSeededExecution"
MAX_JSON = 128 * 1024 * 1024
MAX_RESPONSE = 4 * 1024 * 1024
MAX_STDERR = 64 * 1024
CASE_TIMEOUT_SECONDS = 60
ARTIFACT_NAMES = frozenset({"sourcejoin.json", "pre-runtime-freeze.json",
                            "canonical.jsonl.gz", "summary.json"})
STATUSES = (
    "ActualNativeDownstreamRejoinNotEstablished", "NativeSchedulerNotEstablished",
    "PhysicalSFNotEstablished", "NativeStackSafetyNotEstablished",
    "PeripheralStateOwnershipNotEstablished", "SafeROMPlacementNotEstablished",
    "TargetProgramEquivalenceNotEstablished", "FirmwareIntegrationNotEstablished",
)


class ExecutionError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def require(condition, code):
    if condition is not True:
        raise ExecutionError(code)


def digest(value):
    return sha256(canonical(value)).hexdigest()


def strict_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "DuplicateJsonKey")
            result[key] = value
        return result
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(ExecutionError("NonfiniteJson")))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise ExecutionError("IncompleteOrMalformedJson") from error


def read_json(path, *, canonical_required=True, limit=MAX_JSON):
    path = Path(path)
    require(not path.is_symlink() and path.is_file(), "RegularReceiptRequired")
    with path.open("rb") as stream:
        raw = stream.read(limit + 1)
    require(len(raw) <= limit, "BoundedReceiptRequired")
    value = strict_json(raw)
    if canonical_required:
        require(canonical(value) == raw, "NoncanonicalReceipt")
    return value


def local_directory(path):
    name = os.fspath(path)
    require(type(name) is str and not name.startswith(("\\\\", "//"))
            and re.match(r"^[A-Za-z]+://", name) is None, "LocalOutputRequired")
    candidate = Path(name).absolute()
    for parent in (candidate, *candidate.parents):
        if parent.exists():
            info = parent.lstat()
            require(not parent.is_symlink() and not getattr(info, "st_file_attributes", 0) & 0x400,
                    "OutputReparseAncestor")
    return candidate.resolve(strict=False)


def file_binding(path):
    candidate = Path(path).resolve(strict=True)
    require(candidate.is_file() and not Path(path).is_symlink(), "RegularSelectedFileRequired")
    with candidate.open("rb") as stream:
        before = os.fstat(stream.fileno())
        require(before.st_size <= MAX_JSON, "SelectedFileSizeBound")
        raw = stream.read(MAX_JSON + 1)
        after = os.fstat(stream.fileno())
    require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) ==
            (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
            and len(raw) == before.st_size, "SelectedFileChanged")
    return {"path": str(candidate), "bytes": len(raw), "sha256": sha256(raw).hexdigest()}


def preservation_exception_context(checkpoint_path):
    """Authenticate the separately recorded local permission, not historical PASS."""
    state = read_checkpoint(checkpoint_path)
    selected = state.get("preservationException")
    require(type(selected) is dict and set(selected) == {"path", "bytes", "sha256"},
            "AppliedPreservationExceptionBindingRequired")
    path = local_directory(selected["path"])
    require(path == ROOT / "private/reports/m2bt/authorized-runner-loss/AUTHORIZED_EXCEPTION_V1.json"
            and file_binding(path) == selected, "AppliedPreservationExceptionChanged")
    record = read_json(path)
    require(record.get("schemaVersion") == 1 and record.get("milestone") == "M2bt"
            and record.get("classification") == "AuthorizedHistoricalGeneratedRunnerLoss"
            and record.get("applicable") is True and record.get("allSevenConditionsSatisfied") is True
            and record.get("protectedHistoricalIdentityRestored") is False
            and record.get("strictHistoricalPreservationPass") is False,
            "ExactAuthorizedGeneratedRunnerLossRequired")
    for name, count in (("rawProtectedDifferences", 1), ("authorizedPreservationExceptions", 1),
                        ("otherUnauthorizedProtectedDifferences", 0)):
        require(type(record.get(name)) is int and record[name] == count,
                "PreservationExceptionAccountingChanged")
    for name in ("authorizationBinding", "conditionsAuditBinding", "policyReviewBinding", "sourceCapsuleBinding"):
        row = record.get(name)
        require(type(row) is dict and set(row) == {"path", "bytes", "sha256"}
                and file_binding(local_directory(row["path"])) == row,
                "PreservationExceptionEvidenceChanged")
    conditions = read_json(record["conditionsAuditBinding"]["path"])
    require(conditions.get("allSevenConditionsSatisfiedInDeclaredScope") is True
            and [row.get("number") for row in conditions.get("conditions", [])] == list(range(1, 8))
            and all(row.get("satisfied") is True for row in conditions["conditions"]),
            "PreservationExceptionConditionsNotSatisfied")
    role = record.get("exceptionRole")
    require(type(role) is dict
            and role.get("path") == "rust/p28-slice-runner/target/release/p28-slice-runner.exe"
            and role.get("aliasPaths") == ["rust/p28-slice-runner/target/release/deps/p28_slice_runner.exe"]
            and role.get("expected") == conditions.get("historicalExpectedRunnerIdentity")
            and role.get("observed") == conditions.get("currentIncidentIdentity")
            and role.get("expected") != role.get("observed")
            and record.get("historicalExpectedRebased") is False,
            "AuthorizedLossRoleDiffersFromAuditedIncident")
    return dict(selected)


def publish_bytes(path, raw):
    """No-replace atomic publication; existing/partial evidence is never deleted."""
    path = Path(path)
    require(not path.is_symlink(), "OutputSymlinkRefused")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".m2bt-bytes-", dir=path.parent)
    temporary = Path(temporary)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        if os.name == "nt":
            os.rename(temporary, path)
        else:
            os.link(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def process_identity(pid):
    """Query only. In particular, never use os.kill(pid,0) on Windows."""
    require(type(pid) is int and pid > 0, "PositiveProcessIdRequired")
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
        kernel.WaitForSingleObject.argtypes = (wintypes.HANDLE, wintypes.DWORD)
        kernel.GetProcessTimes.argtypes = (wintypes.HANDLE, *([ctypes.POINTER(wintypes.FILETIME)] * 4))
        kernel.QueryFullProcessImageNameW.argtypes = (wintypes.HANDLE, wintypes.DWORD,
                                                     wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD))
        handle = kernel.OpenProcess(0x1000 | 0x100000, False, pid)
        if not handle:
            if ctypes.get_last_error() in (87, 1168):
                return None
            return {"pid": pid, "identityKnown": False}
        try:
            if kernel.WaitForSingleObject(handle, 0) == 0:
                return None
            times = [wintypes.FILETIME() for _ in range(4)]
            size, image = wintypes.DWORD(32768), ctypes.create_unicode_buffer(32768)
            known = bool(kernel.GetProcessTimes(handle, *(ctypes.byref(t) for t in times))
                         and kernel.QueryFullProcessImageNameW(handle, 0, image, ctypes.byref(size)))
            return {"pid": pid, "identityKnown": known,
                    "startIdentity": str((times[0].dwHighDateTime << 32) | times[0].dwLowDateTime) if known else None,
                    "image": image.value.lower() if known else None}
        finally:
            kernel.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return None
    except PermissionError:
        return {"pid": pid, "identityKnown": False}
    try:
        # Split after the command's final ')': its name may itself contain spaces.
        stat = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
        return {"pid": pid, "identityKnown": True, "startIdentity": stat[19],
                "image": os.readlink(f"/proc/{pid}/exe")}
    except (OSError, IndexError):
        return {"pid": pid, "identityKnown": False}


def refuse_active(saved):
    if saved is None:
        return
    require(type(saved) is dict and set(saved) <= {"controller", "child", "caseId", "attempt"},
            "MalformedActiveProcessIdentity")
    for field in ("controller", "child"):
        identity = saved.get(field)
        if identity is None:
            continue
        require(type(identity) is dict and type(identity.get("pid")) is int,
                "MalformedActiveProcessIdentity")
        observed = process_identity(identity["pid"])
        if observed is not None:
            if identity.get("identityKnown") is not True or observed.get("identityKnown") is not True:
                raise ExecutionError("ActiveRuntimeIdentityUncertain_NoDuplicateStarted")
            if observed == identity:
                raise ExecutionError("SameRuntimeStillActive_NoDuplicateStarted")


def execute_case(runner, program, wire, attempt, active_callback):
    """One explicit source plus one case in one owned Rust process, no shell."""
    attempt.mkdir(parents=True, exist_ok=False)
    stdout_path, stderr_path = attempt / "stdout.partial", attempt / "stderr.partial"
    payload = canonical(program) + canonical(wire)
    require(len(payload) <= 2 * 65536 and all(len(line) <= 65536 for line in payload.splitlines()),
            "ClosedRunnerInputBound")
    timed_out = False
    with stdout_path.open("xb") as stdout, stderr_path.open("xb") as stderr:
        child = subprocess.Popen([str(runner)], stdin=subprocess.PIPE, stdout=stdout, stderr=stderr,
                                 shell=False, cwd=ROOT,
                                 creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        try:
            active_callback(process_identity(child.pid))
            child.communicate(payload, timeout=CASE_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            timed_out = True
            child.kill()  # Only this Popen-owned runner, which spawns no children.
            child.communicate(timeout=5)
        finally:
            # Callback/checkpoint failures and interruption must also reap the
            # exact child we own; never leave it blocked waiting for stdin.
            if child.poll() is None:
                child.kill()
                child.communicate(timeout=5)
    transport = {"schemaVersion": 1, "runnerExitCode": child.returncode, "timedOut": timed_out,
                 "stdout": file_binding(stdout_path), "stderr": file_binding(stderr_path),
                 "caseId": wire["case_id"], "oneRunnerProcessOneCase": True}
    atomic_json(attempt / "transport.json", transport)
    require(not timed_out, "OwnedRunnerTimeout")
    require(child.returncode == 0, "RunnerTransportExitFailure")
    require(stdout_path.stat().st_size <= MAX_RESPONSE and stderr_path.stat().st_size <= MAX_STDERR,
            "RunnerOutputSizeBound")
    require(stderr_path.stat().st_size == 0, "UnexpectedRunnerStderr")
    raw = stdout_path.read_bytes()
    require(raw.endswith(b"\n") and len(raw.splitlines()) == 2, "TwoCompleteRunnerRecordsRequired")
    ack, observation = (strict_json(line) for line in raw.splitlines())
    return ack, observation, transport


def verify_ack(ack, program_identity, public):
    fields = {"kind", "schemaVersion", "classification", "program_sha256", "entry_pc",
              "program_node_count", "native_generation_ownership", "physical_sf_known", "hardware_validated"}
    require(type(ack) is dict and set(ack) == fields, "ClosedProgramAdmissionRecordRequired")
    require(ack["kind"] == "program_admitted" and type(ack["schemaVersion"]) is int
            and ack["schemaVersion"] == 1 and ack["program_node_count"] == 18,
            "ProgramSourceAdmissionFailed")
    expected = "ExplicitInventedPublicFixture" if public else PRIVATE_MODE
    require(ack["classification"] == expected and ack["entry_pc"] == program_identity["program_base"]
            and ack["program_sha256"] == program_identity["program_sha256"], "ProgramSourceIdentityMismatch")
    require(all(ack[key] is False for key in ("native_generation_ownership", "physical_sf_known", "hardware_validated")),
            "ProgramAdmissionPromotedNativeOwnership")


def check_source_join(value):
    require(type(value) is dict and value.get("passed") is True
            and type(value.get("sourceBindings")) is list and bool(value["sourceBindings"])
            and re.fullmatch(r"[0-9a-f]{64}", value.get("sourceFingerprintSha256", "")) is not None,
            "CompletePassedSourceJoinRequired")
    rows = value["sourceBindings"]
    require(sha256(canonical(rows)[:-1]).hexdigest() == value["sourceFingerprintSha256"],
            "SourceJoinFingerprintDoesNotBindRows")
    require(len({row["path"] for row in rows}) == len(rows), "DuplicateSourceBinding")
    return value["sourceFingerprintSha256"]


def source_joins_equal(before, after):
    check_source_join(after)
    require(before["sourceFingerprintSha256"] == after["sourceFingerprintSha256"]
            and before["sourceBindings"] == after["sourceBindings"], "SourceChangedAcrossRuntime")


class VerificationRun:
    """Frozen orchestration; tests inject only invented observations at this seam."""
    def __init__(self, *, output, runner, source_join, source_supplier, cases,
                 wire_cases, expected, program, program_identity, compare,
                 public, source_fence=lambda: True, private_identity=None,
                 historical=None, executor=execute_case, checkpoint_path=None,
                 preservation_binding=None):
        self.output = local_directory(output)
        self.state = local_directory(self.output.parent / (self.output.name + ".state"))
        self.runner = Path(runner).resolve(strict=True)
        self.runner_binding = file_binding(self.runner)
        self.join, self.source_supplier = source_join, source_supplier
        self.fingerprint = check_source_join(source_join)
        self.cases, self.wire_cases, self.expected = cases, wire_cases, expected
        self.program, self.program_identity, self.compare = program, program_identity, compare
        self.public, self.fence, self.executor = public, source_fence, executor
        self.mode = PUBLIC_MODE if public else PRIVATE_MODE
        self.historical, self.private_identity = historical, private_identity
        self.checkpoint_path = Path(checkpoint_path) if checkpoint_path else self.state / "RESUME_STATE.json"
        self.local_checkpoint = self.state / "RESUME_STATE.json"
        self.preservation_binding = preservation_binding
        require(type(cases) is list and 0 < len(cases) <= 128
                and len(cases) == len(wire_cases) == len(expected), "CompleteClosedCaseInventoryRequired")
        identifiers = [case["case_id"] for case in cases]
        require(len(set(identifiers)) == len(identifiers) and all(
            type(name) is str and re.fullmatch(r"[A-Za-z0-9_-]{1,160}", name) is not None
            for name in identifiers), "UniqueSafeCaseIdentitiesRequired")
        self.corpus_digest = digest(cases)
        self.freeze = {"schemaVersion": 1, "milestone": "M2bt", "classification": self.mode,
                       "baseSha": BASE, "sourceFingerprintSha256": self.fingerprint,
                       "sourceBindings": source_join["sourceBindings"], "runnerBinding": self.runner_binding,
                       "corpusSha256": self.corpus_digest, "cases": cases, "wireCases": wire_cases,
                       "independentExpected": expected, "expectedSha256": digest(expected),
                       "programIdentity": program_identity, "programSourceKind": program["kind"],
                       "independentOracleSourceBindings": [row for row in source_join["sourceBindings"]
                           if row["path"].endswith("/oracle.py") or row["path"].endswith("/synthetic_execution_protocol_oracle.py")],
                       "privateSourceIdentity": private_identity, "historicalObligations": historical,
                       "expectedFrozenBeforeRuntime": True, "firmwareReady": False}
        self.records = []

    def cache_path(self, index):
        return self.state / "cases" / f"{index:04d}-{self.cases[index]['case_id']}.json"

    def checkpoint(self, phase, *, active=None, blocker=None):
        value = {"schemaVersion": 1, "milestone": "M2bt", "branch": BRANCH, "baseSha": BASE,
                 "sourceFingerprint": self.fingerprint, "corpusSha256": self.corpus_digest,
                 "executionMode": self.mode, "currentPhase": phase, "phase": phase,
                 "completedSteps": ["SOURCE_VERIFIED", "PRE_RUNTIME_FREEZE"],
                 "lastCompletedCaseId": self.records[-1]["case"]["case_id"] if self.records else None,
                 "canonicalRecordHashes": [digest(record) for record in self.records],
                 "pendingCases": [case["case_id"] for case in self.cases[len(self.records):]],
                 "activeProcess": active, "activeProcessIdentity": active,
                 "ciRunId": None, "finalPushedSha": None,
                 "blockers": [blocker] if blocker else [],
                 "nextAction": "FinalQAAndDelivery" if phase == "ORACLE_COMPARISON" else "ResumeFirstUncompletedCase",
                 "outputDirectory": str(self.output), "stateDirectory": str(self.state),
                 "updatedUtc": datetime.now(timezone.utc).isoformat()}
        if phase == "ORACLE_COMPARISON":
            value["completedSteps"] += ["ROM_EXECUTION", "ORACLE_COMPARISON"]
        if self.preservation_binding is not None:
            value["preservationException"] = self.preservation_binding
        atomic_json(self.local_checkpoint, value, replace=True)
        if self.checkpoint_path != self.local_checkpoint:
            retained = read_checkpoint(self.checkpoint_path) if self.checkpoint_path.exists() else {}
            require(self.preservation_binding is None
                    or retained.get("preservationException") == self.preservation_binding,
                    "PreservationExceptionCheckpointBindingChanged")
            merged = {**retained, **value}
            merged["completedSteps"] = list(dict.fromkeys(retained.get("completedSteps", []) + value["completedSteps"]))
            for name in ("ciRunId", "finalPushedSha"):
                if retained.get(name) is not None:
                    merged[name] = retained[name]
            merged["localOriginalRomExecutions"] = len(self.records) if not self.public else retained.get("localOriginalRomExecutions", 0)
            merged["status"] = "BLOCKED" if blocker else "RUNTIME_VERIFIED" if phase == "ORACLE_COMPARISON" else "RUNTIME_IN_PROGRESS"
            atomic_json(self.checkpoint_path, merged, replace=True)

    def check_record(self, index, record):
        require(type(record) is dict and set(record) == {
            "schemaVersion", "caseIndex", "case", "wireCase", "expected", "programAdmission", "actual", "comparison"},
            "CompleteCanonicalCaseRecordRequired")
        require(record["schemaVersion"] == 1 and record["caseIndex"] == index
                and record["case"] == self.cases[index] and record["wireCase"] == self.wire_cases[index]
                and record["expected"] == self.expected[index], "CachedCaseOrExpectedMismatch")
        verify_ack(record["programAdmission"], self.program_identity, self.public)
        comparison = self.compare(self.cases[index], record["actual"], program_identity=self.program_identity)
        require(comparison["passed"] is True and comparison["expected"] == self.expected[index]
                and comparison["comparison"] == record["comparison"], "CachedIndependentComparisonMismatch")

    def check_transport(self, transport, record):
        require(type(transport) is dict and transport.get("runnerExitCode") == 0
                and transport.get("timedOut") is False and transport.get("oneRunnerProcessOneCase") is True
                and transport.get("caseId") == record["case"]["case_id"], "CompleteSuccessfulRuntimeReceiptRequired")
        for key in ("stdout", "stderr"):
            row = transport[key]
            path = Path(row["path"])
            require(path.resolve().is_relative_to(self.state) and path == path.resolve()
                    and file_binding(path) == row, "ActualTransportEvidenceChangedOrEscapedState")
        require(transport["stderr"]["bytes"] == 0 and transport["stdout"]["bytes"] <= MAX_RESPONSE,
                "BoundedSuccessfulTransportRequired")
        raw = Path(transport["stdout"]["path"]).read_bytes()
        require(raw.endswith(b"\n") and len(raw.splitlines()) == 2, "TwoCompleteRunnerRecordsRequired")
        ack, actual = (strict_json(line) for line in raw.splitlines())
        require(ack == record["programAdmission"] and actual == record["actual"],
                "CanonicalCaseDiffersFromActualRuntimeStdout")

    def prepare(self):
        self.output.mkdir(parents=True, exist_ok=True)
        self.state.mkdir(parents=True, exist_ok=True)
        existing = {path.name for path in self.output.iterdir()}
        require(existing <= ARTIFACT_NAMES, "UnexpectedArtifactDirectoryMember")
        failure = self.state / "first-mismatch.json"
        require(not failure.exists(), "PreservedFirstMismatchBlocksPositiveAttestation")
        previous = None
        if self.checkpoint_path != self.local_checkpoint and self.checkpoint_path.exists():
            global_state = read_checkpoint(self.checkpoint_path)
            refuse_active(global_state.get("activeProcess") or global_state.get("activeProcessIdentity"))
            require(not global_state.get("canonicalRecordHashes")
                    or global_state.get("outputDirectory") == str(self.output),
                    "ExistingPrivateRuntimeScopeCannotBeReplaced")
        if self.local_checkpoint.exists():
            previous = read_checkpoint(self.local_checkpoint, fingerprint=self.fingerprint,
                                       corpus_sha256=self.corpus_digest)
            refuse_active(previous.get("activeProcess"))
        self.fence()
        source_joins_equal(self.join, self.source_supplier())
        join_path = self.output / "sourcejoin.json"
        if join_path.exists():
            source_joins_equal(self.join, read_json(join_path))
        else:
            atomic_json(join_path, self.join)
        frozen_path = self.output / "pre-runtime-freeze.json"
        if frozen_path.exists():
            require(read_json(frozen_path) == self.freeze, "ImmutablePreRuntimeFreezeMismatch")
        else:
            require(not any((self.state / "cases").glob("*.json")), "CaseObservationsWithoutPreRuntimeFreeze")
            atomic_json(frozen_path, self.freeze)
        paths = set((self.state / "cases").glob("*.json"))
        expected_paths = {self.cache_path(index) for index in range(len(self.cases))}
        require(paths <= expected_paths, "UnknownCachedCaseRecord")
        gap = False
        for index in range(len(self.cases)):
            path = self.cache_path(index)
            if not path.exists():
                gap = True
                continue
            require(not gap, "NonprefixCachedObservations")
            cached = read_json(path)
            require(type(cached) is dict and set(cached) == {
                "schemaVersion", "milestone", "sourceFingerprint", "corpusSha256",
                "record", "recordSha256", "transport"} and cached["schemaVersion"] == 1
                and cached["milestone"] == "M2bt", "ClosedCachedObservationReceiptRequired")
            require(cached["sourceFingerprint"] == self.fingerprint and cached["corpusSha256"] == self.corpus_digest
                    and cached["recordSha256"] == digest(cached["record"]), "CachedObservationIdentityMismatch")
            self.check_record(index, cached["record"])
            self.check_transport(cached["transport"], cached["record"])
            self.records.append(cached["record"])
        if previous is not None:
            hashes = previous["canonicalRecordHashes"]
            require(type(hashes) is list and hashes == [digest(record) for record in self.records[:len(hashes)]]
                    and 0 <= len(self.records) - len(hashes) <= 1,
                    "CheckpointCompletedObservationsMissingOrChanged")
            last = self.records[len(hashes) - 1]["case"]["case_id"] if hashes else None
            require(previous["lastCompletedCaseId"] == last, "CheckpointLastCaseIdentityMismatch")
        if (self.output / "canonical.jsonl.gz").exists() or (self.output / "summary.json").exists():
            require(len(self.records) == len(self.cases), "FinalArtifactWithoutCompleteActualObservations")
        self.checkpoint("ROM_EXECUTION")

    def run(self):
        self.prepare()
        resumed = len(self.records)
        for index in range(resumed, len(self.cases)):
            case, wire = self.cases[index], self.wire_cases[index]
            attempt = self.state / "attempts" / (case["case_id"] + "-" + uuid.uuid4().hex)
            active = {"controller": process_identity(os.getpid()), "child": None,
                      "caseId": case["case_id"], "attempt": str(attempt)}
            self.checkpoint("ROM_EXECUTION", active=active)
            def child_started(identity):
                active["child"] = identity
                self.checkpoint("ROM_EXECUTION", active=active)
            ack = actual = transport = None
            try:
                require(file_binding(self.runner) == self.runner_binding, "RunnerChangedAfterFreeze")
                ack, actual, transport = self.executor(self.runner, self.program, wire, attempt, child_started)
                verify_ack(ack, self.program_identity, self.public)
                compared = self.compare(case, actual, program_identity=self.program_identity)
                require(compared["passed"] is True and compared["expected"] == self.expected[index],
                        "IndependentOracleChangedAfterRuntime")
                record = {"schemaVersion": 1, "caseIndex": index, "case": case, "wireCase": wire,
                          "expected": self.expected[index], "programAdmission": ack,
                          "actual": actual, "comparison": compared["comparison"]}
                self.check_record(index, record)
                self.check_transport(transport, record)
                cached = {"schemaVersion": 1, "milestone": "M2bt", "sourceFingerprint": self.fingerprint,
                          "corpusSha256": self.corpus_digest, "record": record,
                          "recordSha256": digest(record), "transport": transport}
                atomic_json(self.cache_path(index), cached)
                self.records.append(record)
                self.checkpoint("ROM_EXECUTION")
            except (ValueError, OSError, subprocess.SubprocessError) as error:
                code = error.code if isinstance(error, ExecutionError) else type(error).__name__
                mismatch = {"schemaVersion": 1, "milestone": "M2bt", "caseId": case["case_id"],
                            "caseIndex": index, "sourceFingerprint": self.fingerprint,
                            "corpusSha256": self.corpus_digest, "diagnosticClass": code,
                            "expected": self.expected[index], "attemptDirectory": str(attempt),
                            "detail": str(error)[:4096],
                            "actual": actual, "programAdmission": ack,
                            "passed": False, "expectationsChanged": False}
                atomic_json(self.state / "first-mismatch.json", mismatch)
                self.checkpoint("ROM_EXECUTION", blocker=code)
                raise
        self.fence()
        source_joins_equal(self.join, self.source_supplier())
        require(file_binding(self.runner) == self.runner_binding, "RunnerChangedAcrossRuntime")
        raw = b"".join(canonical(record) for record in self.records)
        require(len(raw) <= MAX_JSON, "BoundedCanonicalStreamRequired")
        canonical_path = self.output / "canonical.jsonl.gz"
        if canonical_path.exists():
            with gzip.open(canonical_path, "rb") as stream:
                retained = stream.read(MAX_JSON + 1)
            require(retained == raw, "RetainedCanonicalBytesMismatch")
        else:
            publish_bytes(canonical_path, gzip.compress(raw, mtime=0))
        # Complete decompression, including EOF/CRC, also checks a newly written container.
        with gzip.open(canonical_path, "rb") as stream:
            require(stream.read(MAX_JSON + 1) == raw, "CanonicalPublicationRoundTripMismatch")
        paths = dict(Counter(case["path"] for case in self.cases))
        summary = {"schemaVersion": 1, "milestone": "M2bt", "passed": True, "classification": self.mode,
                   "sourceFingerprintSha256": self.fingerprint, "corpusSha256": self.corpus_digest,
                   "cases": len(self.records), "paths": paths,
                   "retiredInstructions": sum(case["budget"] for case in self.cases),
                   "firstMismatch": None, "independentOracle": "PASS",
                   "canonicalDecompressedBytes": len(raw), "canonicalSha256": sha256(raw).hexdigest(),
                   "fullActualObservationsRetained": True, "canonicalFieldExclusions": [],
                   "perCaseMachineAndBusContinuity": "ClosedProductionSessionAndActualJournalCompared",
                   "terminalInstructionsRetired": 0, "p2FunctionalReads": 0, "p2FunctionalWrites": 0,
                   "strictEvidenceBoundCases": 0, "newHistoricalNativeWitnesses": 0,
                   "originalRomCaseExecutions": 0 if self.public else len(self.records),
                   "hardwareExecutions": 0, "firmwareBinaryObjectHexCount": 0,
                   "retainedStatuses": list(STATUSES), "firmwareReady": False}
        summary_path = self.output / "summary.json"
        if summary_path.exists():
            require(read_json(summary_path) == summary, "ImmutableSummaryMismatch")
        else:
            atomic_json(summary_path, summary)
        require({path.name for path in self.output.iterdir()} == ARTIFACT_NAMES,
                "ClosedFinalArtifactMembershipRequired")
        self.checkpoint("ORACLE_COMPARISON")
        return {**summary, "resumedCases": resumed, "newProcessExecutionsThisInvocation": len(self.records) - resumed,
                "outputDirectory": str(self.output), "stateDirectory": str(self.state)}


def verify_execution(*, output, runner, public=False, rom=None, profile=None):
    """Actual CLI path; no caller-supplied observations or expected values."""
    from original_rom_execution import admission, binding, corpus, oracle
    output = local_directory(output)
    require(type(public) is bool and ((public and rom is None and profile is None) or
            (not public and rom is not None and profile is not None)), "SeparatePublicAndPrivateAdmissionsRequired")
    source_path = output / "sourcejoin.json"
    supplied_join = read_json(source_path) if source_path.exists() else None
    allow_saved = not public or (supplied_join is not None and bool(supplied_join.get("retainedPhysicalRepresentations")))
    supplier = lambda: binding.working_source_join(allow_saved_physical=allow_saved)
    current = supplier()
    if supplied_join is not None:
        source_joins_equal(supplied_join, current)
    join = supplied_join or current
    from original_rom_execution.contract_validation import validate_contract
    protocol = validate_contract(source_bindings=current["sourceBindings"])
    require(protocol.get("passed") is True and protocol.get("sourceBindingsVerified") is True
            and protocol.get("sourceFingerprintSha256") == current["sourceFingerprintSha256"],
            "ProtocolDeclarationSourceJoinMismatch")
    cases = list(corpus.iter_cases())
    historical = private_identity = None
    preservation_binding = None
    if public:
        program = {"kind": "public_fixture", "schemaVersion": 1}
        program_identity = oracle.public_program_identity()
        source_fence = lambda: True
    else:
        preservation_binding = preservation_exception_context(ROOT / "private/reports/m2bt/RESUME_STATE.json")
        admission.validate_output_directory(output, rom)
        admitted = admission.AdmittedOriginal(rom, profile, output)
        program, private_identity = admitted.program_request(), admitted.private_identity()
        contract = strict_json(admission.M2BS_CONTRACT.read_bytes())
        selected = {str(row["pc"]): sha256(admitted.image.data[row["pc"]:row["pc"] + row["length"]]).hexdigest()
                    for row in contract["instructionExtents"] if row["pc"] in contract["algorithmPcs"]}
        require(len(selected) == 18, "ClosedOriginalInstructionIdentityRequired")
        program_identity = {"program_base": program["segmentBase"],
                            "program_end_exclusive": program["segmentBase"] + len(program["segmentBytes"]),
                            "program_sha256": program["segmentSha256"], "source_binding": program["sourceBinding"],
                            "selected_extent_sha256": selected}
        from original_rom_boundary.context import select_source
        original_profile, _ = admission.load_profile(profile)
        sources = {}
        for key, source_id in (("slots", "m2z-slots"), ("below", "m2z-below")):
            row = original_profile["historical"][key]
            sources[source_id] = select_source(row["path"], source_id, row["sha256"], row["bytes"],
                                               "HistoricalSourceCpuObservations")
        historical = corpus.historical_technical_cases(admitted.report, sources)
        cases += historical["cases"]
        def source_fence():
            admitted.assert_unchanged()
            require(preservation_exception_context(ROOT / "private/reports/m2bt/RESUME_STATE.json")
                    == preservation_binding, "PreservationExceptionChangedAcrossRuntime")
            return True
    kind = "public_fixture" if public else "private"
    expected = [oracle.expected_case(case, program_kind=kind) for case in cases]
    wires = [corpus.wire_case(case, program_kind=kind) for case in cases]
    def compare(case, actual, *, program_identity):
        result = oracle.compare_observation(case, actual, program_kind=kind, program_identity=program_identity)
        if historical is not None:
            obligations = [row for row in historical["obligations"] if case["case_id"] in row["case_ids"]]
            require(len(obligations) <= 1, "HistoricalTechnicalCaseHasMultipleOwners")
            if obligations:
                result["comparison"] = {**result["comparison"], "historicalSubset":
                    oracle.compare_historical_subset(case, actual, obligations[0])}
        return result
    require(len(cases) == (64 if public else 70), "ExactBoundedCorpusRequired")
    checkpoint = None if public else ROOT / "private/reports/m2bt/RESUME_STATE.json"
    return VerificationRun(output=output, runner=runner, source_join=join, source_supplier=supplier,
                           cases=cases, wire_cases=wires, expected=expected, program=program,
                           program_identity=program_identity, compare=compare, public=public,
                           source_fence=source_fence, private_identity=private_identity,
                           historical=historical, checkpoint_path=checkpoint,
                           preservation_binding=preservation_binding).run()
