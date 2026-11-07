"""Independent equivalence and source-sensitive refusal controls."""
from copy import deepcopy
import unittest

from native_data0217_011f_bridge.helper_cfg import NODE_ROWS

from .analysis import AUTHORITY, OPERATIONS, canonical, record, validate_authority
from .corridor_cfg import CORRIDOR_SCOPE
from .corpus import cases
from .reference_oracle import record as reference_record

EDGES = {pc: following for pc, _, _, following in NODE_ROWS}
FORBIDDEN = {0x60E4, 0x5CCD, 0x2891, 0x3FB5, 0x3FF9, 0x2995}


class SourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.corpus = {case['id']: case for case in cases()}

    def calculate(self, identifier):
        case = self.corpus[identifier]
        return OPERATIONS[case['operation']](deepcopy(case['input']))

    def test_complete_corpus_against_independent_reference(self):
        seen = set()
        observed_edges = set()
        for case in cases():
            self.assertNotIn(case['id'], seen)
            seen.add(case['id'])
            actual = record(case)
            self.assertTrue(canonical(actual) == canonical(reference_record(case)), case['id'])
            observed_edges.update((step['pc'], step['next']) for step in actual['output']['steps']
                                  if step['pc'] in CORRIDOR_SCOPE and step['next'] is not None)
        self.assertEqual(observed_edges, {(pc, successor) for pc in CORRIDOR_SCOPE for successor in EDGES[pc]})

    def test_prefix_and_suffix_join_through_reviewed_intermediate_edges(self):
        for name in ('join-carry-00-00', 'join-nonzero-00-0'):
            with self.subTest(case=name):
                result = self.calculate(name)
                self.assertTrue(result['compositionEstablished'])
                self.assertEqual(result['boundary'], 0x60E4)
                prefix, corridor, suffix = result['inheritedResults']
                self.assertEqual([prefix['boundary'], corridor['boundary'], suffix['boundary']],
                                 [0x7DF5, 0x608F, 0x60E4])
                self.assertEqual(corridor['steps'][0]['pc'], 0x7DF5)
                self.assertEqual(corridor['steps'][-1]['next'], 0x608F)
                self.assertGreater(len(corridor['steps']), 30)
                self.assertEqual(suffix['steps'][0]['pc'], 0x608F)
                for step in result['steps']:
                    self.assertNotIn(step['pc'], FORBIDDEN)
                    self.assertIn(step['next'], EDGES[step['pc']])

    def test_initial_branch_is_from_retained_program_zero(self):
        for name, following in (('middle-carry-00-00', 0x7DF7), ('middle-nonzero-00-0', 0x7DFA)):
            case = self.corpus[name]
            prefix = case['input']['prefix']
            value = self.calculate(name)
            first = value['steps'][0]
            self.assertEqual((first['pc'], first['next']), (0x7DF5, following))
            self.assertEqual(first['afterRegisters']['zf'], prefix['state']['registers']['zf'])
            self.assertEqual(value['state']['generations']['0208'], prefix['state']['generations']['0208'])

    def test_unknown_initial_predicate_has_no_speculative_reads_or_writes(self):
        value = self.calculate('middle-r0-partial-0-None')
        self.assertEqual(value['boundary'], 0x7DF5)
        self.assertEqual(value['status'], 'IndeterminateBranch')
        self.assertEqual(value['reads'], [])
        self.assertEqual(value['journal'], [])
        self.assertFalse(any(step['next'] is not None for step in value['steps']))

    def test_program_binding_failure_excludes_selected_read(self):
        names = [name for name in self.corpus if name.startswith('middle-operand-')]
        names += ['middle-program-missing-generation', 'middle-program-missing-operand']
        for name in names:
            with self.subTest(case=name):
                value = self.calculate(name)
                self.assertNotEqual(value['status'], 'CompleteConditional')
                self.assertNotIn(0x60EA, [row['address'] for row in value['reads'] if row['space'] == 'PROGRAM'])
                self.assertNotEqual(value['boundary'], 0x608F)

    def test_forged_prefix_cannot_skip_effects_or_reseed_registers(self):
        names = [name for name in self.corpus if name.startswith('middle-forged-')]
        names += ['middle-reseed-accumulator']
        for name in names:
            with self.subTest(case=name):
                value = self.calculate(name)
                self.assertNotEqual(value['status'], 'CompleteConditional')
                self.assertEqual(value['journal'], [])
                self.assertEqual(value['reads'], [])
                self.assertFalse(value['steps'])

    def test_zero_and_nonzero_paths_retain_r0_generation_into_suffix(self):
        for name in ('join-carry-00-00', 'join-nonzero-00-0'):
            prefix, corridor, suffix = self.calculate(name)['inheritedResults']
            generation = prefix['state']['generations']['0208']
            self.assertIsNotNone(generation)
            for result in (corridor, suffix):
                self.assertEqual(result['state']['generations']['0208'], generation)
                self.assertEqual(result['state']['memory']['0208'], prefix['state']['memory']['0208'])
                self.assertTrue(all(not (row['space'] == 'DATA'
                    and row['address'] <= 0x0208 < row['address'] + row['widthBits'] // 8)
                    for row in result['journal']))
            inputs = [row for row in suffix['reads'] if row['pc'] == 0x608F and row['address'] == 0x0208]
            self.assertEqual([row['generations'] for row in inputs], [[generation]])

    def test_pswh_undefined_flags_survive_without_fabricated_complement(self):
        result = self.calculate('join-correlated-program-0-1')
        _, corridor, suffix = result['inheritedResults']
        xor = next(row for row in corridor['steps'] if row['pc'] == 0x6016)
        self.assertEqual([xor['afterRegisters'][key] for key in ('cf', 'zf', 'hc')], [None, None, None])
        latch = next(row for row in corridor['steps'] if row['pc'] == 0x6019)
        self.assertNotIn('4', latch['afterOtherPswKnownBits'])
        self.assertEqual(corridor['boundary'], 0x608F)
        self.assertEqual(suffix['boundary'], 0x609C)
        self.assertEqual(suffix['status'], 'IndeterminateBranch')
        self.assertFalse(result['compositionEstablished'])

    def test_correlation_reuses_retained_carry_between_latch_and_branch(self):
        for name, bit in (('middle-carry-00-00', 0), ('middle-carry-80-80', 1)):
            result = self.calculate(name)
            latch = next(row for row in result['steps'] if row['pc'] == 0x7B45)
            branch = next(row for row in result['steps'] if row['pc'] == 0x7B48)
            self.assertEqual(latch['afterRegisters']['cf'], bit)
            self.assertEqual(branch['afterRegisters']['cf'], bit)
            self.assertEqual(branch['next'], 0x7B4F if bit == 0 else 0x7B4A)
            self.assertTrue(result['correlatedPredicates'])

    def test_selected_pointer_bank_and_same_value_write_generations(self):
        result = self.calculate('middle-nonzero-00-0')
        pointer = [row for row in result['journal'] if row['kind'] == 'PointingRegisterWrite']
        self.assertTrue(pointer)
        self.assertTrue(all(row['address'] == 0x84 + 8 * 6 and row['widthBits'] == 16 for row in pointer))
        same = [row for row in result['journal'] if row.get('sameValue') is True]
        self.assertTrue(same)
        self.assertTrue(all(row['afterGeneration'] not in row['beforeGeneration'] for row in same))

    def test_prefix_refusal_does_not_invoke_corridor_or_suffix(self):
        for name in ('join-bank-None', 'join-prefix-noInterference-False', 'join-lrb-None'):
            result = self.calculate(name)
            self.assertFalse(result['compositionEstablished'])
            self.assertEqual([row['stage'] for row in result['stageBoundaries']], ['Prefix'])
            self.assertEqual(len(result['inheritedResults']), 1)

    def test_nested_children_and_input_are_preserved(self):
        case = self.corpus['join-carry-00-00']
        query = deepcopy(case['input'])
        original = deepcopy(query)
        actual = OPERATIONS[case['operation']](query)
        wanted = reference_record(case)['output']
        self.assertEqual(query, original)
        self.assertTrue(canonical(actual['inheritedResults']) == canonical(wanted['inheritedResults']))
        self.assertTrue(all(row['ordinal'] == ordinal for ordinal, row in enumerate(actual['journal'], 1)))

    def test_execution_authority_refuses_promoted_nested_observations(self):
        actual = self.calculate('join-carry-00-00')
        self.assertEqual({key: actual[key] for key in AUTHORITY}, AUTHORITY)
        for field, forged in (('actualReturnExecution', {'pc': 0x27D3}),
                              ('actualFramePop', {'pc': 0x60E4}),
                              ('actualBufferWrite', 1), ('actualTxIrqDelivery', True),
                              ('actualCpuExecutions', False)):
            value = deepcopy(actual)
            value['inheritedResults'][-1][field] = forged
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_authority(value)


if __name__ == '__main__':
    unittest.main()
