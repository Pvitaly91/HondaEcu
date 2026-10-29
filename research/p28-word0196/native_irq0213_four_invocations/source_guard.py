"""Exact accepted-base source join; never invokes a historical validator.

Only the neutral Git/blob readers and the new pure CI projection are reused.
Three already authenticated physical XML representations remain explicit local
metadata; CI validates raw committed Git bytes without those alternatives.
The fourteen new inputs require a matching literal approval in the workflow.
Changing both that policy and its pin requires explicit review/recertification;
the guard never silently derives a replacement approval from changed code.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import os
from pathlib import Path
import stat
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'research/p28-word0196'))
from original_rom_boundary.source_guard import Blob, canonical, contents, git, tree
from original_rom_execution.binding import PHYSICAL_REPRESENTATIONS
from native_irq0213_four_invocations.ci_projection import (
    BASE, BASE_FINGERPRINT, BASE_SOURCE_COUNT, NEW_PATHS, PACKAGE,
    research_projection, source_rows, new_source_fingerprint,
)
from native_irq0213_four_invocations.ci_contract import workflow_approved_fingerprint

WORKFLOW = '.github/workflows/build.yml'


def need(value, reason):
    if value is not True:
        raise ValueError(reason)


def fingerprint(rows):
    return sha256(canonical(rows)).hexdigest()


def base_source(root=ROOT):
    inventory = tree(root, BASE); blobs = contents(root, (inventory,))
    result = {name: Blob(mode, blobs[oid]) for name, (mode, oid) in inventory.items()}
    need(len(result) == BASE_SOURCE_COUNT and fingerprint(source_rows(result)) == BASE_FINGERPRINT,
         'ExactAcceptedM2cg1209RawSourceRequired')
    return result


def check_new_source_approval(active):
    need(WORKFLOW in active and NEW_PATHS <= set(active), 'WorkflowAndAllFourteenNewSourcesRequired')
    approved = workflow_approved_fingerprint(active[WORKFLOW].data)
    observed = new_source_fingerprint(active)
    need(approved == observed, 'ChangedResearchInputRequiresExplicitWorkflowApprovalRecertification')
    return approved


def compare_source_maps(base, active):
    approved = check_new_source_approval(active)
    result = research_projection(base, active, approved)
    return {**result, 'schemaVersion': 1, 'milestone': 'M2ch',
        'classification': 'ClosedBlockedResearchSourceJoin_NotRuntimeOrProtectedStorageAudit',
        'changedBaselinePaths': [WORKFLOW], 'newPaths': sorted(NEW_PATHS),
        'baseSourceFingerprintSha256': BASE_FINGERPRINT,
        'workflowApprovedNewSourceFingerprintSha256': approved,
        'currentNewSourceFingerprintSha256': new_source_fingerprint(active),
        'literalNewSourceApprovalVerified': True,
        'historicalExpectedFingerprintsRewritten': False,
        'originalBranchExecutionAdmitted': False, 'cpuExecutions': 0, 'firmwareReady': False}


def regular(path):
    for node in (path, *path.parents):
        if os.path.lexists(node):
            value = node.lstat()
            need(not stat.S_ISLNK(value.st_mode) and not getattr(value, 'st_file_attributes', 0) & 0x400,
                 'ReparseSourceRefused')
    need(path.is_file() and path.resolve() == path, 'RegularLocalSourceRequired')


def working_source_join(root=ROOT, *, allow_saved_physical=False):
    root = Path(root).resolve(); base = base_source(root); active, physical = {}, []
    for name in sorted(set(base) | NEW_PATHS):
        path = root / name; regular(path)
        need(path.stat().st_size <= 32 * 1024 ** 2, 'BoundedWorkingSourceRequired')
        raw = path.read_bytes(); previous = base.get(name)
        if previous is not None and name != WORKFLOW and raw != previous.data:
            observed = (sha256(previous.data).hexdigest(), len(raw), sha256(raw).hexdigest())
            need(allow_saved_physical is True and PHYSICAL_REPRESENTATIONS.get(name) == observed,
                 'UnchangedAcceptedSourceRequired:' + name)
            physical.append({'path': name, 'bytes': len(raw), 'sha256': observed[2],
                'rawGitSha256': observed[0], 'classification': 'RetainedPhysicalXml_NotRuntimeInput'})
            raw = previous.data
        active[name] = Blob(previous.mode if previous is not None else '100644', raw)
    result = compare_source_maps(base, active)
    need(set(git(root, 'diff', '--name-only', 'HEAD').decode().splitlines()) <= NEW_PATHS | {WORKFLOW},
         'UnrelatedTrackedSourceChangesRefused')
    owned = {name for name in git(root, 'ls-files', '--others', '--exclude-standard').decode().splitlines()
             if name.startswith(PACKAGE)}
    need(owned <= NEW_PATHS, 'UnknownOwnedResearchPathRefused')
    result.update(retainedPhysicalRepresentations=physical,
        physicalWorkingTreeMatchesRawSourceBindings=not physical)
    return result


def check_git_source(root, expected_head):
    root = Path(root).resolve()
    need(git(root, 'rev-parse', 'HEAD').decode().strip() == expected_head, 'ExactActiveCommitRequired')
    need(git(root, 'merge-base', '--is-ancestor', BASE, expected_head) == b'', 'AcceptedM2cgAncestryRequired')
    result = working_source_join(root)
    inventory = tree(root, expected_head); blobs = contents(root, (inventory,))
    committed = {name: Blob(mode, blobs[oid]) for name, (mode, oid) in inventory.items()}
    need(source_rows(committed) == result['sourceBindings'], 'CompleteRawCommittedAndWorkingSourceEqualityRequired')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--expected-head', required=True)
    args = parser.parse_args()
    import json
    result = check_git_source(ROOT, args.expected_head)
    print(json.dumps({'passed': True, 'sourceFingerprintSha256': result['sourceFingerprintSha256'],
        'sourceCount': len(result['sourceBindings']), 'originalBranchExecutionAdmitted': False}, sort_keys=True))
