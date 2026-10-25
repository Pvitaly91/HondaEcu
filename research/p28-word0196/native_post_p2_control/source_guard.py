"""Closed current M2bw source identity; historical source trees remain frozen."""
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
from native_post_p2_control.ci_contract import BASE, workflow_projection

BASE_COUNT = 1011
BASE_FINGERPRINT = '372ad605911fe7a98fdc9e2c46121d097b411dc1419abd01e6e575e69429cc1a'
PACKAGE = 'research/p28-word0196/native_post_p2_control/'
WORKFLOW = '.github/workflows/build.yml'
MANIFEST = 'rust/p28-slice-runner/Cargo.toml'
NEW_PATHS = frozenset(PACKAGE + name for name in (
    '__init__.py', 'admission.py', 'admission_tests.py', 'build_guard.py', 'build_guard_tests.py',
    'checkpoint.py', 'checkpoint_tests.py', 'resume.py', 'resume_tests.py',
    'corpus.py', 'corpus_tests.py', 'oracle.py', 'oracle_tests.py',
    'contract.json', 'contract_validation.py', 'contract_validation_tests.py',
    'source_guard.py', 'source_guard_tests.py', 'verify.py', 'verify_tests.py',
    'ci_contract.py', 'ci_contract_tests.py',
)) | frozenset({
    'research/p28-word0196/validate_native_post_p2_control.py',
    'docs/M2BW_NATIVE_POST_P2_CONTROL_CONTINUITY.md',
    'rust/p28-slice-runner/src/audit_post_p2_control.rs',
    'rust/p28-slice-runner/src/audit_post_p2_control_tests.rs',
    'rust/p28-slice-runner/src/bin/m2bw_post_p2_control.rs',
})
SHARED_PATHS = frozenset({MANIFEST, 'rust/p28-slice-runner/src/audit.rs',
    'rust/p28-slice-runner/src/audit_bus.rs', 'rust/p28-slice-runner/src/bus.rs',
    'rust/p28-slice-runner/src/audit_entry_continuity.rs',
    'rust/p28-slice-runner/src/audit_p2_handoff.rs'})
# New M2bw review pins, after source review/rustfmt/targeted Rust QA and before
# final-source freeze. Historical source bindings are not rewritten.
REVIEWED_SHARED_DELTAS = {'rust/p28-slice-runner/Cargo.toml': ('f758fce92dcfbf49fb0a3d0237edf8dda89ecde2f589c7f21a25a9406d072ea6', '7505bd01ff0ca47077d8c6cf7af7e11ea8a196a95f97f4a57e7901e950aa8469'), 'rust/p28-slice-runner/src/audit.rs': ('ffba8629ad2cc084cf477298e01dee7d6080e92842a8b8b015815860bf4b5025', '534ef7d9e467b5ce41fff964bf000e66f08d2ddaa2407c87f6ec45a0b048e98b'), 'rust/p28-slice-runner/src/audit_bus.rs': ('a1d41601fb409a4db793879f2fd191470c4da9f218037b1a1767e0f339bc0621', '480acb938dc02e421cbc5ead146c576fa5402a4949a889dc4ec60aec383cb36b'), 'rust/p28-slice-runner/src/audit_p2_handoff.rs': ('6ab31ceb6bfa1999fc6dc3f932107a05cc1fe513efb2e2a2faa208e0183d67f9', '91bbc95e012378ff9fce020ccca08c2c87f09ef879f222bc3fc03fe9ae29b8bf'), 'rust/p28-slice-runner/src/bus.rs': ('3559c1cce62d9c22020f0c16a1ba71db0574b63904544d6e2a4165345851b732', 'd9613111c216bc9767c09c60b96d668567c24f66b6772423dcc1ecfc18f15467')}


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
    feature = 'p28-word0196-post-p2-control'
    need(current.get('features', {}).get('default') == [], 'NewFeatureMustRemainDefaultOff')
    need(current['features'].pop(feature, None) == ['p28-word0196-p2-handoff'],
         'ExistingEntryContinuityCapabilityRequired')
    expected_bin = {'name': 'm2bw-post-p2-control', 'path': 'src/bin/m2bw_post_p2_control.rs',
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
    return {'schemaVersion': 1, 'milestone': 'M2bw', 'passed': True, 'exactBase': BASE,
            'classification': 'ClosedM2bwSourceJoin_NotRuntimeOrNativeSchedulingEvidence',
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
         'ExactAcceptedM2bvBase1011Required')
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
