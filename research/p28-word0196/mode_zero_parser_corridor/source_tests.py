"""Exact source effects, path proofs and refusals without a CPU or hardware."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import unittest

from length_checksum_dataflow.dispatch import parser_step

from .analysis import AUTHORITY, canonical, load_contract, operations, record, validate_contract
from .composition import mode_zero_parser_step
from .corpus import cases, detached, parser, suffix
from .corridor import mode_zero_corridor_029d, mode_zero_detached_suffix
from .reference_oracle import expected


class ModeZeroSourceTests(unittest.TestCase):
    def test_reviewed_source_extents_and_distinct_02ae(self):
        inventory = json.loads(Path(__file__).with_name('source_inventory.json').read_bytes())
        self.assertEqual([(row['pc'], row['length']) for row in inventory['sites']],
                         [('021F', 3), ('029D', 1), ('029E', 3), ('02A1', 2), ('02A3', 2),
                          ('02A5', 3), ('02A8', 2), ('02AA', 2), ('02AC', 2), ('02AE', 2)])
        out = mode_zero_detached_suffix(suffix())
        self.assertEqual((out['stopPc'], out['peripheralObligation']['address']), (0x02AE, 0x0055))
        self.assertIsNone(mode_zero_detached_suffix({**suffix(), 'entryPc': 0x28AE})['stopPc'])

    def test_taken_mode_zero_preserves_status_and_does_not_reseed(self):
        for value, bits in ((0, {}), (0x40, {}), (None, {'0356.1': 0}), (None, {'0356.1': 0, '0356.6': 1})):
            query = parser(value, bits=bits)
            before = deepcopy(query)
            out = mode_zero_parser_step(query)
            prefix, handoff, result = out['prefix'], out['handoff'], out['corridor']
            self.assertEqual(query, before)
            self.assertEqual((prefix['steps'][0]['pc'], prefix['steps'][0]['next']), (0x021F, 0x029D))
            self.assertEqual([row['pc'] for row in prefix['steps'] + result['steps']], [0x021F, 0x029D])
            self.assertEqual((prefix['journal'], result['journal'], result['reads']), ([], [], []))
            self.assertFalse(handoff['reseeded'])
            self.assertEqual(handoff['statusGeneration'], query['statusGeneration'])
            for key in ('memory', 'knownBits', 'generations'):
                self.assertEqual(result['state'][key], query['snapshot'][key])
            self.assertEqual((out['entryClass'], out['stopPc']), ('ConfirmedEntryFrom021F', 0x029E))

    def test_unknown_mode_has_no_successor_and_ordinary_is_frozen(self):
        out = mode_zero_parser_step(parser(None, bits={'0356.6': 1}))
        self.assertEqual(out['status'], 'IndeterminateBranchAt021F')
        self.assertIsNone(out['prefix']['steps'][0]['next'])
        self.assertEqual(out['prefix']['journal'], [])
        self.assertIsNone(out['corridor'])
        for status in (2, 0x42):
            query = parser(status)
            out = mode_zero_parser_step(query)
            self.assertEqual(out['entryClass'], 'FrozenM2coOrdinaryPath')
            self.assertEqual(out['prefix'], parser_step(query['snapshot']))
            self.assertEqual(out['steps'], [])

    def test_detached_clrb_changes_only_al_dd_zf(self):
        query = detached({'lrb': None, 'scb': None, 'cf': 0, 'hc': 1, 'ah': 255})
        out = mode_zero_corridor_029d(query)
        expected = {**query['state']['registers'], 'al': 0, 'dd': 0, 'zf': 1}
        self.assertEqual(out['state']['registers'], expected)
        self.assertEqual(out['entryClass'], 'DetachedEntry029D')
        self.assertEqual((out['reads'], out['journal']), ([], []))
        self.assertEqual(out['peripheralObligation']['access'], 'ReadModifyWrite')
        self.assertIsNone(out['peripheralObligation']['actualAccess'])
        self.assertEqual(out['stopBoundary'], 'STOP_BEFORE_UNQUALIFIED_SRSTAT_RMW_029E')

    def test_both_immediate_byte_add_domains(self):
        for branch, op, amount, stop in ((0x02A1, 0x02A3, 1, 0x02A5), (0x02A8, 0x02AA, 2, 0x02AE)):
            for before in range(256):
                out = mode_zero_detached_suffix(suffix(branch, 1, before))
                carry, low = divmod(before + amount, 256)
                self.assertEqual([step['pc'] for step in out['steps'][:2]], [branch, op])
                r = out['state']['registers']
                self.assertEqual((r['al'], r['cf'], r['hc'], r['zf'], r['dd']),
                                 (low, carry, int((before % 16) + amount >= 16), int(low == 0), 0))
                self.assertEqual(out['stopPc'], stop)
                self.assertEqual(out['reads'], [])

    def test_taken_branches_preserve_distinct_histories(self):
        for pc, successor, stop in ((0x02A1, 0x02A5, 0x02A5), (0x02A8, 0x02AC, 0x02AE)):
            out = mode_zero_detached_suffix(suffix(pc, 0, 0x42, 0x42))
            self.assertTrue(out['steps'][0]['branchTaken'])
            self.assertEqual(out['steps'][0]['next'], successor)
            self.assertEqual(out['stopPc'], stop)
            self.assertEqual(out['steps'][0]['predicateEvidence']['sourceClass'],
                             'DetachedSymbolicPremise_NoSrstatAccess')
        write, = out['journal']
        self.assertEqual((write['address'], write['alias'], write['sameValue']), (7, 'DATA0007=AH', True))
        self.assertNotEqual(write['beforeGeneration'], write['afterGeneration'])
        self.assertNotIn('0007', out['state']['memory'])

    def test_partial_byte_retained_through_arithmetic_and_alias(self):
        out = mode_zero_detached_suffix(suffix(al=None, al_bits={'0': 0, '1': 0, '2': 0}))
        state = out['state']
        self.assertEqual(state['registerKnownBits']['al'], {'0': 0, '1': 1, '2': 0})
        self.assertEqual(state['registerKnownBits']['ah'], state['registerKnownBits']['al'])
        self.assertIsNone(state['registers']['ah'])
        self.assertEqual(state['registers']['zf'], 0)

    def test_unproved_flag_or_generation_never_chooses_branch(self):
        stale = suffix()
        stale['statusHypothesis']['generation'] = None
        for query in (stale, suffix(old=None), suffix(registers={'zf': None})):
            out = mode_zero_detached_suffix(query)
            self.assertEqual(out['status'], 'IndeterminateBranch')
            self.assertIsNone(out['steps'][0]['next'])
            self.assertEqual((out['reads'], out['journal']), ([], []))
        conflict = mode_zero_detached_suffix(suffix(registers={'zf': 1}))
        self.assertEqual(conflict['reason'], 'ContradictoryDetachedZfPremise')
        self.assertEqual(conflict['steps'], [])

    def test_wrong_dd_and_missing_input_generation_preserve_prefix(self):
        missing = suffix()
        del missing['state']['registerGenerations']['al']
        for query, pc, reason in ((missing, 0x02AA, 'AlSourceGenerationMissing'),
                                  (suffix(registers={'dd': 1}), 0x02AA, 'ByteFormDd0Required'),
                                  (suffix(old=0, registers={'dd': None}), 0x02AC, 'ByteFormDd0Required')):
            out = mode_zero_detached_suffix(query)
            self.assertEqual((out['reason'], out['stopPc']), (reason, pc))
            self.assertEqual(len(out['steps']), 1)
            self.assertEqual(out['state'], query['state'])
            self.assertEqual(out['journal'], [])

    def test_hardware_claims_do_not_admit_source_scope(self):
        for key in ('actualSrbufRead', 'actualReceivedByte', 'actualRxReady', 'actualRxReadyAcknowledgement',
                    'actualRxReadyReassertion', 'actualIrqDelivery', 'actualFramePop', 'actualStbufWrite',
                    'actualIeWrite', 'cpuInstructionRetirements', 'actualMcuIdentity', 'exactC8Rule'):
            out = mode_zero_detached_suffix({**suffix(), key: True})
            self.assertEqual(out['status'], 'RefusedSourcePremise')
            self.assertEqual((out['steps'], out['reads'], out['journal']), ([], [], []))
            self.assertEqual(out['executionAuthority'], dict(AUTHORITY))

    def test_frozen_contract_and_canonical_records(self):
        functions, lines = operations(), []
        for case in cases():
            with self.subTest(case=case['id']):
                result = functions[case['operation']](case['input'])
                self.assertEqual(canonical(result), canonical(expected(case)))
                self.assertEqual(result['executionAuthority'], dict(AUTHORITY))
                self.assertFalse(result['reads'])
                lines.append(canonical(record(case, result)))
        raw = b''.join(lines)
        self.assertEqual(load_contract()['canonical'], {'records': len(lines), 'bytes': len(raw),
                         'sha256': sha256(raw).hexdigest(), 'canonicalFieldExclusions': []})

    def test_changed_source_and_fake_hardware_sites_fail_frozen_binding(self):
        source = json.loads(Path(__file__).with_name('source_inventory.json').read_bytes())
        contract = load_contract()
        path = next(key for key in contract['sources'] if 'mode_zero_parser_corridor/source_inventory' in key)
        for row, key, value in ((0, 'successors', ['0295']), (1, 'length', 2), (2, 'form', 'LB A,N8'),
                                (6, 'successors', ['0255']), (9, 'pc', '28AE'), (9, 'memorySpace', 'PROGRAM')):
            changed_source = deepcopy(source)
            changed_source['sites'][row][key] = value
            changed = deepcopy(contract)
            changed['sources'][path] = sha256(canonical(changed_source)).hexdigest()
            with self.assertRaisesRegex(ValueError, 'FrozenSourceBindingChanged'):
                validate_contract(changed)
