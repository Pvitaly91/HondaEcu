"""Explicit invented static M2ca review; no CPU, original-ROM or Cargo entry."""
import argparse
import gzip
from hashlib import sha256
import json
import os
from pathlib import Path
import sys

sys.dont_write_bytecode = True
from native_branch064c import source_guard


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True,
                      allow_nan=False).encode('ascii') + b'\n'


def run(args):
    root = source_guard.ROOT
    source_guard.need(not args.allow_saved_physical or args.working_source,
        'PhysicalXmlAcknowledgmentRequiresExplicitLocalWorkingSourceRole')
    if args.working_source:
        source_guard.need(source_guard.git(root, 'rev-parse', 'HEAD').decode().strip() == args.expected_head,
                          'ExactObservedLocalHeadRequired')
        source_guard.need(source_guard.git(root, 'merge-base', '--is-ancestor', source_guard.BASE, args.expected_head) == b'',
                          'AcceptedM2bzAncestryRequired')
        source = source_guard.working_source_join(allow_saved_physical=args.allow_saved_physical)
    else:
        source = source_guard.check_git_source(root, args.expected_head)
    from native_branch064c import provenance
    obligations = provenance.validate_contract()
    records = provenance.static_records(source['sourceFingerprintSha256'])
    raw = b''.join(canonical(record) for record in records)
    expected_counts = [record['primaryExpected']['expected_gate_instructions'] for record in records]
    summary = {'schemaVersion': 1, 'milestone': 'M2ca', 'passed': True,
        'classification': 'InventedStaticCalculations_NotCpuRuntime',
        'sourceFingerprintSha256': source['sourceFingerprintSha256'], 'staticCases': len(records),
        'conditionalExpectedGateInstructionCount': sum(expected_counts),
        'conditionalFullRouteReferenceCount': sum(record['primaryExpected']['expected_full_route_retirements'] for record in records),
        'originalRomExecutions': 0, 'actualCpuExecutions': 0, 'actualRetiredInstructions': 0,
        'runtimeAdmissionGranted': False, 'sourceProvenanceGate': 'BLOCKED',
        'staticFullIndependentExpectedComparison': 'PASS', 'oldReviewedSites': len(obligations['oldReviewedSites']),
        'newReviewedSites': len(obligations['newReviewedSites']), 'combinedReviewedSites': len(obligations['combinedReviewedSites']),
        'firstMismatch': None, 'canonicalFieldExclusions': [],
        'staticCanonicalDecompressedBytes': len(raw), 'staticCanonicalSha256': sha256(raw).hexdigest(),
        'runtimeCanonicalComparison': 'NotApplicable_NoAdmittedCorpus', 'firmwareReady': False}
    output = Path(args.output).absolute()
    allowed_output = (output == root / '.tmp/m2ca-static-evidence'
        or output.is_relative_to(root / '.tmp/m2ca-owned')
        or output.is_relative_to(root / 'private/reports/m2ca'))
    source_guard.need(allowed_output and '..' not in Path(args.output).parts
                      and not output.exists(), 'FreshOwnedStaticOutputDirectoryRequired')
    for node in (output, *output.parents):
        if os.path.lexists(node):
            source_guard.need(not node.is_symlink() and not getattr(node.lstat(), 'st_file_attributes', 0) & 0x400,
                              'StaticOutputReparseRefused')
    source_guard.need(source_guard.working_source_join(allow_saved_physical=args.allow_saved_physical) == source,
                      'SourceChangedAcrossInventedStaticCalculation')
    output.mkdir(parents=True, exist_ok=False)
    for name, payload in (('static-canonical.jsonl.gz', gzip.compress(raw, mtime=0)),
                          ('sourcejoin.json', canonical(source)), ('static-summary.json', canonical(summary))):
        with (output / name).open('xb') as stream:
            stream.write(payload); stream.flush(); os.fsync(stream.fileno())
    source_guard.need(source_guard.working_source_join(allow_saved_physical=args.allow_saved_physical) == source,
                      'SourceChangedAcrossInventedStaticCalculation')
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    parser.add_argument('--expected-head', required=True)
    parser.add_argument('--working-source', action='store_true', help='Explicit local precommit source role; never CI default')
    parser.add_argument('--allow-saved-physical', action='store_true', help='Explicit local acknowledgment of the three frozen XML representations')
    args = parser.parse_args()
    try:
        result = run(args)
    except (ValueError, OSError, KeyError) as error:
        print(canonical({'milestone': 'M2ca', 'passed': False, 'errorType': type(error).__name__,
            'newCpuExecutions': 0, 'runtimeAdmissionGranted': False, 'firmwareReady': False}).decode(), end='')
        return 1
    print(canonical(result).decode(), end='')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
