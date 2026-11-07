"""Invented test inputs for bounded source relations and ordinary frame obligations."""

from mode_caller_continuity.corpus import (
    fixture as accepted_fixture, indexed_event, partial, partial_slot, reaching_query, slot,
)


FRAME_PROOF = '7e4ba87467d98becfeff774b92bfdf2c3aeca07e88baf7b713fd9aafba14c9f8'
MODE_PROOF = 'cceb30cdcd17f7b0bd44ad7d120d46f4b922c3bd3ceb6a0919e576c4ce3fc9d2'
INDEXED_PROOF = 'b46b8fd1a40c084195f779d17fa8ce701f728f05d153fa2ce545c85f1ae7be62'
CALL_IDENTITIES = {
    0x276A: (0x5C86, 0x276D, 0x5CCD),
    0x2B64: (0x5C86, 0x2B67, 0x5CCD),
    0x27D0: (0x5F45, 0x27D3, 0x60E4),
    0x4069: (0x5F45, 0x406C, 0x60E4),
}
FRAME_PREMISES = (
    'matchingEntryReturn', 'stackMemoryApplicable', 'balancedNesting',
    'frameIntegrity', 'noAliasInterference',
)
LINEAGE_PREMISES = (
    'coldPathPredicates', 'indexedSuffixToReturn', 'modeEntryToRead',
    'explicitHandoff', 'interveningWritersExcluded',
)
EXTRA_DATA = ('0209', '0217', '0219', '0227', '0230')
PROGRAM_ADDRESSES = (0x60E6, 0x60E7, 0x60EB, 0x60EC, 0x60ED, 0x60EE,
                     0x60F0, 0x60F1, 0x60FB, 0x6104, 0x6105)


def fixture():
    snapshot = accepted_fixture()
    for key in EXTRA_DATA:
        snapshot['memory'].setdefault(key, 0)
        snapshot['generations'].setdefault(key, 'InventedM2cv:' + key)
    snapshot['sfrReadbacks']['0019'] = slot(0x10, 'Supplied:Irqh')
    return snapshot


def frame_query(caller=0x27D0, ssp=0x047E):
    target, candidate, rt = CALL_IDENTITIES[caller]
    return {
        'inputClass': 'SyntheticTestInput', 'sourceBinding': FRAME_PROOF,
        'callerPc': caller, 'declaredTarget': target, 'returnPc': rt,
        'incomingSsp': ssp, 'sspBeforeReturn': (ssp - 2) % 65536,
        'frame': {'kind': 'NormalCall', 'address': ssp & 0xFFFE,
                  'low': candidate % 256, 'high': candidate // 256,
                  'creatorPc': caller, 'generation': 'InventedMatchingFrame'},
        'premises': dict.fromkeys(FRAME_PREMISES, True), 'claim': 'ConditionalOnly',
    }


def indexed_query(caller=0x276A):
    return {'inputClass': 'SyntheticTestInput', 'callerPc': caller,
            'snapshot': fixture(), 'entryEstablished': True}


def program_operand(address, value, source_binding):
    return {'space': 'PROGRAM', 'address': address, 'widthBits': 8, 'index': None,
            'sourceBinding': source_binding, 'valueClass': 'InventedOnly',
            'slot': slot(value, f'InventedProgram:{address:04X}')}


def program_query(source_binding, value=0x80):
    snapshot = fixture()
    snapshot['memory']['0208'] = 1
    return {'inputClass': 'SyntheticTestInput', 'snapshot': snapshot,
            'entryEstablished': True, 'operand': program_operand(0x6105, value, source_binding)}


def mode_query(source_binding, entry='From5F45', caller=0x27D0):
    return {'inputClass': 'SyntheticTestInput', 'snapshot': fixture(),
            'entryEstablished': True, 'entry': entry,
            'callerPc': caller if entry == 'From5F45' else None,
            'program': {f'{address:04X}': program_operand(
                address, (0x80 if i % 2 else 0x01), source_binding)
                for i, address in enumerate(PROGRAM_ADDRESSES)}}


def case(case_id, operation, query):
    return {'id': case_id, 'operation': operation, 'input': query}


def frame_cases():
    op = 'call_return_obligations'
    for caller in CALL_IDENTITIES:
        for ssp in (0x047E, 0x047F):
            yield case(f'frame-{caller:04X}-{ssp:04X}', op, frame_query(caller, ssp))
    for ssp in (0, 1, 2, 4, 6, 8, 0x80, 0x86, 0xB5, 0x208, 0x356, 0x382, 0x3CB, 0xFFFF):
        yield case(f'frame-alias-{ssp:04X}', op, frame_query(ssp=ssp))
    for caller, slots in ((0x27D0, (0x020A, 0x0216, 0x0219, 0x0227)),
                          (0x276A, (0x0230, 0x03C6, 0x03CF, 0x03D4))):
        for address in slots:
            yield case(f'frame-callee-alias-{caller:04X}-{address:04X}', op, frame_query(caller, address))
    for name in FRAME_PREMISES:
        for value in (None, False):
            query = frame_query()
            query['premises'][name] = value
            yield case(f'frame-{name}-{value}', op, query)
    for key, value in (
        ('sourceBinding', None), ('sourceBinding', 'InventedMismatch'), ('callerPc', 0x4068),
        ('declaredTarget', 0x5C86), ('returnPc', 0x5CCD), ('returnPc', 0x2869),
        ('incomingSsp', None), ('sspBeforeReturn', None), ('sspBeforeReturn', 0x047E),
        ('claim', 'ActualNativeReturn'), ('claim', 'Execute'), ('claim', 'HostSelectedReturn'),
    ):
        query = frame_query()
        query[key] = value
        yield case(f'frame-{key}-{value}', op, query)
    for key, value in (
        ('kind', 'Interrupt'), ('address', None), ('address', 0x047F), ('address', 0x047C),
        ('low', None), ('high', None), ('low', 0x69), ('creatorPc', None),
        ('creatorPc', 0x4069), ('generation', None),
    ):
        query = frame_query()
        query['frame'][key] = value
        yield case(f'frame-slot-{key}-{value}', op, query)


def indexed_cases():
    op = 'indexed_acquisition_caller'
    for caller in (0x276A, 0x2B64):
        for index in range(8):
            query = indexed_query(caller)
            query['snapshot']['sfrReadbacks']['0024']['value'] = index << 5
            yield case(f'acquisition-{caller:04X}-{index}', op, query)
    for bank in (0, 3, 6, 7, None):
        query = indexed_query()
        query['snapshot']['registers']['scb'] = bank
        yield case(f'acquisition-scb-{bank}', op, query)
    for status, irqh in ((8, 0x10), (None, 0x10), (0, 0), (0, None), (0, 0xFF)):
        query = indexed_query()
        query['snapshot']['memory']['0230'] = status
        query['snapshot']['sfrReadbacks']['0019']['value'] = irqh
        yield case(f'acquisition-guard-{status}-{irqh}', op, query)
    for readback in ('0024', '0019', '0061', '0063'):
        for bits in ({}, {4: 1, 5: 1, 6: 0, 7: 1}):
            query = indexed_query()
            partial_slot(query['snapshot']['sfrReadbacks'][readback], bits)
            yield case(f'acquisition-partial-{readback}-{len(bits)}', op, query)
    for value in (None, False):
        query = indexed_query()
        query['entryEstablished'] = value
        yield case(f'acquisition-entry-{value}', op, query)
    for lrb in (None, 0, 0x40, 0x5F):
        query = indexed_query()
        query['snapshot']['registers']['lrb'] = lrb
        yield case(f'acquisition-lrb-{lrb}', op, query)
    for assumption in ('ordinaryByteSemantics', 'noInterference'):
        query = indexed_query()
        query['snapshot']['assumptions'][assumption] = None
        yield case(f'acquisition-assumption-{assumption}', op, query)
    query = indexed_query(0x27D0)
    yield case('acquisition-unsupported-caller', op, query)
    query = indexed_query()
    query['snapshot']['generations']['03CB'] = 'ConditionalEffect:data03cb_indexed_writer:5CB4:3'
    yield case('acquisition-repeated-child-generation', op, query)


def mode_cases():
    op = 'mode_enclosing_caller'
    for caller in (0x27D0, 0x4069, 0x276A):
        for bank in (0, 6, None):
            query = mode_query(MODE_PROOF, caller=caller)
            query['snapshot']['registers'].update(scb=bank, al=None, ah=None, zf=None, cf=None)
            query['snapshot']['registerKnownBits'] = {}
            yield case(f'mode-entry-{caller:04X}-{bank}', op, query)
    for value in (None, False):
        query = mode_query(MODE_PROOF)
        query['entryEstablished'] = value
        yield case(f'mode-entry-premise-{value}', op, query)
    for lrb in (None, 0x40, 0x21):
        query = mode_query(MODE_PROOF)
        query['snapshot']['registers']['lrb'] = lrb
        yield case(f'mode-prefix-lrb-{lrb}', op, query)
    for address in ('60E6', '60EC', '60FB'):
        query = mode_query(MODE_PROOF)
        del query['program'][address]
        yield case(f'mode-prefix-missing-{address}', op, query)
    query = mode_query(MODE_PROOF)
    query['snapshot']['assumptions']['ordinaryByteSemantics'] = False
    yield case('mode-prefix-byte-guard', op, query)
    query = mode_query(MODE_PROOF)
    for address in ('60E6', '60EC', '60FB'):
        partial_slot(query['program'][address]['slot'], {7: 1} if address == '60EC' else {})
    query['snapshot'] = partial(query['snapshot'], '0216', {0: 1, 4: 1})
    query['snapshot'] = partial(query['snapshot'], '03C7', {7: 1})
    yield case('mode-prefix-partial-words-and-bytes', op, query)

    for r0, guard, value in (
        (1, 0, 0x80), (1, 0, 0), (0, 0x40, None), (0, 0, 0x80),
        (0, 0, 0), (0, 0, None), (0, None, 0), (None, 0, 0),
    ):
        query = mode_query(MODE_PROOF, 'At608F')
        query['snapshot']['memory'].update({'0208': r0, '0217': guard, '03CB': 0x80})
        query['program']['6104']['slot']['value'] = value
        yield case(f'mode-suffix-{r0}-{guard}-{value}', op, query)
    for dd in (1, None):
        query = mode_query(MODE_PROOF, 'At608F')
        query['snapshot']['registers']['dd'] = dd
        yield case(f'mode-suffix-dd-{dd}', op, query)
    query = mode_query(MODE_PROOF, 'At608F')
    query['callerPc'] = 0x27D0
    yield case('mode-suffix-reject-borrowed-caller', op, query)


def program_cases():
    op = 'program_table_path'
    for value in (0, 1, 0x7F, 0x80, 0xFE, 0xFF, None):
        query = program_query(MODE_PROOF, value)
        yield case(f'program-operand-{value}', op, query)
    for value in (0, None):
        query = program_query(MODE_PROOF)
        query['snapshot']['memory']['0208'] = value
        yield case(f'program-r0-{value}', op, query)
    for value in (0x40, None):
        query = program_query(MODE_PROOF)
        query['snapshot']['registers']['lrb'] = value
        yield case(f'program-lrb-{value}', op, query)
    for dd in (1, None):
        query = program_query(MODE_PROOF)
        query['snapshot']['registers']['dd'] = dd
        yield case(f'program-shift-dd-{dd}', op, query)
    for key, value in (
        ('space', 'DATA'), ('address', 0x6104), ('address', None), ('widthBits', 16),
        ('index', 1), ('index', 0xFFFF), ('sourceBinding', None),
        ('sourceBinding', 'MismatchedSource'), ('valueClass', 'ClaimedOemByte'),
    ):
        query = program_query(MODE_PROOF)
        query['operand'][key] = value
        yield case(f'program-refuse-{key}-{value}', op, query)
    query = program_query(MODE_PROOF)
    query['operand'] = None
    yield case('program-missing-operand', op, query)
    for bit3 in (0, 1, None):
        query = program_query(MODE_PROOF)
        partial_slot(query['operand']['slot'], {7: 1})
        query['snapshot']['memory']['0216'] = None if bit3 is None else bit3 << 3
        yield case(f'program-partial-known-high-bit-mode-{bit3}', op, query)


def lineage_query(indexed_caller=0x276A, mode_caller=0x27D0):
    return {
        'inputClass': 'SyntheticTestInput', 'sourceBinding': INDEXED_PROOF,
        'indexedCallerPc': indexed_caller, 'modeCallerPc': mode_caller,
        'localLineage': reaching_query('WriterWindowRetention'),
        'indexedReturn': frame_query(indexed_caller),
        'modeIncomingSsp': 0x047E, 'premises': dict.fromkeys(LINEAGE_PREMISES, True),
        'claim': 'ConditionalOnly',
    }


def lineage_cases():
    op = 'indexed_to_mode_reaching_definitions'
    for indexed in (0x276A, 0x2B64):
        for mode in (0x27D0, 0x4069):
            yield case(f'lineage-{indexed:04X}-{mode:04X}', op, lineage_query(indexed, mode))
    for name in LINEAGE_PREMISES:
        for value in (False, None):
            query = lineage_query()
            query['premises'][name] = value
            yield case(f'lineage-premise-{name}-{value}', op, query)
    for key, value in (
        ('sourceBinding', None), ('sourceBinding', 'InventedWrongProof'),
        ('indexedCallerPc', 0x5C86), ('modeCallerPc', 0x5F45), ('modeCallerPc', 0x2869),
        ('modeIncomingSsp', None), ('modeIncomingSsp', 0x0208), ('modeIncomingSsp', 0x03CB),
        ('modeIncomingSsp', 0x0356), ('modeIncomingSsp', 0x0382),
        ('claim', 'NativeOwner'), ('claim', 'ActualHardware'), ('claim', 'RuntimeAdmission'),
    ):
        query = lineage_query()
        query[key] = value
        yield case(f'lineage-{key}-{value}', op, query)
    for field, value in (('sspBeforeReturn', None), ('incomingSsp', 0x047C), ('returnPc', 0x60E4)):
        query = lineage_query()
        query['indexedReturn'][field] = value
        yield case(f'lineage-unproved-frame-{field}', op, query)
    query = lineage_query()
    query['indexedReturn'] = frame_query(0x2B64)
    yield case('lineage-borrowed-return', op, query)
    for selector in (0, 7, None):
        query = lineage_query()
        query['localLineage']['events'][0]['p2']['value'] = None if selector is None else selector << 5
        yield case(f'lineage-selector-{selector}', op, query)
    query = lineage_query()
    query['localLineage']['requestedGeneration'] = 'OlderAdc'
    yield case('lineage-stale-request', op, query)
    query = lineage_query()
    later = indexed_event('AdcSample2')
    later['id'] = 'SecondAcquisitionSameValue'
    query['localLineage']['events'].append(later)
    yield case('lineage-repeat-same-value-new-generation', op, query)
    for address, width in ((0x03CB, 8), (0x03CB, 16), (None, 8)):
        query = lineage_query()
        query['localLineage']['events'].append({
            'kind': 'AlternateStore', 'id': 'CompetingDeclaredWriter', 'address': address,
            'widthBits': width, 'value': 0x80 if width == 8 else 0x8077,
            'generation': 'LaterGeneration',
        })
        yield case(f'lineage-overlap-{address}-{width}', op, query)


def clobber_query(caller=0x27D0, phase='ModeCalleeBeforeRt', scb=0):
    return {'inputClass': 'SyntheticTestInput', 'callerPc': caller, 'phase': phase,
            'scb': scb, 'contextEstablished': True}


def clobber_cases():
    op = 'callee_clobber_summary'
    for caller in (0x27D0, 0x4069):
        for bank in (*range(8), None):
            yield case(f'clobber-mode-{caller:04X}-{bank}', op, clobber_query(caller, scb=bank))
        yield case(f'clobber-pre-entry-{caller:04X}', op, clobber_query(caller, 'CallerPreEntry'))
    for value in (None, False):
        query = clobber_query()
        query['contextEstablished'] = value
        yield case(f'clobber-context-{value}', op, query)
    yield case('clobber-unreviewed-caller', op, clobber_query(0x276A))


def cases():
    for group in (frame_cases, indexed_cases, mode_cases, program_cases, lineage_cases, clobber_cases):
        yield from group()
