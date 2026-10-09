"""Closed structural/type/CFG/provenance validation; standard library only."""
from pathlib import Path
import json
import sys

EXPECTED = {
    0x556F: ('LB A, off N8', 2, 'R', 'LB', [], ['ZF','DD'], [0x5571]),
    0x5571: ('SLLB A', 1, '0', 'SLLB', ['DD'], ['CF'], [0x5572]),
    0x5572: ('ROLB off N8', 3, 'U', 'ROLB', ['CF'], ['CF'], [0x5575]),
    0x5575: ('LB A, r0', 1, 'R', 'LB', [], ['ZF','DD'], [0x5576]),
    0x5576: ('ANDB A, off N8', 2, '0', 'ANDB', ['DD'], ['ZF'], [0x5578]),
    0x5578: ('CMP off N8, #N16', 5, 'U', 'CMP', [], ['CF','ZF'], [0x557D]),
    0x557D: ('JLT rel8', 2, 'U', 'JLT', ['CF'], [], [0x55BF,0x557F]),
    0x557F: ('MOVB r1, off N8', 3, 'U', 'MOVB', [], [], [0x5582]),
    0x5582: ('ANDB off N8, A', 3, 'U', 'ANDB', [], ['ZF'], [0x5585]),
    0x5585: ('JBS off N8.7, rel8', 3, 'U', 'JBS', [], [], [0x5592,0x5588]),
    0x5588: ('JBS off N8.5, rel8', 3, 'U', 'JBS', [], [], [0x5592,0x558B]),
    0x558B: ('ANDB off N8, A', 3, 'U', 'ANDB', [], ['ZF'], [0x558E]),
    0x558E: ("ORB off N'8, #N8", 4, 'U', 'ORB', [], ['ZF'], [0x5592]),
    0x5592: ('LB A, off N8', 2, 'R', 'LB', [], ['ZF','DD'], [0x5594]),
    0x5594: ('ORB A, #N8', 2, '0', 'ORB', ['DD'], ['ZF'], [0x5596]),
    0x55BF: ('LB A, #N8', 2, 'R', 'LB', [], ['ZF','DD'], [0x55C1]),
    0x55C1: ('STB A, off N8', 2, '0', 'STB', ['DD'], [], [0x55C3]),
    0x55C3: ('STB A, off N8', 2, '0', 'STB', ['DD'], [], [0x55C5]),
}

ROOT_KEYS = {'schemaVersion','classification','entryPc','stopBeforePcs','context','stateTypes',
             'numericRules','retainedState','provenanceRestrictions','instructions'}
NODE_KEYS = {'pc','form','incomingContext','inputs','outputs','flagsRead','flagsWritten','flagsPreserved',
             'effects','branchPredicate','successors','provenance'}
FORM_KEYS = {'mnemonic','pinnedPatternIndex','length','ddMode','parsedOperation','operands'}
EFFECT_OPS = {'LoadAccumulatorLow','AssignZeroFlag','AssignDataDescriptor','LogicalShiftLeft',
              'AssignCarryFromOldBit','ReadModifyWriteRotateThroughCarry','BitwiseAnd','UnsignedCompare',
              'ConditionalJump','CopyByte','ReadModifyWriteAnd','ReadModifyWriteOr','BitwiseOr','StoreByte',
              'FlagIsSet','BitIsSet'}

def demand(condition, message):
    if not condition:
        raise ValueError(message)

def walk(value):
    if isinstance(value, dict):
        for key, child in value.items():
            demand(key.lower() not in {'bytes','opcodebytes','rawhex','rawbytes','romwindow','machineid','imageid'},
                   f'Prohibited private/raw key {key}')
            walk(child)
        if 'op' in value:
            demand(value['op'] in EFFECT_OPS and value.get('type') in {'u8','u16','bool','pc16'},
                   'Unknown typed operation')
        if 'kind' in value:
            demand(value['kind'] in {'AccumulatorLow','LocalRegister','CurrentPageRam','CodeOwnedImmediate'},
                   'Unknown operand location')
            demand(value.get('widthBits') in {8,16}, 'Wrong operand width')
            if value['kind'] == 'CurrentPageRam':
                demand(value['requiredLrb'] == 0x21 and value['selectorField'] in {'n8','n8_alt'}, 'Unknown addressing context')
                demand(value['byteOrder'] == ('LittleEndian' if value['widthBits'] == 16 else 'NotApplicable'), 'Wrong byte order')
            if value['kind'] == 'LocalRegister':
                demand(value['name'] in {'r0','r1'} and value['address'] == 0x108 + int(value['name'][1:]) and
                       value['widthBits'] == 8, 'Wrong local register alias/width')
    elif isinstance(value, list):
        for child in value:
            walk(child)

def validate(ir, c_source):
    demand(set(ir) == ROOT_KEYS, 'IR root schema changed')
    demand(ir['schemaVersion'] == 1 and ir['entryPc'] == 0x556F and ir['stopBeforePcs'] == [0x5596,0x55C5], 'Wrong software boundary')
    demand(ir['context']['lrb'] == 0x21 and ir['context']['currentPage'] == 0x100 and ir['context']['localBank'] == 0x108,
           'Unknown memory alias context')
    demand(ir['numericRules'] == {'unsignedOnly':True,'byteTruncation':'Modulo256','wordAccess':'EvenLittleEndian',
            'loadByteExtension':'None;AHpreserved','signExtension':'NoneInThisFragment',
            'accumulatorByteOperations':'DD0;EstablishedBy556F'}, 'Changed width/extension rules')
    demand(ir['provenanceRestrictions']['nativeOwnerAcceptedFromHost'] is False, 'Host owner is not native proof')
    demand([n['pc'] for n in ir['instructions']] == list(EXPECTED), 'Missing/reordered/extra native extent')
    walk(ir)
    nodes = {n['pc']: n for n in ir['instructions']}
    for pc, expected in EXPECTED.items():
        node = nodes[pc]
        demand(set(node) == NODE_KEYS and set(node['form']) == FORM_KEYS, f'Node schema changed {pc:04X}')
        form = node['form']
        observed = (form['mnemonic'],form['length'],form['ddMode'],form['parsedOperation'],node['flagsRead'],
                    node['flagsWritten'],node['successors'])
        demand(observed == expected, f'Exact form/flags/CFG mismatch {pc:04X}')
        demand(isinstance(form['pinnedPatternIndex'],int) and 0 <= form['pinnedPatternIndex'] < 2623, 'Wrong pattern index')
        demand(node['flagsPreserved'] == [x for x in ['CF','ZF','HC','DD','OtherPSW'] if x not in node['flagsWritten']], 'Wrong retained flags')
        demand(node['effects'] and node['provenance']['nativeExtentIndependentlyVerified'] is True, 'No typed effects/provenance')
        for tag in node['provenance']['cStatementTags']:
            demand(tag in c_source, f'Missing native-to-C statement tag {tag}')
        if node['branchPredicate'] is None:
            demand(len(node['successors']) == 1, 'Nonbranch has multiple successors')
        else:
            demand(len(node['successors']) == 2 and node['branchPredicate']['type'] == 'bool', 'Untyped branch')
    comparison = nodes[0x5578]['form']['operands']
    demand(comparison == [{'kind':'CurrentPageRam','address':0x196,'widthBits':16,'selectorField':'n8',
                          'requiredLrb':0x21,'byteOrder':'LittleEndian'},
                         {'kind':'CodeOwnedImmediate','value':0xC0,'widthBits':16}], 'Wrong CMP width/address/immediate')
    demand(nodes[0x5585]['branchPredicate'] == {'op':'BitIsSet','type':'bool','address':0x12A,'bit':7}, 'Wrong first gate')
    demand(nodes[0x5588]['branchPredicate'] == {'op':'BitIsSet','type':'bool','address':0x124,'bit':5}, 'Wrong second gate')
    demand(nodes[0x557D]['branchPredicate'] == {'op':'FlagIsSet','type':'bool','flag':'CF'}, 'Wrong comparison branch')
    demand(nodes[0x5572]['effects'][0]['carryInput'] == 'IncomingCF' and
           nodes[0x5572]['effects'][0]['sameValueWrite'] == 'RetainFreshOrdinal', 'Wrong rotate/write identity')
    paths = []
    def explore(pc, path):
        if pc in ir['stopBeforePcs']:
            paths.append(path)
            return
        demand(pc not in path, 'Unexpected loop')
        demand(pc in nodes, 'Unsupported continuation')
        for successor in nodes[pc]['successors']:
            explore(successor,path+[pc])
    explore(ir['entryPc'],[])
    demand(sorted(map(len,paths)) == [10,12,13,15], 'Wrong complete CFG paths')
    return {'instructions':18,'cfgPaths':4,'pathLengths':[10,12,13,15],'passed':True}

def negative_cases(ir,c_source):
    mutations = [
        lambda x: x['instructions'][5]['form']['operands'][0].update(widthBits=8),
        lambda x: x['instructions'][5]['form']['operands'][1].update(value=0xC1),
        lambda x: x['instructions'][5]['form']['operands'][0].update(address=0xC0),
        lambda x: x['instructions'][6].update(successors=[0x5596,0x557F]),
        lambda x: x['instructions'][9]['branchPredicate'].update(bit=6),
        lambda x: x['context'].update(lrb=0x20),
        lambda x: x['instructions'][0]['form'].update(ddMode='U'),
        lambda x: x['instructions'].pop(),
        lambda x: x['provenanceRestrictions'].update(nativeOwnerAcceptedFromHost=True),
        lambda x: x['instructions'][2]['effects'][0].update(carryInput='CircularBit7'),
    ]
    for mutate in mutations:
        copy = json.loads(json.dumps(ir))
        mutate(copy)
        try:
            validate(copy,c_source)
        except ValueError:
            continue
        raise ValueError('Invalid IR mutation accepted')
    return len(mutations)

if __name__ == '__main__':
    directory = Path(sys.argv[1]) if len(sys.argv) == 2 else Path(__file__).resolve().parent
    raw = (directory/'word0196_ir.json').read_bytes()
    ir = json.loads(raw)
    canonical = (json.dumps(ir,indent=2,ensure_ascii=True)+'\n').encode('utf-8')
    demand(raw == canonical, 'Serialization is not canonical UTF-8/LF/two-space JSON')
    c_source = (directory/'word0196_equivalent.c').read_text(encoding='utf-8')
    result = validate(ir,c_source)
    result['rejectedMalformedIR'] = negative_cases(ir,c_source)
    print(json.dumps(result,sort_keys=True))
