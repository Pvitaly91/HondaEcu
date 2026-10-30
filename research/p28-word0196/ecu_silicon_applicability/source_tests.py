"""Independent M2cl map/provenance checks; no CPU, ROM or receiver execution."""
from copy import deepcopy
import importlib
import hashlib
import json
from pathlib import Path
import unittest

from .reference_oracle import (FROZEN_CANONICAL_BYTES, FROZEN_CANONICAL_SHA256, MODELS,
                               SELECTED_ADDRESSES, expected_address, expected_address_inventory,
                               expected_graph, expected_records)


class SourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Only imported when the parent runs QA after the independent freeze.
        cls.address_map = importlib.import_module(__package__ + '.address_map')

    def test_all_280_standard_address_classifications_match_reference(self):
        expected = expected_address_inventory()
        self.assertEqual(280, len(expected))
        actual = [self.address_map.classify(r['model'], r['space'], r['address']) for r in expected]
        self.assertEqual(expected, actual)

    def test_ram_begins_at0080_and_pointing_alias_is_in_internal_ram(self):
        for model in MODELS:
            with self.subTest(model=model):
                self.assertEqual('SFRNamespace_ImplementedHolesUnknown', self.address_map.classify(model, 'DATA', 0x007F)['documentedRegion'])
                self.assertEqual('InternalRam_PointingBankAlias', self.address_map.classify(model, 'DATA', 0x0080)['documentedRegion'])
                self.assertEqual('InternalRam_PointingBankAlias', self.address_map.classify(model, 'DATA', 0x00BF)['documentedRegion'])
                self.assertEqual('InternalRam_ZeroPage', self.address_map.classify(model, 'DATA', 0x00C0)['documentedRegion'])
                self.assertEqual('InternalRam_ZeroPage', self.address_map.classify(model, 'DATA', 0x00FF)['documentedRegion'])
                self.assertEqual('InternalRam_Paged', self.address_map.classify(model, 'DATA', 0x0100)['documentedRegion'])

    def test_201_and_207_ram_boundaries_and_otp_map_counterparts(self):
        for base, otp, final in (('MSM66201', 'MSM66P201', 0x027F), ('MSM66207', 'MSM66P207', 0x047F)):
            for model in (base, otp):
                with self.subTest(model=model):
                    self.assertEqual('InternalRam_Paged', self.address_map.classify(model, 'DATA', final)['documentedRegion'])
                    self.assertEqual('ExternalData_BoardMappingUnknown', self.address_map.classify(model, 'DATA', final + 1)['documentedRegion'])
            for address in SELECTED_ADDRESSES:
                for space in ('PROGRAM', 'DATA'):
                    a = self.address_map.classify(base, space, address)
                    b = self.address_map.classify(otp, space, address)
                    self.assertEqual(a['documentedRegion'], b['documentedRegion'])
                    self.assertIs(a['actualMappingVerified'], False)
                    self.assertIs(b['actualMappingVerified'], False)

    def test_parser03f3_and_stack047e_are_external_on201_not_chip_identity(self):
        for address in (0x03F0, 0x03F3, 0x03F7, 0x047E):
            for model in MODELS:
                with self.subTest(model=model, address=address):
                    result = self.address_map.classify(model, 'DATA', address)
                    expected = 'ExternalData_BoardMappingUnknown' if model.endswith('201') else 'InternalRam_Paged'
                    self.assertEqual(expected, result['documentedRegion'])
                    self.assertIs(result['actualMappingVerified'], False)

    def test_program_internal_boundaries_do_not_select_actual_rom_source(self):
        for model in MODELS:
            boundary = 0x4000 if model.endswith('201') else 0x8000
            self.assertEqual('InternalProgram16K' if model.endswith('201') else 'InternalProgram32K',
                             self.address_map.classify(model, 'PROGRAM', boundary - 1)['documentedRegion'])
            for address in (boundary, 0xFFFF):
                result = self.address_map.classify(model, 'PROGRAM', address)
                self.assertEqual('ExternalProgram_BoardMappingUnknown', result['documentedRegion'])
                self.assertIs(result['actualMappingVerified'], False)

    def test_program_and_data_spaces_are_distinct_at_sfr_and_code_addresses(self):
        for model in MODELS:
            for address in (0x000A, 0x0018, 0x0055, 0x0269, 0x54EA):
                program = self.address_map.classify(model, 'PROGRAM', address)
                data = self.address_map.classify(model, 'DATA', address)
                self.assertNotEqual(program['documentedRegion'], data['documentedRegion'])
                self.assertEqual('PROGRAM', program['space'])
                self.assertEqual('DATA', data['space'])

    def test_no_address_classification_claims_all_sfr_bytes_implemented(self):
        for model in MODELS:
            for address in (0x0000, 0x000A, 0x0018, 0x0055, 0x007F):
                result = self.address_map.classify(model, 'DATA', address)
                self.assertEqual('SFRNamespace_ImplementedHolesUnknown', result['documentedRegion'])
                self.assertIs(result['actualMappingVerified'], False)
                self.assertEqual(('JapaneseY3', 17), (result['sourceId'], result['sourcePage']))

    def test_invalid_model_space_and_address_types_are_not_coerced(self):
        controls = [(m, 'DATA', 0x0055) for m in ('P28', 'M66207', 'MSM66507', '', None, 66207, [], {})]
        controls += [('MSM66207', s, 0x0055) for s in ('RAM', 'ROM', 'SFR', 'program', '', None, 1, [])]
        controls += [('MSM66207', 'DATA', a) for a in (-1, 0x10000, True, False, 0.0, '0055', None, [])]
        for model, space, address in controls:
            with self.subTest(model=model, space=space, address=address), self.assertRaises(ValueError):
                self.address_map.classify(model, space, address)


class DocumentaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.analysis = importlib.import_module(__package__ + '.analysis')
        cls.provenance = importlib.import_module(__package__ + '.provenance')

    @staticmethod
    def record(source='JapaneseY3', scope='StandardDocument', target='MSM66207'):
        # False links mean not established, not proof that a donor differs.
        return {'sourceId': source, 'scope': scope, 'targetModel': target,
                'actualEcuId': None, 'donorLinked': False, 'romCustodyLinked': False,
                'maskRevisionConfirmed': False, 'actualHardwareObservation': None}

    def test_complete_twelve_record_stream_equals_frozen_reference(self):
        expected = expected_records()
        raw = b''.join((json.dumps(r, sort_keys=True, separators=(',', ':'), ensure_ascii=True) + '\n').encode('ascii') for r in expected)
        self.assertEqual(FROZEN_CANONICAL_BYTES, len(raw))
        self.assertEqual(FROZEN_CANONICAL_SHA256, hashlib.sha256(raw).hexdigest())
        self.assertEqual(expected, self.analysis.canonical_records())

    def test_canonical_records_preserve_all_unknown_runtime_fields(self):
        records = self.analysis.canonical_records()
        self.assertEqual(12, len(records))
        self.assertEqual(12, len({r['recordId'] for r in records}))
        for row in records:
            self.assertEqual({'recordId', 'recordClass', 'payload', 'actualHardwareObservation', 'executionBlocked', 'firmwareReady'}, set(row))
            self.assertIsNone(row['actualHardwareObservation'])
            self.assertIs(row['executionBlocked'], True)
            self.assertIs(row['firmwareReady'], False)
        authority = records[-1]['payload']
        self.assertEqual('ECU_SILICON_IDENTITY_UNRESOLVED', authority['classification'])
        self.assertEqual('EXECUTION_BLOCKED', authority['runtime'])
        self.assertIsNone(authority['actualEcuId'])
        self.assertIsNone(authority['actualCpuMarking'])
        self.assertEqual(0, authority['newCpuRomIrqRtiExecutions'])

    def test_variant_rom_ram_otp_and_package_properties_stay_separate(self):
        candidates = {r['payload']['candidate']: r['payload'] for r in self.analysis.canonical_records() if r['recordClass'] == 'CandidateComparison'}
        for model in MODELS:
            row = candidates[model]
            small = model.endswith('201')
            otp = model.startswith('MSM66P')
            self.assertEqual(16384 if small else 32768, row['nominalInternalProgramBytes'])
            self.assertEqual(512 if small else 1024, row['nominalInternalDataRamBytes'])
            self.assertEqual(['0080', '027F' if small else '047F'], row['totalInternalRamRangeInclusive'])
            self.assertEqual(not otp, row['qfpListed'])
            self.assertEqual('OneTimePROMCounterpart' if otp else 'StandardInternalROM', row['programMemoryKind'])
            self.assertIs(row['actualEcuLinkEstablished'], False)
            self.assertIsNone(row['actualPackageMarking'])
            self.assertIsNone(row['actualMaskOrRevision'])

    def test_matrix_schema_source_hashes_alternatives_and_proof_needs_are_complete(self):
        contract = json.loads(Path(__file__).with_name('contract.json').read_bytes())
        registry = {r['sourceId']: r['sha256'] for r in contract['source_registry'] + contract['boundPublicReports']}
        matrix = next(r['payload']['claims'] for r in self.analysis.canonical_records() if r['recordClass'] == 'EvidenceMatrix')
        self.assertEqual(49, len(matrix))
        self.assertEqual(49, len({r['claimId'] for r in matrix}))
        required = {'claimId', 'component', 'statement', 'sourceRefs', 'classification', 'confidence',
                    'rationale', 'applicability', 'alternatives', 'unknownConditions', 'neededEvidence'}
        for row in matrix:
            self.assertEqual(required, set(row))
            for field in ('component', 'statement', 'classification', 'confidence', 'rationale', 'applicability'):
                self.assertTrue(type(row[field]) is str and row[field])
            for field in ('alternatives', 'unknownConditions', 'neededEvidence', 'sourceRefs'):
                self.assertTrue(type(row[field]) is list and row[field])
            for ref in row['sourceRefs']:
                self.assertEqual({'sourceId', 'locator', 'sourceHash'}, set(ref))
                self.assertEqual(registry[ref['sourceId']], ref['sourceHash'])
                self.assertTrue(ref['locator'])

    def test_six_source_hashes_pin_actual_documents_not_receipt_wrappers(self):
        sources = json.loads(Path(__file__).with_name('contract.json').read_bytes())['source_registry']
        expected = {
            'JapaneseY3': (602102, '9da5f4c364fb8aed21c783bc5ad7b1e114c4b8773c7a00b9a7373c261112bf7a'),
            'EnglishY4': (583437, 'fe18068dc496a03f5b6bdefe5818741e572cb7626acfb3d1df427547f8b3264b'),
            'ISA1991': (4563117, 'f6e423ac0bd15378754e30c35ed426415ec219e360c68e817ab451df72142271'),
            'UserIncomplete': (16203609, 'f061cb5bcbd1804699fb60b543c425646fbb15b939c9bc51b24edbb4da4c6ddf'),
            'ArchiveCatalogue': (104246, '3e2a71a91e3ca05d9bda349b5e4caba0b66a68f6a986c4859e9129a6ab7e473b'),
            'BomarcSchematic': (9147356, '7d5380ad1341980def330eec6798e98ec0f44268ac44d1c802587da52241a7c5'),
        }
        self.assertEqual(set(expected), {r['sourceId'] for r in sources})
        for source in sources:
            self.assertEqual(expected[source['sourceId']], (source['bytes'], source['sha256']))

    def test_matrix_reference_and_unknowns_cannot_be_mutated_into_hardware_evidence(self):
        rows = next(r['payload']['claims'] for r in expected_records() if r['recordClass'] == 'EvidenceMatrix')
        self.assertEqual({'valid': True, 'actualHardwareIdentityEstablished': False, 'executionAdmission': False},
                         self.analysis.validate_matrix(deepcopy(rows)))
        mutants = []
        changed = deepcopy(rows)
        changed[0]['sourceRefs'][0]['sourceHash'] = '0' * 64
        mutants.append(changed)
        changed = deepcopy(rows)
        changed[0]['sourceRefs'][0]['sourceId'] = 'UnlinkedNewManufacturer'
        mutants.append(changed)
        changed = deepcopy(rows)
        del changed[0]['unknownConditions']
        mutants.append(changed)
        changed = deepcopy(rows)
        changed[0]['classification'] = 'ActualHardwareObserved'
        mutants.append(changed)
        for index, changed in enumerate(mutants):
            with self.subTest(mutation=index), self.assertRaises(ValueError):
                self.analysis.validate_matrix(changed)

    def test_japanese_user_bit8_and_historical_bit11_correction_retained(self):
        matrix = next(r['payload']['claims'] for r in self.analysis.canonical_records() if r['recordClass'] == 'EvidenceMatrix')
        row = next(r for r in matrix if r['claimId'] == 'LOCAL-MAP-005')
        for text in ('JapaneseY3 MIEbit8', 'EnglishY4 MIPbit8', 'User31 MIEbit8', 'bit11 nonexistent/read1', 'Historical M2ck bit11 annotation'):
            self.assertIn(text, row['statement'])
        self.assertEqual('SourceSpecificAttributionCorrection_HistoricalFilesFrozen', row['classification'])

    def test_catalogue_and_unlinked_board_variant_are_not_merged(self):
        matrix = next(r['payload']['claims'] for r in self.analysis.canonical_records() if r['recordClass'] == 'EvidenceMatrix')
        lookup = {r['claimId']: r for r in matrix}
        self.assertIn('P28-A01', lookup['LOCAL-ECU-002']['statement'])
        self.assertIn('37820-P28-A51', lookup['BOARD-LABEL']['statement'])
        self.assertIn('MSM66207-251', lookup['BOARD-LABEL']['statement'])
        self.assertEqual('UnlinkedThirdPartyDrawingObservation', lookup['BOARD-LABEL']['classification'])
        self.assertIn('Separate U7', lookup['BOARD-ASIC']['statement'])
        self.assertIn('do not prove custom internal peripherals', lookup['BOARD-ASIC']['statement'])

    def test_qualified_provenance_positive_relations_never_admit_execution(self):
        for model in MODELS:
            for source in ('JapaneseY3', 'EnglishY4'):
                result = self.provenance.validate_claim('StandardDeviceProperty', self.record(source=source, target=model))
                self.assertEqual({'classification': 'StandardDocumentOnly', 'actualEcuConfirmed': False, 'executionAdmission': False}, result)
        for kind, record, classification in (
            ('ArchiveAssociation', self.record('ArchiveCatalogue', 'ArchiveCatalogue', None), 'ArchiveAssociationOnly'),
            ('ThirdPartyBoardObservation', self.record('BomarcSchematic', 'UnlinkedThirdPartyBoard', 'MSM66207'), 'UnlinkedBoardObservation'),
        ):
            self.assertEqual({'classification': classification, 'actualEcuConfirmed': False, 'executionAdmission': False}, self.provenance.validate_claim(kind, record))

    def test_source_specific_isa_and_user_device_scopes_are_not_widened(self):
        allowed = {'ISA1991': {'MSM66201'}, 'UserIncomplete': {'MSM66201', 'MSM66207'}}
        for source, targets in allowed.items():
            for model in MODELS:
                with self.subTest(source=source, model=model):
                    record = self.record(source=source, target=model)
                    if model in targets:
                        self.assertEqual('StandardDocumentOnly', self.provenance.validate_claim('StandardDeviceProperty', record)['classification'])
                    else:
                        with self.assertRaises(ValueError):
                            self.provenance.validate_claim('StandardDeviceProperty', record)

    def test_host_asserted_actual_identity_or_link_flags_are_not_evidence(self):
        for source in ('JapaneseY3', 'EnglishY4', 'ISA1991', 'UserIncomplete', 'ArchiveCatalogue', 'BomarcSchematic'):
            record = self.record(source=source)
            with self.subTest(source=source), self.assertRaises(ValueError):
                self.provenance.validate_claim('ActualEcuIdentity', record)
        for field, value in (('actualEcuId', '37820-P28-A01'), ('donorLinked', True),
                             ('romCustodyLinked', True), ('maskRevisionConfirmed', True),
                             ('actualHardwareObservation', {'marking': 'MSM66207-251'})):
            record = self.record()
            record[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.provenance.validate_claim('StandardDeviceProperty', record)

    def test_weak_identity_bases_never_promote_standard_property(self):
        for basis in ('FilenameDerivedActual', 'SizeDerivedActual', 'IsaDerivedActual',
                      'SuffixDerivedActual', 'ChecksumDerivedActual', 'UnlinkedPhotoActual',
                      'LearnedBoardActual', 'UnknownSfrImpliesCustomAsic'):
            record = self.record()
            record['scope'] = basis
            with self.subTest(scope=basis), self.assertRaises(ValueError):
                self.provenance.validate_claim('StandardDeviceProperty', record)

    def test_wrong_kind_source_target_relations_are_refused(self):
        controls = [
            ('ArchiveAssociation', self.record('BomarcSchematic', 'ArchiveCatalogue', None)),
            ('ThirdPartyBoardObservation', self.record('ArchiveCatalogue', 'UnlinkedThirdPartyBoard', 'MSM66207')),
            ('ThirdPartyBoardObservation', self.record('BomarcSchematic', 'UnlinkedThirdPartyBoard', 'MSM66201')),
            ('ArchiveAssociation', self.record('ArchiveCatalogue', 'ArchiveCatalogue', 'MSM66207')),
            ('StandardDeviceProperty', self.record('UnknownManufacturer', 'StandardDocument', 'MSM66207')),
            ('StandardDeviceProperty', self.record('JapaneseY3', 'StandardDocument', 'M66207')),
            ('StandardDeviceProperty', self.record('JapaneseY3', 'StandardDocument', 'MSM66507')),
            ('FirmwareReady', self.record()),
        ]
        for kind, record in controls:
            with self.subTest(kind=kind, record=record), self.assertRaises(ValueError):
                self.provenance.validate_claim(kind, record)

    def test_claim_types_missing_fields_extra_authority_are_not_coerced(self):
        for field in self.record():
            record = self.record()
            del record[field]
            with self.subTest(missing=field), self.assertRaises(ValueError):
                self.provenance.validate_claim('StandardDeviceProperty', record)
        for field, value in (('sourceId', None), ('targetModel', 66207), ('scope', []),
                             ('donorLinked', 0), ('romCustodyLinked', 0), ('maskRevisionConfirmed', 0)):
            record = self.record()
            record[field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                self.provenance.validate_claim('StandardDeviceProperty', record)
        for extra in ('runtimeAdmission', 'factoryRomIdentity', 'actualReadJournal'):
            record = self.record()
            record[extra] = True
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                self.provenance.validate_claim('StandardDeviceProperty', record)

    def test_documentary_graph_is_complete_acyclic_but_execution_blocked(self):
        graph = expected_graph()
        self.assertEqual(16, len(graph['nodes']))
        self.assertEqual({'acyclic': True, 'executionAdmission': False}, self.analysis.validate_graph(graph))
        ids = {node['id'] for node in graph['nodes']}
        for node in graph['nodes']:
            self.assertIsNone(node['actualObservation'])
            self.assertTrue(set(node['requires']) <= ids)
            self.assertTrue(node['neededEvidence'])

    def test_removing_each_dependency_cannot_shortcut_admission(self):
        graph = expected_graph()
        count = 0
        for index, node in enumerate(graph['nodes']):
            for dependency in node['requires']:
                changed = deepcopy(graph)
                changed['nodes'][index]['requires'].remove(dependency)
                with self.subTest(node=node['id'], dependency=dependency), self.assertRaises(ValueError):
                    self.analysis.validate_graph(changed)
                count += 1
        self.assertGreater(count, 30)

    def test_graph_cycle_dangling_missing_and_duplicate_nodes_refused(self):
        graph = expected_graph()
        mutations = []
        changed = deepcopy(graph)
        changed['nodes'][0]['requires'].append('execution')
        mutations.append(changed)
        changed = deepcopy(graph)
        changed['nodes'][0]['requires'].append('absent_owner')
        mutations.append(changed)
        changed = deepcopy(graph)
        changed['nodes'].pop(0)
        mutations.append(changed)
        changed = deepcopy(graph)
        changed['nodes'][1]['id'] = changed['nodes'][0]['id']
        mutations.append(changed)
        for index, changed in enumerate(mutations):
            with self.subTest(mutation=index), self.assertRaises(ValueError):
                self.analysis.validate_graph(changed)

    def test_graph_status_and_actual_observation_promotions_refused(self):
        for index in range(16):
            for field, value in (('status', 'ActualOwnerEstablished'),
                                 ('actualObservation', {'observed': True})):
                graph = expected_graph()
                graph['nodes'][index][field] = value
                with self.subTest(node=index, field=field), self.assertRaises(ValueError):
                    self.analysis.validate_graph(graph)

    def test_graph_malformed_structures_are_typed_refusals(self):
        for graph in (None, [], {}, {'nodes': []}, {'nodes': 'verified'}, {'nodes': True}):
            with self.subTest(graph=graph), self.assertRaises(ValueError):
                self.analysis.validate_graph(graph)

    def test_invented_byte_binding_positive_does_not_establish_actual_ecu(self):
        raw = b'M2cl invented documentary binding\n'
        digest = hashlib.sha256(raw).hexdigest()
        self.assertEqual({'byteIdentityVerified': True, 'actualEcuConfirmed': False, 'executionAdmission': False},
                         self.provenance.verify_bytes(raw, digest, len(raw)))

    def test_byte_digest_size_and_type_mutations_are_refused(self):
        raw = b'M2cl invented documentary binding\n'
        digest = hashlib.sha256(raw).hexdigest()
        controls = ((raw+b'x', digest, len(raw)), (raw[:-1], digest, len(raw)),
                    (b'X'+raw[1:], digest, len(raw)), (raw, '0'*64, len(raw)),
                    (raw, digest, len(raw)+1), (raw, digest.upper(), len(raw)),
                    ('not-bytes', digest, len(raw)), (raw, digest, True), (raw, None, len(raw)))
        for changed, sha, count in controls:
            with self.subTest(raw=changed, sha=sha, count=count), self.assertRaises(ValueError):
                self.provenance.verify_bytes(changed, sha, count)


if __name__ == '__main__':
    unittest.main()
