"""Source-contract mutations and independent invented calculations; zero CPU."""
from copy import deepcopy
import unittest

from . import provenance


class ProvenanceTests(unittest.TestCase):
    def test_changed_allowed_code_cannot_reuse_the_old_workflow_literal_approval(self):
        from . import source_guard
        current = {name: source_guard.Blob('100644', b'# Invented closed-source unit fixture\n')
                   for name in source_guard.NEW_PATHS}
        approved = source_guard.new_source_fingerprint(current)
        current[source_guard.WORKFLOW] = source_guard.Blob('100644',
            ('--approved-new-source-fingerprint "' + approved + '"\n').encode('ascii'))
        self.assertEqual(source_guard.check_new_source_approval(current), approved)
        changed = dict(current)
        changed['research/p28-word0196/native_branch064c/gate_model.py'] = source_guard.Blob(
            '100644', b'raise RuntimeError("Unreviewed changed allowed runtime code")\n')
        with self.assertRaisesRegex(ValueError, 'ExplicitWorkflowApprovalRecertification'):
            source_guard.check_new_source_approval(changed)
        # A replacement approval is not generated here. Recertifying a changed
        # policy plus workflow pin is a separate explicit review trust boundary.

    def test_closed_source_inventory_is_unowned_at_first_branch(self):
        result = provenance.validate_contract()
        self.assertEqual((len(result['oldReviewedSites']), len(result['newReviewedSites']),
            len(result['combinedReviewedSites'])), (59, 6, 65))
        self.assertNotIn(0x011B, result['ordinaryDataInventory'])
        self.assertNotIn(0x011F, result['ordinaryDataInventory'])
        self.assertFalse(result['runtimeAdmission'])

    def test_meaningful_provenance_and_admission_changes_are_refused(self):
        changes = [lambda v: v['sources']['011F'].update(classification='NativeCurrentSessionWriterEstablished'),
            lambda v: v['sources']['011B'].update(generation={'writerPc': 0x55C1}),
            lambda v: v['sources']['012A'].update(newInitialBit0OrBit3Allowed=True),
            lambda v: v['publicFixtureMapping'].update(literalPublic011BIsPrivateBranch011B=True),
            lambda v: v['historicalSources'].update(transferAllowed=True),
            lambda v: v['authority'].update(originalBranchExecutionAdmitted=True),
            lambda v: v['proofPolicy'].update(expectedArchitecturalEffectsAreProductionJournals=True),
            lambda v: v['currentContext']['ordinaryDataInventory'].append(0x011F),
            lambda v: v['candidateProgram'].update(actualNewWindowOpened=True),
            lambda v: v['routes'][0].update(currentOriginalAdmission=True),
            lambda v: v.update(extra_source='silently expanded')]
        for change in changes:
            value = deepcopy(provenance.EXPECTED_CONTRACT); change(value)
            with self.subTest(value=value), self.assertRaises(ValueError):
                provenance.validate_contract(value)

    def test_exact_types_cannot_promote_zero_or_one_to_boolean_authority(self):
        for path, replacement in [(('authority', 'runtimeFeatureAdded'), 0),
                (('currentContext', 'old012ABit0'), False), (('sources', '011B', 'width'), True)]:
            value = deepcopy(provenance.EXPECTED_CONTRACT); target = value
            for part in path[:-1]:
                target = target[part]
            target[path[-1]] = replacement
            with self.subTest(path=path), self.assertRaises(ValueError):
                provenance.validate_contract(value)

    def test_four_static_canonical_records_include_both_full_independent_traces(self):
        records = provenance.static_records('1' * 64)
        self.assertEqual(len(records), 4)
        self.assertEqual([r['primaryExpected']['expected_full_route_retirements'] for r in records], [52, 53, 55, 53])
        self.assertEqual([r['primaryExpected']['expected_gate_instructions'] for r in records], [3, 4, 6, 4])
        for record in records:
            self.assertEqual(record['primaryExpected'], record['independentReference'])
            self.assertFalse(record['comparison']['runtime_admission_granted'])
            self.assertEqual(record['comparison']['cpu_executions'], 0)
