"""Compose accepted mode fragments through the source-owned middle corridor."""
from copy import deepcopy

from enclosing_caller_return.mode_caller import (
    SOURCE_SITES, SUFFIX_SITES, _detached_suffix, mode_enclosing_caller,
)
from enclosing_caller_return.program_table import TABLE_SITES, require_entry
from enclosing_caller_return.state import Boundary, Effects as AcceptedEffects

from .middle_corridor import CORRIDOR_SCOPE, corridor_from_prefix, validate_program
from .state import Effects, expand_snapshot, input_class, label, need, shape

SCOPE = tuple(sorted(set(SOURCE_SITES) | set(CORRIDOR_SCOPE)))
SUFFIX_SCOPE = tuple(sorted(set(SUFFIX_SITES) | set(TABLE_SITES)))


def _frozen_suffix(snapshot, program):
    # Prefix generations keep their original namespace. New suffix effects
    # need a separate namespace to preserve same-machine writer identity.
    effects = AcceptedEffects(snapshot, 'mode_enclosing_suffix', SUFFIX_SCOPE)
    try:
        require_entry(effects, True, 0x608F)
        result = _detached_suffix(effects, program)
    except Boundary as stopped:
        result = effects.result(stopped.status, stopped.reason, stopped.pc)
    return {**result, 'entryVariant': 'At608F', 'callerContext': None}


def mode_enclosing_continuation(query):
    shape(query, ('inputClass', 'prefixQuery', 'program', 'sourceBinding'), 'ClosedModeContinuationQueryRequired')
    input_class(query['inputClass'])
    prefix_query = query['prefixQuery']
    shape(prefix_query, ('inputClass', 'callerPc', 'snapshot', 'entry', 'entryEstablished', 'program'),
          'ClosedModePrefixQueryRequired')
    need(prefix_query['entry'] == 'From5F45' and prefix_query['inputClass'] == query['inputClass'],
         'MatchingFrom5f45PrefixRequired')
    need(label(query['sourceBinding']), 'TypedCorridorSourceBindingRequired')
    validate_program(query['program'])
    effects = Effects(expand_snapshot(prefix_query['snapshot']), 'mode_enclosing_continuation', SCOPE)
    stages = []
    middle = None

    def retain(stage, child):
        effects.absorb(child)
        stages.append({'stage': stage, 'status': child['status'], 'boundary': child['boundary']})

    def finish(child, complete=False):
        result = effects.result(child['status'], child['reason'], child['boundary'], child['outcome'])
        return {**result, 'stageBoundaries': stages, 'compositionEstablished': complete,
                'correlatedPredicates': deepcopy(middle.get('correlatedPredicates', [])) if middle else [],
                'r0Lineage': deepcopy(middle.get('r0Lineage')) if middle else None}

    prefix = mode_enclosing_caller(prefix_query)
    retain('Prefix', prefix)
    if prefix['status'] != 'CompleteConditional' or prefix['boundary'] != 0x7DF5:
        return finish(prefix)

    middle = corridor_from_prefix(prefix_query, prefix, query['program'], query['sourceBinding'])
    retain('Middle', middle)
    if middle['status'] != 'CompleteConditional' or middle['boundary'] != 0x608F:
        return finish(middle)

    suffix = _frozen_suffix(effects.m2cv_snapshot(), prefix_query['program'])
    retain('Suffix', suffix)
    return finish(suffix, suffix['status'] == 'CompleteConditional' and suffix['boundary'] == 0x60E4)
