"""M2br private draft: bounded lossless streams and truthful owned children.

No process or output is created on import. PROGRAM commands are ephemeral stdin
only. All setup/failure paths retain honest PID/exit/partial-output facts; no
retry, unrelated-process cleanup, or successful result is inferred from failure.
"""

from hashlib import sha256
import gzip
import os
from pathlib import Path
import queue
import subprocess
import threading
import time
from production_transfer_common import bounded_json, canonical, require
from production_transfer_projection import canonical_row

ROW_LIMIT = 16 * 1024 * 1024
STREAM_LIMIT = 8 * 1024 * 1024 * 1024
CHUNK_BYTES = 1024 * 1024


def file_binding(path):
    path = Path(path)
    require(path.is_file() and not path.is_symlink(), "RegularEvidenceFile")
    before = path.stat()
    digest, size = sha256(), 0
    with path.open("rb") as source:
        while chunk := source.read(CHUNK_BYTES):
            digest.update(chunk)
            size += len(chunk)
    after = path.stat()
    require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
            == (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
            and size == before.st_size, "EvidenceChangedDuringHash")
    return {"bytes": size, "sha256": digest.hexdigest()}


def write_new(path, value):
    with Path(path).open("xb") as output:
        output.write(canonical(value) + b"\n")


class CanonicalWriter:
    def __init__(self, root, path):
        self.root, self.path = Path(root), Path(path)
        self.raw = self.path.open("xb")
        try:
            self.output = gzip.GzipFile(filename="", fileobj=self.raw, mode="wb", mtime=0)
        except BaseException:
            self.raw.close()
            raise
        self.digest, self.pending, self.chunks = sha256(), bytearray(), []
        self.records = self.bytes = self.maximum_row_bytes = 0
        self.receipt = None

    def put(self, actual):
        line = canonical_row(self.root, actual)
        require(len(line) <= ROW_LIMIT and self.bytes + len(line) <= STREAM_LIMIT, "BoundedCompleteCanonicalStream")
        self.output.write(line)
        self.digest.update(line)
        self.pending.extend(line)
        self.records += 1
        self.bytes += len(line)
        self.maximum_row_bytes = max(self.maximum_row_bytes, len(line))
        while len(self.pending) >= CHUNK_BYTES:
            self.chunks.append(sha256(self.pending[:CHUNK_BYTES]).hexdigest())
            del self.pending[:CHUNK_BYTES]

    def close(self):
        if self.receipt is not None:
            return self.receipt
        if self.pending:
            self.chunks.append(sha256(self.pending).hexdigest())
            self.pending.clear()
        try:
            self.output.close()
        finally:
            self.raw.close()
        self.receipt = {"compressed": file_binding(self.path), "decompressedBytes": self.bytes,
                        "records": self.records, "sha256": self.digest.hexdigest(),
                        "chunkBytes": CHUNK_BYTES, "chunkSha256": self.chunks,
                        "maximumRowBytes": self.maximum_row_bytes,
                        "allDeclaredFieldsRetained": True, "platformExclusions": []}
        return self.receipt


def compare_full_stream(left, right):
    before = [file_binding(left), file_binding(right)]
    digest, total, chunks = sha256(), 0, 0
    with gzip.open(left, "rb") as a, gzip.open(right, "rb") as b:
        while True:
            x, y = a.read(CHUNK_BYTES), b.read(CHUNK_BYTES)
            require(total + max(len(x), len(y)) <= STREAM_LIMIT, "BoundedEightGiBFullComparison")
            if x != y:
                offset = next((i for i, pair in enumerate(zip(x, y)) if pair[0] != pair[1]), min(len(x), len(y)))
                raise ValueError("FullCanonicalByteMismatchAt:" + str(total + offset))
            if not x:
                break
            digest.update(x)
            total += len(x)
            chunks += 1
    require(before == [file_binding(left), file_binding(right)], "CompressedSourcesUnchangedAcrossFullEofCrcComparison")
    return {"passed": True, "comparison": "FullDecompressedBytes_NoExcludedFields", "bytes": total,
            "sha256": digest.hexdigest(), "chunks": chunks, "chunkBytes": CHUNK_BYTES,
            "fullEofAndCrcChecked": True, "leftCompressed": before[0], "rightCompressed": before[1]}


def read_rows(path):
    total, count = 0, 0
    with gzip.open(path, "rb") as source:
        while line := source.readline(ROW_LIMIT + 1):
            require(len(line) <= ROW_LIMIT and line.endswith(b"\n"), "BoundedCompleteFrozenCanonicalRow")
            total += len(line)
            count += 1
            require(total <= STREAM_LIMIT, "BoundedFrozenCanonicalStream")
            yield bounded_json(line, ROW_LIMIT)


class Harness:
    def __init__(self, command, cwd, output, timeout=60, row_limit=ROW_LIMIT):
        self.command, self.cwd, self.output = list(command), Path(cwd), Path(output)
        self.timeout, self.started = timeout, time.time_ns()
        require(type(row_limit) is int and 0 < row_limit <= ROW_LIMIT, "FrozenRawObservationRowLimit")
        self.row_limit = row_limit
        self.child, self.stdout_thread, self.stderr_thread = None, None, None
        self.rows, self.stopping = queue.Queue(maxsize=2), threading.Event()
        self.stderr_count = 0
        self.stderr_overflow = self.stdout_eof = self.stderr_eof = self.finished = False
        self.read_error = None
        self.response_failure = self.response_retention_error = None
        self.stderr_path = self.output / "runtime.stderr.log"
        self.stderr_file = self.stderr_path.open("xb")
        try:
            self.child = subprocess.Popen(self.command, cwd=self.cwd, stdin=subprocess.PIPE,
                                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                          creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            write_new(self.output / "runtime.start.json", {"pid": self.child.pid, "command": self.command,
                      "cwd": str(self.cwd), "startedUnixNs": self.started,
                      "stdin": "ClosedInventedProgramAndFrozenSeeds_EphemeralNeverLogged"})
            self.stdout_thread = threading.Thread(target=self._stdout, daemon=True)
            self.stderr_thread = threading.Thread(target=self._stderr, daemon=True)
            self.stdout_thread.start()
            self.stderr_thread.start()
        except BaseException:
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

    def _stdout(self):
        try:
            while True:
                line = self.child.stdout.readline(self.row_limit + 1)
                if line == b"":
                    self.stdout_eof = True
                if not self._enqueue(line) or not line or len(line) > self.row_limit:
                    return
        except BaseException as error:
            self._enqueue(error)

    def _stderr(self):
        try:
            while data := self.child.stderr.read(4096):
                self.stderr_count += len(data)
                available = max(0, 131072 - self.stderr_file.tell())
                self.stderr_file.write(data[:available])
                self.stderr_overflow |= len(data) > available
            self.stderr_eof = True
        except BaseException as error:
            self.read_error = repr(error)

    def send(self, command):
        incoming = canonical(command) + b"\n"
        require(len(incoming) <= 262144, "BoundedClosedStdinCommand")
        self.child.stdin.write(incoming)
        self.child.stdin.flush()

    def receive(self):
        try:
            line = self.rows.get(timeout=self.timeout)
        except queue.Empty as error:
            raise ValueError("BoundedActualResponseTimeout") from error
        if isinstance(line, BaseException):
            raise ValueError("ActualStdoutFailure:" + repr(line))
        try:
            require(type(line) is bytes and 0 < len(line) <= self.row_limit and line.endswith(b"\n"),
                    "BoundedCompleteActualObservation")
            return bounded_json(line, self.row_limit)
        except BaseException as error:
            # This is stdout only: never retain the ephemeral PROGRAM stdin.
            # readline reads at most the independently frozen row bound + 1;
            # an overlong response is retained as an explicitly partial prefix,
            # not relabeled as a complete JSON line or successful observation.
            if self.response_failure is None and type(line) is bytes:
                try:
                    prefix = self.output / "runtime.first-invalid-response-prefix.log"
                    with prefix.open("xb") as target:
                        target.write(line)
                    self.response_failure = {
                        "classification": "FirstMalformedActualStdoutResponse_BoundedRawPrefix",
                        "reason": repr(error), "rawPrefixPath": prefix.name,
                        "rawPrefix": file_binding(prefix), "capturedBytes": len(line),
                        "frozenRowLimit": self.row_limit, "readLimitBytes": self.row_limit + 1,
                        "rowBoundExceeded": len(line) > self.row_limit,
                        "capturedPrefixEndsWithLf": line.endswith(b"\n"),
                        "completeFramedResponseCaptured": 0 < len(line) <= self.row_limit and line.endswith(b"\n"),
                        "unreadResponseTailMayExist": len(line) > self.row_limit or not line.endswith(b"\n"),
                        "stdinOrProgramCommandLogged": False, "accepted": False}
                    write_new(self.output / "runtime.first-invalid-response.json", self.response_failure)
                except BaseException as retention_error:
                    self.response_retention_error = repr(retention_error)
            raise

    def _close(self, code, killed, trailing=None):
        self.stopping.set()
        close_error = None
        if self.child is not None and self.child.stdin and not self.child.stdin.closed:
            try:
                self.child.stdin.close()
            except (OSError, ValueError) as error:
                close_error = repr(error)
        for thread in (self.stdout_thread, self.stderr_thread):
            if thread is not None and thread.ident is not None:
                thread.join(timeout=5)
        joined = all(t is None or not t.is_alive() for t in (self.stdout_thread, self.stderr_thread))
        if joined and not self.stderr_file.closed:
            self.stderr_file.close()
        receipt = {"pid": self.child.pid if self.child is not None else None, "exitCode": code,
                   "actualExitObserved": self.child is not None and code is not None,
                   "startedUnixNs": self.started, "finishedUnixNs": time.time_ns(),
                   "stderr": file_binding(self.stderr_path) if joined else None,
                   "stderrBytesObserved": self.stderr_count, "stderrOverflow": self.stderr_overflow,
                   "readFailure": self.read_error, "automaticRetry": False,
                   "firstMalformedResponse": self.response_failure,
                   "malformedResponseRetentionDiagnostic": self.response_retention_error,
                   "stdinCloseDiagnostic": close_error,
                   "ownedChildKilledAfterFailure": killed, "ownedStreamThreadsFinished": joined,
                   "stdoutEofObserved": self.stdout_eof, "stderrEofObserved": self.stderr_eof,
                   "trailingStdoutWasEof": trailing == b"" if trailing is not None else None}
        if not (self.output / "runtime.end.json").exists():
            write_new(self.output / "runtime.end.json", receipt)
        self.finished = joined
        return receipt

    def finish(self):
        self.child.stdin.close()
        code = self.child.wait(timeout=self.timeout)
        trailing = self.rows.get(timeout=5)
        receipt = self._close(code, False, trailing)
        require(code == 0 and trailing == b"" and receipt["ownedStreamThreadsFinished"]
                and self.stdout_eof and self.stderr_eof and not self.stderr_overflow
                and self.stderr_count == 0 and self.read_error is None
                and receipt["stdinCloseDiagnostic"] is None, "ActualSuccessfulOwnedHarnessExit")
        return receipt

    def abort(self):
        if self.finished:
            return
        killed, code, cleanup_error = False, None, None
        try:
            if self.child is not None:
                if self.child.poll() is None:
                    self.child.kill()
                    killed = True
                code = self.child.wait(timeout=10)
        except BaseException as error:
            cleanup_error = repr(error)
        receipt = self._close(code, killed)
        receipt.update({"cleanupDiagnostic": cleanup_error, "acceptance": False})
        if not (self.output / "runtime.failure.json").exists():
            write_new(self.output / "runtime.failure.json", receipt)


def native_build(root, target, output):
    command = ["cargo", "+1.85.1", "build", "--locked", "--offline", "--release", "--jobs", "1",
               "--manifest-path", "research/p28-word0196/rust-production-transfer/Cargo.toml", "--target-dir", str(target)]
    stdout, stderr = output / "build.stdout.log", output / "build.stderr.log"
    started, child, code, failure, cleanup = time.time_ns(), None, None, None, None
    killed = False
    with stdout.open("xb") as out, stderr.open("xb") as err:
        try:
            child = subprocess.Popen(command, cwd=root, stdout=out, stderr=err,
                                     creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            write_new(output / "build.start.json", {"pid": child.pid, "command": command,
                      "cwd": str(root), "startedUnixNs": started})
            code = child.wait(timeout=1800)
        except BaseException as error:
            failure = error
            if child is not None:
                try:
                    if child.poll() is None:
                        child.kill()
                        killed = True
                    code = child.wait(timeout=10)
                except BaseException as cleanup_error:
                    cleanup = repr(cleanup_error)
    result = {"pid": child.pid if child is not None else None, "exitCode": code,
              "actualExitObserved": code is not None, "startedUnixNs": started, "finishedUnixNs": time.time_ns(),
              "stdout": file_binding(stdout), "stderr": file_binding(stderr), "automaticRetry": False,
              "ownedCargoKilledAfterFailure": killed, "originalWaitFailure": repr(failure) if failure is not None else None,
              "cleanupDiagnostic": cleanup,
              "descendantCleanup": "NotEstablishedAfterInterruptedCargo" if failure is not None else "CargoExitedNormally"}
    write_new(output / "build.end.json", result)
    if failure is not None:
        raise failure
    require(code == 0, "ActualLockedOfflineTransferHarnessBuild")
    binary = Path(target) / "release" / ("m2br-production-transfer.exe" if os.name == "nt" else "m2br-production-transfer")
    require(binary.is_file(), "ActualOwnedTransferExecutable")
    return binary, result
