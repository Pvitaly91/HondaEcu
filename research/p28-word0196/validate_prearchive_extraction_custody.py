"""Publish only independently matched, public-safe M2dd source records."""
import argparse
import gzip
from hashlib import sha256
import json

from prearchive_extraction_custody import ci
from prearchive_extraction_custody.analysis import canonical, load_contract, operations, record
from prearchive_extraction_custody.corpus import cases
from prearchive_extraction_custody.reference_oracle import expected


def publish(head, destination):
    source = ci.guard(head)
    contract = load_contract()
    functions = operations()
    output = ci.output_directory(destination)
    output.mkdir(parents=True, exist_ok=False)
    seen, outcomes = set(), {}
    digest, size = sha256(), 0
    with (output / 'static-canonical.jsonl.gz').open('xb') as raw:
        with gzip.GzipFile(filename='', mode='wb', fileobj=raw, mtime=0) as stream:
            for case in cases():
                identifier, operation = case['id'], case['operation']
                if identifier in seen:
                    raise ValueError('DuplicateCaseIdentity')
                seen.add(identifier)
                actual = functions[operation](case['input'])
                line = canonical(record(case, actual))
                if line != canonical(record(case, expected(case))):
                    raise ValueError(f'IndependentCanonicalMismatch {identifier}')
                status = actual.get('status') or actual['classification']
                outcomes[status] = outcomes.get(status, 0) + 1
                size += len(line)
                digest.update(line)
                stream.write(line)
    identity = {'records': len(seen), 'bytes': size, 'sha256': digest.hexdigest(),
                'canonicalFieldExclusions': []}
    if identity != contract['canonical']:
        raise ValueError('FrozenCanonicalIdentityMismatch')
    if ci.guard(head) != source:
        raise ValueError('SourceChangedDuringPublication')
    summary = {'milestone': 'M2dd', 'passed': True, 'identity': identity,
               'sourceFingerprintSha256': source['sourceFingerprintSha256'],
               'outcomes': outcomes, 'procedures': len(functions),
               'firstMismatch': None, 'executionAuthority': contract['authority']}
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
