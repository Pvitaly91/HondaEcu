"""M2bq source draft: actual executable loader/unknown-operation refusals.

Both controls start a real owned host process after the formal freeze. Neither
may construct the emulated Cpu/Bus. Fixed invented input is stdin-only; the ROM
name deliberately does not identify a real file and the argument guard must
return before any file loader or PROGRAM admission exists.
"""

from hashlib import sha256
from pathlib import Path
import os
import subprocess
import time
from production_composite_common import canonical, require
import production_composite_records as records
from production_composite_stream import file_binding, write_new

IDS = ("external-rom-file-argument", "arbitrary-instruction-command")
SCHEMA = {"classification": "ActualExecutableBoundaryRefusals_SeparateFrom33SessionCapabilities",
          "records": 2, "cpuInstances": 0, "busInstances": 0,
          "semanticRecord": "ExactActualArgvSuffixStdinDigestStdoutStderrExit_NoExcludedFields",
          "rawTransportEvidence": "ActualPidCwdFullArgvExecutableBindingStartEndAndAllRawStreams",
          "externalFilename": "/invented/no-file.rom", "actualFileReadAllowed": False,
          "arbitraryInput": "SingleInventedA5Byte_UnknownOperationNeverAdmitted",
          "positive5470CasesChanged": 0, "automaticRetries": 0}


def command(identity):
    require(identity in IDS, "ClosedExecutableBoundaryIdentity")
    if identity == IDS[0]:
        return ["--rom", "/invented/no-file.rom"], b""
    return [], canonical({"kind": "execute_bytes", "base": 4096, "bytes": [0xA5]}) + b"\n"


def expected_records(root):
    for identity in IDS:
        arguments, incoming = command(identity)
        stdout = "" if identity == IDS[0] else (canonical(records.header(root)) + b"\n").decode("ascii")
        diagnostic = "No path/file/ROM/executor arguments" if identity == IDS[0] else \
            "Unknown operation; arbitrary CPU/ROM loading is not admitted"
        yield {"kind": "negative_process_boundary", "id": identity,
               "classification": "ActualClosedExecutableBoundaryRefusal_NoCpu", "argv_suffix": arguments,
               "stdin_sha256": sha256(incoming).hexdigest(), "stdout": stdout,
               "stderr": "M2BQ_HARNESS_ERROR=" + diagnostic + "\n", "exit_code": 1,
               "actual_process_exit_observed": True, "cpu_instances": 0, "bus_instances": 0,
               "positive_composite_executions": 0, "negative_control_composite_executions": 0,
               "original_rom_executions": 0, "firmware_ready": False}


def observe(executable, root, output):
    for identity in IDS:
        arguments, incoming = command(identity)
        label = "boundary-" + identity
        stdout, stderr = output / (label + ".stdout.log"), output / (label + ".stderr.log")
        started = time.time_ns()
        child, code, failure, killed = None, None, None, False
        cleanup_error, exit_observed = None, False
        binary_before = file_binding(executable)
        with stdout.open("xb") as out, stderr.open("xb") as err:
            try:
                child = subprocess.Popen([str(executable), *arguments], cwd=root, stdin=subprocess.PIPE,
                                         stdout=out, stderr=err,
                                         creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
                write_new(output / (label + ".start.json"), {"pid": child.pid, "command": [str(executable), *arguments],
                          "cwd": str(root), "startedUnixNs": started, "executable": binary_before,
                          "stdinSha256": sha256(incoming).hexdigest(), "stdinPersisted": False})
                child.communicate(incoming, timeout=60)
                code, exit_observed = child.returncode, True
            except BaseException as error:
                failure = error
                if child is not None:
                    try:
                        if child.poll() is None:
                            child.kill()
                            killed = True
                        code = child.wait(timeout=10)
                        exit_observed = True
                    except BaseException as error_cleanup:
                        cleanup_error = str(error_cleanup)
        end = {"pid": child.pid if child is not None else None, "exitCode": code,
               "actualExitObserved": exit_observed, "startedUnixNs": started, "finishedUnixNs": time.time_ns(),
               "stdout": file_binding(stdout) if exit_observed else None,
               "stderr": file_binding(stderr) if exit_observed else None,
               "ownedChildKilledAfterFailure": killed, "failure": str(failure) if failure is not None else None,
               "cleanupDiagnostic": cleanup_error, "automaticRetry": False,
               "expectedRefusalIsNotPositiveCpuExecution": True}
        write_new(output / (label + ".end.json"), end)
        if failure is not None:
            raise failure
        require(exit_observed and file_binding(executable) == binary_before, "ActualExecutableBoundaryExitAndBinaryStable")
        require(end["stdout"]["bytes"] <= 131072 and end["stderr"]["bytes"] <= 131072,
                "BoundedClosedExecutableBoundaryStreams")
        actual_stdout, actual_stderr = stdout.read_bytes(), stderr.read_bytes()
        actual = {"kind": "negative_process_boundary", "id": identity,
                         "classification": "ActualClosedExecutableBoundaryRefusal_NoCpu", "argv_suffix": arguments,
                         "stdin_sha256": sha256(incoming).hexdigest(), "stdout": actual_stdout.decode("utf-8", "strict"),
                         "stderr": actual_stderr.decode("utf-8", "strict"), "exit_code": code,
                         "actual_process_exit_observed": exit_observed, "cpu_instances": 0, "bus_instances": 0,
                         "positive_composite_executions": 0, "negative_control_composite_executions": 0,
                         "original_rom_executions": 0, "firmware_ready": False}
        receipt = {"id": identity, "start": file_binding(output / (label + ".start.json")),
                         "end": file_binding(output / (label + ".end.json")),
                         "stdout": end["stdout"], "stderr": end["stderr"]}
        # The caller compares this complete actual row before resuming the
        # generator; an unexpected first refusal stops before the next child.
        yield actual, receipt
