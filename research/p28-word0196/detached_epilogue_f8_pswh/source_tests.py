"""Source equation and negative controls for the bounded software epilogue."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import unittest

from .analysis import AUTHORITY, canonical, load_contract, operations, record, validate_contract
from .corpus import cases, detached_query, direct_query, snapshot, write_event
from .epilogue import detached_epilogue_0244_0246
from .ingress import compare_epilogue_ingresses, epilogue_ingress_adapter
from .reference_oracle import expected


class EpilogueSourceTests(unittest.TestCase):
    def test_exact_source_extents_and_hard_stop(self):
        inventory = json.loads(Path(__file__).with_name('source_inventory.json').read_bytes())
        self.assertEqual([(row['pc'], row['length']) for row in inventory['sites']],
                         [('0244', 2), ('0246', 3), ('0249', 2), ('024B', 1)])
        result = detached_epilogue_0244_0246(snapshot())
        self.assertEqual([(row['pc'], row['next']) for row in result['steps']],
                         [(0x0244, 0x0246), (0x0246, 0x0249)])
        self.assertEqual(result['stopBoundary'], 'STOP_BEFORE_IE_WRITE_0249')
        self.assertEqual([(row['space'], row['address'], row['widthBits']) for row in result['reads']],
                         [('DATA', 0xF8, 16), ('REGISTER', 5, 8)])
        self.assertEqual([(row['space'], row['address'], row['widthBits']) for row in result['journal']],
                         [('REGISTER', 5, 8)])

    def test_little_endian_and_register_preservation_without_bank_prerequisites(self):
        query = snapshot(0x34, 0x12, registers={'lrb': 0, 'scb': 7, 'usp': 0x1234, 'ssp': 0x047E})
        original = deepcopy(query)
        result = detached_epilogue_0244_0246(query)
        loaded, final = result['steps'][0]['state']['registers'], result['state']['registers']
        self.assertEqual(result['reads'][0]['value'], 0x1234)
        self.assertEqual((loaded['al'], loaded['ah'], loaded['dd'], loaded['zf']), (0x34, 0x12, 1, 0))
        self.assertEqual((loaded['cf'], loaded['hc']), (1, 1))
        for key in ('al', 'ah', 'dd', 'lrb', 'scb', 'usp', 'ssp', 'otherPsw'):
            self.assertEqual(final[key], loaded[key])
        self.assertEqual(query, original)

    def test_partial_word_zero_consensus_without_invented_bytes(self):
        for inputs, expected_zf, expected_high in (
            (snapshot(None, None), None, None),
            (snapshot(0, None), None, None),
            (snapshot(0x80, None), 0, None),
            (snapshot(None, None, high_bits={'7': 1}), 0, None),
            (snapshot(None, 0, low_bits={str(bit): 0 for bit in range(8)}), 1, 0),
        ):
            out = detached_epilogue_0244_0246(inputs)
            loaded = out['steps'][0]['state']['registers']
            self.assertEqual((loaded['zf'], loaded['ah']), (expected_zf, expected_high))
            self.assertEqual(loaded['dd'], 1)
            if expected_high is None:
                self.assertIsNone(out['prospectiveIe']['value'])

    def test_mask_has_candidate_but_three_final_flags_stay_unknown(self):
        for mie in (0, 1, None):
            result = detached_epilogue_0244_0246(snapshot(0, 0, registers={'mie': mie}))
            registers = result['state']['registers']
            mask = result['pswh']
            self.assertEqual(mask['maskCandidate']['knownBits']['6'], 1)
            self.assertEqual(mask['maskCandidate']['knownBits']['7'], 1)
            self.assertEqual(mask['maskCandidate']['knownBits']['0'], 0)
            self.assertEqual(mask['maskCandidateSameValue'], None if mie is None else mie == 0)
            self.assertEqual([registers[key] for key in ('cf', 'hc', 'zf', 'mie', 'dd')], [None, None, None, 0, 1])
            self.assertTrue(all(bit not in mask['after']['knownBits'] for bit in ('5', '6', '7')))
            self.assertEqual(mask['after']['knownBits']['0'], 0)
            self.assertEqual(mask['after']['knownBits']['3'], mask['before']['knownBits']['3'])
            self.assertEqual(len(result['journal']), 1)

    def test_lineage_is_distinct_from_value_and_same_value_overlap_is_retained(self):
        writer = {'pc': 0x54E5, 'generation': 'Pair'}
        for query, classification in (
            (snapshot(generations=('Pair', 'Pair'), writer=writer), 'ConditionalCandidateGenerationMatched'),
            (snapshot(generations=('Pair', 'LaterHigh'), writer=writer), 'CandidateGenerationMismatch'),
            (snapshot(generations=(None, 'Pair'), writer=writer), 'CurrentReadGenerationMissing'),
            (snapshot(generations=('Pair', 'Pair'), writer=writer,
                      events=[write_event(0xF9, 16, 'LaterPair', 0x2BAB)]), 'InterveningWriterPossible'),
        ):
            out = detached_epilogue_0244_0246(query)
            proof = out['shadowProof']
            self.assertEqual(proof['classification'], classification)
            self.assertEqual(out['prospectiveIe']['value'], 0x2BAB)
            self.assertIsNone(proof['nativeOwner'])
            self.assertEqual(out['prospectiveIe']['sourceGenerations'], proof['readGenerations'])
        self.assertEqual(proof['overlapOrdinals'], [1])
        self.assertEqual(proof['interveningEvents'][0]['value'], proof['candidateWord'])
        self.assertFalse(proof['conditionalWordWriterGenerationMatched'])

    def test_refusal_retains_exact_prefix(self):
        first = detached_epilogue_0244_0246(snapshot(premises={'memoryModel': None}))
        self.assertEqual((first['stopPc'], first['reads'], first['journal']), (0x0244, [], []))
        self.assertEqual((first['state']['registers']['al'], first['state']['registers']['dd']), (0x42, 0))
        self.assertEqual(first['state']['registerKnownBits']['ah'], {'7': 1})
        second = detached_epilogue_0244_0246(snapshot(0, 0, premises={'pswhAlias': False}))
        self.assertEqual((second['stopPc'], len(second['reads']), second['journal']), (0x0246, 1, []))
        self.assertEqual((second['state']['registers']['dd'], second['state']['registers']['zf'],
                          second['state']['registers']['mie']), (1, 1, 1))
        self.assertIsNone(second['prospectiveIe'])

    def test_adapter_keeps_full_histories_and_does_not_write_ie(self):
        for query, path in ((direct_query(), 'M2df024fTo0244'), (detached_query(), 'M2dg0240To0241To0244')):
            adapted = epilogue_ingress_adapter(query)
            self.assertEqual(adapted['status'], 'QualifiedSymbolicIngress')
            self.assertEqual(adapted['sourceHistory']['sourcePath'], path)
            self.assertEqual(adapted['journal'], [])
            local = detached_epilogue_0244_0246(adapted['projectedInput'])
            self.assertEqual(local['prospectiveIe']['address'], 0x1A)
            self.assertEqual(local['prospectiveIe']['requiredDd'], 1)
            self.assertIsNone(local['prospectiveIe']['actualWrite'])
            self.assertEqual(set(row['space'] for row in local['journal']), {'REGISTER'})
            self.assertIsNone(local['executionAuthority']['actualIeWrite'])

    def test_equal_word_is_insufficient_to_join_ingresses(self):
        direct, detached = direct_query(), detached_query()
        equivalent = compare_epilogue_ingresses({'direct': direct, 'detached': detached})
        self.assertEqual(equivalent['status'], 'ConditionalEquivalentLocalEpilogueEffect')
        self.assertEqual(equivalent['fields']['sourcePath']['relation'], 'Different')
        for other in (detached_query(generations=('OtherLow', 'OtherHigh')), detached_query(cf=1)):
            outcome = compare_epilogue_ingresses({'direct': direct, 'detached': other})
            self.assertEqual(outcome['fields']['prospectiveIeWord']['relation'], 'Equal')
            self.assertEqual(outcome['status'], 'DistinctLocalEpilogueEffectsCompared')

    def test_replay_rejects_forged_execution_or_generation(self):
        base = detached_query()
        for key in ('actualStbufWrite', 'actualTransmission', 'actualIeWrite', 'actualIrqDelivery',
                    'actualReturnExecution', 'actualFramePop', 'cpuInstructionRetirements', 'exactC8Rule'):
            forged = deepcopy(base)
            forged['source']['result']['executionAuthority'][key] = True
            out = epilogue_ingress_adapter(forged)
            self.assertIsNone(out['projectedInput'])
            self.assertEqual(out['reason'], 'FrozenIngressReplayMismatch')
        forged = deepcopy(base)
        forged['source']['result']['state']['generations']['00F9'] = 'ForgedHigh'
        self.assertIsNone(epilogue_ingress_adapter(forged)['projectedInput'])

    def test_frozen_contract_and_canonical_records(self):
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

    def test_reject_changed_source_inventory_binding(self):
        source = json.loads(Path(__file__).with_name('source_inventory.json').read_bytes())
        contract = load_contract()
        path = next(key for key in contract['sources'] if 'detached_epilogue_f8_pswh/source_inventory' in key)
        for row, key, value in ((0, 'length', 1), (0, 'form', 'LB A,N8'), (1, 'form', 'RB PSWH.0'),
                                (2, 'role', 'ExecutedIeWrite'), (3, 'role', 'ExecutedRti')):
            changed_source = deepcopy(source)
            changed_source['sites'][row][key] = value
            changed = deepcopy(contract)
            changed['sources'][path] = sha256(canonical(changed_source)).hexdigest()
            with self.assertRaisesRegex(ValueError, 'FrozenSourceBindingChanged'):
                validate_contract(changed)
