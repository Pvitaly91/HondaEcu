"""Read-only Git classification; only the GitHub-owned output file is written."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import stat
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'research/p28-word0196'))

from original_rom_boundary.source_guard import Blob, canonical, contents, git, tree
from native_branch064c.ci_projection import BASE, classify_changes, full_qa_decision


def classify_git(root, expected_head, approved_new_source_fingerprint):
    """No build, private ROM, local evidence inventory, source write or CPU."""
    try:
        root = Path(root).resolve()
        if re.fullmatch(r'[0-9a-f]{40}', expected_head) is None:
            raise ValueError('ExactHeadRequired')
        if git(root, 'rev-parse', 'HEAD').decode('ascii').strip() != expected_head:
            raise ValueError('WrongActiveHead')
        git(root, 'merge-base', '--is-ancestor', BASE, expected_head)
        before, after = tree(root, BASE), tree(root, expected_head)
        data = contents(root, (before, after))
        baseline = {name: Blob(mode, data[oid]) for name, (mode, oid) in before.items()}
        current = {name: Blob(mode, data[oid]) for name, (mode, oid) in after.items()}
        decision = classify_changes(baseline, current, approved_new_source_fingerprint)
        return {**decision, 'headSha': expected_head}
    except Exception:
        return full_qa_decision('RoutingError_FullHistoricalQaRequired')


def output_text(decision):
    if (type(decision) is not dict or type(decision.get('full_qa')) is not bool
            or type(decision.get('research_only')) is not bool
            or decision['full_qa'] == decision['research_only']):
        raise ValueError('ExactlyOneCiLaneRequired')
    return ('full_qa=' + str(decision['full_qa']).lower() + '\n'
            'research_only=' + str(decision['research_only']).lower() + '\n')


def _output_path(path):
    raw = os.fspath(path)
    if (type(raw) is not str or not raw or '\0' in raw
            or raw.startswith(('//', '\\\\'))
            or any(part in ('.', '..') for part in raw.replace('\\', '/').split('/'))):
        raise ValueError('AbsoluteLocalNontraversalGithubOutputRequired')
    supplied = Path(raw)
    if not supplied.is_absolute():
        raise ValueError('AbsoluteLocalNontraversalGithubOutputRequired')
    try:
        supplied.relative_to(ROOT)
    except ValueError:
        return supplied
    raise ValueError('GithubOutputMustNotAliasCheckoutSource')


def _output_identities(path):
    identities = []
    for index, node in enumerate((path, *path.parents)):
        info = node.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise ValueError('ReparseGithubOutputOrAncestorRefused')
        if index == 0:
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                raise ValueError('ExistingRegularSinglyLinkedGithubOutputRequired')
        elif not stat.S_ISDIR(info.st_mode):
            raise ValueError('RegularGithubOutputParentRequired')
        identities.append((node, info.st_dev, info.st_ino))
    return identities


def write_github_output(path, decision):
    payload = output_text(decision).encode('ascii')
    supplied = _output_path(path)
    owner = os.environ.get('GITHUB_OUTPUT')
    if not owner or supplied != _output_path(owner):
        raise ValueError('OnlyExplicitGithubOwnedOutputPathAllowed')
    before = _output_identities(supplied)
    flags = os.O_WRONLY | os.O_APPEND | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_BINARY', 0)
    descriptor = os.open(supplied, flags)
    try:
        opened = os.fstat(descriptor)
        if (not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1
                or (supplied, opened.st_dev, opened.st_ino) != before[0]
                or _output_identities(supplied) != before):
            raise ValueError('GithubOutputIdentityChangedBeforeAppend')
        offset = 0
        while offset < len(payload):
            written = os.write(descriptor, payload[offset:])
            if written <= 0:
                raise OSError('IncompleteGithubOutputAppend')
            offset += written
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


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
