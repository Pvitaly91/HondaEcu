"""Exact source equations, refusal behavior and distinct boundary obligations."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import unittest

from .analysis import AUTHORITY, canonical, load_contract, operations, record, validate_contract
from .corpus import PREMISES, cases, detached, selector_source
from .composition import epilogue_0244_ingress_comparison, m2df_candidate_to_detached_0240
from .fragment import detached_0240_0241_transform
from .reference_oracle import expected


class DetachedSourceTests(unittest.TestCase):
    def test_reviewed_four_instruction_extents(self):
        inventory = json.loads(Path(__file__).with_name('source_inventory.json').read_bytes())
        self.assertEqual([(row['pc'], row['length'], row['endExclusive']) for row in inventory['sites']],
                         [('023E', 2, '0240'), ('0240', 1, '0241'), ('0241', 3, '0244'), ('0244', 2, '0246')])
        self.assertEqual([(row['from'], row['to'], row['branchFlags']) for row in inventory['edges']],
                         [('023E', '0240', []), ('0240', '0241', []), ('0241', '0244', [])])
        self.assertEqual(inventory['otherIngress']['from'], '024F')
        self.assertFalse(inventory['otherIngress']['mergedWithDetached'])
        self.assertTrue(all(not row['programOperandAccesses'] for row in inventory['sites']))

    def test_both_byte_domains_and_exact_flag_lifetime(self):
        for value in range(256):
            out = detached_0240_0241_transform(detached(value, value, registers={'cf': 1, 'dd': 1}))
            before_sb = out['steps'][0]['state']['registers']
            after = out['state']['registers']
            self.assertEqual(out['state']['memory']['03F5'], (value + 1) & 255)
            self.assertEqual(before_sb['zf'], int(value == 255))
            self.assertEqual(after['hc'], int(value % 16 == 15))
            self.assertEqual(out['state']['memory']['0356'], value | 64)
            self.assertEqual(after['zf'], int(value & 64 == 0))
            self.assertEqual((after['cf'], after['dd']), (1, 1))
            self.assertEqual(out['journal'][1]['sameValue'], bool(value & 64))

    def test_same_value_rmw_keeps_a_new_generation(self):
        value = detached(255, 64)
        out = detached_0240_0241_transform(value)
        self.assertEqual([(row['pc'], row['address'], row['widthBits']) for row in out['reads']],
                         [(0x0240, 0x03F5, 8), (0x0241, 0x0356, 8)])
        inc, status = out['journal']
        self.assertEqual((inc['before'], inc['after']), (255, 0))
        self.assertEqual((status['before'], status['after'], status['sameValue']), (64, 64, True))
        self.assertNotEqual(status['beforeGeneration'], status['afterGeneration'])
        self.assertEqual(out['state']['generations']['0356'], status['afterGeneration'])
        self.assertEqual(value['state']['generations']['0356'], 'InventedStatus')

    def test_partial_state_and_dd_independence(self):
        value = detached(None, None, bits={'0356.6': 1, '0356.0': 0},
                         registers={'al': None, 'ah': 0x81, 'cf': None, 'dd': None})
        value['state']['registerKnownBits']['al'] = {'7': 1}
        out = detached_0240_0241_transform(value)
        registers, state = out['state']['registers'], out['state']
        self.assertEqual((registers['al'], registers['ah'], registers['cf'], registers['dd']), (None, 0x81, None, None))
        self.assertEqual(state['registerKnownBits']['al'], {'7': 1})
        self.assertEqual(state['knownBits'], {'0356.6': 1, '0356.0': 0})
        self.assertEqual((registers['zf'], registers['hc']), (0, None))
        self.assertIsNone(state['memory']['0356'])

    def test_no_alias_for_neighbor_or_unrelated_memory(self):
        value = detached(registers={'al': 0xFF, 'ah': 0, 'lrb': 0x007E})
        for key, byte in (('03F4', 0x82), ('0051', 0x12), ('00F8', 0x90)):
            value['state']['memory'][key] = byte
            value['state']['generations'][key] = 'Invented:' + key
        out = detached_0240_0241_transform(value)
        self.assertEqual(out['status'], 'ConditionalSourceArrivalAt0244')
        for key in ('03F4', '0051', '00F8'):
            self.assertEqual(out['state']['memory'][key], value['state']['memory'][key])
            self.assertEqual(out['state']['generations'][key], value['state']['generations'][key])
        self.assertEqual([row['pc'] for row in out['journal']], [0x0240, 0x0241])
        self.assertEqual(out['stopBoundary'], 'STOP_BEFORE_EPILOGUE_0244')

    def test_preserve_prefix_before_missing_status_generation(self):
        value = detached(0x0F)
        value['state']['generations']['0356'] = None
        out = detached_0240_0241_transform(value)
        self.assertEqual((out['stopPc'], out['reason']), (0x0241, 'RequiredDataGenerationMissing'))
        self.assertIsNone(out['stopBoundary'])
        self.assertEqual([row['pc'] for row in out['reads']], [0x0240])
        self.assertEqual(out['state']['memory'], {'03F5': 0x10, '0356': 2})
        self.assertEqual(out['state']['registers']['hc'], 1)

    def test_wrong_page_and_contradictory_active_alias_have_no_effects(self):
        wrong_page = detached(registers={'lrb': 0})
        wrong_page['state']['memory']['0056'] = 2
        wrong_page['state']['generations']['0056'] = 'InventedSrstat'
        contradictory = detached(registers={'scb': 1, 'usp': 0x0180})
        contradictory['state']['memory']['008E'] = 0
        contradictory['state']['generations']['008E'] = 'InventedWrongLowUsp'
        for query, reason in ((wrong_page, 'ExactReviewedLrb007ERequired'),
                              (contradictory, 'TypedSourceStateRequired')):
            out = detached_0240_0241_transform(query)
            self.assertEqual(out['reason'], reason)
            self.assertEqual((out['steps'], out['reads'], out['journal']), ([], [], []))

    def test_projection_is_dd0_cpu_frame_only(self):
        source = selector_source(r5=2, r2=7)
        out = m2df_candidate_to_detached_0240({'source': source, 'assumptions': PREMISES})
        self.assertEqual(out['status'], 'ConditionalCpuStateProjection')
        self.assertEqual(out['stopBoundary'], 'STOP_BEFORE_STBUF_023E')
        self.assertEqual((out['steps'], out['reads'], out['journal']), ([], [], []))
        self.assertEqual(out['projectedInput']['state']['registers'], source['result']['state']['registers'])
        self.assertEqual(out['projectedInput']['state']['generations'], source['result']['state']['generations'])
        result = detached_0240_0241_transform(out['projectedInput'])
        self.assertEqual(result['state']['memory']['03F5'], 3)
        self.assertEqual(result['state']['registers']['al'], 7)
        self.assertEqual(result['state']['memory']['03F6'], source['result']['state']['memory']['03F6'])
        self.assertIsNone(out['executionAuthority']['actualStbufWrite'])

    def test_fake_runtime_evidence_and_source_journal_are_refused(self):
        source = selector_source(r5=2, r2=7)
        for key in ('actualStbufWrite', 'actualTransmission', 'actualTxReady', 'actualTxCompletion',
                    'actualIrqDelivery', 'actualIeWrite', 'actualReturnExecution', 'actualFramePop',
                    'cpuInstructionRetirements', 'actualPeripheralOperations', 'exactC8Rule'):
            forged = deepcopy(source)
            forged['result'][key] = True
            out = m2df_candidate_to_detached_0240({'source': forged, 'assumptions': PREMISES})
            self.assertEqual(out['reason'], 'FrozenM2dfReplayMismatch')
            self.assertIsNone(out['projectedInput'])
            self.assertEqual(out['journal'], [])

    def test_two_0244_source_paths_keep_separate_generations(self):
        direct = selector_source(r5=5, r2=4)
        query = detached(4, 64, registers={'al': 5, 'ah': 0, 'cf': 0, 'dd': 0})
        out = epilogue_0244_ingress_comparison({'source': direct, 'detached': query})
        self.assertEqual(out['status'], 'DistinctSourceIngressCompared')
        self.assertEqual(out['fields']['registers.al']['relation'], 'Equal')
        for field in ('sourcePath', 'precedingWrites', 'generations.03F5'):
            self.assertIn(field, out['discrepancies'])
        self.assertIn('registers.ssp', out['unknown'])
        self.assertEqual((out['steps'], out['reads'], out['journal']), ([], [], []))

    def test_frozen_canonical_identity_and_refusals(self):
        data = []
        for case in cases():
            with self.subTest(case=case['id']):
                out = operations()[case['operation']](case['input'])
                self.assertEqual(canonical(out), canonical(expected(case)))
                self.assertEqual(out['executionAuthority'], dict(AUTHORITY))
                self.assertTrue(all(row['pc'] in (0x0240, 0x0241) for row in out['reads'] + out['journal']))
                data.append(canonical(record(case, out)))
        raw = b''.join(data)
        self.assertEqual(load_contract()['canonical'], {'records': len(data), 'bytes': len(raw),
                         'sha256': sha256(raw).hexdigest(), 'canonicalFieldExclusions': []})

    def test_reject_modified_instruction_inventory_binding(self):
        contract = load_contract()
        path = next(key for key in contract['sources'] if 'detached_post_stbuf_0240_0241/source_inventory' in key)
        source = json.loads(Path(__file__).with_name('source_inventory.json').read_bytes())
        for row, key, value in ((1, 'length', 2), (1, 'form', 'DECB r5'), (1, 'successors', ['0244']),
                                (2, 'pc', '0242'), (2, 'branchTarget', '024C'), (3, 'successors', ['0246'])):
            mutated = deepcopy(source)
            mutated['sites'][row][key] = value
            changed = deepcopy(contract)
            changed['sources'][path] = sha256(canonical(mutated)).hexdigest()
            with self.assertRaisesRegex(ValueError, 'FrozenSourceBindingChanged'):
                validate_contract(changed)
