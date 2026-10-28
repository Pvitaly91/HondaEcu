"""Invented-only byte/bit ownership ledger, separate from production execution.

Numeric equality never creates a semantic owner. Every storage write receives
a new local ordinal even when its value is unchanged. A conditional code-bit
transformation does not establish a complete native byte or interrupt history.
"""
from copy import deepcopy

INVENTED = 'InventedOnly_NotNativeRuntime'
STATIC = 'StaticProvenanceCanonical_NotOriginalRomCpuExecution'
COPIES = {0x0400: (0x0212, 0x011A), 0x0404: (0x0214, 0x011C),
    0x0408: (0x0216, 0x011E), 0x5C2D: (0x0212, 0x011A),
    0x5C31: (0x0214, 0x011C), 0x5C35: (0x0216, 0x011E)}
CONSTRAINTS = {'rootReachable', 'writerDominates', 'irqEstablished',
    'stackPreserved', 'aliasesResolved', 'historyCompatible'}


def need(value, reason):
    if value is not True:
        raise ValueError(reason)


def number(value, maximum):
    return type(value) is int and 0 <= value <= maximum


def validate(scenario):
    need(type(scenario) is dict and set(scenario) == {'caseId', 'classification',
        'machineId', 'context', 'history', 'seeds', 'events', 'reader',
        'old012A', 'context012A', 'constraints'}, 'ClosedInventedScenarioRequired')
    need(scenario['classification'] == INVENTED, 'InventedScopeRequired')
    for key in ('caseId', 'machineId', 'history', 'context012A'):
        need(type(scenario[key]) is str and 0 < len(scenario[key]) <= 128, 'BoundedIdentityRequired')
    need(scenario['machineId'].startswith('invented:'), 'InventedMachineRequired')
    need(type(scenario['context']) is dict and scenario['context'] == {'lrb': 0x21, 'usp': 0x280, 'scb': 2}
        and all(type(v) is int for v in scenario['context'].values()), 'ExactConditionalCopyAddressContextRequired')
    need(type(scenario['constraints']) is dict and set(scenario['constraints']) == CONSTRAINTS
        and all(type(v) is bool for v in scenario['constraints'].values()), 'ClosedBooleanObligationsRequired')
    need(number(scenario['old012A'], 255), 'Old012AByteRequired')
    need(type(scenario['reader']) is dict and set(scenario['reader']) == {'address', 'bit'}
        and (scenario['reader']['address'], scenario['reader']['bit']) in ((0x011F, 3), (0x011B, 7)), 'ExactTargetReaderRequired')
    need(type(scenario['seeds']) is list and len(scenario['seeds']) <= 16
        and type(scenario['events']) is list and len(scenario['events']) <= 16, 'BoundedCuratedLedgerRequired')
    seen = set()
    for seed in scenario['seeds']:
        need(type(seed) is dict and set(seed) == {'address', 'value', 'owner'}, 'ClosedSeedRequired')
        need(number(seed['address'], 65535) and seed['address'] not in seen, 'DistinctByteSeedRequired')
        seen.add(seed['address'])
        need(seed['value'] is None or number(seed['value'], 255), 'OptionalByteValueRequired')
        need(seed['owner'] is None or type(seed['owner']) is str
            and seed['owner'].startswith('invented:') and len(seed['owner']) <= 128, 'NoImportedNativeOrHistoricalOwner')
        need(seed['owner'] is None or seed['value'] is not None, 'OwnedSeedRequiresExplicitInventedValue')
    for event in scenario['events']:
        need(type(event) is dict and type(event.get('op')) is str, 'TypedStaticEventRequired')
        op = event['op']
        if op == 'copy':
            need(set(event) == {'op', 'pc', 'source', 'target', 'width', 'complete', 'sourceMachine'}, 'ClosedCopyRequired')
            need(type(event['pc']) is int and event['pc'] in COPIES
                and COPIES[event['pc']] == (event['source'], event['target']), 'ExactWriterSourceTargetRequired')
            need(type(event['width']) is int and event['width'] == 16, 'ExactWordWidthRequired')
            need(event['complete'] is True, 'CompleteStaticWriterRequired')
            need(event['sourceMachine'] == scenario['machineId'], 'SameMachineSourceGenerationRequired')
        elif op == 'programBit':
            need(set(event) == {'op', 'pc', 'programByte'} and event['pc'] == 0x5F6B
                and type(event['pc']) is int, 'ExactProgramBitWriterRequired')
            need(event['programByte'] is None or number(event['programByte'], 255), 'InventedOptionalProgramByteRequired')
        elif op == 'overlap':
            need(set(event) == {'op', 'pc', 'address', 'value'} and number(event['pc'], 65535)
                and number(event['address'], 65534) and event['address'] % 2 == 0
                and (event['value'] is None or number(event['value'], 65535)), 'TypedWordOverlapRequired')
        elif op == 'unknownAlias':
            need(set(event) == {'op', 'addresses'} and type(event['addresses']) is list
                and 0 < len(event['addresses']) <= 16 and len(set(event['addresses'])) == len(event['addresses'])
                and all(number(a, 65535) for a in event['addresses']), 'BoundedUnknownAliasRequired')
        else:
            raise ValueError('UnknownStaticOperation')


def blank():
    return {'value': None, 'bitValues': [None] * 8, 'bitSources': [None] * 8,
        'bitPaths': [[] for _ in range(8)], 'storageGeneration': None}


def run_scenario(scenario):
    validate(scenario)
    memory, writes, unresolved, ordinal = {}, [], [], 0
    machine = scenario['machineId']
    for seed in scenario['seeds']:
        cell = blank(); cell['value'] = seed['value']
        if seed['value'] is not None:
            cell['bitValues'] = [seed['value'] >> bit & 1 for bit in range(8)]
        if seed['owner'] is not None:
            cell['bitSources'] = [seed['owner'] + ':' + str(bit) for bit in range(8)]
        memory[seed['address']] = cell

    def get(address):
        return deepcopy(memory.get(address, blank()))

    for index, event in enumerate(scenario['events']):
        op = event['op']
        if op == 'unknownAlias':
            for address in event['addresses']:
                cell = get(address); cell.update(value=None, bitValues=[None] * 8, bitSources=[None] * 8,
                    bitPaths=[[] for _ in range(8)], storageGeneration=None)
                memory[address] = cell
            unresolved.append({'eventIndex': index, 'addresses': event['addresses'], 'reason': 'IndirectAliasPreservationUnknown'})
            continue
        ordinal += 1; generation = machine + ':' + str(ordinal)
        if op == 'copy':
            source, target, width = event['source'], event['target'], 16
            cells = [get(source), get(source + 1)]
            value = None if any(c['value'] is None for c in cells) else cells[0]['value'] | cells[1]['value'] << 8
        elif op == 'programBit':
            source, target, width = 0x60EC, 0x0217, 8
            cell = get(target); incoming = event['programByte']
            cell['bitValues'][3] = None if incoming is None else incoming >> 7 & 1
            cell['value'] = None if any(v is None for v in cell['bitValues']) else sum(v << bit for bit, v in enumerate(cell['bitValues']))
            cell['bitSources'][3] = None if incoming is None else 'invented:PROGRAM60EC:7'
            cell['bitPaths'][3] = []
            cells, value = [cell], cell['value']
        else:
            source, target, width = None, event['address'], 16
            value = event['value']; cells = [blank(), blank()]
            for offset in range(2):
                cells[offset]['value'] = None if value is None else value >> (offset * 8) & 255
                if cells[offset]['value'] is not None:
                    cells[offset]['bitValues'] = [cells[offset]['value'] >> bit & 1 for bit in range(8)]
        old_values = [get(target + offset)['value'] for offset in range(len(cells))]
        same = all(c['value'] is not None and old == c['value'] for old, c in zip(old_values, cells))
        for offset, cell in enumerate(cells):
            # Preserve each bit's semantic lineage; all bytes receive this new
            # storage generation, including neighbors retained by a bit RMW.
            for bit in range(8):
                if cell['bitSources'][bit] is not None:
                    cell['bitPaths'][bit].append(generation)
            cell['storageGeneration'] = generation
            memory[target + offset] = cell
        writes.append({'ordinal': ordinal, 'eventIndex': index, 'writerPC': event['pc'],
            'address': target, 'widthBits': width, 'value': value, 'sourceAddress': source,
            'storageGeneration': generation, 'sameValue': same, 'op': op})
    address, bit = scenario['reader']['address'], scenario['reader']['bit']
    # Include an explicitly unknown reader cell in the symbolic snapshot; this
    # diagnostic inventory is not a functional target-CPU access.
    memory.setdefault(address, blank())
    cell = get(address)
    reader = {'address': address, 'bit': bit,
        'value': cell['bitValues'][bit],
        'source': cell['bitSources'][bit], 'lineage': cell['bitPaths'][bit],
        'storageGeneration': cell['storageGeneration']}
    missing = sorted(key for key, value in scenario['constraints'].items() if not value)
    if scenario['history'] != scenario['context012A']:
        missing.append('Incompatible012AHistory')
    if reader['source'] is None:
        missing.append('ReaderSourceUnknown')
    if cell['value'] is None:
        missing.append('WholeReaderByteUnknown')
    if any(source is None for source in cell['bitSources']):
        missing.append('WholeReaderByteOwnerUnknown')
    if not reader['lineage']:
        missing.append('NoObservedEvenInventedWriterChain')
    if unresolved:
        missing.append('UnknownAliasPresent')
    return {'caseId': scenario['caseId'], 'classification': STATIC, 'machineId': machine,
        'memory': [{'address': key, **memory[key]} for key in sorted(memory)],
        'writes': writes, 'reader': reader, 'aliasUnknowns': unresolved,
        'conditionalBit3Terminal': 0x0667 if scenario['old012A'] & 8 else 0x0664,
        'context012ACompatible': scenario['history'] == scenario['context012A'],
        'missingObligations': sorted(set(missing)),
        'symbolicBridge': 'InventedOnly_SourceToReaderObligationsSatisfied' if not missing else 'SameMachineBridgeBlocked',
        'sourceValueKnownIsNativeOwner': False, 'actualCpuExecutions': 0,
        'actualOriginalRomExecutions': 0, 'actualRetiredInstructions': 0,
        'nativeSourceOwnershipEstablished': False, 'firmwareReady': False}
