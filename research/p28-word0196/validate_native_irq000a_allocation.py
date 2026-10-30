"""M2ci documentary static evidence only; no ROM, CPU or IRQ execution input."""
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
    from native_irq000a_allocation import ci
    from native_irq000a_allocation.analysis import canonical_records
    source = ci.guard(args.expected_head)
    output = ci.validate_output(Path(args.output))
    records = canonical_records()
    raw = b''.join(canonical(record) for record in records)
    summary = {'schemaVersion': 1, 'milestone': 'M2ci', 'passed': True,
        'classification': 'DocumentaryStaticAllocationReview_NotExecution',
        'sourceFingerprintSha256': source['sourceFingerprintSha256'],
        'staticRecords': len(records), 'newManufacturerDocuments': 0,
        'transcriptionCorrection': 'PriorTranscriptionErrorCorrected',
        'independentComparison': 'SeparateTestGate_NotClaimedByCLI',
        'actualCpuExecutions': 0, 'originalRomExecutions': 0, 'actualIrqDeliveries': 0,
        'actualRtiExecutions': 0, 'actualRetiredInstructions': 0,
        'actualMachineId': None, 'actualEventOrdinal': None, 'actualWriteOrdinal': None,
        'runtimeAdmissionGranted': False, 'firstMismatch': None,
        'staticCanonicalDecompressedBytes': len(raw),
        'staticCanonicalSha256': sha256(raw).hexdigest(), 'canonicalFieldExclusions': [],
        'runtimeCanonicalComparison': 'NotApplicable_NoExecution',
        'deliveryCertifiedByThisStaticCli': False, 'firmwareReady': False}
    if ci.guard(args.expected_head) != source:
        raise ValueError('SourceChangedDuringStaticCalculation')
    output.mkdir(parents=True, exist_ok=False)
    for name, payload in (('static-canonical.jsonl.gz', gzip.compress(raw, mtime=0)),
            ('sourcejoin.json', canonical(source)), ('static-summary.json', canonical(summary))):
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
        print(canonical({'milestone': 'M2ci', 'passed': False,
            'actualCpuExecutions': 0, 'runtimeAdmissionGranted': False,
            'firmwareReady': False}).decode(), end='')
        return 1
    print(canonical(result).decode(), end='')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
