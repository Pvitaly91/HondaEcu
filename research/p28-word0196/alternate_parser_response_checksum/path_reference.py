"""Independent CFG and finite-value equations for the alternate parser paths."""

from conditional_flag_mode_shadow.state import Boundary, Effects, word


_REGISTER_NAMES = ('al', 'ah', 'cf', 'zf', 'hc', 'dd')
_LIMITS = {'ConditionalStandardInternal201': 0x280, 'ConditionalStandardInternal207': 0x480}
_MISSING = ['ActualEcuEquivalenceNotEstablished', 'PhysicalDataMappingNotEstablished',
            'NativeEntryOwnershipNotEstablished', 'StbufTransmissionNotPerformed']


def _common(values):
    values = set(values)
    return next(iter(values)) if len(values) == 1 else None


def _domain(value, bits):
    if value is not None:
        return (value,)
    return tuple(candidate for candidate in range(256)
                 if all((candidate // (1 << int(bit))) % 2 == expected for bit, expected in bits.items()))


def _project(values):
    value = _common(values)
    bits = {}
    if value is None:
        for bit in range(8):
            shared = _common(v // (1 << bit) % 2 for v in values)
            if shared is not None:
                bits[str(bit)] = shared
    return value, bits


def _arith(left, right, radix=256, sign=1):
    rows = [(divmod(a + sign * b, radix), divmod(a % 16 + sign * (b % 16), 16)[0])
            for a in left for b in right]
    residues = [value for (_, value), _ in rows]
    flags = {
        'cf': _common(int(bool(carry)) for (carry, _), _ in rows),
        'zf': _common(int(value == 0) for value in residues),
        'hc': _common(int(bool(carry)) for _, carry in rows),
    }
    return residues, flags


def _qualification(pc, address, scb, lrb, mapping):
    width = 16 if pc == 0x0231 else 8
    pointer, local = None, []
    if address is None:
        classification = 'UnknownEffectiveAddress'
    elif pc == 0x0231:
        classification = 'ConditionalArchitecturalAlias'
    else:
        if 0x80 <= address < 0xC0:
            bank, within = divmod(address - 0x80, 8)
            pointer = {'bank': bank, 'register': ('X1', 'X2', 'DP', 'USP')[within // 2],
                       'byteOffset': within % 2, 'selected': None if scb is None else scb == bank}
        if lrb is not None:
            offset = address - (lrb % 0x2000) * 8
            if 0 <= offset <= 7:
                local = [offset]
        special = {0x51: 'WriteOnlyRegisterReadBlocked', 0x55: 'UnresolvedReadSideEffect'}
        if address < 0x80:
            classification = special.get(address, 'PotentialSfrRead')
        elif mapping == 'Unknown':
            classification = 'AddressApplicabilityUnknown'
        elif pointer is not None:
            classification = 'ConditionalPointerBankRead'
        elif address < _LIMITS[mapping]:
            classification = 'QualifiedOrdinaryDataRead'
        else:
            classification = 'ExternalDataApplicabilityUnknown'
    return {'pc': pc, 'space': 'DATA', 'rawAddress': address, 'effectiveAddress': address,
            'widthBits': width, 'classification': classification, 'allowed': classification in (
                'ConditionalArchitecturalAlias', 'ConditionalPointerBankRead', 'QualifiedOrdinaryDataRead'),
            'pointerAlias': pointer, 'localAliases': local, 'actualHardwareRead': None}


class _Reference(Effects):
    def __init__(self, query, procedure, qualification):
        super().__init__(query['snapshot'], procedure)
        self.context = query['context']
        for key, slot in self.context['data'].items():
            self.state['memory'][key] = slot['value']
            self.state['generations'][key] = slot['generation']
        self.state['knownBits'].update(self.context['knownDataBits'])
        self.qualification = qualification
        self.reg_gen = {name: 'InputRegister:' + name.upper() for name in _REGISTER_NAMES}
        self.reg_bits = {'al': {}, 'ah': {}}
        self.register_sites = {}
        self.qualifiers, self.dependencies = [], []
        self.checksum_update, self.checksum_negated = False, False
        self.reserved_generations = set(self.state['generations'].values()) | {
            item['generation'] for item in self.context['programWords']}

    def read_data(self, pc, address, width=8):
        self.read(pc, address, width)
        locations = range(address, address + width // 8)
        result = [_common(self.data_domain(location)) for location in locations]
        self.reads[-1].update(bytes=result, value=result[0] if width == 8 else word(result),
                             generations=[self.state['generations'][f'{location:04X}'] for location in locations])
        return result

    def data_domain(self, address):
        key = f'{address:04X}'
        bits = {name[5:]: value for name, value in self.state['knownBits'].items() if name[:4] == key}
        return _domain(self.state['memory'][key], bits)

    def reg_domain(self, name):
        return _domain(self.r[name], self.reg_bits[name])

    def a_domain(self):
        return tuple(lo + hi * 256 for lo in self.reg_domain('al') for hi in self.reg_domain('ah'))

    def update(self, pc, **registers):
        for name, value in registers.items():
            self.r[name] = value
            self.reg_gen[name] = f'ConditionalRegister:{self.procedure}:{pc:04X}:{name.upper()}'
            self.register_sites[name] = pc
            if name in self.reg_bits:
                self.reg_bits[name] = {}

    def bytes_result(self, pc, regs, **flags):
        values = {name: _project(domain) for name, domain in regs.items()}
        self.update(pc, **{name: item[0] for name, item in values.items()}, **flags)
        for name, (_, bits) in values.items():
            self.reg_bits[name] = bits

    def word_result(self, pc, numbers, **flags):
        self.bytes_result(pc, {'al': [v % 256 for v in numbers], 'ah': [v // 256 for v in numbers]}, **flags)

    def load(self, pc, address, following):
        if self.input['assumptions']['ordinaryByteSemantics'] is not True:
            self.halt('OutsideVerifiedScope', 'OrdinaryByteSemanticsNotEstablished', pc)
        self.read_data(pc, address)
        domain = self.data_domain(address)
        self.bytes_result(pc, {'al': domain}, dd=0, zf=_common(int(v == 0) for v in domain))
        self.step(pc, following)

    def cmp(self, pc, right, following):
        pairs = tuple((a, b) for a in self.reg_domain('al') for b in right)
        self.update(pc, cf=_common(int(a < b) for a, b in pairs), zf=_common(int(a == b) for a, b in pairs))
        self.step(pc, following)

    def jump(self, pc, target):
        self.step(pc, target, 'Jump', True)

    def ask(self, pc, flag, accepted, first, second):
        actual = self.r[flag]
        return self.branch(pc, None if actual is None else actual == accepted, first, second)

    def reserve_next_write(self, pc):
        generation = f'ConditionalEffect:{self.procedure}:{pc:04X}:{len(self.journal) + 1}'
        if generation in self.reserved_generations:
            self.halt('OutsideVerifiedScope', 'WriterGenerationCollision', pc)
        self.reserved_generations.add(generation)

    def accumulate(self, outcome):
        self.read_data(0x023C, 0x03F6)
        self.reserve_next_write(0x023C)
        numbers, flags = _arith(self.data_domain(0x03F6), self.reg_domain('al'))
        new, bits = _project(numbers)
        self.update(0x023C, **flags)
        self.state['knownBits'] = {key: value for key, value in self.state['knownBits'].items() if key[:4] != '03F6'}
        self.state['knownBits'].update({f'03F6.{bit}': value for bit, value in bits.items()})
        self.store(0x023C, 0x03F6, [new], 'RMW', 'DATA03F6+AL', preserve_bits=True)
        self.checksum_update = True
        self.step(0x023C, 0x023E)
        return self.finish(outcome, 0x023E)

    def r2_path(self):
        self.load(0x024C, 0x03F2, 0x024D)
        self.jump(0x024D, 0x023C)
        return self.accumulate('LengthRegisterResponse')

    def remaining_path(self):
        if self.ask(0x024F, 'zf', 0, 0x0244, 0x0251):
            return self.finish('CounterBeyondLength', 0x0244)
        self.update(0x0251, al=0, zf=1, dd=0)
        self.step(0x0251, 0x0252)
        self.read_data(0x0252, 0x03F6)
        numbers, flags = _arith((0,), self.data_domain(0x03F6), sign=-1)
        self.bytes_result(0x0252, {'al': numbers}, **flags)
        self.checksum_negated = True
        self.step(0x0252, 0x0253)
        self.jump(0x0253, 0x023E)
        return self.finish('NegatedChecksumResponse', 0x023E)

    def dp_base(self):
        if self.context['dataMapping'] == 'Unknown':
            self.halt('OutsideVerifiedScope', 'PointerMappingNotEstablished', 0x0237)
        if self.r['scb'] is None:
            self.halt('OutsideVerifiedScope', 'SelectedPointingBankUnknown', 0x0237)
        base = 0x84 + 8 * self.r['scb']
        if any(f'{address:04X}' not in self.state['memory'] for address in (base, base + 1)):
            self.halt('OutsideVerifiedScope', 'PointerStorageSnapshotMissing', 0x0237)
        return base

    def copy_a_to_dp(self, pc, base, following):
        self.reserve_next_write(pc)
        keys = (f'{base:04X}', f'{base + 1:04X}')
        self.state['knownBits'] = {name: value for name, value in self.state['knownBits'].items() if name[:4] not in keys}
        self.state['knownBits'].update({f'{key}.{bit}': value for key, register in zip(keys, ('al', 'ah'))
                                        for bit, value in self.reg_bits[register].items()})
        self.store(pc, base, [self.r['al'], self.r['ah']], 'PointerStore', 'A', preserve_bits=True)
        self.step(pc, following)

    def reread_a(self):
        self.qualifiers.append(_qualification(0x0231, 6, self.r['scb'], self.r['lrb'], self.context['dataMapping']))
        parts = [self.r['al'], self.r['ah']]
        bits = {f'{address:04X}.{bit}': value for address, name in ((6, 'al'), (7, 'ah'))
                for bit, value in self.reg_bits[name].items()}
        self.reads.append({'pc': 0x0231, 'space': 'DATA', 'address': 6, 'widthBits': 16, 'value': word(parts),
                           'bytes': parts, 'knownBits': bits, 'generations': [self.reg_gen['al'], self.reg_gen['ah']]})
        loaded = self.a_domain()
        self.word_result(0x0231, loaded, dd=1, zf=_common(int(v == 0) for v in loaded))
        self.step(0x0231, 0x0233)

    def program_pointer(self, base):
        address = word(self.read_data(0x0238, base, 16))
        selected = next((item for item in self.context['programWords'] if item['address'] == address), None)
        if selected is None:
            self.halt('OutsideVerifiedScope', 'ProgramWordInputMissing', 0x0238)
        generation, value = selected['generation'], selected['value']
        if generation is None:
            self.halt('OutsideVerifiedScope', 'ProgramWordGenerationMissing', 0x0238)
        parts = [None, None] if value is None else [value % 256, value // 256]
        self.reads.append({'pc': 0x0238, 'space': 'PROGRAM', 'address': address, 'widthBits': 16, 'value': value,
                           'bytes': parts, 'knownBits': {}, 'generations': [generation, generation]})
        self.dependencies.append({'pc': 0x0238, 'address': address, 'widthBits': 16, 'value': value,
                                  'generation': generation, 'sourceClass': 'DeclaredProgramWordInput',
                                  'actualProgramRead': None})
        self.update(0x0238, al=parts[0], ah=parts[1], zf=None if value is None else int(value == 0))
        self.step(0x0238, 0x023A)

    def table_path(self):
        self.read_data(0x0230, 0x03F3)
        numbers, flags = _arith(self.reg_domain('al'), self.data_domain(0x03F3))
        self.bytes_result(0x0230, {'al': numbers}, **flags)
        self.step(0x0230, 0x0231)
        self.reread_a()
        previous = self.a_domain()
        self.word_result(0x0233, [(2 * value) % 65536 for value in previous],
                         cf=_common(value // 32768 for value in previous))
        self.step(0x0233, 0x0234)
        numbers, flags = _arith(self.a_domain(), (0x6E12,), 65536)
        self.word_result(0x0234, numbers, **flags)
        self.step(0x0234, 0x0237)
        base = self.dp_base()
        self.copy_a_to_dp(0x0237, base, 0x0238)
        self.program_pointer(base)
        self.copy_a_to_dp(0x023A, base, 0x023B)
        target = word(self.read_data(0x023B, base, 16))
        obligation = _qualification(0x023B, target, self.r['scb'], self.r['lrb'], self.context['dataMapping'])
        self.qualifiers.append(obligation)
        if not obligation['allowed']:
            self.halt('OutsideVerifiedScope', obligation['classification'], 0x023B)
        if f'{target:04X}' not in self.state['memory']:
            self.halt('OutsideVerifiedScope', 'DataSnapshotMissing', 0x023B)
        self.load(0x023B, target, 0x023C)
        return self.accumulate('ProgramSelectedDataResponse')

    def result(self, status, reason, boundary, outcome=None):
        result = super().result(status, reason, boundary, outcome)
        response, intent = None, None
        if boundary == 0x023E:
            value, generation = self.r['al'], self.reg_gen['al']
            response = {'status': 'IndeterminateResponseByte' if value is None else 'ResponseByteComputed',
                        'value': value, 'sourcePc': self.register_sites.get('al'), 'generation': generation}
            intent = {'pc': 0x023E, 'space': 'DATA', 'address': 0x51, 'widthBits': 8, 'value': value,
                      'sourceRegister': 'AL', 'sourceGeneration': generation, 'actualWrite': None}
        checksum = {'address': 0x03F6, 'value': self.state['memory']['03F6'],
                    'generation': self.state['generations']['03F6'], 'updatedAtPc': 0x023C if self.checksum_update else None,
                    'relation': 'AccumulatedSelectedByte' if self.checksum_update else (
                        'NegatedForResponseOnly' if self.checksum_negated else 'Unchanged')}
        result.update(entryQualification=self.qualification, registerGenerations=self.reg_gen,
                      registerKnownBits=self.reg_bits, readQualifications=self.qualifiers,
                      programDependencies=self.dependencies, responseCandidate=response, checksumState=checksum,
                      prospectiveStbufIntent=intent, stopBoundary={0x023E: 'STOP_BEFORE_STBUF_023E',
                          0x0244: 'STOP_BEFORE_EPILOGUE_0244'}.get(boundary),
                      unresolvedConstraints=[*_MISSING, *([reason] if status != 'CompleteConditional' else [])])
        return result


def expected_selector(query):
    ref = _Reference(query, 'alternate_response_selector', 'DetachedConditionalSourcePath')
    try:
        ref.admit(0x0227)
        ref.update(0x0227, al=0, ah=0, dd=1, zf=1)
        ref.step(0x0227, 0x0228)
        ref.load(0x0228, 0x03F5, 0x0229)
        ref.cmp(0x0229, (2,), 0x022B)
        if ref.ask(0x022B, 'zf', 1, 0x024C, 0x022D):
            return ref.r2_path()
        ref.read_data(0x022D, 0x03F2)
        ref.cmp(0x022D, ref.data_domain(0x03F2), 0x022E)
        return ref.remaining_path() if ref.ask(0x022E, 'cf', 0, 0x024F, 0x0230) else ref.table_path()
    except Boundary as boundary:
        return ref.result(boundary.status, boundary.reason, boundary.pc)


def expected_auxiliary(query):
    ref = _Reference(query, 'alternate_auxiliary_024c_0253', 'DetachedAuxiliaryEntry')
    try:
        ref.admit(query['entryPc'])
        return ref.r2_path() if query['entryPc'] == 0x024C else ref.remaining_path()
    except Boundary as boundary:
        return ref.result(boundary.status, boundary.reason, boundary.pc)
