"""Publish static M2cm provenance obligations, accepting no ROM or CPU input."""
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
    from ecu_rom_provenance import ci
    from ecu_rom_provenance.analysis import canonical_records, load_contract
    source = ci.guard(args.expected_head)
    output = ci.validate_output(Path(args.output))
    contract = load_contract()
    raw = b''.join(canonical(record) for record in canonical_records())
    summary = {'milestone': 'M2cm', 'passed': True,
        'classification': 'ROM_PROVENANCE_ESTABLISHED_HARDWARE_UNBOUND', 'executionStatus': 'EXECUTION_BLOCKED',
        'classificationScope': 'RecordedProjectArchiveAcquisitionAndComputedByteBlobIdentity_NotOriginalDonorProof',
        'projectAcquisitionCategory': 'B_PublicFirmwareArchive', 'prearchiveDonorCategory': 'E_Unknown',
        'privateAcquisitionRecordsVerifiedByThisCLI': False,
        'artifactClass': 'DocumentaryProvenanceAndConditionalCompatibility_NotHardwareObservation',
        'sourceFingerprintSha256': source['sourceFingerprintSha256'],
        'staticRecords': 9, 'conditionalConfigurationComparisons': 60, 'sourceInventoryBindings': 24,
        'graphNodes': 14, 'graphEdges': 18, 'staticBacklogEntries': 8, 'physicalChecklistItems': 10,
        'actualEcuIdentity': None, 'actualMcuIdentity': None, 'physicalPeripheralApplicability': None,
        'independentComparison': 'SeparateFrozenReferenceTestGate_NotClaimedByCLI',
        'actualCpuExecutions': 0, 'originalRomExecutions': 0, 'actualIrqDeliveries': 0,
        'actualRtiExecutions': 0, 'actualRetiredInstructions': 0, 'newDisassemblyPerformed': False,
        'runtimeAdmissionGranted': False, 'firmwareReady': False,
        'staticCanonicalDecompressedBytes': len(raw), 'staticCanonicalSha256': sha256(raw).hexdigest(),
        'canonicalFieldExclusions': [], 'runtimeCanonicalComparison': 'NotApplicable_NoExecution',
        'deliveryCertifiedByThisStaticCli': False}
    if len(raw.splitlines()) != 9 or len(contract['sourceInventory']) != 24:
        raise ValueError('ClosedDocumentaryInventoryRequired')
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
        print(canonical({'milestone': 'M2cm', 'passed': False,
                         'actualCpuExecutions': 0, 'firmwareReady': False}).decode(), end='')
        return 1
    print(canonical(result).decode(), end='')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
