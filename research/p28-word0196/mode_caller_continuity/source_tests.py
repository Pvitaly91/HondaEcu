"""Independent semantic comparisons; new implementation imports occur only in tests."""
from copy import deepcopy
import importlib
import unittest

from . import reference_oracle as reference
from .corpus import fixture, reaching_query, join_query, indexed_event, cases, partial, partial_slot, SOURCE_BINDING

MODULES = {'data03cb_indexed_writer': 'data03cb_writers', 'mode_producer_extended': 'mode_producer_extended',
    'configuration_caller': 'caller_cfg', 'configuration_reader_caller': 'caller_cfg',
    'data03cb_reaching_definitions': 'reaching_definitions', 'cross_block_source_join': 'cross_block_join'}


def resolve(operation):
    return getattr(importlib.import_module('.' + MODULES[operation], __package__), operation)


class SourceTests(unittest.TestCase):
    def check(self, operation, query):
        expected = reference.OPERATIONS[operation](deepcopy(query))
        actual = resolve(operation)(deepcopy(query))
        self.assertEqual(reference.canonical(expected), reference.canonical(actual))
        return actual

    def malformed(self, operation, query):
        with self.assertRaises(ValueError): reference.OPERATIONS[operation](deepcopy(query))
        with self.assertRaises(ValueError): resolve(operation)(deepcopy(query))

    def test_full_canonical_corpus_equality(self):
        ids = set()
        for case in cases():
            self.assertNotIn(case['id'], ids); ids.add(case['id'])
            expected = reference.record(case, reference.evaluate(case))
            actual = reference.record(case, resolve(case['operation'])(deepcopy(case['input'])))
            self.assertEqual(reference.canonical(expected), reference.canonical(actual), case['id'])

    def test_original_inputs_are_immutable(self):
        inputs = [(name, fixture('At60BD') if name == 'mode_producer_extended' else fixture())
            for name in tuple(MODULES)[:4]]
        inputs += [('data03cb_reaching_definitions', reaching_query()), ('cross_block_source_join', join_query())]
        for operation, query in inputs:
            before = deepcopy(query)
            resolve(operation)(query)
            self.assertEqual(reference.canonical(before), reference.canonical(query))

    def test_indexed_all_p2_values_and_flag_dependencies(self):
        for byte in range(256):
            q = fixture(); q['sfrReadbacks']['0024']['value'] = byte
            v = self.check('data03cb_indexed_writer', q); index = byte >> 5
            self.assertEqual(v['selectedIndex'], index)
            self.assertEqual([e['address'] for e in v['journal']], [0x80, 0x3CE + index, 0x3C6 + index])
            self.assertEqual((v['state']['registers']['cf'], v['state']['registers']['dd'], v['state']['registers']['ah']), ((byte >> 4) & 1, 0, 0))
            self.assertEqual(v['conditionalData03cbWriterEstablished'], index == 5)
            if byte == 0x10:
                shift = next(step for step in v['steps'] if step['pc'] == 0x5CA8)
                self.assertEqual((shift['afterRegisters']['al'], shift['afterRegisters']['zf']), (0, 0))

    def test_indexed_unknown_index_preserves_prefix_and_read_order(self):
        q = fixture(); partial_slot(q['sfrReadbacks']['0024'], {})
        v = self.check('data03cb_indexed_writer', q)
        self.assertEqual((v['boundary'], v['reason'], len(v['steps']), len(v['journal'])), (0x5CAF, 'IndexedAddressNotEstablished', 7, 1))
        self.assertEqual([x['address'] for x in v['reads'] if x['space'] == 'SYMBOLIC_SFR_READBACK'], [0x24, 0x63])
        self.assertTrue(all(e['address'] < 0x3C6 for e in v['journal']))

    def test_indexed_known_index_from_partial_p2_and_same_value_stores(self):
        q = fixture(); partial_slot(q['sfrReadbacks']['0024'], {5: 1, 6: 0, 7: 1})
        q['memory'].update({'03D3': 0x55, '03CB': 0x80})
        v = self.check('data03cb_indexed_writer', q)
        self.assertEqual(v['selectedIndex'], 5); self.assertIsNone(v['state']['registers']['cf'])
        self.assertEqual([e['sameValue'] for e in v['journal'][-2:]], [True, True])
        self.assertNotEqual(v['state']['generations']['03CB'], q['generations']['03CB'])

    def test_indexed_bank_aliases_and_first_required_scb_gate(self):
        for bank in range(8):
            q = fixture(); q['registers']['scb'] = bank
            v = self.check('data03cb_indexed_writer', q)
            self.assertEqual(v['journal'][0]['address'], 0x80 + 8 * bank)
        q = fixture(); q['registers']['scb'] = None
        v = self.check('data03cb_indexed_writer', q)
        self.assertEqual((v['boundary'], len(v['steps']), v['journal']), (0x5CAC, 5, []))

    def test_mode_all03cb_values_frozen_history_and_new_word(self):
        for byte in (0, 1, 0x7F, 0x80, 0xFE, 0xFF):
            q = fixture('At60BD'); q['memory']['03CB'] = byte
            v = self.check('mode_producer_extended', q)
            self.assertEqual((v['state']['memory']['0356'] >> 1) & 1, byte >> 7)
            self.assertEqual((v['state']['memory']['0382'], v['state']['memory']['0383']), (0, 5))
            self.assertIsNone(v['inheritedResults'][0]['state']['registers']['zf'])
            self.assertEqual((v['state']['registers']['zf'], v['state']['registers']['dd'], v['boundary']), (0, 1, 0x60E4))

    def test_mode_nonzero_and_unknown_r0_stop_before_program_read(self):
        for byte, boundary in ((1, 0x60C2), (None, 0x60C0)):
            q = fixture('At60BD'); q['memory']['0208'] = byte
            v = self.check('mode_producer_extended', q)
            self.assertEqual(v['boundary'], boundary); self.assertEqual(v['journal'], [])
            self.assertEqual(len(v['steps']), 2); self.assertEqual(v['inheritedResults'], [])

    def test_mode_suffix_unknown_guard_and_page_gate_keep_prefix(self):
        q = fixture('Compare3cb'); q['memory']['0216'] = None
        v = self.check('mode_producer_extended', q)
        self.assertEqual((v['boundary'], v['state']['registers']['ah']), (0x60DA, 7))
        self.assertNotIn(0x60E0, [s['pc'] for s in v['steps']])
        q = fixture('SymbolicCarryTail'); q['registers']['lrb'] = None
        v = self.check('mode_producer_extended', q)
        self.assertEqual((v['reason'], v['boundary'], v['state']['registers']['zf']), ('LocalPage0216NotEstablished', 0x60DA, 0))
        self.assertEqual(len(v['inheritedResults']), 1)

    def test_configuration_retains_order_and_stops_before_external_read(self):
        for bit, con in ((0, 0x31), (1, 0x1C)):
            q = fixture(); q['memory']['0356'] = bit << 1
            v = self.check('configuration_caller', q)
            self.assertEqual((v['journal'][0]['address'], v['journal'][0]['after']), (0x2CD, 0x32))
            self.assertEqual(v['state']['configurationIntents']['0050']['value'], con)
            self.assertEqual((v['pointerState']['value'], v['boundary']), (0x4700, 0x2891))
            self.assertFalse(any(r['address'] == 0x4700 for r in v['reads']))

    def test_reader_adscan_precheck_controls_parent_call(self):
        q = fixture(); q['sfrReadbacks']['0058']['value'] = 0
        v = self.check('configuration_reader_caller', q)
        self.assertEqual((v['boundary'], v['state']['memory']['00F5'], v['inheritedResults']), (0x3FB5, 0x50, []))
        self.assertEqual([r['address'] for r in v['reads'] if r['space'] == 'SYMBOLIC_SFR_READBACK'], [0x58])
        q = fixture(); partial_slot(q['sfrReadbacks']['0058'], {})
        v = self.check('configuration_reader_caller', q)
        self.assertEqual((v['boundary'], v['journal']), (0x3FD2, []))

    def test_reader_failure_and_success_continuations_have_distinct_effects(self):
        q = fixture(); q['sfrReadbacks']['0050']['value'] = 0
        v = self.check('configuration_reader_caller', q)
        self.assertEqual((v['boundary'], v['journal'][-1]['address']), (0x3FB5, 0xF5))
        q = fixture(); q['memory'].update({'00FA': 0x34, '00FB': 0x12})
        v = self.check('configuration_reader_caller', q)
        self.assertEqual((v['boundary'], v['state']['registers']['al'], v['state']['registers']['ah'], v['state']['registers']['dd']), (0x3FF9, 0x34, 0x12, 1))
        self.assertFalse(any(e['address'] == 0x1A for e in v['journal']))

    def test_reaching_alignment_same_value_and_generation_competition(self):
        q = reaching_query(); q['events'].append({'kind': 'AlternateStore', 'id': 'word', 'address': 0x3CB, 'widthBits': 16, 'value': 0x8077, 'generation': 'Other2'})
        v = self.check('data03cb_reaching_definitions', q)
        self.assertEqual((v['journal'][-1]['address'], v['journal'][-1]['sameDeclaredValue']), (0x3CA, True))
        self.assertEqual(v['state']['reachingDefinitions']['relation'], 'CompetingWriter')
        self.assertEqual(v['state']['lastSlot']['generation'], 'Other2')

    def test_reaching_stale_unknown_and_unproved_paths_refuse_lineage(self):
        for field, value, relation in (('requestedGeneration', 'Stale', 'StaleGeneration'), ('noInterference', None, 'UnknownInterference'), ('path', 'WriterTo60C9', 'ReachingPathUnestablished')):
            q = reaching_query(); q[field] = value
            v = self.check('data03cb_reaching_definitions', q)
            self.assertEqual(v['state']['reachingDefinitions']['relation'], relation)
        q = reaching_query(); q['events'][0]['generation'] = q['initial']['generation']
        v = self.check('data03cb_reaching_definitions', q)
        self.assertEqual((v['reason'], v['journal'], v['boundary']), ('WriterGenerationReused', [], 0))

    def test_join_exact_state_handoffs_and_frozen_children_remain_unchanged(self):
        q = join_query(); v = self.check('cross_block_source_join', q)
        self.assertEqual((v['status'], v['boundary']), ('CompleteConditional', 0x3FF9))
        self.assertEqual(len(v['inheritedResults']), 4)
        writer, mode, config, reader = v['inheritedResults']
        self.assertEqual(writer['state']['generations']['03CB'], mode['state']['generations']['03CB'])
        self.assertEqual(config['state']['configurationIntents']['0050']['value'], 0x1C)
        self.assertEqual(reader['steps'][0]['afterRegisters']['al'], 0x10)
        self.assertEqual(v['journal'][3]['ordinal'], 4)
        self.assertEqual(v['journal'][3]['afterGeneration'], mode['journal'][0]['afterGeneration'])
        self.assertIsNone(v['state']['actualNativeContinuity'])

    def test_join_missing_handoffs_and_wrong_stage_order_stop_before_next_stage(self):
        q = join_query(); q['handoffs']['writerToMode'] = None
        v = self.check('cross_block_source_join', q)
        self.assertEqual((v['boundary'], len(v['inheritedResults'])), (0x5CB7, 1))
        q = join_query(); q['stageOrder'].reverse()
        v = self.check('cross_block_source_join', q)
        self.assertEqual((v['reason'], v['journal'], v['inheritedResults']), ('UnreviewedStageOrder', [], []))

    def test_deep_authority_is_shape_aware_for_frozen_m2cr(self):
        value = self.check('cross_block_source_join', join_query())
        def walk(node):
            if type(node) is dict:
                if 'procedure' in node and 'status' in node:
                    self.assertIsNone(node['actualHardwareObservation']); self.assertEqual(type(node['cpuInstructionRetirements']), int)
                    self.assertEqual(node['cpuInstructionRetirements'], 0); self.assertEqual(node['executionStatus'], 'EXECUTION_BLOCKED'); self.assertIs(node['firmwareReady'], False)
                    if node['procedure'] == 'stbuf_boundary_obligations':
                        for key in ('actualBufferWrite', 'actualAcceptance', 'actualTransmission', 'actualCompletion', 'actualTxIrq'): self.assertIsNone(node['state'][key])
                    else:
                        for key, expected in reference.AUTHORITY.items(): self.assertEqual(node[key], expected)
                for child in node.values(): walk(child)
            elif type(node) is list:
                for child in node: walk(child)
        walk(value)

    def test_binding_types_and_native_claims_never_promote_authority(self):
        for op, factory in (('data03cb_reaching_definitions', reaching_query), ('cross_block_source_join', join_query)):
            q = factory(); q['sourceBinding'] = False; self.malformed(op, q)
            q = factory(); q['sourceBinding'] = {**SOURCE_BINDING, 'base': True}
            self.assertEqual(self.check(op, q)['reason'], 'SourceBindingMismatch')
            for claim in ('NativeOwner', 'ActualHardware', 'RuntimeAdmission'):
                q = factory(); q['claim'] = claim
                v = self.check(op, q); self.assertEqual((v['status'], v['journal']), ('OutsideVerifiedScope', []))
        q = join_query(); q['stbufQuery']['claim'] = 'ActualBufferWrite'
        v = self.check('cross_block_source_join', q)
        self.assertEqual((v['reason'], v['journal'], v['boundary']), ('NestedStbufObligationRefused', [], 0x5CA5))
        q = join_query(); q['stbufQuery']['premises'] = {key: None for key in q['stbufQuery']['premises']}
        v = self.check('cross_block_source_join', q)
        self.assertEqual(v['status'], 'CompleteConditional')
        self.assertEqual(v['stbufObligations']['status'], 'IndeterminateObligation')

    def test_closed_shapes_partial_contradictions_and_nested_validation(self):
        q = fixture(); q['extra'] = 1; self.malformed('data03cb_indexed_writer', q)
        q = fixture(); q['knownBits']['03CB.7'] = 0; self.malformed('data03cb_indexed_writer', q)
        q = reaching_query(); q['events'].append(deepcopy(q['events'][0])); self.malformed('data03cb_reaching_definitions', q)
        q = join_query(); q['claim'] = 'NativeOwner'; q['stbufQuery']['extra'] = 1; self.malformed('cross_block_source_join', q)


if __name__ == '__main__':
    unittest.main()
