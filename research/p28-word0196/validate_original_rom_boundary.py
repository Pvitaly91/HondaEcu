"""M2bs explicit-private-input read-only verifier; no ROM execution or loader."""
import argparse
import sys

from original_rom_boundary.verify import (
    BoundaryError, canonical, preflight_outputs, verify_original_rom,
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rom", required=True, help="Explicit private immutable candidate")
    parser.add_argument("--profile", required=True, help="Explicit private source/evidence bindings")
    parser.add_argument("--output", required=True, help="Fresh private JSON evidence path")
    parser.add_argument("--public-output", help="Optional fresh public-safe JSON summary")
    args = parser.parse_args()
    try:
        output_names = [args.output] + ([args.public_output] if args.public_output else [])
        targets = preflight_outputs(args.rom, output_names)
        report = verify_original_rom(args.rom, args.profile)
        for target, value in zip(targets, [report, report["publicSummary"]]):
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as stream:
                stream.write(canonical(value))
        print(canonical({"passed": True, "classification": "LocalOriginalRomReadOnlyVerification",
                         "extentCount": report["extents"]["extentCount"],
                         "ddInterpretationChecks": report["extents"]["ddInterpretationChecks"],
                         "romUnchanged": True, "originalRomExecutions": 0,
                         "firmwareReady": False}).decode("ascii"), end="")
        return 0
    except (BoundaryError, ValueError, OSError) as error:
        code = error.code if isinstance(error, BoundaryError) else type(error).__name__
        print(canonical({"passed": False, "error": code,
                         "originalRomExecutions": 0, "firmwareReady": False}).decode("ascii"), end="")
        return 1


if __name__ == "__main__":
    sys.dont_write_bytecode = True
    raise SystemExit(main())
