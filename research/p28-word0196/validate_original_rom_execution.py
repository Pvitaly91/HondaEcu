"""Bounded production execution: explicit private ROM or separate public fixture."""
from __future__ import annotations

import argparse
import subprocess
import sys

from original_rom_execution.checkpoint import canonical
from original_rom_execution.verify import ExecutionError, verify_execution


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--public", action="store_true", help="Only invented, public-safe PROGRAM fixture")
    parser.add_argument("--rom", help="Explicit immutable private original candidate; never searched")
    parser.add_argument("--profile", help="Explicit private verified M2bs source profile")
    parser.add_argument("--output", required=True, help="Four-file result directory; state is adjacent")
    parser.add_argument("--runner", required=True, help="Already-built required-feature production research runner")
    args = parser.parse_args()
    try:
        result = verify_execution(output=args.output, runner=args.runner, public=args.public,
                                  rom=args.rom, profile=args.profile)
        print(canonical(result).decode("ascii"), end="")
        return 0
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        code = error.code if isinstance(error, ExecutionError) else type(error).__name__
        print(canonical({"schemaVersion": 1, "milestone": "M2bt", "passed": False,
                         "diagnosticClass": code, "firmwareReady": False,
                         "retainedActualEvidenceNeverReplaced": True}).decode("ascii"), end="")
        return 1


if __name__ == "__main__":
    sys.dont_write_bytecode = True
    raise SystemExit(main())
