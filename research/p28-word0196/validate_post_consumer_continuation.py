"""Publish complete conditional source outputs and formal obligations, without CPU input."""
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


def no_peripheral_observations(value):
    if type(value) is dict:
        for key, child in value.items():
            if key in ('actualBufferWrite', 'actualAcceptance', 'actualTransmission',
                       'actualCompletion', 'actualTxIrq', 'actualHardwareObservation') and child is not None:
                return False
            if not no_peripheral_observations(child):
                return False
    elif type(value) is list:
        return all(no_peripheral_observations(child) for child in value)
    return True


def observe_record(record, operations, statuses):
    """Count envelopes only; heterogeneous logical/formal reads stay untouched."""
    if (type(record) is not dict or set(record) != {'caseId', 'operation', 'input', 'output'}
            or type(record['caseId']) is not str or not record['caseId']
            or type(record['operation']) is not str or not record['operation']
            or type(record['output']) is not dict):
        raise ValueError('ClosedCanonicalEnvelopeRequired')
    result = record['output']
    if (type(result.get('status')) is not str or not result['status']
            or result.get('actualHardwareObservation') is not None
            or 'actualHardwareObservation' not in result
            or type(result.get('cpuInstructionRetirements')) is not int
            or result['cpuInstructionRetirements'] != 0
            or result.get('executionStatus') != 'EXECUTION_BLOCKED'
            or result.get('firmwareReady') is not False
            or not no_peripheral_observations(result)):
        raise ValueError('ConditionalOutputCannotAdmitExecutionOrHardwareObservations')
    operation, status = record['operation'], result['status']
    operations[operation] = operations.get(operation, 0) + 1
    statuses[status] = statuses.get(status, 0) + 1


def run(args):
    from post_consumer_continuation import ci
    from post_consumer_continuation.analysis import canonical_records, load_contract
    source = ci.guard(args.expected_head)
    output = ci.validate_output(Path(args.output))
    contract = load_contract()
    expected_count = contract['corpus']['records']
    if type(expected_count) is not int or expected_count <= 0:
        raise ValueError('PositiveSourceBoundCorpusCountRequired')
    output.mkdir(parents=True, exist_ok=False)
    digest, count, size = sha256(), 0, 0
    status_counts, operations, seen = {}, {}, set()
    with (output / 'static-canonical.jsonl.gz').open('xb') as raw_output:
        with gzip.GzipFile(filename='', mode='wb', fileobj=raw_output, mtime=0) as stream:
            for record in canonical_records():
                observe_record(record, operations, status_counts)
                if record['caseId'] in seen:
                    raise ValueError('UniqueCanonicalCaseIdentitiesRequired')
                seen.add(record['caseId'])
                raw = canonical(record)
                size += len(raw)
                if size > MAX_CANONICAL_BYTES:
                    raise ValueError('ClosedCanonicalSizeBoundExceeded')
                stream.write(raw)
                digest.update(raw)
                count += 1
        raw_output.flush()
        os.fsync(raw_output.fileno())
    if count != expected_count:
        raise ValueError('ClosedSourceBoundCorpusCountRequired')
    summary = {'milestone': 'M2cr', 'passed': True,
        'classification': 'ConditionalSourceModelsAndFormalObligations_IndependentEquivalenceGateSeparate',
        'executionStatus': 'EXECUTION_BLOCKED',
        'artifactClass': 'ConditionalOutputsAndFormalObligations_NotActualCpuTrace',
        'sourceFingerprintSha256': source['sourceFingerprintSha256'], 'staticRecords': count,
        'sourceInstructionSites': len(contract['instructionEvidence']), 'procedures': len(contract['functions']),
        'operations': operations, 'conditionalResultCounts': status_counts,
        'staticCanonicalDecompressedBytes': size, 'staticCanonicalSha256': digest.hexdigest(),
        'independentComparison': 'SeparateFrozenReferenceGate_NotClaimedByCLI',
        'firstMismatch': 'NotCertifiedByThisCLI_SeeIndependentComparison', 'canonicalFieldExclusions': [],
        'formalObligationReadsAreActualObservations': False,
        'actualCpuExecutions': 0, 'originalRomExecutions': 0, 'actualIrqDeliveries': 0,
        'actualRtiExecutions': 0, 'actualFramePops': 0, 'actualRetiredInstructions': 0,
        'actualPeripheralWrites': 0, 'actualTransmissions': 0, 'actualTxInterruptRequests': 0,
        'cpuBusInstancesCreated': 0, 'actualHardwareObservation': None,
        'runtimeAdmissionGranted': False, 'firmwareReady': False, 'deliveryCertifiedByThisCLI': False}
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
        print(canonical({'milestone': 'M2cr', 'passed': False, 'actualCpuExecutions': 0,
                         'firmwareReady': False}).decode(), end='')
        return 1
    print(canonical(result).decode(), end='')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
