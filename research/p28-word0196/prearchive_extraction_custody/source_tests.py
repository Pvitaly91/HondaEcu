"""Independent exact records and custody boundary regressions."""
import ast
from copy import deepcopy
from pathlib import Path
import unittest

from . import analysis, documentary_reference, reference_oracle
from .corpus import artifact, cases, extraction


class SourceTests(unittest.TestCase):
    def setUp(self):
        self.functions = analysis.operations()

    def result(self, identity):
        row = next(item for item in cases() if item['id'] == identity)
        return self.functions[row['operation']](deepcopy(row['input']))

    def test_full_records_match_independent_oracle(self):
        seen = set()
        for row in cases():
            with self.subTest(case=row['id']):
                self.assertNotIn(row['id'], seen)
                seen.add(row['id'])
                actual = self.functions[row['operation']](deepcopy(row['input']))
                self.assertTrue(analysis.canonical(analysis.record(row, actual)) ==
                                analysis.canonical(analysis.record(row, reference_oracle.expected(row))),
                                'IndependentCanonicalMismatch')
        self.assertTrue(seen)

    def test_earliest_parent_and_earliest_git_remain_distinct(self):
        proof = self.result('lineage-recorded')
        self.assertEqual(proof['earliestAuthenticatedMetadata'], 'ArchivedParent2004')
        self.assertEqual(proof['earliestAuthenticatedExactArtifact'], 'ArchivePreImport')
        self.assertEqual([row['matchingEntries'] for row in proof['archiveHistory']], [2, 3, 1])
        metadata, *digital = proof['acceptedEdges']
        self.assertEqual(metadata['exactApplicability'], 'PublicationMetadataOnly')
        self.assertIsNone(metadata['artifactIdentity'])
        self.assertTrue(all(row['exactApplicability'] == 'DigitalArchiveOnly' for row in digital))
        self.assertEqual(proof['rejectedEdges'][0]['missingObligation'],
                         'ExactHistoricalAttachmentToImportedBlobBinding')
        self.assertIsNone(proof['originalPublication'])
        self.assertIsNone(proof['originalExtraction'])
        self.assertIsNone(proof['sameUnitDonor'])

    def test_parent_record_and_unavailable_sources_are_not_fabricated(self):
        first = self.result('attachment-parent-2004-replay')
        self.assertEqual(first['retainedParentRevision'], 'r1.20')
        self.assertEqual(first['archiveCapture']['time'], '2004-05-22T16:20:12')
        self.assertIsNone(first['recordedUpload']['zone'])
        self.assertIsNone(first['linkedPayloadIdentity'])
        self.assertIsNone(first['uploaderIdentity'])
        self.assertIsNone(first['parentExtractionRecord'])
        self.assertIsNone(self.result('attachment-invent-parent')['parentTopic'])
        self.assertIsNone(self.result('attachment-index-only')['recordedUpload'])
        self.assertIsNone(self.result('attachment-force-observed-http')['independentlyObservedHttp'])

    def test_dependent_paths_never_supply_an_extraction_witness(self):
        result = self.result('dependency-same-blob-three-paths')
        self.assertEqual(result['sourceCount'], 3)
        self.assertEqual(len(result['knownOriginGroups']), 1)
        self.assertTrue(all(pair['relation'] == 'DependentForOrigin' for pair in result['pairs']))
        self.assertEqual(result['independentExtractionWitnessCount'], 0)
        self.assertEqual(self.result('dependency-fixture-independent-record')['independentExtractionWitnessCount'], 0)

    def test_digital_identity_strength_does_not_choose_physical_identity(self):
        self.assertIs(self.result('artifact-project-exact')['actualImageBinding'], True)
        self.assertIs(self.result('artifact-earliest-blob')['actualImageBinding'], True)
        for case in ('full-byte-fixture', 'same-size-different', 'partial', 'filename', 'size-only',
                     'archived-page-no-bytes', 'unavailable'):
            with self.subTest(case=case):
                self.assertIs(self.result('artifact-' + case)['actualImageBinding'], False)
        for claim in ('reject-factory', 'reject-same-donor', 'reject-mcu-size'):
            result = self.result('artifact-' + claim)
            self.assertIsNone(result['actualEcuIdentity'])
            self.assertIsNone(result['actualMcuIdentity'])
            self.assertIsNone(result['factoryOriginality'])

    def test_temporal_checks_preserve_uncertainty_and_detect_incompatibility(self):
        recorded = self.result('chronology-recorded-Inspect')
        self.assertTrue(any(item['status'] == 'Consistent' for item in recorded['relations']))
        self.assertTrue(any(item['status'] == 'Unresolved' for item in recorded['relations']))
        self.assertEqual(self.result('chronology-invented-contradiction')['status'], 'Conflicting')
        self.assertEqual(self.result('chronology-invented-unknown-zone')['status'], 'Unresolved')
        self.assertEqual(self.result('chronology-invented-consistent')['status'], 'Consistent')
        for claim in ('ArchiveDateIsReadDate', 'UploadDateIsReadDate', 'UnknownZoneIsUtc',
                      'LiteralHttpIsObserved', 'MirrorIsFirstPublication'):
            result = self.result('chronology-recorded-' + claim)
            self.assertIsNone(result['actualExtractionTime'])
            self.assertIsNone(result['originalPublicationTime'])
            self.assertIsNone(result['observedHttpResponse'])
            self.assertIs(result['chronologyEstablishesProvenance'], False)

    def test_extraction_role_and_factory_proof_are_separate(self):
        self.assertIs(self.result('read-forged-primary')['recordTypeSupported'], False)
        self.assertIs(self.result('read-mirror')['conditionalExtractionEstablished'], False)
        self.assertIs(self.result('read-missing-bytes')['identitySupportsFullLink'], False)
        self.assertIs(self.result('read-checksum-factory')['conditionalExtractionEstablished'], True)
        self.assertIsNone(self.result('read-checksum-factory')['factoryOriginality'])
        self.assertEqual(self.result('read-fixture-modified')['conditionalFactoryOriginality'], 'ModifiedFirmware')
        self.assertIsNone(self.result('read-fixture-modified')['actualOriginalPhysicalExtraction'])

    def test_join_requires_same_subject_and_board_custody(self):
        good = self.result('donor-fixture-complete')
        self.assertIs(good['conditionalSameUnitChain'], True)
        self.assertIsNone(good['actualEcuIdentity'])
        self.assertIsNone(good['actualMcuIdentity'])
        for name in ('different-ecu', 'third-party', 'missing-pcb', 'missing-mcu',
                     'real-extraction-absent', 'mismatched-board-link'):
            with self.subTest(case=name):
                refused = self.result('donor-' + name)
                self.assertIs(refused['conditionalSameUnitChain'], False)
                self.assertIsNone(refused['conditionalMcuMarking'])
                self.assertIsNone(refused['actualHardwareObservation'])
        self.assertIn('DependentDuplicate', {row['status'] for row in self.result('donor-duplicate')['linkResults']})

    def test_shapes_refuse_private_or_actual_evidence_injection(self):
        identify = self.functions['rom_artifact_identity']
        with self.assertRaises(ValueError):
            identify(artifact('HistoricalAttachment', 'FullBytes', 32768, True))
        with self.assertRaises(ValueError):
            identify({**artifact('ProjectAcquisition'), 'privatePayload': 'InventedSentinel'})
        custody = self.functions['extraction_session_provenance']
        for key in ('actualCpuExecutions', 'actualHardwareObservation', 'actualIrqDelivery',
                    'actualIeWrite', 'actualBufferWrite', 'actualFramePop', 'exactC8Rule', 'flash'):
            with self.subTest(field=key), self.assertRaises(ValueError):
                custody({**extraction(), key: True})
        self.assertIsNone(analysis.AUTHORITY['exactC8Rule'])
        self.assertIsNone(analysis.AUTHORITY['actualHardwareObservation'])
        self.assertEqual(analysis.AUTHORITY['cpuInstructionRetirements'], 0)

    def test_frozen_contract_and_oracle_independence(self):
        original = analysis.load_contract()
        modified = deepcopy(original)
        modified['authority']['firmwareReady'] = True
        with self.assertRaisesRegex(ValueError, 'ExactSourceContractRequired'):
            analysis.validate_contract(modified)
        modified = deepcopy(original)
        modified['sources'][min(modified['sources'])] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'FrozenSourceBindingChanged'):
            analysis.validate_contract(modified)
        for module in (reference_oracle, documentary_reference):
            for node in ast.walk(ast.parse(Path(module.__file__).read_bytes())):
                if isinstance(node, ast.ImportFrom):
                    self.assertNotIn(node.module, ('documentary', 'extraction', 'analysis'))
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    self.assertNotEqual(node.func.id, 'print')
