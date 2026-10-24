"""Closed current M2bu source identity; historical source trees remain frozen."""
from __future__ import annotations

import argparse
from hashlib import sha256
import os
from pathlib import Path
import stat
import sys
import tomllib

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'research/p28-word0196'))
from original_rom_boundary.source_guard import Blob, canonical, contents, git, tree
from original_rom_execution.binding import PHYSICAL_REPRESENTATIONS
from native_entry_continuity.ci_contract import BASE, workflow_projection

BASE_COUNT = 957
BASE_FINGERPRINT = '5467e3f7113979de9fefc61a0f4f4f8680f69a790370dbdaf6c406372dc5f286'
PACKAGE = 'research/p28-word0196/native_entry_continuity/'
WORKFLOW = '.github/workflows/build.yml'
MANIFEST = 'rust/p28-slice-runner/Cargo.toml'
NEW_PATHS = frozenset(PACKAGE + name for name in (
    '__init__.py', 'admission.py', 'build_guard.py', 'build_guard_tests.py',
    'checkpoint.py', 'checkpoint_tests.py', 'resume.py', 'resume_tests.py',
    'corpus.py', 'corpus_tests.py', 'oracle.py', 'oracle_tests.py',
    'contract.json', 'contract_validation.py', 'contract_validation_tests.py',
    'source_guard.py', 'source_guard_tests.py', 'verify.py', 'verify_tests.py',
    'ci_contract.py', 'ci_contract_tests.py',
)) | frozenset({
    'research/p28-word0196/validate_native_entry_continuity.py',
    'docs/M2BU_NATIVE_ENTRY_CONTINUITY.md',
    'rust/p28-slice-runner/src/audit_entry_continuity.rs',
    'rust/p28-slice-runner/src/audit_entry_continuity_tests.rs',
    'rust/p28-slice-runner/src/bin/m2bu_entry_continuity.rs',
})
SHARED_PATHS = frozenset({MANIFEST, 'rust/p28-slice-runner/src/audit.rs',
    'rust/p28-slice-runner/src/audit_original_rom.rs', 'rust/p28-slice-runner/src/lib.rs'})
# Filled only after reviewing the actual narrow M2bu diff and rustfmt, before
# final-source runtime. These are NEW review pins, never historical rebasing.
REVIEWED_SHARED_DELTAS = {
    MANIFEST: ('a895447460b84337dd78f255c4e0b1fbce3c240f26bf6afbf3721b1311d735a4',
               '9c57616f43ad122e3e1437fde5e5d124018b097646da482c7c7c120ec478fc4f'),
    'rust/p28-slice-runner/src/audit.rs': (
        '15e5e78bda5db28146daae2df3f7417999af05d6074506730f74498079acf7e1',
        '203025f969795a87bab41debd7f7c8b37d04db910692ba7c977baaabb70ad97a'),
    'rust/p28-slice-runner/src/audit_original_rom.rs': (
        '371f79b04197d6900f5f2dfd11865aeebe4290fb044dd84a6376a121339c743c',
        'a737b6f417e333f03f1a69db5ae23d8be9ec9f0512506bba5b45d557ec98ed78'),
}


def need(condition, code):
    if condition is not True:
        raise ValueError(code)


def rows(blobs):
    return [{'path': name, 'mode': blob.mode, 'bytes': len(blob.data),
             'sha256': sha256(blob.data).hexdigest()} for name, blob in sorted(blobs.items())]


def fingerprint(bindings):
    return sha256(canonical(bindings)).hexdigest()


def validate_manifest(before, after):
    old, current = tomllib.loads(before.decode()), tomllib.loads(after.decode())
    feature = 'p28-word0196-entry-continuity'
    need(current.get('features', {}).get('default') == [], 'NewFeatureMustRemainDefaultOff')
    need(current['features'].pop(feature, None) == ['p28-word0196-original-rom'],
         'ExistingOriginalRomCapabilityRequired')
    expected_bin = {'name': 'm2bu-entry-continuity', 'path': 'src/bin/m2bu_entry_continuity.rs',
                    'required-features': [feature]}
    binaries = current.get('bin', [])
    need(binaries.count(expected_bin) == 1, 'ExactlyOneRequiredFeatureBinary')
    binaries.remove(expected_bin)
    need(current == old, 'OldCargoPackageDependenciesFeaturesOrProfilesChanged')


def compare_source_maps(base, current):
    need(set(current) == set(base) | NEW_PATHS and not (set(base) & NEW_PATHS),
         'ClosedBaseAndNewSourceMembershipRequired')
    changed = []
    for name, previous in base.items():
        actual = current[name]
        need(actual.mode == previous.mode == '100644', 'SourceModeChanged')
        if actual.data == previous.data:
            continue
        changed.append(name)
        if name == WORKFLOW:
            workflow_projection(previous.data, actual.data)
        else:
            pair = (sha256(previous.data).hexdigest(), sha256(actual.data).hexdigest())
            need(name in SHARED_PATHS and REVIEWED_SHARED_DELTAS.get(name) == pair,
                 'UnreviewedSharedOrHistoricalSourceChange:' + name)
    need(MANIFEST in changed and WORKFLOW in changed, 'RequiredClosedFeatureAndWorkflowDeltaMissing')
    validate_manifest(base[MANIFEST].data, current[MANIFEST].data)
    for name in NEW_PATHS:
        need(current[name].mode == '100644' and bool(current[name].data)
             and len(current[name].data) <= 2 * 1024 * 1024, 'BoundedNewTextSourceRequired')
        current[name].data.decode('utf-8', 'strict')
    current_rows = rows(current)
    return {'schemaVersion': 1, 'milestone': 'M2bu', 'passed': True, 'exactBase': BASE,
            'classification': 'ClosedM2buSourceJoin_NotRuntimeOrNativeSchedulingEvidence',
            'sourceBindings': current_rows, 'sourceFingerprintSha256': fingerprint(current_rows),
            'changedBaselinePaths': sorted(changed), 'newPaths': sorted(NEW_PATHS),
            'historicalExpectedFingerprintsRewritten': False, 'firmwareReady': False}


def _regular(path):
    for node in (path, *path.parents):
        if os.path.lexists(node):
            info = node.lstat()
            need(not stat.S_ISLNK(info.st_mode) and not getattr(info, 'st_file_attributes', 0) & 0x400,
                 'ReparseSourcePathRefused')
    need(path.is_file() and path.resolve() == path, 'RegularLocalSourceRequired')


def working_source_join(root=ROOT, *, allow_saved_physical=False):
    root = Path(root).resolve()
    inventory = tree(root, BASE)
    blobs = contents(root, (inventory,))
    base = {name: Blob(mode, blobs[oid]) for name, (mode, oid) in inventory.items()}
    need(len(base) == BASE_COUNT and fingerprint(rows(base)) == BASE_FINGERPRINT,
         'ExactAcceptedM2btBase957Required')
    current, physical = {}, []
    for name in sorted(set(base) | NEW_PATHS):
        path = root / name
        _regular(path)
        need(path.stat().st_size <= 32 * 1024 * 1024, 'BoundedSourceRequired')
        raw = path.read_bytes()
        expected = base.get(name)
        if expected is not None and name not in SHARED_PATHS | {WORKFLOW} and raw != expected.data:
            alternative = (sha256(expected.data).hexdigest(), len(raw), sha256(raw).hexdigest())
            need(allow_saved_physical is True and PHYSICAL_REPRESENTATIONS.get(name) == alternative,
                 'UnchangedBaselineSourceRequired:' + name)
            physical.append({'path': name, 'bytes': len(raw), 'sha256': alternative[2],
                             'rawGitSha256': alternative[0], 'classification': 'RetainedPhysicalXml_NotRustInput'})
            raw = expected.data
        current[name] = Blob('100644', raw)
    result = compare_source_maps(base, current)
    dirty = set(git(root, 'diff', '--name-only', 'HEAD').decode().splitlines())
    need(dirty <= SHARED_PATHS | {WORKFLOW} | NEW_PATHS, 'UnrelatedTrackedChangesRefused')
    owned = {name for name in git(root, 'ls-files', '--others', '--exclude-standard').decode().splitlines()
             if name.startswith(PACKAGE)}
    need(owned <= NEW_PATHS, 'UnexpectedOwnedResearchSource')
    result['retainedPhysicalRepresentations'] = physical
    result['physicalWorkingTreeMatchesRawSourceBindings'] = not physical
    result['baseSourceFingerprintSha256'] = BASE_FINGERPRINT
    return result


def check_git_source(root, expected_head):
    root = Path(root).resolve()
    need(git(root, 'rev-parse', 'HEAD').decode().strip() == expected_head, 'ExactActiveHeadRequired')
    need(git(root, 'merge-base', '--is-ancestor', BASE, expected_head) == b'', 'AcceptedBaseAncestryRequired')
    result = working_source_join(root)
    active = tree(root, expected_head)
    need(set(active) == {row['path'] for row in result['sourceBindings']}, 'CommittedSourceMembershipRequired')
    data = contents(root, (active,))
    committed = {name: Blob(mode, data[oid]) for name, (mode, oid) in active.items()}
    need(rows(committed) == result['sourceBindings'], 'CurrentPhysicalSourcesMustMatchCommittedGit')
    return {**result, 'headSha': expected_head, 'committedSourcesVerified': True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--expected-head', required=True)
    args = parser.parse_args()
    print(canonical(check_git_source(ROOT, args.expected_head)).decode('ascii'))


if __name__ == '__main__':
    main()
