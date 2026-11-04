"""Publish closed high-level software transformations; no ROM/CPU input exists."""
import argparse
import gzip
from hashlib import sha256
import json
import os
from pathlib import Path
import sys

sys.dont_write_bytecode = True
MAX_CANONICAL_BYTES = 128 * 1024 * 1024


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True,
                      allow_nan=False).encode('ascii') + b'\n'


def run(args):
    from conditional_flag_mode_shadow import ci
    from conditional_flag_mode_shadow.analysis import canonical_records, load_contract
    source = ci.guard(args.expected_head)
    output = ci.validate_output(Path(args.output))
    contract = load_contract()
    output.mkdir(parents=True, exist_ok=False)
    digest, count, size = sha256(), 0, 0
    status_counts, operations = {}, {}
    data_writes = register_writes = 0
    with (output / 'static-canonical.jsonl.gz').open('xb') as raw_output:
        with gzip.GzipFile(filename='', mode='wb', fileobj=raw_output, mtime=0) as stream:
            for record in canonical_records():
                raw = canonical(record)
                size += len(raw)
                if size > MAX_CANONICAL_BYTES:
                    raise ValueError('ClosedCanonicalSizeBoundExceeded')
                stream.write(raw)
                digest.update(raw)
                count += 1
                operations[record['operation']] = operations.get(record['operation'], 0) + 1
                result = record['output']
                if 'status' in result:
                    status_counts[result['status']] = status_counts.get(result['status'], 0) + 1
                    data_writes += sum(row['space'] == 'DATA' for row in result['journal'])
                    register_writes += sum(row['space'] == 'REGISTER' for row in result['journal'])
        raw_output.flush()
        os.fsync(raw_output.fileno())
    if count != 1744:
        raise ValueError('Closed1744RecordsRequired')
    summary = {'milestone': 'M2cn', 'passed': True,
        'classification': 'ConditionalSoftwareTransformations_IndependentEquivalenceGateSeparate',
        'executionStatus': 'EXECUTION_BLOCKED', 'artifactClass': 'ConditionalSourceWitnesses_NotActualCpuTrace',
        'sourceFingerprintSha256': source['sourceFingerprintSha256'], 'staticRecords': count,
        'sourceInstructionSites': len(contract['instructionEvidence']), 'procedures': len(contract['functions']),
        'operations': operations, 'conditionalResultCounts': status_counts,
        'logicalDataWriteEffects': data_writes, 'logicalRegisterWriteEffects': register_writes,
        'staticCanonicalDecompressedBytes': size, 'staticCanonicalSha256': digest.hexdigest(),
        'independentComparison': 'SeparateFrozenReferenceGate_NotClaimedByCLI',
        'firstMismatch': 'NotCertifiedByThisCLI_SeeIndependentComparison', 'canonicalFieldExclusions': [],
        'actualCpuExecutions': 0, 'originalRomExecutions': 0, 'actualIrqDeliveries': 0,
        'actualRtiExecutions': 0, 'actualRetiredInstructions': 0, 'cpuBusInstancesCreated': 0,
        'actualHardwareObservation': None, 'runtimeAdmissionGranted': False, 'firmwareReady': False,
        'deliveryCertifiedByThisCLI': False}
    if ci.guard(args.expected_head) != source:
        raise ValueError('SourceChangedDuringConditionalCalculation')
    for name, payload in (('static-summary.json', canonical(summary)), ('sourcejoin.json', canonical(source))):
        with (output / name).open('xb') as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    if ci.guard(args.expected_head) != source:
        raise ValueError('SourceChangedDuringPublication')
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    parser.add_argument('--expected-head', required=True)
    args = parser.parse_args()
    try:
        result = run(args)
    except (ValueError, OSError, KeyError, TypeError):
        print(canonical({'milestone': 'M2cn', 'passed': False, 'actualCpuExecutions': 0,
                         'firmwareReady': False}).decode(), end='')
        return 1
    print(canonical(result).decode(), end='')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
