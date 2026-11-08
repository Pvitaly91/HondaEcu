"""Full independent records and semantic evidence-promotion refusals."""
import ast
from copy import deepcopy
from pathlib import Path
import unittest

from . import analysis, reference_oracle
from .corpus import cases


class SourceTests(unittest.TestCase):
    def setUp(self):
        self.functions = analysis.operations()

    def result(self, identity):
        row = next(item for item in cases() if item['id'] == identity)
        return self.functions[row['operation']](deepcopy(row['input']))

    def test_full_records_match_frozen_independent_expectations(self):
        seen = set()
        for case in cases():
            identity = case['id']
            with self.subTest(case=identity):
                self.assertNotIn(identity, seen)
                seen.add(identity)
                actual = self.functions[case['operation']](deepcopy(case['input']))
                self.assertTrue(analysis.canonical(analysis.record(case, actual)) ==
                                analysis.canonical(analysis.record(case, reference_oracle.expected(case))),
                                'IndependentCanonicalMismatch')
        self.assertTrue(seen)

    def test_historical_binding_requires_correct_subject_and_complete_untransformed_payload(self):
        for name in ('FixtureWrongParent', 'FixtureTransformed', 'FixtureTruncated',
                     'FixtureIndexOnly', 'FixtureUnavailable'):
            with self.subTest(case=name):
                result = self.result('payload-' + name)
                self.assertNotEqual(result['status'], 'AuthenticatedOriginalAttachmentBytes')
                self.assertIs(result['actualOriginalPayloadBound'], False)
        self.assertEqual(self.result('payload-KnownLaterBlob')['status'], 'ByteIdenticalDerivative')
        self.assertIs(self.result('payload-FixtureOriginalExact')['actualOriginalPayloadBound'], False)
        for month in ('June', 'September'):
            result = self.result('payload-HistoricalCapture' + month + '2004')
            self.assertIs(result['actualOriginalPayloadBound'], True)
            self.assertIsNone(result['physicalExtractionRecord'])

    def test_digest_origin_and_exact_scope_are_independent_of_equality(self):
        for name in ('ArchiveCaptureDigest', 'KnownLaterDigest', 'FixtureLaterDigest', 'FixtureCopiedDigest', 'FixtureUnknownDigest',
                     'FixturePartialDigest', 'FixtureLegacyDigest', 'FixtureUnboundDigest'):
            with self.subTest(case=name):
                result = self.result('digest-' + name)
                self.assertNotEqual(result['status'], 'AuthenticatedOriginalAttachmentDigest')
                self.assertIs(result['actualOriginalDigestBound'], False)
        result = self.result('digest-FixtureOriginalDigest')
        self.assertEqual(result['status'], 'AuthenticatedOriginalAttachmentDigest')
        self.assertIs(result['actualOriginalDigestBound'], False)

    def test_digital_proof_refuses_conflicting_identity_and_dependent_copies(self):
        result = self.result('join-later-only')
        self.assertEqual(len(result['dependencyLineage']), 1)
        self.assertEqual(len(result['dependencyLineage'][0]['sourceIds']), 3)
        self.assertEqual(result['independentExtractionWitnessCount'], 0)
        self.assertIsNone(result['actualAttachmentToBlobBinding'])
        result = self.result('join-conflict')
        self.assertEqual(result['status'], 'AttachmentIdentityConflict')
        self.assertFalse(result['acceptedEdges'])
        self.assertIsNone(result['conditionalFixtureBinding'])
        self.assertIsNone(self.result('join-wrong-parent')['conditionalFixtureBinding'])
        self.assertIsNone(self.result('join-archive-digest-alone')['actualAttachmentToBlobBinding'])

    def test_verified_captures_close_only_the_actual_digital_edge(self):
        reviewed = self.result('status-reviewed')
        self.assertEqual(reviewed['status'], 'ORIGINAL_ATTACHMENT_BYTE_IDENTITY_ESTABLISHED')
        self.assertEqual(reviewed['acceptedEdges'], ['HistoricalAttachmentToPinnedBlob'])
        self.assertIsNone(reviewed['minimumNextEvidence']['digital'])
        self.assertIsNotNone(reviewed['minimumNextEvidence']['physical'])
        self.assertIsNone(reviewed['physicalAxis']['actualOriginalPhysicalExtraction'])
        self.assertIsNone(reviewed['actualMcuIdentity'])
        self.assertEqual(reviewed['digitalAxis']['independentExtractionWitnessCount'], 0)

    def test_two_axes_do_not_convert_fixture_or_byte_equality_into_physical_proof(self):
        digital_only = self.result('status-digital-fixture-missing-donor')
        self.assertIsNotNone(digital_only['digitalAxis']['conditionalFixtureBinding'])
        self.assertIs(digital_only['physicalAxis']['conditionalSameUnitChain'], False)
        fixture = self.result('status-digital-fixture-complete-donor')
        self.assertIs(fixture['physicalAxis']['conditionalSameUnitChain'], True)
        self.assertTrue(fixture['conditionalFixtureEdges'])
        self.assertFalse(fixture['acceptedEdges'])
        for row in (digital_only, fixture, self.result('status-digital-fixture-missing-mcu'),
                    self.result('status-digital-fixture-wrong-donor')):
            self.assertIsNone(row['physicalExtractionRecord'])
            self.assertIsNone(row['actualEcuIdentity'])
            self.assertIsNone(row['actualMcuIdentity'])
            self.assertIsNone(row['factoryOriginality'])
            self.assertIsNone(row['exactC8Rule'])
        self.assertIsNone(self.result('status-digital-fixture-missing-mcu')['physicalAxis']['conditionalMcuMarking'])
        self.assertIs(self.result('status-digital-fixture-wrong-donor')['physicalAxis']['conditionalSameUnitChain'], False)

    def test_chronology_retains_timezone_precision_and_qualifications(self):
        chronology = self.result('status-reviewed')['chronology']
        dates = {event['event']: event for event in chronology['recordedEvents']}
        self.assertIsNone(dates['AttachmentUpload']['zone'])
        self.assertEqual(dates['ArchivedParentReplay']['time'], '2004-05-22T16:20:12')
        self.assertEqual(dates['ArchivePreImport']['time'], '2024-08-10T22:29:55')
        self.assertIsNone(chronology['originalPublicationTime'])
        self.assertIsNone(chronology['observedPhysicalExtractionTime'])
        self.assertIs(chronology['dateOrderConfersCustody'], False)

    def test_scope_refuses_authority_and_raw_evidence_injection(self):
        join = self.functions['attachment_to_rom_blob_proof']
        for sources in (['FixtureOriginalExact', 'KnownLaterBlob'], ['FixtureOriginalExact'] * 2,
                        ['UnreviewedAttachment']):
            with self.subTest(sources=sources), self.assertRaises(ValueError):
                join({'sourceIds': sources, 'claim': 'Inspect'})
        for field in ('actualCpuExecutions', 'actualIrqDelivery', 'actualBufferWrite', 'actualIeWrite',
                      'actualHardwareObservation', 'privatePayload', 'flash'):
            with self.subTest(field=field), self.assertRaises(ValueError):
                join({'sourceIds': ['KnownLaterBlob'], 'claim': 'Inspect', field: True})
        for case in ('force-donor', 'force-factory', 'force-c8', 'force-execution'):
            row = self.result('join-' + case)
            self.assertEqual(row['status'], 'RefusedEvidencePromotion')
            self.assertFalse(row['acceptedEdges'])
        self.assertIsNone(analysis.AUTHORITY['exactC8Rule'])
        self.assertEqual(analysis.AUTHORITY['cpuInstructionRetirements'], 0)

    def test_frozen_contract_and_oracle_independence(self):
        baseline = analysis.load_contract()
        altered = deepcopy(baseline)
        altered['authority']['actualSiliconConfirmed'] = True
        with self.assertRaisesRegex(ValueError, 'ExactSourceContractRequired'):
            analysis.validate_contract(altered)
        altered = deepcopy(baseline)
        altered['sources'][min(altered['sources'])] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'FrozenSourceBindingChanged'):
            analysis.validate_contract(altered)
        for node in ast.walk(ast.parse(Path(reference_oracle.__file__).read_bytes())):
            if isinstance(node, ast.ImportFrom):
                self.assertNotIn(node.module, ('identity', 'analysis', 'extraction'))
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                self.assertNotEqual(node.func.id, 'print')
