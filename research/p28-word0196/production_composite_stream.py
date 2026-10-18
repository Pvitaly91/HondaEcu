"""M2bq source draft: bounded streaming evidence and owned child transport.

No child is started by import. PROGRAM commands are stdin-only, deliberately
never logged. Canonical rows are lossless projections of complete observations.
"""

from hashlib import sha256
import gzip
import os
from pathlib import Path
import queue
import subprocess
import threading
import time
from production_composite_common import bounded_json, canonical, require
from production_composite_projection import canonical_row

ROW_LIMIT = 2 * 1024 * 1024
STREAM_LIMIT = 8 * 1024 * 1024 * 1024
CHUNK_BYTES = 1024 * 1024


def file_binding(path):
    path = Path(path)
    require(path.is_file() and not path.is_symlink(), "RegularOwnedEvidenceFile")
    before = path.stat()
    digest, size = sha256(), 0
    with path.open("rb") as source:
        while chunk := source.read(CHUNK_BYTES):
            size += len(chunk)
            digest.update(chunk)
    after = path.stat()
    require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
            == (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
            and size == before.st_size, "OwnedEvidenceFileChangedDuringHash")
    return {"bytes": size, "sha256": digest.hexdigest()}


def write_new(path, value):
    with Path(path).open("xb") as output:
        output.write(canonical(value) + b"\n")


class CanonicalWriter:
    def __init__(self, path):
        self.path = Path(path)
        self.raw = self.path.open("xb")
        try:
            self.output = gzip.GzipFile(filename="", mode="wb", fileobj=self.raw, mtime=0)
        except BaseException:
            self.raw.close()
            raise
        self.digest = sha256()
        self.bytes = self.records = 0
        self.pending = bytearray()
        self.chunks = []
        self.closed_receipt = None

    def put(self, actual):
        data = canonical_row(actual)
        require(len(data) <= ROW_LIMIT and self.bytes + len(data) <= STREAM_LIMIT, "BoundedCanonicalStream")
        self.output.write(data)
        self.digest.update(data)
        self.bytes += len(data)
        self.records += 1
        self.pending.extend(data)
        while len(self.pending) >= CHUNK_BYTES:
            self.chunks.append(sha256(self.pending[:CHUNK_BYTES]).hexdigest())
            del self.pending[:CHUNK_BYTES]

    def close(self):
        if self.closed_receipt is not None:
            return self.closed_receipt
        if self.pending:
            self.chunks.append(sha256(self.pending).hexdigest())
            self.pending.clear()
        self.output.close()
        self.raw.close()
        self.closed_receipt = {"compressed": file_binding(self.path), "decompressedBytes": self.bytes,
                               "records": self.records, "sha256": self.digest.hexdigest(),
                               "chunkBytes": CHUNK_BYTES, "chunkSha256": self.chunks,
                               "allDeclaredFieldsRetained": True, "platformExclusions": []}
        return self.closed_receipt


def compare_full_stream(left, right):
    """All decompressed bytes, full EOF/CRC, exact chunk/tail comparison.

    Equality is not inferred from matching hashes. A mismatch is retained at
    the exact first byte and the caller must refuse acceptance immediately.
    """
    left_before, right_before = file_binding(left), file_binding(right)
    left_digest, right_digest = sha256(), sha256()
    size = chunks = 0
    with gzip.open(left, "rb") as a, gzip.open(right, "rb") as b:
        while True:
            x, y = a.read(CHUNK_BYTES), b.read(CHUNK_BYTES)
            require(size + max(len(x), len(y)) <= STREAM_LIMIT, "BoundedFullCanonicalComparison")
            left_digest.update(x)
            right_digest.update(y)
            if x != y:
                offset = next((index for index, pair in enumerate(zip(x, y)) if pair[0] != pair[1]), min(len(x), len(y)))
                raise ValueError("FullCanonicalByteMismatchAt:" + str(size + offset))
            if not x:
                break
            size += len(x)
            chunks += 1
    require(left_digest.digest() == right_digest.digest(), "AdditionalWholeStreamDigestEquality")
    require(file_binding(left) == left_before and file_binding(right) == right_before,
            "CompressedStreamsUnchangedAcrossFullByteComparison")
    return {"passed": True, "comparison": "FullDecompressedBytes_NoExcludedFields", "bytes": size,
            "sha256": left_digest.hexdigest(), "chunks": chunks, "chunkBytes": CHUNK_BYTES,
            "fullEofAndCrcChecked": True, "leftCompressed": left_before, "rightCompressed": right_before}


class Harness:
    """One owned research process, bounded request/response, no retries.

    Stderr is drained by a dedicated thread to avoid pipe deadlock. Only this
    started child PID is cleaned up; no unrelated process is searched/killed.
    No fixture/PROGRAM command bytes are ever written to a receipt.
    """
    def __init__(self, command, cwd, output, timeout=60):
        self.command, self.cwd, self.output = list(command), Path(cwd), Path(output)
        self.timeout = timeout
        self.started = time.time_ns()
        self.child = None
        self.rows = queue.Queue(maxsize=2)
        self.stderr_count = 0
        self.stderr_overflow = False
        self.failure = None
        self.finished = False
        self.stopping = threading.Event()
        self.stdout_thread = self.stderr_thread = None
        self.stdout_eof = self.stderr_eof = False
        self.stderr_path = self.output / "runtime.stderr.log"
        self.stderr_file = self.stderr_path.open("xb")
        try:
            self.child = subprocess.Popen(self.command, cwd=self.cwd, stdin=subprocess.PIPE,
                                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                          creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            write_new(self.output / "runtime.start.json", {"pid": self.child.pid, "command": self.command,
                      "cwd": str(self.cwd), "startedUnixNs": self.started,
                      "stdin": "EphemeralActualM2bjProgramAndFrozenInventedSeeds_NotLogged"})
            self.stdout_thread = threading.Thread(target=self._read_stdout, daemon=True)
            self.stderr_thread = threading.Thread(target=self._read_stderr, daemon=True)
            self.stdout_thread.start()
            self.stderr_thread.start()
        except BaseException:
            # __init__ has not returned; the caller cannot own/abort this child
            # yet, so setup failure MUST perform its own truthful cleanup.
            self.abort()
            raise

    def _enqueue(self, item):
        while not self.stopping.is_set():
            try:
                self.rows.put(item, timeout=0.1)
                return True
            except queue.Full:
                pass
        return False

    def _read_stdout(self):
        try:
            while True:
                line = self.child.stdout.readline(ROW_LIMIT + 1)
                if line == b"":
                    self.stdout_eof = True
                if not self._enqueue(line) or not line or len(line) > ROW_LIMIT:
                    return
        except BaseException as error:
            self._enqueue(error)

    def _read_stderr(self):
        try:
            while block := self.child.stderr.read(4096):
                self.stderr_count += len(block)
                remaining = max(0, 131072 - self.stderr_file.tell())
                self.stderr_file.write(block[:remaining])
                if len(block) > remaining:
                    self.stderr_overflow = True
            self.stderr_eof = True
        except BaseException as error:
            self.failure = repr(error)

    def receive(self):
        try:
            line = self.rows.get(timeout=self.timeout)
        except queue.Empty as error:
            raise ValueError("BoundedActualChildResponseTimeout") from error
        if isinstance(line, BaseException):
            raise ValueError("ActualStdoutReadFailure:" + repr(line))
        require(type(line) is bytes and 0 < len(line) <= ROW_LIMIT and line.endswith(b"\n"),
                "BoundedCompleteActualObservationRow")
        return bounded_json(line, ROW_LIMIT)

    def send(self, command):
        value = canonical(command) + b"\n"
        require(len(value) <= 262144, "BoundedClosedHarnessCommand")
        self.child.stdin.write(value)
        self.child.stdin.flush()

    def finish(self):
        self.child.stdin.close()
        code = self.child.wait(timeout=self.timeout)
        trailing = self.rows.get(timeout=5)
        self.stopping.set()
        self.stdout_thread.join(timeout=5)
        self.stderr_thread.join(timeout=5)
        threads_finished = not self.stdout_thread.is_alive() and not self.stderr_thread.is_alive()
        if threads_finished:
            self.stderr_file.close()
        write_new(self.output / "runtime.end.json", {"pid": self.child.pid, "exitCode": code,
                  "startedUnixNs": self.started, "finishedUnixNs": time.time_ns(),
                  "stderr": file_binding(self.stderr_path) if threads_finished else None,
                  "stderrBytesObserved": self.stderr_count,
                  "stderrOverflow": self.stderr_overflow, "readFailure": self.failure,
                  "automaticRetry": False, "actualExitObserved": True,
                  "ownedStreamThreadsFinished": threads_finished,
                  "trailingStdoutWasEof": trailing == b"", "ownedChildKilledAfterFailure": False,
                  "stdoutEofObserved": self.stdout_eof, "stderrEofObserved": self.stderr_eof})
        self.finished = threads_finished
        require(trailing == b"", "NoExtraActualStdoutRecordsAfterSummary")
        require(threads_finished and self.stdout_eof and self.stderr_eof, "OwnedStreamThreadsAndEofFinished")
        require(code == 0 and self.stderr_count == 0 and self.failure is None,
                "ActualHarnessMustExitZeroWithoutStderr")

    def abort(self):
        if self.finished:
            return
        killed = False
        if self.child is not None and self.child.poll() is None:
            self.child.kill()
            killed = True
        code = self.child.wait(timeout=10) if self.child is not None else None
        self.stopping.set()
        if self.child is not None and self.child.stdin and not self.child.stdin.closed:
            self.child.stdin.close()
        for thread in (self.stdout_thread, self.stderr_thread):
            if thread is not None and thread.ident is not None:
                thread.join(timeout=5)
        threads_finished = all(thread is None or not thread.is_alive()
                               for thread in (self.stdout_thread, self.stderr_thread))
        if threads_finished and not self.stderr_file.closed:
            self.stderr_file.close()
        if self.child is not None and not (self.output / "runtime.end.json").exists():
            write_new(self.output / "runtime.end.json", {"pid": self.child.pid, "exitCode": code,
                      "startedUnixNs": self.started, "finishedUnixNs": time.time_ns(),
                      "stderr": file_binding(self.stderr_path) if threads_finished else None,
                      "stderrBytesObserved": self.stderr_count, "stderrOverflow": self.stderr_overflow,
                      "readFailure": self.failure, "automaticRetry": False, "actualExitObserved": True,
                      "ownedStreamThreadsFinished": threads_finished, "ownedChildKilledAfterFailure": killed,
                      "stdoutReaderStarted": self.stdout_thread is not None and self.stdout_thread.ident is not None,
                      "stderrReaderStarted": self.stderr_thread is not None and self.stderr_thread.ident is not None,
                      "stdoutEofObserved": self.stdout_eof, "stderrEofObserved": self.stderr_eof,
                      "acceptance": False})
        failure_path = self.output / "runtime.failure.json"
        if not failure_path.exists():
            write_new(failure_path, {"pid": self.child.pid if self.child is not None else None, "exitCode": code,
                      "ownedChildKilledAfterFailure": killed, "automaticRetry": False,
                      "actualExitObserved": self.child is not None, "ownedStreamThreadsFinished": threads_finished,
                      "acceptance": False})
        self.finished = threads_finished


def native_build(root, target, output):
    command = ["cargo", "+1.85.1", "build", "--locked", "--offline", "--release", "--jobs", "1",
               "--manifest-path", "research/p28-word0196/rust-production-composite/Cargo.toml",
               "--target-dir", str(target)]
    stdout, stderr = output / "build.stdout.log", output / "build.stderr.log"
    started = time.time_ns()
    failure = None
    code_observed = False
    killed = False
    exit_code = None
    child = None
    cleanup_diagnostic = None
    with stdout.open("xb") as out, stderr.open("xb") as err:
        try:
            child = subprocess.Popen(command, cwd=root, stdout=out, stderr=err,
                                     creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            write_new(output / "build.start.json", {"pid": child.pid, "command": command,
                      "cwd": str(root), "startedUnixNs": started})
            exit_code = child.wait(timeout=1800)
            code_observed = True
        except BaseException as error:
            # This command owns cargo but does not assert descendant cleanup.
            # An interruption is a failure, never a retry or successful build.
            failure = error
            if child is not None:
                try:
                    if child.poll() is None:
                        child.kill()
                        killed = True
                    exit_code = child.wait(timeout=10)
                    code_observed = True
                except BaseException as cleanup_error:
                    cleanup_diagnostic = str(cleanup_error)
    result = {"pid": child.pid if child is not None else None, "exitCode": exit_code, "startedUnixNs": started,
              "finishedUnixNs": time.time_ns(), "stdout": file_binding(stdout),
              "stderr": file_binding(stderr), "automaticRetry": False, "actualExitObserved": code_observed,
              "ownedCargoKilledAfterFailure": killed, "originalWaitFailure": str(failure) if failure is not None else None,
              "cleanupDiagnostic": cleanup_diagnostic,
              "descendantCleanup": "NotEstablishedAfterInterruptedCargo" if failure is not None else "CargoExitedNormally"}
    write_new(output / "build.end.json", result)
    if failure is not None:
        raise failure
    require(exit_code == 0, "ActualLockedOfflineCompositeHarnessBuild")
    executable = Path(target) / "release" / ("m2bq-production-composite.exe" if os.name == "nt" else "m2bq-production-composite")
    require(executable.is_file(), "ActualNewOwnedHarnessBinaryMissing")
    return executable, result
