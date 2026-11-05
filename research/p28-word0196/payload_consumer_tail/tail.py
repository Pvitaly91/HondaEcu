"""Reviewed pre-RTI prefix and an unchanged-parser adapter; RTI is never applied."""
from copy import deepcopy

from generic_payload_multibyte.analysis import SITES as PARSER_SITES
from generic_payload_multibyte.dispatch import parser_step
from .rti_obligations import rti_obligations, unknown_query
from .state import Boundary, Effects, expand_state, inherited, pointer_view, project, register_bits

SITES = frozenset((0x295, 0x297, 0x29A))
ADAPTER_SITES = PARSER_SITES | SITES | {0x272}


def tail_body(effects):
    effects.specific = ['PswhSelfDestinationZfOrderNotEstablished']
    if any(effects.state['generations'][key] is None for key in ('00F8', '00F9')):
        effects.specific.append('F8GenerationNotEstablished')
    effects.load_word(0x295, 0x297, address=0xF8)
    effects.mask_pswh(0x297, 0, 0x29A)
    effects.store(0x29A, 0x1A, [effects.r['al'], effects.r['ah']],
                  partial=effects.a_partial(0x1A, ('al', 'ah')))
    effects.step(0x29A, 0x29C)
    result = effects.finish('PreRtiTailSpecified', 0x29C)
    result['rtiObligations'] = rti_obligations(unknown_query(effects.input['inputClass'], effects.r['ssp']))
    return result


def post_checksum_tail(snapshot):
    effects = Effects(snapshot, 'post_checksum_tail', SITES)
    effects.specific = ['PswhSelfDestinationZfOrderNotEstablished']
    if any(effects.state['generations'][key] is None for key in ('00F8', '00F9')):
        effects.specific.append('F8GenerationNotEstablished')
    try:
        effects.admit(0x295)
        return tail_body(effects)
    except Boundary as boundary:
        return effects.result(boundary.status, boundary.reason, boundary.pc)


def prefix_effects(snapshot, result):
    effects = Effects(snapshot, 'parser_step_with_tail', ADAPTER_SITES)
    effects.state = expand_state(result['state'], snapshot)
    effects.r = effects.state['registers']
    effects.journal = deepcopy(result['journal'])
    effects.intermediate = [{**deepcopy(row), 'state': expand_state(row['state'], snapshot)}
                            for row in result['intermediateStates']]
    order = {step['pc']: index for index, step in enumerate(result['steps'])}
    effects.reads = []
    for row in result['reads']:
        labels = dict(snapshot['generations'])
        for event in result['journal']:
            if order.get(event['pc'], len(order)) < order.get(row['pc'], len(order)):
                for byte in range(event['widthBits'] // 8):
                    labels[f"{event['address'] + byte:04X}"] = event['afterGeneration']
        effects.reads.append({**deepcopy(row), 'generations': [labels[f"{row['address'] + byte:04X}"]
            for byte in range(row['widthBits'] // 8)], 'accessRole': 'FunctionalOperand'})
    effects.steps = [{**deepcopy(step), 'afterRegisterKnownBits': register_bits(step['afterRegisters']),
                      'afterPointerState': pointer_view(effects.state)} for step in result['steps']]
    return effects


def parser_step_with_tail(snapshot):
    effects = Effects(snapshot, 'parser_step_with_tail', ADAPTER_SITES)
    try:
        effects.admit(0x21F, ('parser_step@M2cqPrefix',))
        unsupported = {k for k in snapshot['knownBits'] if k[:4] in inherited.DATA_KEYS
                       and k not in inherited.BIT_FIELDS and k[:4] not in ('00F8', '00F9')}
        if unsupported:
            effects.halt('OutsideVerifiedScope', 'UnsupportedPartialParserKnowledge', 0x21F)
        prefix = parser_step(project(snapshot), stage_id='M2cqPrefix')
        effects = prefix_effects(snapshot, prefix)
        if prefix['status'] == 'CompleteConditional' and prefix['boundary'] in (0x272, 0x295):
            if prefix['boundary'] == 0x272:
                effects.step(0x272, 0x295, 'Jump', True)
            return tail_body(effects)
        return effects.result(prefix['status'], prefix['reason'], prefix['boundary'], prefix['outcome'])
    except Boundary as boundary:
        return effects.result(boundary.status, boundary.reason, boundary.pc)
