"""Closed current M2by source identity; historical source trees remain frozen."""
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
from native_cal_rt_continuity.ci_contract import BASE, workflow_projection

BASE_COUNT = 1065
BASE_FINGERPRINT = 'd08972f117683eef14336dd929c5700141514f2289416962645ffeb0dc8b0dc0'
PACKAGE = 'research/p28-word0196/native_cal_rt_continuity/'
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
    'research/p28-word0196/validate_native_cal_rt_continuity.py',
    'docs/M2BY_NATIVE_CAL_RT_FRAME_CONTINUITY.md',
    'rust/p28-slice-runner/src/audit_cal_rt_continuity.rs',
    'rust/p28-slice-runner/src/audit_cal_rt_continuity_tests.rs',
    'rust/p28-slice-runner/src/bin/m2by_cal_rt_continuity.rs',
})
SHARED_PATHS = frozenset({MANIFEST, 'rust/p28-slice-runner/src/audit.rs',
    'rust/p28-slice-runner/src/audit_bus.rs', 'rust/p28-slice-runner/src/audit_p2_handoff.rs',
    'rust/p28-slice-runner/src/audit_post_p2_control.rs',
    'rust/p28-slice-runner/src/audit_below_second_p2.rs',
    'research/p28-word0196/native_below_second_p2/resume.py'})
# Root records exact accepted-before/final-after pairs following source review.
# These exact deltas are independently reviewed; no mutable source admits itself.
REVIEWED_SHARED_DELTAS = {
    'research/p28-word0196/native_below_second_p2/resume.py': ('ab844a3728e888ccf835616b3db4a6417fe3244073789d34efe8b5d759de61e3',
        '2d52e6125857b9fc79133cc893c7811fbd2fcc4fb9a6e928eb76a90e1c801b02'),
    'rust/p28-slice-runner/Cargo.toml': ('b7c0a14d80f95401bf55870c274cd0e0d992b7a1b4583b8dfa2abf6f9793293d',
        'b4d2e7d1421b3398967d6242f6990303a1a79107eb05a45ba88bca265ff6466f'),
    'rust/p28-slice-runner/src/audit.rs': ('4a22e4b583bd911844e4f90c0e00008f47b29b5e09c29b0553c9bbfd464bd886',
        'e584996f4cea6d274ece15f6c52f8d837b2d4edc3fc504863fd3c47ce10ea8fe'),
    'rust/p28-slice-runner/src/audit_below_second_p2.rs': ('8477c0f234d89f5175f0087918c7ac63d109d6ca43764d8bdd84aaa5f41071a9',
        '4905e9f5537ac55bd9b9659f18b1e33267406704ea09a7af123537f74ecff489'),
    'rust/p28-slice-runner/src/audit_bus.rs': ('117fa1b2500175a82228ac668e82b1b5c74545ffefd952f052cadcf383ee13fe',
        '781598f9be69b46cf3c4f682ce6b688f038bea4daf928d65597543642689ff8a'),
    'rust/p28-slice-runner/src/audit_p2_handoff.rs': ('807be62587f6243450fe7bc87b10a4c4ff0f540a6eb4babc9d848b9933253471',
        '0406c998576490dc077887ee080ea2fbe4e78d6949c0abe67edc87a2875642f3'),
    'rust/p28-slice-runner/src/audit_post_p2_control.rs': ('634cbefe5142ceb5465f73a65d79ff282fb730766b29952b6538eee1da3e5d8b',
        '957b7f1e4c355028da5fe038bfe8588c4fa39ad467a47435b0da02857377da85'),
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
    feature = 'p28-word0196-cal-rt-continuity'
    need(current.get('features', {}).get('default') == [], 'NewFeatureMustRemainDefaultOff')
    need(current['features'].pop(feature, None) == ['p28-word0196-below-second-p2-continuity'],
         'ExistingEntryContinuityCapabilityRequired')
    expected_bin = {'name': 'm2by-cal-rt-continuity', 'path': 'src/bin/m2by_cal_rt_continuity.rs',
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
    return {'schemaVersion': 1, 'milestone': 'M2by', 'passed': True, 'exactBase': BASE,
            'classification': 'ClosedM2bySourceJoin_NotRuntimeOrNativeSchedulingEvidence',
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
         'ExactAcceptedM2bxBase1065Required')
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
