"""Finite M2cl documentary-source overlay; errors retain full historical QA."""
from __future__ import annotations

import argparse
import ast
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import stat
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'research/p28-word0196'))
from original_rom_boundary.source_guard import Blob, canonical, contents, git, tree
from original_rom_execution.binding import PHYSICAL_REPRESENTATIONS
from native_branch064c.ci_routing import write_github_output
from rxready_acknowledgement import ci as inherited
from native_irq0213_four_invocations.ci_projection import source_rows

BASE = '081c9c49f2cda648a6be6c63d87e58c4417bf519'
BASE_COUNT = 1252
BASE_FP = '178cbfdddc7c84a40a1d3e20d64a06ef7c094b48cd7a78109f4befeb309133ba'
BASE_WORKFLOW_SHA = 'bad2e6c2a12a279cad440bc5a7e91aec41ede8b99ab12c39f5afef87b2be0c53'
BASE_APPROVAL = 'ade894431a906d23bc146b90018519d1da818054bc72cf8c740cce804b3ae686'
WORKFLOW = '.github/workflows/build.yml'
PACKAGE = 'research/p28-word0196/ecu_silicon_applicability/'
NEW_PATHS = frozenset(PACKAGE + name for name in (
    '__init__.py', 'contract.json', 'address_map.py', 'provenance.py', 'analysis.py',
    'reference_oracle.py', 'source_tests.py', 'ci.py', 'ci_tests.py',
)) | frozenset({
    'research/p28-word0196/validate_ecu_silicon_applicability.py',
    'docs/M2CL_ACTUAL_ECU_SILICON_APPLICABILITY.md',
})
ROUTER_JOB = inherited.ROUTER_JOB.replace(
    'rxready_acknowledgement/ci.py', 'ecu_silicon_applicability/ci.py'
).replace('__M2CK_APPROVED_NEW_SOURCE_FINGERPRINT__', '__M2CL_APPROVED_NEW_SOURCE_FINGERPRINT__')
STATIC_JOB = inherited.STATIC_JOB.replace(
    'validate_rxready_acknowledgement.py', 'validate_ecu_silicon_applicability.py'
).replace('rxready_acknowledgement', 'ecu_silicon_applicability').replace(
    'rxready-ack-static', 'ecu-silicon-static'
).replace('M2ck', 'M2cl').replace('m2ck-static-evidence', 'm2cl-static-evidence').replace(
    'RX-ready source authentication and acknowledgement regressions',
    'ECU silicon documentary applicability and source regressions')


def need(value, reason):
    if value is not True:
        raise ValueError(reason)


def fingerprint(blobs):
    return sha256(canonical(source_rows(blobs))).hexdigest()


def new_fingerprint(blobs):
    return fingerprint({name: blobs[name] for name in NEW_PATHS})


def approval(raw):
    matches = re.findall(rb'--approved-new-source-fingerprint "([0-9a-f]{64})"', raw)
    need(len(matches) == 1, 'OneLiteralIndependentApprovalRequired')
    return matches[0].decode('ascii')


def make_workflow(base, pin):
    need(type(pin) is str and re.fullmatch('[0-9a-f]{64}', pin) is not None,
         'LiteralReviewedFingerprintRequired')
    need(type(base) is bytes and sha256(base).hexdigest() == BASE_WORKFLOW_SHA,
         'ExactM2ckWorkflowRequired')
    need(inherited.approval(base) == BASE_APPROVAL,
         'InheritedM2ckApprovalMustRemainFrozen')
    old = inherited.ROUTER_JOB.replace('__M2CK_APPROVED_NEW_SOURCE_FINGERPRINT__', BASE_APPROVAL) + inherited.STATIC_JOB
    new = ROUTER_JOB.replace('__M2CL_APPROVED_NEW_SOURCE_FINGERPRINT__', pin) + STATIC_JOB
    need(base.count(old.encode()) == 1, 'ExactInheritedBlocksRequired')
    return base.replace(old.encode(), new.encode(), 1)


def projection(base, active, pin):
    need(type(base) is dict and type(active) is dict, 'CompleteSourceMapsRequired')
    need(len(base) == BASE_COUNT and fingerprint(base) == BASE_FP, 'Exact1252M2ckRawSourceRequired')
    need(set(active) == set(base) | NEW_PATHS and not set(base) & NEW_PATHS,
         'FiniteElevenNewPathsRequired')
    for name, previous in base.items():
        if name != WORKFLOW:
            need(active[name] == previous, 'InheritedSourceChanged_FullQaRequired')
    need(new_fingerprint(active) == pin, 'NewSourceNotIndependentlyApproved')
    need(active[WORKFLOW].mode == base[WORKFLOW].mode
         and active[WORKFLOW].data == make_workflow(base[WORKFLOW].data, pin),
         'UnreviewedWorkflowOrHistoricalLaneChange')
    for name in NEW_PATHS:
        blob = active[name]
        need(blob.mode == '100644' and 0 < len(blob.data) < 1024 * 1024
             and b'\0' not in blob.data, 'BoundedRegularResearchTextRequired')
        text = blob.data.decode('utf-8', 'strict')
        if name.endswith('.py'):
            ast.parse(text, filename=name)
        elif name.endswith('.json'):
            need(type(json.loads(text)) is dict, 'ContractObjectRequired')
    rows = source_rows(active)
    return {'passed': True, 'classification': 'EcuSiliconDocumentaryApplicability_NotHardwareObservation',
            'exactBase': BASE, 'sourceBindings': rows,
            'sourceFingerprintSha256': sha256(canonical(rows)).hexdigest(),
            'approvedNewSourceFingerprintSha256': pin, 'unchangedBaseFiles': BASE_COUNT - 1,
            'newPublicPaths': sorted(NEW_PATHS), 'historicalJobsNotRun': 17,
            'targetCpuExecutions': 0, 'firmwareReady': False}


def full_qa(reason):
    return {'full_qa': True, 'research_only': False, 'reason': reason,
            'historicalRequiredJobCount': 17, 'targetCpuExecutions': 0, 'firmwareReady': False}


def classify(base, active, pin):
    try:
        p = projection(base, active, pin)
        return {**full_qa('ExactReviewedEcuSiliconDocumentaryRefinement'), 'full_qa': False,
                'research_only': True, 'sourceFingerprintSha256': p['sourceFingerprintSha256']}
    except Exception:
        return full_qa('UnknownRuntimeOrUnreviewedChange_FullHistoricalQaRequired')


def git_maps(root=ROOT, expected_head=BASE):
    need(re.fullmatch('[0-9a-f]{40}', expected_head or '') is not None, 'ExactHeadRequired')
    need(git(root, 'rev-parse', 'HEAD').decode().strip() == expected_head, 'WrongActiveHead')
    git(root, 'merge-base', '--is-ancestor', BASE, expected_head)
    before, after = tree(root, BASE), tree(root, expected_head)
    blobs = contents(root, (before, after))
    maps = [{n: Blob(mode, blobs[oid]) for n, (mode, oid) in m.items()} for m in (before, after)]
    return maps


def regular(path):
    for p in (path, *path.parents):
        if os.path.lexists(p):
            st = p.lstat()
            need(not stat.S_ISLNK(st.st_mode) and not getattr(st, 'st_file_attributes', 0) & 0x400,
                 'ReparsePathRefused')


def guard(expected_head):
    base, committed = git_maps(expected_head=expected_head)
    active, physical = {}, []
    for name in sorted(set(base) | NEW_PATHS):
        p = ROOT / name
        regular(p)
        raw = p.read_bytes()
        previous = base.get(name)
        if previous and name != WORKFLOW and raw != previous.data:
            observed = (sha256(previous.data).hexdigest(), len(raw), sha256(raw).hexdigest())
            need(PHYSICAL_REPRESENTATIONS.get(name) == observed, 'WorkingInheritedSourceChanged')
            physical.append(name)
            raw = previous.data
        active[name] = Blob(previous.mode if previous else '100644', raw)
    p = projection(base, active, approval(active[WORKFLOW].data))
    tracked = set(git(ROOT, 'diff', '--name-only', 'HEAD').decode().splitlines())
    need(tracked <= NEW_PATHS | {WORKFLOW}, 'UnrelatedWorkingSourceChange')
    owned = {n for n in git(ROOT, 'ls-files', '--others', '--exclude-standard', '-z').decode().split('\0')
             if n.startswith(PACKAGE)}
    need(owned <= NEW_PATHS, 'UnknownOwnedResearchPath')
    if expected_head != BASE:
        need(source_rows(committed) == p['sourceBindings'], 'ExactCommittedWorkingEqualityRequired')
    p['retainedPhysicalXmlPaths'] = physical
    return p


def validate_output(value):
    p = Path(value).absolute()
    regular(p)
    need(p.resolve() == p, 'CanonicalOwnedOutputPathRequired')
    allowed = (ROOT / '.tmp/m2cl-static-evidence', ROOT / 'private/reports/m2cl')
    need(p != allowed[1], 'ReportControlRootReservedEvenWhenAbsent')
    need(any(p == a or a in p.parents for a in allowed), 'OwnedM2clOutputOnly')
    need(not p.exists(), 'FreshOutputRequired')
    return p


def main():
    a = argparse.ArgumentParser(description=__doc__)
    mode = a.add_mutually_exclusive_group(required=True)
    mode.add_argument('--route', action='store_true')
    mode.add_argument('--guard', action='store_true')
    a.add_argument('--expected-head', required=True)
    a.add_argument('--approved-new-source-fingerprint')
    a.add_argument('--github-output')
    args = a.parse_args()
    if args.guard:
        result = guard(args.expected_head)
        print(json.dumps({k: v for k, v in result.items() if k != 'sourceBindings'}, sort_keys=True))
    else:
        try:
            base, active = git_maps(expected_head=args.expected_head)
            result = classify(base, active, args.approved_new_source_fingerprint)
        except Exception:
            result = full_qa('RoutingError_FullHistoricalQaRequired')
        if args.github_output:
            write_github_output(args.github_output, result)
        print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
