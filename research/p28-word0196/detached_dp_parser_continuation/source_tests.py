"""Source equations and refusal controls for detached DP state."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import unittest

from .analysis import AUTHORITY, canonical, load_contract, operations, record, validate_contract
from .continuation import detached_02b0_02b2_transform
from .corpus import MAP_201, cases, qualification, snapshot
from .data_access import indirect_data_address_qualification
from .reference_oracle import expected


class DetachedDpSourceTests(unittest.TestCase):
    def test_exact_instruction_extents(self):
        inventory = json.loads(Path(__file__).with_name('source_inventory.json').read_bytes())
        self.assertEqual([(row['pc'], row['length'], row['endExclusive']) for row in inventory['sites']],
                         [('02AE', 2, '02B0'), ('02B0', 1, '02B1'), ('02B1', 1, '02B2'),
                          ('02B2', 2, '02B4'), ('02B4', 1, '02B5'), ('02B5', 2, '02B7'),
                          ('02B7', 1, '02B8'), ('02B8', 2, '02BA'), ('02C2', 3, '02C5'),
                          ('02C5', 1, '02C6'), ('02C6', 2, '02C8')])

    def test_word_move_independent_of_incoming_dd(self):
        for dd in (None, 0, 1):
            query = snapshot(0x03F4, registers={'dd': dd}, scb=7)
            frozen = deepcopy(query)
            out = detached_02b0_02b2_transform(query)
            self.assertEqual(query, frozen)
            first, loaded = out['steps'][0]['state']['registers'], out['steps'][1]['state']['registers']
            self.assertEqual((first['dd'], first['zf'], first['cf'], first['hc']), (dd, None, 1, 1))
            self.assertEqual((loaded['dd'], loaded['zf'], loaded['cf'], loaded['hc']), (1, 0, 1, 1))
            self.assertEqual(out['reads'][0]['space'], 'REGISTER')
            self.assertEqual(out['reads'][0]['address'], 0x00BC)
            self.assertEqual(out['reads'][0]['value'], 0x03F4)
            self.assertEqual(out['journal'][0]['afterBytes'], [0xF4, 3])

    def test_three_paths_keep_distinct_pointer_writers_and_exact_stops(self):
        for word, pcs, address, width, stop in (
            (0x0200, [0x02B0, 0x02B1, 0x02B2, 0x02B4, 0x02B5, 0x02B7], 0x0200, 16, 0x02B8),
            (0x0201, [0x02B0, 0x02B1, 0x02B2, 0x02B4, 0x02B5, 0x02C5], 0x0201, 8, 0x02C6),
            (0, [0x02B0, 0x02B1, 0x02B2, 0x02C2, 0x02C5], 0x035C, 8, 0x02C6),
        ):
            out = detached_02b0_02b2_transform(snapshot(word))
            self.assertEqual([row['pc'] for row in out['steps']], pcs)
            self.assertEqual((out['pointer']['value'], out['reads'][-1]['address'], out['reads'][-1]['widthBits'],
                              out['stopPc']), (address, address, width, stop))
            self.assertEqual([row['pc'] for row in out['journal']], [0x02B0] if word else [0x02B0, 0x02C2])
            if word:
                shifted = out['steps'][3]['state']['registers']
                self.assertEqual((shifted['al'], shifted['ah'], shifted['cf'], shifted['zf']),
                                 ((word // 2) & 255, (word // 2) >> 8, word & 1, 0))
            self.assertEqual(out['steps'][2]['predicateEvidence']['generation'], 'M2dj:02B1:ZF')
            if width == 8:
                self.assertEqual(out['state']['registers']['dd'], 0)

    def test_partial_knowledge_never_chooses_unknown_branch_or_pointer(self):
        for query, stop, status in (
            (snapshot(None, al=0, ah=None), 0x02B2, 'IndeterminateBranch'),
            (snapshot(None, ah=3, reg_bits={'al': {'1': 1}}), 0x02B5, 'IndeterminateBranch'),
            (snapshot(None, ah=3, reg_bits={'al': {'0': 0, '1': 1}}), 0x02B7, 'UnqualifiedIndirectDataRead'),
        ):
            out = detached_02b0_02b2_transform(query)
            self.assertEqual((out['status'], out['stopPc']), (status, stop))
            self.assertEqual([row['space'] for row in out['reads']], ['REGISTER'])
            if status == 'IndeterminateBranch':
                self.assertIsNone(out['steps'][-1]['next'])
                self.assertIsNone(out['steps'][-1]['branchTaken'])

    def test_same_value_and_self_alias_share_current_byte_generations(self):
        out = detached_02b0_02b2_transform(snapshot(0x0084, old_dp=0x0084))
        event, = out['journal']
        self.assertTrue(event['sameValue'])
        self.assertNotEqual(event['afterGenerations'][0], event['afterGenerations'][1])
        self.assertNotEqual(event['beforeGenerations'], event['afterGenerations'])
        self.assertEqual(out['reads'][-1]['generations'], event['afterGenerations'])
        self.assertEqual(out['reads'][-1]['value'], 0x0084)
        self.assertEqual(out['pointer']['generations'], event['afterGenerations'])

    def test_qualified_alias_references_current_r4_and_r5_bytes(self):
        out = detached_02b0_02b2_transform(snapshot())
        self.assertEqual(out['qualification']['localAliases'], [
            {'address': 0x03F4, 'register': 'r4', 'lrb': 0x7E},
            {'address': 0x03F5, 'register': 'r5', 'lrb': 0x7E},
        ])
        self.assertEqual(out['reads'][-1]['generations'], ['InventedData:03F4', 'InventedData:03F5'])
        self.assertEqual(out['a16']['value'], 0x1231)
        old_map = detached_02b0_02b2_transform(snapshot(mapping=MAP_201))
        self.assertEqual((old_map['stopPc'], old_map['reason']), (0x02B7, 'ExternalDataApplicabilityUnknown'))
        self.assertEqual(len(old_map['reads']), 1)

    def test_byte_and_word_alignment_are_distinct_without_wrap(self):
        for address, pc, effective, count in (
            (0x0201, 0x02B7, 0x0200, 2), (0x0201, 0x02C5, 0x0201, 1),
            (0xFFFF, 0x02B7, 0xFFFE, 2), (0xFFFF, 0x02C5, 0xFFFF, 1),
        ):
            result = indirect_data_address_qualification(qualification(address, pc=pc))
            self.assertEqual(result['effectiveAddress'], effective)
            self.assertEqual([row['address'] for row in result['byteObligations']],
                             list(range(effective, effective + count)))

    def test_unqualified_peripheral_blocks_entire_word_before_read(self):
        for pointer, classification in ((0x0051, 'WriteOnlyRegisterReadBlocked'),
                                        (0x0054, 'UnresolvedReadSideEffect'),
                                        (0x0055, 'UnresolvedReadSideEffect'),
                                        (0x0056, 'PotentialSfrRead')):
            out = detached_02b0_02b2_transform(snapshot(pointer, data={'0055': 0x66}))
            self.assertEqual(out['qualification']['classification'], classification)
            self.assertEqual(out['qualification']['sourceBytes'], [])
            self.assertEqual([row['pc'] for row in out['reads']], [0x02B1])
            self.assertIsNone(out['executionAuthority']['actualSrbufRead'])

    def test_equal_numeric_pointer_does_not_bypass_generation_or_alias_history(self):
        query = qualification()
        for mutation, reason in (
            ({'expectedDpGenerations': ['OldLow', 'OldHigh']}, 'PointerGenerationMismatch'),
            ({'interveningWrites': [{'address': 0x0085, 'widthBits': 16, 'generation': 'InventedData:0085'}]},
             'InterveningDpWriteOverlap'),
            ({'interveningWrites': [{'address': 0x03F5, 'widthBits': 16, 'generation': 'DifferentWriter'}]},
             'InterveningTargetWriteOverlap'),
            ({'interveningWrites': [{'address': None, 'widthBits': 8, 'generation': 'UnknownWriter'}]},
             'UnknownInterveningWriteFootprint'),
        ):
            out = indirect_data_address_qualification({**query, **mutation})
            self.assertEqual(out['classification'], reason)
            self.assertFalse(out['allowed'])
            self.assertEqual(out['sourceGenerations'], [])

    def test_closed_input_rejects_fabricated_pointer_or_hardware_evidence(self):
        for key in ('dp', 'actualSrbufRead', 'actualReceivedByte', 'actualRxReadyAcknowledgement',
                    'actualIrqDelivery', 'actualReturnExecution', 'actualFramePop', 'actualStbufWrite',
                    'actualIeWrite', 'cpuInstructionRetirements', 'exactC8Rule'):
            out = detached_02b0_02b2_transform({**snapshot(), key: True})
            self.assertEqual(out['status'], 'RefusedSourcePremise')
            self.assertEqual((out['steps'], out['reads'], out['journal']), ([], [], []))
            self.assertEqual(out['executionAuthority'], dict(AUTHORITY))
        for query in (snapshot(scb=None), snapshot(scb=None, scb_bits={'0': 1})):
            out = detached_02b0_02b2_transform(query)
            self.assertIsNone(out['pointer'])
            self.assertEqual(out['reason'], 'SelectedPointingBankUnknown')

    def test_full_frozen_record_identity(self):
        functions, lines = operations(), []
        for case in cases():
            with self.subTest(case=case['id']):
                result = functions[case['operation']](case['input'])
                self.assertEqual(canonical(result), canonical(expected(case)))
                self.assertEqual(result['executionAuthority'], dict(AUTHORITY))
                lines.append(canonical(record(case, result)))
        raw = b''.join(lines)
        self.assertEqual(load_contract()['canonical'], {'records': len(lines), 'bytes': len(raw),
                         'sha256': sha256(raw).hexdigest(), 'canonicalFieldExclusions': []})

    def test_changed_source_identity_rejects_fake_extent_or_predicate(self):
        source = json.loads(Path(__file__).with_name('source_inventory.json').read_bytes())
        contract = load_contract()
        path = next(key for key in contract['sources'] if 'detached_dp_parser_continuation/source_inventory' in key)
        for row, key, value in ((1, 'length', 2), (2, 'form', 'L A,[DP]'), (3, 'pc', '02B3'),
                                (5, 'form', 'JEQ rel8'), (6, 'form', 'LB A,[DP]')):
            changed_source = deepcopy(source)
            changed_source['sites'][row][key] = value
            changed = deepcopy(contract)
            changed['sources'][path] = sha256(canonical(changed_source)).hexdigest()
            with self.assertRaisesRegex(ValueError, 'FrozenSourceBindingChanged'):
                validate_contract(changed)
