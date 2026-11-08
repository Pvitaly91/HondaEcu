"""Frozen source arrivals and comparison of their distinct local epilogue effects."""
from copy import deepcopy

from alternate_parser_response_checksum.path import alternate_response_selector
from detached_post_stbuf_0240_0241.fragment import detached_0240_0241_transform

from .analysis import AUTHORITY, canonical

DIRECT = 'DirectM2dfIngress'
DETACHED = 'DetachedM2dgIngress'
STOP_0244 = 'STOP_BEFORE_EPILOGUE_0244'
STOP_0249 = 'STOP_BEFORE_IE_WRITE_0249'
MEMORY_MODEL = 'ConditionalDocumentedInternalRam'
SOURCE_IDS = {
    DIRECT: ('a9eeb45292a120711bb1adf918385675c2456409',
             'a1c554e17305f199effbc2e3aae2b42ab83081da7e527b4eeeab181faf691e55'),
    DETACHED: ('b20f1341219888afd72b950e4a592e18b0e3f02a',
               '466c2a69e86de5f56058166d28e6c82e93243caa84f7655a730957d12da98470'),
}
_INPUT_FIELDS = {'source', 'assumptions', 'shadowEvidence'}
_SOURCE_FIELDS = {'kind', 'baseSha', 'sourceFingerprint', 'input', 'result'}
_ASSUMPTIONS = {'noInterference', 'memoryModel', 'pswhAlias'}
_FLAGS = ('cf', 'zf', 'hc', 'dd', 'mie', 'otherPsw')
_INGRESS_OBLIGATIONS = ('UnprovedNativeHandoff', 'PhysicalDataMappingUnknown', 'HardwareInterruptStateUnknown')
_COMPARE_OBLIGATIONS = ('SourceHistoriesRemainDistinct', 'CurrentNativeShadowOwnerUnknown',
                        'PswhFlagPrecedenceUnestablished', 'IeAndRtiOutsideScope')
_QUALIFIED_SHADOW = {'CurrentReadGenerationsDeclared', 'ConditionalCandidateGenerationMatched'}


def _shape(value, fields):
    return type(value) is dict and value.keys() == fields


def _events(obligations):
    return {'steps': [], 'reads': [], 'journal': [], 'unresolved': list(obligations),
            'executionAuthority': dict(AUTHORITY)}


def _ingress_result(reason, history=None, projected=None):
    return {
        'status': 'QualifiedSymbolicIngress' if projected is not None else 'RefusedSourcePremise',
        'reason': reason,
        'entryClass': history['sourceKind'] if history is not None else None,
        'stopBoundary': STOP_0244 if history is not None else None,
        'projectedInput': projected,
        'sourceHistory': history,
        **_events(_INGRESS_OBLIGATIONS),
    }


def _source_history(source):
    if not _shape(source, _SOURCE_FIELDS):
        return 'ClosedFrozenIngressSourceRequired', None
    kind = source['kind']
    if type(kind) is not str or kind not in SOURCE_IDS or (
            source['baseSha'], source['sourceFingerprint']) != SOURCE_IDS[kind]:
        return 'ExactFrozenIngressIdentityRequired', None
    run = alternate_response_selector if kind == DIRECT else detached_0240_0241_transform
    try:
        actual = run(source['input'])
        exact = canonical(actual) == canonical(source['result'])
    except (ValueError, TypeError, KeyError, RecursionError, OverflowError):
        exact = False
    if not exact:
        return 'FrozenIngressReplayMismatch', None
    steps = actual['steps']
    if kind == DIRECT:
        if (actual['status'] != 'CompleteConditional' or actual['outcome'] != 'CounterBeyondLength'
                or actual['entryQualification'] != 'DetachedConditionalSourcePath'
                or actual['boundary'] != 0x0244 or actual['stopBoundary'] != STOP_0244
                or not steps or steps[0]['pc'] != 0x0227 or steps[-1]['pc'] != 0x024F
                or steps[-1]['next'] != 0x0244 or steps[-1]['branchTaken'] is not True
                or actual['responseCandidate'] is not None or actual['prospectiveStbufIntent'] is not None):
            return 'Direct024fIngressRequired', None
        state = {**actual['state'], 'registerGenerations': actual['registerGenerations'],
                 'registerKnownBits': actual['registerKnownBits']}
        assumptions = source['input']['snapshot']['assumptions']
        unresolved = actual['unresolvedConstraints']
        path = 'M2df024fTo0244'
    else:
        if (actual['status'] != 'ConditionalSourceArrivalAt0244' or actual['entryKind'] != 'DetachedSymbolicEntry'
                or actual['stopPc'] != 0x0244 or actual['stopBoundary'] != STOP_0244
                or [(row['pc'], row['next']) for row in steps] != [(0x0240, 0x0241), (0x0241, 0x0244)]):
            return 'CompleteDetached0240IngressRequired', None
        state = actual['state']
        assumptions = source['input']['assumptions']
        unresolved = actual['unresolved']
        path = 'M2dg0240To0241To0244'
    return None, {'sourceKind': kind, 'sourceBaseSha': source['baseSha'],
                  'sourceFingerprint': source['sourceFingerprint'], 'sourcePath': path,
                  'sourceState': state, 'sourceAssumptions': assumptions, 'precedingWrites': actual['journal'],
                  'steps': steps, 'unresolved': unresolved}


def _shadow_byte(state, slot):
    return {'value': state['memory'][slot], 'generation': state['generations'][slot],
            'knownBits': {field[-1]: value for field, value in state['knownBits'].items() if field[:4] == slot}}


def epilogue_ingress_adapter(query):
    """Verify a frozen arrival and project only the 0244 mathematical inputs."""
    if not _shape(query, _INPUT_FIELDS):
        return _ingress_result('ClosedEpilogueIngressQueryRequired')
    reason, history = _source_history(query['source'])
    if reason is not None:
        return _ingress_result(reason)
    assumptions, shadow = query['assumptions'], query['shadowEvidence']
    if (not _shape(assumptions, _ASSUMPTIONS)
            or any(assumptions[name] is not None and type(assumptions[name]) is not bool
                   for name in ('noInterference', 'pswhAlias'))
            or assumptions['memoryModel'] is not None and type(assumptions['memoryModel']) is not str):
        return deepcopy(_ingress_result('ClosedEpilogueIngressAssumptionsRequired', history))
    if not _shape(shadow, {'writer', 'events'}):
        return deepcopy(_ingress_result('ClosedIngressShadowEvidenceRequired', history))
    state = history['sourceState']
    if not {'00F8', '00F9'} <= state['memory'].keys() & state['generations'].keys():
        return deepcopy(_ingress_result('ExactFrozenShadowByteSlotsRequired', history))
    projection = {'sourceId': 'M2dhReviewed0244_0246', 'entryPc': 0x0244,
                  'entryClass': 'DetachedSymbolic0244', 'assumptions': assumptions,
                  'registers': state['registers'], 'registerGenerations': state['registerGenerations'],
                  'registerKnownBits': state['registerKnownBits'],
                  'shadow': {'low': _shadow_byte(state, '00F8'), 'high': _shadow_byte(state, '00F9'),
                             **shadow}}
    return deepcopy(_ingress_result('ExactFrozenIngressReplay', history, projection))


def _pair(left, right):
    relation = 'Unknown' if left is None or right is None else 'Equal' if left == right else 'Different'
    return {'direct': left, 'detached': right, 'relation': relation}


def _comparison_result(reason, direct=None, detached=None, fields=None, *, equivalent=False):
    both = direct is not None and detached is not None and direct['local'] is not None and detached['local'] is not None
    at_boundary = both and all(row['local']['stopBoundary'] == STOP_0249 for row in (direct, detached))
    status = ('ConditionalEquivalentLocalEpilogueEffect' if equivalent else
              'DistinctLocalEpilogueEffectsCompared' if both else 'RefusedSourcePremise')
    return {'status': status, 'reason': reason, 'entryClass': None,
            'stopBoundary': STOP_0249 if at_boundary else None, 'direct': direct, 'detached': detached,
            'fields': {} if fields is None else fields, **_events(_COMPARE_OBLIGATIONS)}


def _compare_lanes(direct, detached):
    left, right = direct['ingress']['projectedInput'], detached['ingress']['projectedInput']
    left_result, right_result = direct['local'], detached['local']
    left_ie, right_ie = left_result['prospectiveIe'] or {}, right_result['prospectiveIe'] or {}
    left_pswh, right_pswh = left_result['pswh'] or {}, right_result['pswh'] or {}
    left_proof, right_proof = left_result['shadowProof'] or {}, right_result['shadowProof'] or {}
    fields = {
        'memoryModel': _pair(left['assumptions']['memoryModel'], right['assumptions']['memoryModel']),
        'lowGeneration': _pair(left['shadow']['low']['generation'], right['shadow']['low']['generation']),
        'highGeneration': _pair(left['shadow']['high']['generation'], right['shadow']['high']['generation']),
        'prospectiveIeWord': _pair(left_ie.get('value'), right_ie.get('value')),
        'prospectiveIeKnownBits': _pair(left_ie.get('knownBits'), right_ie.get('knownBits')),
        'pswhMaskCandidate': _pair(left_pswh.get('maskCandidate'), right_pswh.get('maskCandidate')),
        'shadowClassification': _pair(left_proof.get('classification'), right_proof.get('classification')),
        'sourcePath': _pair(direct['ingress']['sourceHistory']['sourcePath'],
                            detached['ingress']['sourceHistory']['sourcePath']),
    }
    for flag in _FLAGS:
        fields[f'incoming.{flag}'] = _pair(left['registers'].get(flag), right['registers'].get(flag))
    left_registers = (left_result['state'] or {}).get('registers', {})
    right_registers = (right_result['state'] or {}).get('registers', {})
    for name in ('al', 'ah', *_FLAGS):
        fields[f'local.{name}'] = _pair(left_registers.get(name), right_registers.get(name))
    return fields


def _local_equivalence(fields):
    exact = ('memoryModel', 'lowGeneration', 'highGeneration', 'prospectiveIeWord', 'prospectiveIeKnownBits',
             'pswhMaskCandidate')
    return (all(fields[key]['relation'] == 'Equal' for key in exact)
            and fields['memoryModel']['direct'] == MEMORY_MODEL
            and all(fields['shadowClassification'][lane] in _QUALIFIED_SHADOW for lane in ('direct', 'detached'))
            and not any(fields[f'incoming.{flag}']['relation'] == 'Different' for flag in _FLAGS)
            and all(row['direct'] == row['detached'] for key, row in fields.items() if key.startswith('local.')))


def compare_epilogue_ingresses(query):
    """Keep both histories even when the bounded local effects are equivalent."""
    from .epilogue import detached_epilogue_0244_0246

    if not _shape(query, {'direct', 'detached'}):
        return _comparison_result('ClosedIngressComparisonRequired')
    results = []
    for lane, kind in (('direct', DIRECT), ('detached', DETACHED)):
        ingress = epilogue_ingress_adapter(query[lane])
        local = (detached_epilogue_0244_0246(ingress['projectedInput'])
                 if ingress['status'] == 'QualifiedSymbolicIngress' and ingress['entryClass'] == kind else None)
        results.append({'ingress': ingress, 'local': local})
    direct, detached = results
    if any(result['local'] is None for result in results):
        return _comparison_result('DistinctQualifiedIngressKindsRequired', direct, detached)
    fields = _compare_lanes(direct, detached)
    complete = all(result['local']['status'] == 'ConditionalSourceArrivalAt0249' for result in results)
    equivalent = complete and _local_equivalence(fields)
    reason = ('ExactConditionalLocalEffectsMatch' if equivalent else
              'LocalEpilogueProofIncomplete' if not complete else 'LocalEquivalenceNotEstablished')
    return _comparison_result(reason, direct, detached, fields, equivalent=equivalent)
