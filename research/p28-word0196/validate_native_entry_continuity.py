"""M2bu bounded production entry-to-exit execution; private and public separated."""
import argparse
import subprocess
import sys

from native_entry_continuity.checkpoint import canonical
from native_entry_continuity.verify import verify_execution


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--public', action='store_true')
    parser.add_argument('--rom', help='Explicit private verified candidate; never searched')
    parser.add_argument('--profile', help='Explicit existing M2bs source profile')
    parser.add_argument('--output', required=True)
    parser.add_argument('--runner', required=True, help='Already-built required-feature M2bu runner')
    parser.add_argument('--branch-controls', action='store_true', help='Separate two stop-before controls, not32 positives')
    parser.add_argument('--checkpoint', help='Optional explicit global M2bu checkpoint for public local QA')
    args = parser.parse_args()
    try:
        result = verify_execution(output=args.output, runner=args.runner, public=args.public,
                                  rom=args.rom, profile=args.profile, branch_controls=args.branch_controls,
                                  checkpoint_path=args.checkpoint)
        print(canonical(result).decode('ascii'), end='')
        return 0
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        print(canonical({'milestone': 'M2bu', 'passed': False,
                         'diagnosticClass': getattr(error, 'code', type(error).__name__),
                         'retainedActualEvidenceNeverReplaced': True,
                         'firmwareReady': False}).decode('ascii'), end='')
        return 1


if __name__ == '__main__':
    sys.dont_write_bytecode = True
    raise SystemExit(main())
