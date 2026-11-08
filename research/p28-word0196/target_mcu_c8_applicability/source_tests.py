"""Documentary qualification, frozen coverage, and refusal regressions."""
import ast
from copy import deepcopy
from pathlib import Path
import unittest

from . import analysis, candidate_reference, reference_oracle
from .corpus import cases, custody, isa_query, memory_query


class SourceTests(unittest.TestCase):
    def setUp(self):
        self.functions = analysis.operations()

    def result(self, identity):
        case = next(case for case in cases() if case['id'] == identity)
        return self.functions[case['operation']](deepcopy(case['input']))

    def test_full_records_match_independent_oracle(self):
        seen = set()
        for case in cases():
            identity, operation = case['id'], case['operation']
            with self.subTest(case=identity):
                self.assertNotIn(identity, seen)
                seen.add(identity)
                actual = self.functions[operation](deepcopy(case['input']))
                self.assertTrue(analysis.canonical(analysis.record(case, actual)) ==
                                analysis.canonical(analysis.record(case, reference_oracle.expected(case))),
                                'IndependentCanonicalMismatch')
        self.assertTrue(seen)

    def test_archive_identity_never_creates_donor_date_or_factory_identity(self):
        for name in ('archive', 'photo-is-not-donor', 'hash-is-not-factory', 'upload-is-not-extraction'):
            with self.subTest(case=name):
                result = self.result('custody-' + name)
                self.assertIs(result['projectArchiveAcquisition'], True)
                self.assertIsNone(result['originalPhysicalExtraction'])
                self.assertIsNone(result['studiedDonor'])
                self.assertIsNone(result['factoryOriginality'])
                self.assertIsNone(result['physicalExtractionDate'])
        self.assertIs(self.result('custody-filename')['projectArchiveAcquisition'], False)
        self.assertIs(self.result('custody-mismatch')['projectArchiveAcquisition'], False)

    def test_witness_origin_and_same_subject_distinction(self):
        archives = self.result('custody-same-hash-origins')
        self.assertEqual((archives['sourceCount'], archives['independentWitnessCount']), (3, 1))
        self.assertEqual({row['relation'] for row in archives['pairRelations']}, {'DependentDuplicate'})
        subjects = self.result('custody-different-subjects')
        self.assertIn('DifferentPhysicalSubjects', {row['relation'] for row in subjects['pairRelations']})
        fixture = self.result('custody-invented-conflict')
        self.assertIn('FixtureExclusiveSameUnitConflict', {row['relation'] for row in fixture['pairRelations']})
        self.assertIs(fixture['actualHardwareConfirmed'], False)
        self.assertIsNone(self.result('custody-invented-promotion')['studiedDonor'])

    def test_catalog_photo_suffix_and_memory_do_not_set_actual_identity(self):
        for name in ('photo-to-unit', 'unsupported-alias', 'code-to-revision', 'code-to-c8'):
            with self.subTest(case=name):
                result = self.result('attribution-' + name)
                self.assertEqual(result['promotionDecision'], 'Rejected')
                self.assertIs(result['manufacturerAliasEstablished'], False)
                self.assertIsNone(result['siliconRevision'])
                self.assertIsNone(result['actualMcuIdentity'])
        unknown = self.result('attribution-unknown')
        self.assertIsNone(unknown['literalCodeToken'])
        self.assertIsNone(unknown['source']['pcbRevision'])
        self.assertIsNone(unknown['source']['catalogMcuPart'])
        self.assertIsNone(self.result('memory-201-socket')['actualProgramSelection'])
        self.assertIsNone(self.result('memory-207-drawing')['actualDataMapping'])

    def test_memory_overlay_preserves_base_and_separates_space_overlap(self):
        rows = [row for row in cases() if row['id'].startswith('memory-base-')]
        self.assertEqual(len(rows), 60)
        check = self.result('memory-otp-external')
        self.assertTrue(check['sameSpaceOverlaps'])
        self.assertTrue(check['crossSpaceNumericOverlaps'])
        self.assertIsNone(check['actualProgramSelection'])
        self.assertEqual(check['stackApplicability'], 'Unestablished')
        self.assertIs(check['actualSiliconConfirmed'], False)
        self.assertTrue(self.result('memory-selector-conflict')['premiseConflicts'])

    def test_c8_mnemonic_mirror_and_wrong_family_are_not_revision_proof(self):
        early = self.result('isa-early-207')
        self.assertIsNotNone(early['preliminary207Mnemonic'])
        self.assertIsNone(early['primaryC8Text'])
        self.assertIsNone(early['exactSiliconPredicate'])
        self.assertIsNone(self.result('isa-201-with-207-only')['preliminary207Mnemonic'])
        mirror = self.result('isa-printed-and-mirror')
        self.assertEqual(len(mirror['sourceWitnesses']), 1)
        self.assertEqual(mirror['primaryC8Text']['predicate'], 'PrintedOr')
        self.assertIsNone(mirror['exactRevisionApplicable'])
        wrong = self.result('isa-wrong-family')
        self.assertEqual(wrong['comparativeText']['opcode'], 0xF0)
        self.assertIsNone(wrong['exactSiliconPredicate'])
        for name in ('force-or', 'force-and', 'force-target'):
            self.assertEqual(self.result('isa-' + name)['status'], 'OutsideVerifiedScope')

    def test_graph_never_transitively_promotes_archive_or_catalog(self):
        graph = self.result('junction-independent-axes')
        self.assertEqual([(row['from'], row['to']) for row in graph['acceptedEdges']],
                         [('StudiedROM', 'ArchiveAcquisition')])
        self.assertEqual(graph['rejectedEdges'][0]['to'], 'PrearchiveExtraction')
        self.assertIsNone(graph['targetC8Applicability'])
        self.assertIs(graph['junctionEstablished'], False)
        self.assertEqual(len(graph['minimumProofPacket']), 3)
        self.assertFalse(self.result('junction-filename-unbound')['acceptedEdges'])
        self.assertEqual(self.result('junction-execution-refused')['status'], 'OutsideVerifiedScope')

    def test_unreviewed_or_physical_input_fields_are_refused(self):
        functions = self.functions
        cases_to_refuse = (
            ('rom_to_hardware_provenance', custody(('M1aAcquisition', 'FixtureSameUnitA'))),
            ('rom_to_hardware_provenance', {**custody(), 'privatePayload': 'InventedSentinel'}),
            ('rom_to_hardware_provenance', {**custody(), 'extractionCustody': 'HostAssertion'}),
            ('c8_revision_evidence', isa_query(nativeFlags={'cf': 0, 'zf': 1})),
            ('c8_revision_evidence', isa_query(sourceIds=['UnreviewedVendorResponse'])),
            ('memory_architecture_compatibility', memory_query(accesses=[
                {'space': 'PROGRAM', 'address': 0xFFFF, 'widthBytes': 2}])),
            ('memory_architecture_compatibility', memory_query(accesses=[
                {'space': 'DATA', 'address': False, 'widthBytes': 1}])),
            ('memory_architecture_compatibility', memory_query(actualSiliconConfirmed=True)),
        )
        for operation, query in cases_to_refuse:
            with self.subTest(operation=operation), self.assertRaises(ValueError):
                functions[operation](query)
        for field in ('actualCpuExecutions', 'actualCallExecution', 'actualIeWrite', 'actualBufferWrite',
                      'actualIrqDelivery', 'actualFramePop', 'actualHardwareObservation', 'flash'):
            with self.subTest(field=field), self.assertRaises(ValueError):
                functions['target_c8_applicability']({
                    'custody': custody(), 'isa': isa_query(), 'claim': 'Inspect', field: True})
        self.assertIsNone(analysis.AUTHORITY['actualHardwareObservation'])
        self.assertEqual(analysis.AUTHORITY['cpuInstructionRetirements'], 0)
        self.assertIs(analysis.AUTHORITY['firmwareReady'], False)

    def test_frozen_authority_and_source_bindings_are_guarded(self):
        contract = analysis.load_contract()
        mutant = deepcopy(contract)
        mutant['authority']['actualSiliconConfirmed'] = True
        with self.assertRaisesRegex(ValueError, 'ExactSourceContractRequired'):
            analysis.validate_contract(mutant)
        mutant = deepcopy(contract)
        mutant['sources'][min(mutant['sources'])] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'FrozenSourceBindingChanged'):
            analysis.validate_contract(mutant)

    def test_independent_oracle_does_not_import_or_log_new_models(self):
        for module in (candidate_reference, reference_oracle):
            syntax = ast.parse(Path(module.__file__).read_bytes())
            for node in ast.walk(syntax):
                if isinstance(node, ast.ImportFrom):
                    self.assertNotIn(node.module, ('analysis', 'candidates', 'graph', 'isa', 'provenance'))
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    self.assertNotEqual(node.func.id, 'print')
