"""M2cg static zero-source constraints only; no private ROM or CPU execution API."""
import argparse
import gzip
from hashlib import sha256
import json
import os
from pathlib import Path
import sys

sys.dont_write_bytecode = True
from native_data011b7_zero_source import source_guard


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
            'AcceptedM2ceAncestryRequired')
        source = source_guard.working_source_join(allow_saved_physical=args.allow_saved_physical)
    else:
        source = source_guard.check_git_source(root, args.expected_head)
    from native_data011b7_zero_source.analysis import canonical_records
    records = canonical_records(); raw = b''.join(canonical(record) for record in records)
    summary = {'schemaVersion': 1, 'milestone': 'M2cg', 'passed': True,
        'classification': 'StaticData011B7ZeroSourceProvenance_NotCpuExecution',
        'sourceFingerprintSha256': source['sourceFingerprintSha256'],
        'staticCases': len(records), 'inventedConstraintCases': 37, 'analysisRecords': 4,
        'negativeRequirementCategories': 31,
        'staticExactPrivateRomExtentChecksAtPublicInvocation': 0,
        'privateExtentVerification': 'SeparateLocalReceipt_NotCIClaim',
        'independentFullConstraintComparisons': 39, 'independentComparison': 'PASS',
        'originalRomExecutions': 0, 'actualCpuExecutions': 0, 'actualRetiredInstructions': 0,
        'runtimeAdmissionGranted': False, 'actualFrameReadAdmitted': False,
        'actualNativeInstructionIndex': None, 'actualLogicalWriteOrdinal': None,
        'actualRawByteWriteOrdinals': None, 'actualAllNativeWriteOrdinal': None, 'firstMismatch': None,
        'staticCanonicalDecompressedBytes': len(raw), 'staticCanonicalSha256': sha256(raw).hexdigest(),
        'canonicalFieldExclusions': [], 'runtimeCanonicalComparison': 'NotApplicable_NoAdmittedCorpus',
        'researchClassification': 'CONDITIONAL_DATA011B7_ZERO_PRODUCER_ESTABLISHED / EXECUTION_BLOCKED',
        'deliveryCertifiedByThisStaticCli': False, 'firmwareReady': False}
    output = Path(args.output).absolute()
    allowed = (output == root / '.tmp/m2cg-static-evidence'
        or output.is_relative_to(root / '.tmp/m2cg-owned')
        or output.is_relative_to(root / 'private/reports/m2cg'))
    source_guard.need(allowed and '..' not in Path(args.output).parts and not output.exists(),
        'FreshOwnedStaticOutputDirectoryRequired')
    for node in (output, *output.parents):
        if os.path.lexists(node):
            source_guard.need(not node.is_symlink() and not getattr(node.lstat(), 'st_file_attributes', 0) & 0x400,
                'StaticOutputReparseRefused')
    source_guard.need(source_guard.working_source_join(allow_saved_physical=args.allow_saved_physical) == source,
        'SourceChangedDuringStaticCalculation')
    output.mkdir(parents=True, exist_ok=False)
    for name, payload in (('static-canonical.jsonl.gz', gzip.compress(raw, mtime=0)),
            ('sourcejoin.json', canonical(source)), ('static-summary.json', canonical(summary))):
        with (output / name).open('xb') as stream:
            stream.write(payload); stream.flush(); os.fsync(stream.fileno())
    source_guard.need(source_guard.working_source_join(allow_saved_physical=args.allow_saved_physical) == source,
        'SourceChangedDuringStaticPublication')
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    parser.add_argument('--expected-head', required=True)
    parser.add_argument('--working-source', action='store_true')
    parser.add_argument('--allow-saved-physical', action='store_true')
    args = parser.parse_args()
    try:
        result = run(args)
    except (ValueError, OSError, KeyError) as error:
        print(canonical({'milestone': 'M2cg', 'passed': False, 'errorType': type(error).__name__,
            'newCpuExecutions': 0, 'runtimeAdmissionGranted': False, 'firmwareReady': False}).decode(), end='')
        return 1
    print(canonical(result).decode(), end='')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
