"""Curated state/effect and refusal checks; no target runtime capability."""
from copy import deepcopy
import unittest

from native_data011f_011b_ownership.feasibility import (
    EXPECTED_CONTRACT, curated_scenarios, example, read_contract,
    symbolic_records, validate_contract, verify_claim,
)
from native_data011f_011b_ownership.symbolic_owner import run_scenario


def negative_categories():
    """Twenty-nine named requirements; input and fabricated-result changes."""
    cases = []
    def invalid(name, edit):
        value = example(name); edit(value); cases.append((name, 'InputRefusal', value, None))
    def false_claim(name, edit_input, edit_result):
        value = example(name); edit_input(value); result = run_scenario(value)
        edit_result(result); cases.append((name, 'FabricatedExpectedEffectRefusal', value, result))
    invalid('WrongWriterPC', lambda x: x['events'][-1].update(pc=0x0409))
    invalid('WrongSourceWidth', lambda x: x['events'][-1].update(width=8))
    false_claim('WrongEndianMapping', lambda x: None,
        lambda r: r['memory'].__setitem__(0, {**r['memory'][0], 'value': 0xA5}))
    invalid('WrongCopiedHighByte', lambda x: x['events'][-1].update(source=0x0215))
    invalid('IncorrectTargetBit', lambda x: x['reader'].update(bit=2))
    false_claim('UnownedSourcePromoted', lambda x: x['seeds'][-1].update(owner=None),
        lambda r: r['reader'].update(source='native:invented-owner'))
    invalid('HistoricalM2agImport', lambda x: x['seeds'][-1].update(owner='historical:M2ag'))
    invalid('HistoricalLimiterSnapshotImport', lambda x: x['seeds'][-1].update(owner='historical:limiter'))
    false_claim('MissingActualEvenInventedWriter', lambda x: x.update(events=[]),
        lambda r: r['reader'].update(lineage=['invented:old-machine:1']))
    false_claim('UnreachableWriter', lambda x: x['constraints'].update(rootReachable=False),
        lambda r: r.update(symbolicBridge='InventedOnly_SourceToReaderObligationsSatisfied'))
    false_claim('WriterBypass', lambda x: x['constraints'].update(writerDominates=False),
        lambda r: r.update(missingObligations=[]))
    false_claim('WrongPathPredicate', lambda x: x['constraints'].update(rootReachable=False, historyCompatible=False),
        lambda r: r.update(missingObligations=['rootReachable']))
    false_claim('NonDominatingTreatedUnconditional', lambda x: x['constraints'].update(writerDominates=False),
        lambda r: r.update(nativeSourceOwnershipEstablished=True))
    false_claim('WordOverlap011F', lambda x: x['events'].append({'op': 'overlap', 'pc': 0x7000, 'address': 0x011E, 'value': 0xA55A}),
        lambda r: r['reader'].update(source='invented:seed0217:3'))
    def overlap_b(x):
        x['reader'] = {'address': 0x011B, 'bit': 7}
        x['events'].append({'op': 'overlap', 'pc': 0x7000, 'address': 0x011A, 'value': 0x8031})
    false_claim('WordOverlap011B', overlap_b, lambda r: r['reader'].update(source='invented:seed0213:7'))
    false_claim('IndirectAliasUncertainty', lambda x: x['events'].append({'op': 'unknownAlias', 'addresses': [0x011F]}),
        lambda r: r.update(aliasUnknowns=[]))
    false_claim('StackFrameOverlap', lambda x: x['constraints'].update(stackPreserved=False),
        lambda r: r.update(missingObligations=[]))
    invalid('WrongLRBPage', lambda x: x['context'].update(lrb=0x22))
    invalid('WrongSCBPointerContext', lambda x: x['context'].update(scb=3))
    invalid('InterruptedWriter', lambda x: x['events'][-1].update(complete=False))
    false_claim('SameValueDeduplication', lambda x: x['events'].append(deepcopy(x['events'][-1])),
        lambda r: r['writes'].pop())
    false_claim('UnknownSubstitutedWithA5', lambda x: x['seeds'][-1].update(value=None, owner=None),
        lambda r: r['reader'].update(value=0))
    false_claim('IncompatibleCallerHistories', lambda x: x.update(context012A='invented-other'),
        lambda r: r.update(context012ACompatible=True))
    false_claim('Wrong012ABit3Correlation', lambda x: x.update(old012A=8),
        lambda r: r.update(conditionalBit3Terminal=0x0664))
    false_claim('CorrectNumberInvalidSource', lambda x: x['seeds'][-1].update(owner=None),
        lambda r: r.update(sourceValueKnownIsNativeOwner=True))
    invalid('OtherMachineWriteOrdinal', lambda x: x['events'][-1].update(sourceMachine='invented:another-machine'))
    false_claim('StaticTraceAsRetirement', lambda x: None, lambda r: r.update(actualRetiredInstructions=1))
    false_claim('FabricatedOriginalRomWrite', lambda x: None,
        lambda r: r['writes'][-1].update(writerPC=0x064C))
    contract = deepcopy(EXPECTED_CONTRACT); contract['baseSha'] = '0' * 40
    cases.append(('ModifiedHistoricalExpectedFingerprint', 'ContractIdentityRefusal', contract, None))
    return cases


class OwnershipTests(unittest.TestCase):
    def test_closed_contract_and_five_distinct_levels(self):
        self.assertEqual(read_contract(), EXPECTED_CONTRACT)
        self.assertEqual(len(EXPECTED_CONTRACT['proofLevels']), 5)

    def test_full_independent_curated_symbolic_equality(self):
        records = symbolic_records()
        self.assertEqual(len(records), 12)
        self.assertEqual(len({r['input']['caseId'] for r in records}), 12)
        self.assertTrue(all(r['result']['actualCpuExecutions'] == 0 for r in records))

    def test_all29_named_negative_requirements(self):
        cases = negative_categories(); self.assertEqual(len(cases), 29)
        self.assertEqual(len({x[0] for x in cases}), 29)
        for name, kind, scenario, claimed in cases:
            with self.subTest(name=name, kind=kind), self.assertRaises(ValueError):
                if kind == 'ContractIdentityRefusal':
                    validate_contract(scenario)
                elif kind == 'InputRefusal':
                    run_scenario(scenario)
                else:
                    verify_claim(scenario, claimed)

    def test_same_value_store_has_distinct_storage_generation(self):
        item = next(x for x in curated_scenarios() if x['caseId'] == 'same-value-writes')
        result = run_scenario(item)
        self.assertTrue(result['writes'][-1]['sameValue'])
        self.assertNotEqual(result['writes'][-1]['storageGeneration'], result['writes'][-2]['storageGeneration'])
        self.assertEqual([w['ordinal'] for w in result['writes']], [1, 2, 3])
        self.assertEqual(result['reader']['lineage'], [result['writes'][-1]['storageGeneration']])

    def test_code_bit_known_with_unknown_neighbor_byte(self):
        item = next(x for x in curated_scenarios() if x['caseId'] == 'program-bit-with-unknown-neighbors')
        result = run_scenario(item)
        cell = next(c for c in result['memory'] if c['address'] == 0x011F)
        self.assertIsNone(cell['value']); self.assertEqual(result['reader']['value'], 1)
        self.assertEqual(sum(x is not None for x in cell['bitSources']), 1)
        self.assertFalse(result['nativeSourceOwnershipEstablished'])
        self.assertIn('WholeReaderByteUnknown', result['missingObligations'])
        self.assertEqual(result['symbolicBridge'], 'SameMachineBridgeBlocked')

    def test_zero_a5_ff_numbers_never_create_semantic_owner(self):
        for number in (0, 0xA5, 0xFF):
            item = example('unknown-number-' + str(number))
            item['seeds'][-1].update(value=number, owner=None)
            result = run_scenario(item)
            self.assertIsNone(result['reader']['source'])
            self.assertIn('ReaderSourceUnknown', result['missingObligations'])

    def test_owner_token_without_explicit_invented_value_refused(self):
        item = example('missing-owner-value'); item['seeds'][-1]['value'] = None
        with self.assertRaisesRegex(ValueError, 'OwnedSeedRequiresExplicitInventedValue'):
            run_scenario(item)

    def test_known_numeric_neighbors_do_not_acquire_semantic_owners(self):
        item = example('known-unowned-neighbors'); item['seeds'][-1]['owner'] = None
        item['events'].insert(0, {'op': 'programBit', 'pc': 0x5F6B, 'programByte': 0x80})
        result = run_scenario(item)
        self.assertEqual(result['reader']['value'], 1)
        self.assertIsNotNone(result['reader']['source'])
        self.assertIn('WholeReaderByteOwnerUnknown', result['missingObligations'])
        self.assertEqual(result['symbolicBridge'], 'SameMachineBridgeBlocked')

    def test_reader_obligation_uses_selected_byte_not_highest_memory_address(self):
        item = example('unknown-011b-known-0217')
        item['reader'] = {'address': 0x011B, 'bit': 7}
        item['seeds'][1].update(value=None, owner=None)
        result = run_scenario(item)
        self.assertIn('WholeReaderByteUnknown', result['missingObligations'])
        verify_claim(item, result)

    def test_rmw_retains_neighbor_semantic_sources(self):
        item = next(x for x in curated_scenarios() if x['caseId'] == 'program-bit-preserved-neighbors')
        result = run_scenario(item)
        cell = next(c for c in result['memory'] if c['address'] == 0x0217)
        self.assertEqual(cell['bitSources'][2], 'invented:seed0217:2')
        self.assertEqual(cell['bitSources'][3], 'invented:PROGRAM60EC:7')

    def test_unaligned_overlap_cannot_claim_wrong_word_footprint(self):
        item = example('odd-word')
        item['events'].append({'op': 'overlap', 'pc': 0x7000, 'address': 0x011F, 'value': 0})
        with self.assertRaises(ValueError):
            run_scenario(item)

    def test_cfg_dominance_independent_fixed_point(self):
        from native_data011f_011b_ownership.caller_reachability import analyze_cfg
        report = analyze_cfg(); graph = report['graph']; edges = graph['edges']
        edges = {int(k): v for k, v in edges.items()}
        for root in graph['roots']:
            reached, pending = set(), [root]
            while pending:
                node = pending.pop()
                if node not in reached:
                    reached.add(node); pending.extend(edges[node])
            dom = {node: ({root} if node == root else set(reached)) for node in reached}
            changed = True
            while changed:
                changed = False
                for node in sorted(reached - {root}):
                    parents = [p for p in reached if node in edges[p]]
                    updated = {node} | set.intersection(*(dom[p] for p in parents))
                    if updated != dom[node]:
                        dom[node] = updated; changed = True
            for relation in report['writerReaderRelations']:
                if relation['root'] == root:
                    writer, reader = relation['candidateWriterPC'], relation['readerPC']
                    self.assertEqual(relation['writerReachableWithinGraph'], writer in reached)
                    self.assertEqual(relation['readerReachableWithinGraph'], reader in reached)
                    self.assertEqual(relation['writerDominatesReaderWithinGraph'],
                        reader in reached and writer in dom[reader])

    def test_alias_footprints_and_context_are_independent_obligations(self):
        from native_data011f_011b_ownership.alias_analysis import aliases
        report = aliases()
        self.assertTrue(report['pointingRegisterStorageDisjointForAllEightScb'])
        for row in report['stackCollisions']:
            target = row['targetWord']
            self.assertEqual(row['calEvenSspCollisions'], [target])
            self.assertEqual(row['irqEvenSspCollisions'], [target + 2 * n for n in range(4)])
        self.assertFalse(report['technicalCalFrame']['authority'].endswith('EnclosingIrqVerified'))

    def test_copy_inventory_agrees_with_word_address_and_source_model(self):
        from native_data011f_011b_ownership.source_inventory import reviewed_inventory
        from native_data011f_011b_ownership.symbolic_owner import COPIES
        rows = reviewed_inventory()['wordCopies']
        self.assertEqual({r['writerPC']: (r['source']['address'], r['address']) for r in rows}, COPIES)
        for row in rows:
            source = row['source']
            self.assertEqual((source['usp'] + source['signedOffset']) & 65535, source['address'])
            self.assertEqual(row['widthBits'], 16)
            self.assertEqual(row['footprint'], [row['address'], row['address'] + 1])
            self.assertFalse(row['writerExecutedOnCurrentMachine'])

    def test_sbr_editorial_conflict_cannot_establish_known_one_owner(self):
        from native_data011f_011b_ownership.source_inventory import reviewed_inventory
        for row in reviewed_inventory()['indexedBitmapCandidates']:
            self.assertIn('DD0BeforeSUBB5B7E', row['conditions'])
            self.assertIn('PreserveDD', row['incomingDD'])
            self.assertNotIn('SetsDD0', row['incomingDD'])
            self.assertTrue(row['addressAndSelectedBitRelationEstablished'])
            self.assertFalse(row['setDirectionPrimaryEstablished'])
            self.assertFalse(row['knownOneSourceEstablished'])
            self.assertFalse(row['codeOwnedTransformationEstablished'])

    def test_canonical_records_survive_json_roundtrip_without_key_or_field_loss(self):
        import json
        from native_data011f_011b_ownership.feasibility import canonical_records
        records = canonical_records()
        encoded = json.dumps(records, ensure_ascii=True, sort_keys=True, separators=(',', ':'))
        self.assertEqual(records, json.loads(encoded))
        self.assertEqual(encoded, json.dumps(json.loads(encoded), ensure_ascii=True, sort_keys=True, separators=(',', ':')))
        self.assertEqual(len(records), 17)


if __name__ == '__main__':
    unittest.main()
