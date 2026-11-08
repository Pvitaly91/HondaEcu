"""Exact finite M2da static routing over the accepted M2cz tree."""
import argparse
import ast
import json
from hashlib import sha256
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'research/p28-word0196'))
from cold_return_c8_writer_proof import ci as parent

prior = parent.prior

BASE = '9d0547a312162a9d2509bf3db1a23a018c5cc008'
BASE_FINGERPRINT = '68a2ee3219946c178929e365ac7c8ab01feaecc47f4c9533e0b364cd07866c34'
BASE_WORKFLOW_HASH = 'e4f8a3de6879d577d2243c007cc7b136c2a0c6e3d5fa292017329ba3c495a7bd'
BASE_PIN = '3ec2a2a30d24836786b06a0f5f3181e798b4b424ae71ac79c920e78a8343ac8a'
WORKFLOW = prior.WORKFLOW
PACKAGE = 'research/p28-word0196/c8_normal_helper_continuity/'
NEW_PATHS = frozenset(PACKAGE + name for name in (
    '__init__.py', 'analysis.py', 'ci.py', 'ci_tests.py', 'contract.json',
    'corpus.py', 'helper_continuity.py', 'frame_graph.py', 'data03cb_reaching.py',
    'reference_oracle.py', 'source_tests.py', 'wire.py',
)) | frozenset(('docs/M2DA_C8_NORMAL_HELPER_CONTINUITY.md',
                'research/p28-word0196/validate_c8_normal_helper_continuity.py'))
ROUTER_JOB = parent.ROUTER_JOB.replace('cold_return_c8_writer_proof/ci.py', 'c8_normal_helper_continuity/ci.py').replace(
    '__M2CZ_APPROVED_NEW_SOURCE_FINGERPRINT__', '__M2DA_APPROVED_NEW_SOURCE_FINGERPRINT__')
STATIC_JOB = (parent.STATIC_JOB.replace('cold_return_c8_writer_proof', 'c8_normal_helper_continuity')
              .replace('cold-return-c8-static', 'c8-normal-helper-static')
              .replace('M2cz', 'M2da').replace('m2cz', 'm2da')
              .replace('Cold return and C8 writer proof', 'C8 and normal helper continuity'))


def new_fingerprint(blobs):
    return prior.fingerprint({name: blobs[name] for name in NEW_PATHS})


def make_workflow(base, pin):
    prior.need(type(pin) is str and re.fullmatch(r'[0-9a-f]{64}', pin) is not None, 'LiteralReviewPinRequired')
    prior.need(sha256(base).hexdigest() == BASE_WORKFLOW_HASH and prior.approval(base) == BASE_PIN,
               'ExactAcceptedWorkflowRequired')
    old = parent.ROUTER_JOB.replace('__M2CZ_APPROVED_NEW_SOURCE_FINGERPRINT__', BASE_PIN) + parent.STATIC_JOB
    new = ROUTER_JOB.replace('__M2DA_APPROVED_NEW_SOURCE_FINGERPRINT__', pin) + STATIC_JOB
    prior.need(base.count(old.encode()) == 1, 'ExactInheritedRoutingBlocksRequired')
    return base.replace(old.encode(), new.encode(), 1)


def projection(base, active, pin):
    prior.need(len(base) == 1481 and prior.fingerprint(base) == BASE_FINGERPRINT, 'ExactAcceptedSourceRequired')
    prior.need(not set(base) & NEW_PATHS and set(active) == set(base) | NEW_PATHS, 'FiniteNewPathsRequired')
    prior.need(all(active[key] == item for key, item in base.items() if key != WORKFLOW),
               'InheritedSourceChanged')
    prior.need(new_fingerprint(active) == pin, 'NewSourceReviewPinMismatch')
    prior.need(active[WORKFLOW].mode == base[WORKFLOW].mode
               and active[WORKFLOW].data == make_workflow(base[WORKFLOW].data, pin),
               'WorkflowOutsideReviewedOverlay')
    for name in sorted(NEW_PATHS):
        blob = active[name]
        prior.need(blob.mode == '100644' and 0 < len(blob.data) < 1024 * 1024 and b'\0' not in blob.data,
                   'BoundedRegularResearchTextRequired')
        content = blob.data.decode('utf-8', 'strict')
        if name.endswith('.py'):
            ast.parse(content, filename=name)
        elif name.endswith('.json'):
            prior.need(type(json.loads(content)) is dict, 'ContractObjectRequired')
    rows = prior.source_rows(active)
    return {'passed': True, 'classification': 'ConditionalC8NormalHelperResearch',
            'exactBase': BASE, 'sourceBindings': rows,
            'sourceFingerprintSha256': sha256(prior.canonical(rows)).hexdigest(),
            'approvedNewSourceFingerprintSha256': pin, 'unchangedBaseFiles': 1480,
            'newPublicPaths': sorted(NEW_PATHS), 'historicalJobsNotRun': 17,
            'targetCpuExecutions': 0, 'firmwareReady': False}


def classify(base, active, pin):
    try:
        source = projection(base, active, pin)
    except Exception:
        return prior.full_qa('UnknownRuntimeOrUnreviewedChange_FullHistoricalQaRequired')
    return {**prior.full_qa('ExactReviewedC8NormalHelperContinuity'), 'full_qa': False,
            'research_only': True, 'sourceFingerprintSha256': source['sourceFingerprintSha256']}


def git_maps(head):
    prior.need(type(head) is str and re.fullmatch(r'[0-9a-f]{40}', head) is not None, 'ExactHeadRequired')
    prior.need(prior.git(ROOT, 'rev-parse', 'HEAD').decode().strip() == head, 'WrongActiveHead')
    prior.git(ROOT, 'merge-base', '--is-ancestor', BASE, head)
    before, after = prior.tree(ROOT, BASE), prior.tree(ROOT, head)
    data = prior.contents(ROOT, (before, after))
    return tuple({key: prior.Blob(mode, data[oid]) for key, (mode, oid) in nodes.items()}
                 for nodes in (before, after))


def guard(head):
    base, committed = git_maps(head)
    active, physical = {}, []
    for name in sorted(set(base) | NEW_PATHS):
        path = ROOT / name
        prior.regular(path)
        raw = path.read_bytes()
        old = base.get(name)
        if old is not None and name != WORKFLOW and raw != old.data:
            identity = (sha256(old.data).hexdigest(), len(raw), sha256(raw).hexdigest())
            prior.need(prior.PHYSICAL_REPRESENTATIONS.get(name) == identity, 'WorkingInheritedSourceChanged')
            raw = old.data
            physical.append(name)
        active[name] = prior.Blob(old.mode if old else '100644', raw)
    result = projection(base, active, prior.approval(active[WORKFLOW].data))
    changed = set(prior.git(ROOT, 'diff', '--name-only', 'HEAD').decode().splitlines())
    prior.need(changed <= NEW_PATHS | {WORKFLOW}, 'UnrelatedWorkingSourceChange')
    untracked = prior.git(ROOT, 'ls-files', '--others', '--exclude-standard', '-z').decode().split('\0')
    prior.need(all(not path.startswith(PACKAGE) or path in NEW_PATHS for path in untracked), 'UnknownOwnedSourcePath')
    if head != BASE:
        prior.need(prior.source_rows(committed) == result['sourceBindings'], 'CommittedWorkingSourceMismatch')
    return {**result, 'retainedPhysicalXmlPaths': physical}


def output_directory(name):
    path = Path(name).absolute()
    prior.regular(path)
    allowed = (ROOT / '.tmp/m2da-static-evidence', ROOT / 'private/reports/m2da')
    prior.need(path == path.resolve() and path != allowed[1]
               and any(path == base or base in path.parents for base in allowed), 'OwnedM2daOutputOnly')
    prior.need(not path.exists(), 'FreshOutputRequired')
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--route', action='store_true')
    mode.add_argument('--guard', action='store_true')
    parser.add_argument('--expected-head', required=True)
    parser.add_argument('--approved-new-source-fingerprint')
    parser.add_argument('--github-output')
    args = parser.parse_args()
    if args.guard:
        result = guard(args.expected_head)
        result.pop('sourceBindings')
    else:
        try:
            result = classify(*git_maps(args.expected_head), args.approved_new_source_fingerprint)
        except Exception:
            result = prior.full_qa('RoutingError_FullHistoricalQaRequired')
        if args.github_output:
            prior.write_github_output(args.github_output, result)
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
