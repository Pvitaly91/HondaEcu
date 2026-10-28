"""M2cb read-only raw Git classification; no private evidence or runtime."""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'research/p28-word0196'))

from original_rom_boundary.source_guard import Blob, canonical, contents, git, tree
from native_branch064c.ci_routing import output_text, write_github_output
from native_data011f_011b_ownership.ci_projection import BASE, classify_changes, full_qa_decision


def classify_git(root, expected_head, approved_new_source_fingerprint):
    """Every read/identity error selects inherited full QA; none is run here."""
    try:
        root = Path(root).resolve()
        if type(expected_head) is not str or re.fullmatch(r'[0-9a-f]{40}', expected_head) is None:
            raise ValueError('ExactHeadRequired')
        if git(root, 'rev-parse', 'HEAD').decode('ascii').strip() != expected_head:
            raise ValueError('WrongActiveHead')
        git(root, 'merge-base', '--is-ancestor', BASE, expected_head)
        before, after = tree(root, BASE), tree(root, expected_head)
        data = contents(root, (before, after))
        baseline = {name: Blob(mode, data[oid]) for name, (mode, oid) in before.items()}
        current = {name: Blob(mode, data[oid]) for name, (mode, oid) in after.items()}
        return {**classify_changes(baseline, current, approved_new_source_fingerprint),
                'headSha': expected_head}
    except Exception:
        return full_qa_decision('RoutingError_FullHistoricalQaRequired')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--expected-head', required=True)
    parser.add_argument('--approved-new-source-fingerprint', required=True)
    parser.add_argument('--github-output')
    args = parser.parse_args()
    decision = classify_git(ROOT, args.expected_head, args.approved_new_source_fingerprint)
    if args.github_output is not None:
        write_github_output(args.github_output, decision)
    print(canonical(decision).decode('ascii'))


if __name__ == '__main__':
    main()
