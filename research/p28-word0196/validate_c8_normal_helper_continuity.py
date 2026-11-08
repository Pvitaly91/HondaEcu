"""Publish deterministic research records for the exact reviewed M2da source."""
import argparse
import gzip
from hashlib import sha256
import json

from c8_normal_helper_continuity import ci
from c8_normal_helper_continuity.analysis import canonical, load_contract, record
from c8_normal_helper_continuity.corpus import cases


def publish(head, destination):
    source = ci.guard(head)
    contract = load_contract()
    output = ci.output_directory(destination)
    output.mkdir(parents=True, exist_ok=False)
    seen, outcomes, operations = set(), {}, {}
    digest, size = sha256(), 0
    with (output / 'static-canonical.jsonl.gz').open('xb') as raw:
        with gzip.GzipFile(filename='', mode='wb', fileobj=raw, mtime=0) as stream:
            for case in cases():
                result = record(case)
                identifier = result['caseId']
                if identifier in seen:
                    raise ValueError('DuplicateCaseIdentity')
                seen.add(identifier)
                outcome = result['output']['status']
                operation = result['operation']
                outcomes[outcome] = outcomes.get(outcome, 0) + 1
                operations[operation] = operations.get(operation, 0) + 1
                line = canonical(result)
                size += len(line)
                if size > 128 * 1024 * 1024:
                    raise ValueError('CanonicalByteLimitExceeded')
                digest.update(line)
                stream.write(line)
    identity = {'records': len(seen), 'bytes': size, 'sha256': digest.hexdigest(),
                'canonicalFieldExclusions': []}
    if identity != contract['canonical']:
        raise ValueError('IndependentCanonicalIdentityMismatch')
    if ci.guard(head) != source:
        raise ValueError('SourceChangedDuringPublication')
    summary = {'milestone': 'M2da', 'passed': True, 'identity': identity,
               'sourceFingerprintSha256': source['sourceFingerprintSha256'],
               'outcomes': outcomes, 'operations': operations, 'procedures': len(contract['operations']),
               'executionAuthority': contract['authority']}
    for name, value in (('static-summary.json', summary), ('sourcejoin.json', source)):
        with (output / name).open('xb') as stream:
            stream.write(canonical(value))
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--expected-head', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    print(json.dumps(publish(args.expected_head, args.output), sort_keys=True))


if __name__ == '__main__':
    main()
