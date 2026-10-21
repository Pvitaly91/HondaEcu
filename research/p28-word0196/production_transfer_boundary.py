"""M2br private draft: actual closed executable ROM/HEX/unknown-op refusals.

Three owned no-target-Cpu processes are run only after formal expected freezing
and building. No real file is named/read, no PROGRAM is supplied, and raw exact
stdout/stderr/exit are compared. Transport PIDs/times remain separate receipts.
"""

from hashlib import sha256
import os
import subprocess
import time
from production_transfer_common import canonical, require
from production_transfer_records import header
from production_transfer_stream import file_binding, write_new

IDS = ("external-rom-file-argument", "external-hex-file-argument", "arbitrary-instruction-command")
SCHEMA = {"records": 3, "classification": "ActualExecutableBoundaryRefusals_NoTargetCpuOrBus",
          "actualFilesRead": 0, "actualRomPayloadSupplied": False, "programAdmissionAttempts": 0,
          "allStdoutStderrAndExitCompared": True, "automaticRetries": 0,
          "negative58SessionControlsSeparate": True, "positive5470Changed": 0}


def command(identity):
    require(identity in IDS, "ClosedExecutableBoundaryIdentity")
    if identity == IDS[0]:
        return ["--rom", "/invented/no-file.rom"], b""
    if identity == IDS[1]:
        return ["--hex", "/invented/no-file.hex"], b""
    return [], canonical({"kind": "execute_bytes", "base": 4096, "bytes": [0xA5]}) + b"\n"


def expected_records(root):
    for identity in IDS:
        arguments, incoming = command(identity)
        unknown = identity == IDS[2]
        yield {"kind": "negative_process_boundary", "id": identity,
               "classification": "ActualClosedExecutableBoundaryRefusal_NoCpu", "argv_suffix": arguments,
               "stdin_sha256": sha256(incoming).hexdigest(),
               "stdout": (canonical(header(root)) + b"\n").decode("ascii") if unknown else "",
               "stderr": "M2BR_HARNESS_ERROR=" + ("Unknown operation; arbitrary CPU/ROM loading is not admitted" if unknown
                              else "No path/file/ROM/executor arguments") + "\n",
               "exit_code": 1, "actual_process_exit_observed": True,
               "cpu_instances": 0, "bus_instances": 0, "positive_transfer_executions": 0,
               "original_rom_executions": 0, "firmware_ready": False}


def observe(binary, root, output):
    for identity in IDS:
        arguments, incoming = command(identity)
        label = "boundary-" + identity
        stdout, stderr = output / (label + ".stdout.log"), output / (label + ".stderr.log")
        started, child, code, failure, cleanup = time.time_ns(), None, None, None, None
        killed = False
        executable_before = file_binding(binary)
        with stdout.open("xb") as out, stderr.open("xb") as err:
            try:
                child = subprocess.Popen([str(binary), *arguments], cwd=root, stdin=subprocess.PIPE,
                                         stdout=out, stderr=err,
                                         creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
                write_new(output / (label + ".start.json"), {"pid": child.pid, "command": [str(binary), *arguments],
                          "cwd": str(root), "startedUnixNs": started, "executable": executable_before,
                          "stdinSha256": sha256(incoming).hexdigest(), "stdinPersisted": False})
                child.communicate(incoming, timeout=60)
                code = child.returncode
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
        end = {"pid": child.pid if child is not None else None, "exitCode": code,
               "actualExitObserved": code is not None, "startedUnixNs": started, "finishedUnixNs": time.time_ns(),
               "stdout": file_binding(stdout), "stderr": file_binding(stderr), "automaticRetry": False,
               "ownedChildKilledAfterFailure": killed, "failure": repr(failure) if failure is not None else None,
               "cleanupDiagnostic": cleanup, "expectedRefusalIsNotPositiveTargetExecution": True}
        write_new(output / (label + ".end.json"), end)
        if failure is not None:
            raise failure
        require(code is not None and file_binding(binary) == executable_before, "ActualBoundaryExitAndBinaryStable")
        require(end["stdout"]["bytes"] <= 131072 and end["stderr"]["bytes"] <= 131072, "BoundedBoundaryRawLogs")
        actual = {"kind": "negative_process_boundary", "id": identity,
                  "classification": "ActualClosedExecutableBoundaryRefusal_NoCpu", "argv_suffix": arguments,
                  "stdin_sha256": sha256(incoming).hexdigest(), "stdout": stdout.read_bytes().decode("utf-8", "strict"),
                  "stderr": stderr.read_bytes().decode("utf-8", "strict"), "exit_code": code,
                  "actual_process_exit_observed": code is not None, "cpu_instances": 0, "bus_instances": 0,
                  "positive_transfer_executions": 0, "original_rom_executions": 0, "firmware_ready": False}
        yield actual, {"id": identity, "start": file_binding(output / (label + ".start.json")),
                       "end": file_binding(output / (label + ".end.json")), "stdout": end["stdout"], "stderr": end["stderr"]}
