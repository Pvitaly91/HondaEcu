"""Publish static M2ck documentary claims; accepts no ROM, CPU or IRQ input."""
import argparse
import gzip
from hashlib import sha256
import json
import os
from pathlib import Path
import sys

sys.dont_write_bytecode = True


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True,
                      allow_nan=False).encode('ascii') + b'\n'


def run(args):
    from rxready_acknowledgement import ci
    from rxready_acknowledgement.analysis import canonical_records
    source = ci.guard(args.expected_head)
    output = ci.validate_output(Path(args.output))
    records = canonical_records()
    raw = b''.join(canonical(record) for record in records)
    summary = {'milestone': 'M2ck', 'passed': True,
        'classification': 'RXREADY_SOURCE_CONFLICT_UNRESOLVED', 'executionStatus': 'EXECUTION_BLOCKED',
        'artifactClass': 'DocumentaryStaticClaims_NotHardwareObservations',
        'sourceFingerprintSha256': source['sourceFingerprintSha256'],
        'staticRecords': len(records), 'newApplicableAcknowledgementManualAcquired': False,
        'newJapaneseSpecificationAcquired': True, 'sameEditionEnglishMirrorAcquired': True,
        'iePolarity': 'EvidenceFavorsSet1But167ConflictRetained',
        'independentComparison': 'SeparateFrozenReferenceTestGate_NotClaimedByCLI',
        'actualCpuExecutions': 0, 'originalRomExecutions': 0, 'actualIrqDeliveries': 0,
        'actualRtiExecutions': 0, 'actualRetiredInstructions': 0,
        'actualMachineId': None, 'actualEventOrdinal': None, 'actualWriteOrdinal': None,
        'runtimeAdmissionGranted': False, 'firmwareReady': False,
        'staticCanonicalDecompressedBytes': len(raw), 'staticCanonicalSha256': sha256(raw).hexdigest(),
        'canonicalFieldExclusions': [], 'runtimeCanonicalComparison': 'NotApplicable_NoExecution',
        'deliveryCertifiedByThisStaticCli': False}
    if ci.guard(args.expected_head) != source:
        raise ValueError('SourceChangedDuringStaticCalculation')
    output.mkdir(parents=True, exist_ok=False)
    for name, payload in (('static-canonical.jsonl.gz', gzip.compress(raw, mtime=0)),
                          ('static-summary.json', canonical(summary)),
                          ('sourcejoin.json', canonical(source))):
        with (output / name).open('xb') as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    if ci.guard(args.expected_head) != source:
        raise ValueError('SourceChangedDuringStaticPublication')
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    parser.add_argument('--expected-head', required=True)
    args = parser.parse_args()
    try:
        result = run(args)
    except (ValueError, OSError, KeyError, TypeError):
        print(canonical({'milestone': 'M2ck', 'passed': False,
                         'actualCpuExecutions': 0, 'firmwareReady': False}).decode(), end='')
        return 1
    print(canonical(result).decode(), end='')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
