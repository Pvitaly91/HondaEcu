"""Bounded alternate-parser equations; no fetch, decoder or peripheral execution."""
from copy import deepcopy
import re

from conditional_flag_mode_shadow.state import Boundary, Effects, need, number

from .addressing import TABLE_BASE, qualify_data_read
from .checksum import byte_effect

_MAPPINGS = {'ConditionalStandardInternal201', 'ConditionalStandardInternal207', 'Unknown'}
_TRACKED = ('al', 'ah', 'cf', 'zf', 'hc', 'dd')
_CONSTRAINTS = ('ActualEcuEquivalenceNotEstablished', 'PhysicalDataMappingNotEstablished',
                'NativeEntryOwnershipNotEstablished', 'StbufTransmissionNotPerformed')


def _label(value):
    return value is None or type(value) is str and 0 < len(value) <= 128


def _context(value, snapshot):
    need(type(value) is dict and set(value) == {'data', 'knownDataBits', 'programWords', 'dataMapping'},
         'ClosedAlternateContextRequired')
    data, bits, words = value['data'], value['knownDataBits'], value['programWords']
    need(type(value['dataMapping']) is str and value['dataMapping'] in _MAPPINGS,
         'ClosedConditionalMappingRequired')
    need(type(data) is dict and len(data) <= 256 and not set(data) & set(snapshot['memory']),
         'DisjointBoundedAdditionalDataRequired')
    for key, row in data.items():
        need(type(key) is str and re.fullmatch(r'[0-9A-F]{4}', key) is not None
             and type(row) is dict and set(row) == {'value', 'generation'}
             and number(row['value'], 255) and _label(row['generation']), 'TypedAdditionalDataRequired')
        need(int(key, 16) >= 8, 'ArchitecturalRegisterDataOverrideNotAdmitted')
    memory = {**snapshot['memory'], **{key: row['value'] for key, row in data.items()}}
    need(type(bits) is dict and len(bits) <= 8 * len(memory), 'BoundedPartialDataKnowledgeRequired')
    for key, bit in bits.items():
        need(type(key) is str and re.fullmatch(r'[0-9A-F]{4}\.[0-7]', key) is not None
             and key[:4] in memory and type(bit) is int and bit in (0, 1), 'TypedPartialDataKnowledgeRequired')
        need(memory[key[:4]] is None or memory[key[:4]] >> int(key[-1]) & 1 == bit,
             'ContradictoryPartialDataKnowledge')
        need(key not in snapshot['knownBits'] or snapshot['knownBits'][key] == bit,
             'ContradictoryInheritedBitKnowledge')
    scb, usp = snapshot['registers']['scb'], snapshot['registers']['usp']
    if scb is not None and usp is not None:
        known = {**snapshot['knownBits'], **bits}
        for offset in range(2):
            key = f'{0x86 + 8 * scb + offset:04X}'
            if key in memory:
                expected = usp >> (8 * offset) & 255
                need(memory[key] is None or memory[key] == expected, 'ContradictoryActiveUspAlias')
                need(all(expected >> int(field[-1]) & 1 == bit
                         for field, bit in known.items() if field[:4] == key),
                     'ContradictoryActiveUspAliasBits')
    need(type(words) is list and len(words) <= 256, 'BoundedProgramWordInputsRequired')
    seen = set()
    for row in words:
        need(type(row) is dict and set(row) == {'address', 'value', 'generation'}
             and type(row['address']) is int and 0 <= row['address'] <= 65534 and row['address'] % 2 == 0
             and row['address'] not in seen and number(row['value'], 65535) and _label(row['generation']),
             'DistinctTypedProgramWordInputsRequired')
        seen.add(row['address'])
    return deepcopy(value)


def _consensus(values):
    unique = set(values)
    return next(iter(unique)) if len(unique) == 1 else None


def _partial(values):
    values = set(values)
    value = _consensus(values)
    bits = {} if value is not None else {str(bit): selected for bit in range(8)
        if (selected := _consensus(value >> bit & 1 for value in values)) is not None}
    return value, bits


def _possibilities(value, bits):
    if value is not None:
        return (value,)
    return tuple(candidate for candidate in range(256)
                 if all(candidate >> int(bit) & 1 == selected for bit, selected in bits.items()))


class _PathEffects(Effects):
    """Reuse frozen ordered DATA effects while extending its explicit storage scope."""

    def __init__(self, snapshot, context, procedure, entry):
        super().__init__(snapshot, procedure)
        self.context = _context(context, snapshot)
        for key, row in self.context['data'].items():
            self.state['memory'][key] = row['value']
            self.state['generations'][key] = row['generation']
        self.state['knownBits'].update(self.context['knownDataBits'])
        self.register_generations = {key: 'InputRegister:' + key.upper() for key in _TRACKED}
        self.register_bits = {'al': {}, 'ah': {}}
        self.last_writer = {key: None for key in _TRACKED}
        self.qualifications, self.program_dependencies = [], []
        self.entry = entry
        self.used_generations = {value for value in self.state['generations'].values() if value is not None}
        self.used_generations.update(row['generation'] for row in self.context['programWords']
                                     if row['generation'] is not None)
        self.used_generations.update(self.register_generations.values())

    def fresh_store_generation(self, pc):
        generation = f'ConditionalEffect:{self.procedure}:{pc:04X}:{len(self.journal) + 1}'
        if generation in self.used_generations:
            self.halt('OutsideVerifiedScope', 'WriterGenerationCollision', pc)
        return generation

    def store(self, pc, address, parts, kind='Store', source='A', preserve_bits=False):
        generation = self.fresh_store_generation(pc)
        super().store(pc, address, parts, kind, source, preserve_bits)
        self.used_generations.add(generation)

    def assign(self, pc, **values):
        for key, value in values.items():
            self.r[key] = value
            self.register_generations[key] = f'ConditionalRegister:{self.procedure}:{pc:04X}:{key.upper()}'
            self.last_writer[key] = pc
            if key in self.register_bits:
                self.register_bits[key] = {}

    def set_byte(self, pc, key, possibilities):
        value, bits = _partial(possibilities)
        self.assign(pc, **{key: value})
        self.register_bits[key] = bits

    def register_values(self, key):
        return _possibilities(self.r[key], self.register_bits[key])

    def data_values(self, address):
        key = f'{address:04X}'
        bits = {field[-1]: bit for field, bit in self.state['knownBits'].items() if field[:4] == key}
        return _possibilities(self.state['memory'][key], bits)

    def read(self, pc, address, width=8):
        address = address & 0xFFFE if width == 16 else address
        keys = [f'{address + offset:04X}' for offset in range(width // 8)]
        if any(key not in self.state['memory'] for key in keys):
            self.halt('OutsideVerifiedScope', 'DataSnapshotMissing', pc)
        parts = [_consensus(self.data_values(address + offset)) for offset in range(width // 8)]
        value = parts[0] if width == 8 else None if None in parts else parts[0] | parts[1] << 8
        self.reads.append({'pc': pc, 'space': 'DATA', 'address': address, 'widthBits': width,
            'value': value, 'bytes': parts,
            'knownBits': {key: bit for key, bit in self.state['knownBits'].items() if key[:4] in keys},
            'generations': [self.state['generations'][key] for key in keys]})
        return parts

    def load_byte(self, pc, address, following):
        if self.input['assumptions']['ordinaryByteSemantics'] is not True:
            self.halt('OutsideVerifiedScope', 'OrdinaryByteSemanticsNotEstablished', pc)
        self.read(pc, address)
        possible = self.data_values(address)
        self.set_byte(pc, 'al', possible)
        self.assign(pc, dd=0, zf=_consensus(int(value == 0) for value in possible))
        self.step(pc, following)

    def compare(self, pc, right, following):
        left = self.register_values('al')
        self.assign(pc, cf=_consensus(int(a < b) for a in left for b in right),
                    zf=_consensus(int(a == b) for a in left for b in right))
        self.step(pc, following)

    def byte_arithmetic(self, pc, kind, left, right, destination, following):
        if destination != 'al':
            self.fresh_store_generation(pc)
        values = [byte_effect(kind, a, b) for a in left for b in right]
        self.assign(pc, **{key: _consensus(row[key] for row in values) for key in ('cf', 'zf', 'hc')})
        possible = {row['value'] for row in values}
        if destination == 'al':
            self.set_byte(pc, 'al', possible)
        else:
            value, bits = _partial(possible)
            key = f'{destination:04X}'
            self.state['knownBits'] = {field: bit for field, bit in self.state['knownBits'].items()
                                       if field[:4] != key}
            self.state['knownBits'].update({key + '.' + bit: selected for bit, selected in bits.items()})
            self.store(pc, destination, [value], 'RMW', 'DATA03F6+AL', preserve_bits=True)
        self.step(pc, following)

    def pointer_address(self, pc, writing=False):
        if self.r['scb'] is None:
            self.halt('OutsideVerifiedScope', 'SelectedPointingBankUnknown', pc)
        if self.context['dataMapping'] == 'Unknown':
            self.halt('OutsideVerifiedScope', 'PointerMappingNotEstablished', pc)
        address = 0x84 + 8 * self.r['scb']
        if any(f'{address + i:04X}' not in self.state['memory'] for i in range(2)):
            self.halt('OutsideVerifiedScope', 'PointerStorageSnapshotMissing' if writing else 'DataSnapshotMissing', pc)
        return address

    def store_pointer(self, pc, following):
        address = self.pointer_address(pc, writing=True)
        self.fresh_store_generation(pc)
        keys = [f'{address + offset:04X}' for offset in range(2)]
        self.state['knownBits'] = {field: bit for field, bit in self.state['knownBits'].items()
                                   if field[:4] not in keys}
        for key, register in zip(keys, ('al', 'ah')):
            self.state['knownBits'].update({key + '.' + bit: selected
                                           for bit, selected in self.register_bits[register].items()})
        self.store(pc, address, [self.r['al'], self.r['ah']], 'PointerStore', 'A', preserve_bits=True)
        self.step(pc, following)

    def load_self_word(self):
        pc = 0x231
        self.qualifications.append(qualify_data_read(pc, 6, 16, self.r['scb'], self.r['lrb'],
                                                   self.context['dataMapping']))
        low, high = self.register_values('al'), self.register_values('ah')
        self.reads.append({'pc': pc, 'space': 'DATA', 'address': 6, 'widthBits': 16,
            'value': None if self.r['al'] is None or self.r['ah'] is None else self.r['al'] | self.r['ah'] << 8,
            'bytes': [self.r['al'], self.r['ah']],
            'knownBits': {f'{address:04X}.{bit}': selected for address, register in ((6, 'al'), (7, 'ah'))
                          for bit, selected in self.register_bits[register].items()},
            'generations': [self.register_generations[key] for key in ('al', 'ah')]})
        self.set_byte(pc, 'al', low)
        self.set_byte(pc, 'ah', high)
        self.assign(pc, dd=1, zf=_consensus(int(a == b == 0) for a in low for b in high))
        self.step(pc, 0x233)

    def word_shift_and_add(self):
        values = {low | high << 8 for low in self.register_values('al') for high in self.register_values('ah')}
        shifted = {(value << 1) & 65535 for value in values}
        self.assign(0x233, cf=_consensus(value >> 15 for value in values))
        self.set_byte(0x233, 'al', {value & 255 for value in shifted})
        self.set_byte(0x233, 'ah', {value >> 8 for value in shifted})
        self.step(0x233, 0x234)
        # ADD word uses carry out bit15 and half carry out bit3, not bit11.
        sums = {value + TABLE_BASE for value in shifted}
        self.assign(0x234, cf=_consensus(int(value > 65535) for value in sums),
                    zf=_consensus(int(value & 65535 == 0) for value in sums),
                    hc=_consensus(int((value & 15) + (TABLE_BASE & 15) > 15) for value in shifted))
        self.set_byte(0x234, 'al', {value & 255 for value in sums})
        self.set_byte(0x234, 'ah', {(value & 65535) >> 8 for value in sums})
        self.step(0x234, 0x237)

    def load_program_word(self):
        pc = 0x238
        parts = self.read(pc, self.pointer_address(pc), 16)
        address = None if None in parts else parts[0] | parts[1] << 8
        if address is None:
            self.halt('OutsideVerifiedScope', 'ProgramAddressUnknown', pc)
        row = next((row for row in self.context['programWords'] if row['address'] == address), None)
        if row is None:
            self.halt('OutsideVerifiedScope', 'ProgramWordInputMissing', pc)
        if row['generation'] is None:
            self.halt('OutsideVerifiedScope', 'ProgramWordGenerationMissing', pc)
        value, generation = row['value'], row['generation']
        parts = [None, None] if value is None else [value & 255, value >> 8]
        self.reads.append({'pc': pc, 'space': 'PROGRAM', 'address': address, 'widthBits': 16,
            'value': value, 'bytes': parts, 'knownBits': {}, 'generations': [generation, generation]})
        self.program_dependencies.append({'pc': pc, 'address': address, 'widthBits': 16, 'value': value,
            'generation': generation, 'sourceClass': 'DeclaredProgramWordInput', 'actualProgramRead': None})
        self.assign(pc, al=parts[0], ah=parts[1], zf=None if value is None else int(value == 0))
        self.step(pc, 0x23A)

    def load_selected_data(self):
        pc = 0x23B
        parts = self.read(pc, self.pointer_address(pc), 16)
        address = None if None in parts else parts[0] | parts[1] << 8
        qualification = qualify_data_read(pc, address, 8, self.r['scb'], self.r['lrb'],
                                          self.context['dataMapping'])
        self.qualifications.append(qualification)
        if not qualification['allowed']:
            self.halt('OutsideVerifiedScope', qualification['classification'], pc)
        self.load_byte(pc, address, 0x23C)

    def result(self, status, reason, boundary, outcome=None):
        result = super().result(status, reason, boundary, outcome)
        candidate, intent = None, None
        if status == 'CompleteConditional' and boundary == 0x23E:
            candidate = {'status': 'ResponseByteComputed' if self.r['al'] is not None else 'IndeterminateResponseByte',
                'value': self.r['al'], 'sourcePc': self.last_writer['al'],
                'generation': self.register_generations['al']}
            intent = {'pc': 0x23E, 'space': 'DATA', 'address': 0x51, 'widthBits': 8,
                'value': self.r['al'], 'sourceRegister': 'AL',
                'sourceGeneration': self.register_generations['al'], 'actualWrite': None}
        accumulated = any(row['pc'] == 0x23C for row in self.journal)
        negated = any(row['pc'] == 0x252 for row in self.steps)
        constraints = list(_CONSTRAINTS)
        if status != 'CompleteConditional':
            constraints.append(reason)
        return {**result,
            'entryQualification': 'DetachedConditionalSourcePath' if self.entry == 0x227 else 'DetachedAuxiliaryEntry',
            'registerGenerations': self.register_generations, 'registerKnownBits': self.register_bits,
            'readQualifications': self.qualifications, 'programDependencies': self.program_dependencies,
            'responseCandidate': candidate, 'prospectiveStbufIntent': intent,
            'checksumState': {'address': 0x3F6, 'value': self.state['memory']['03F6'],
                'generation': self.state['generations']['03F6'], 'updatedAtPc': 0x23C if accumulated else None,
                'relation': 'AccumulatedSelectedByte' if accumulated else 'NegatedForResponseOnly' if negated else 'Unchanged'},
            'stopBoundary': 'STOP_BEFORE_STBUF_023E' if boundary == 0x23E else
                            'STOP_BEFORE_EPILOGUE_0244' if boundary == 0x244 else None,
            'unresolvedConstraints': constraints}


def _accumulate(effects, outcome):
    effects.read(0x23C, 0x3F6)
    effects.byte_arithmetic(0x23C, 'Add', effects.data_values(0x3F6),
                            effects.register_values('al'), 0x3F6, 0x23E)
    return effects.finish(outcome, 0x23E)


def _length_response(effects):
    effects.load_byte(0x24C, 0x3F2, 0x24D)
    effects.step(0x24D, 0x23C, 'Jump', True)
    return _accumulate(effects, 'LengthRegisterResponse')


def _at_or_beyond_length(effects):
    if effects.branch(0x24F, None if effects.r['zf'] is None else effects.r['zf'] == 0, 0x244, 0x251):
        return effects.finish('CounterBeyondLength', 0x244)
    effects.assign(0x251, al=0, dd=0, zf=1)
    effects.step(0x251, 0x252)
    effects.read(0x252, 0x3F6)
    effects.byte_arithmetic(0x252, 'Subtract', (0,), effects.data_values(0x3F6), 'al', 0x253)
    effects.step(0x253, 0x23E, 'Jump', True)
    return effects.finish('NegatedChecksumResponse', 0x23E)


def _selector(effects):
    effects.assign(0x227, al=0, ah=0, dd=1, zf=1)
    effects.step(0x227, 0x228)
    effects.load_byte(0x228, 0x3F5, 0x229)
    effects.compare(0x229, (2,), 0x22B)
    if effects.branch(0x22B, None if effects.r['zf'] is None else effects.r['zf'] == 1, 0x24C, 0x22D):
        return _length_response(effects)
    effects.read(0x22D, 0x3F2)
    effects.compare(0x22D, effects.data_values(0x3F2), 0x22E)
    if effects.branch(0x22E, None if effects.r['cf'] is None else effects.r['cf'] == 0, 0x24F, 0x230):
        return _at_or_beyond_length(effects)
    effects.read(0x230, 0x3F3)
    effects.byte_arithmetic(0x230, 'Add', effects.register_values('al'), effects.data_values(0x3F3), 'al', 0x231)
    effects.load_self_word()
    effects.word_shift_and_add()
    effects.store_pointer(0x237, 0x238)
    effects.load_program_word()
    effects.store_pointer(0x23A, 0x23B)
    effects.load_selected_data()
    return _accumulate(effects, 'ProgramSelectedDataResponse')


def _run(query, auxiliary):
    keys = {'snapshot', 'context', 'entryPc'} if auxiliary else {'snapshot', 'context'}
    need(type(query) is dict and set(query) == keys, 'ClosedAlternatePathQueryRequired')
    entry = query['entryPc'] if auxiliary else 0x227
    need(type(entry) is int and entry in ((0x24C, 0x24F) if auxiliary else (0x227,)),
         'ClosedAlternateEntryRequired')
    procedure = 'alternate_auxiliary_024c_0253' if auxiliary else 'alternate_response_selector'
    effects = _PathEffects(query['snapshot'], query['context'], procedure, entry)
    try:
        effects.admit(entry)
        return (_length_response if entry == 0x24C else _at_or_beyond_length if entry == 0x24F else _selector)(effects)
    except Boundary as boundary:
        return effects.result(boundary.status, boundary.reason, boundary.pc)


def alternate_response_selector(query):
    """Detached conditional entry0227; source-prefix reach is a separate proof."""
    return _run(query, False)


def alternate_auxiliary_024c_0253(query):
    """Two independently explicit auxiliary entries; never enter an epilogue."""
    return _run(query, True)
