"""Compose the exact M2co status return with the bounded alternate path."""
from copy import deepcopy

from enclosing_caller_return.state import label, need, shape
from length_checksum_dataflow.dispatch import parser_step

from .path import alternate_response_selector


def alternate_parser_step(query):
    """Continue only the retained 0225 fallthrough with the frozen RMW state."""
    shape(query, ('snapshot', 'statusGeneration', 'context'), 'ClosedAlternateCompositionRequired')
    snapshot = query['snapshot']
    need(label(query['statusGeneration']), 'TypedStatusGenerationRequired')
    prefix = parser_step(snapshot)
    handoff = None
    alternate = None
    status, reason, boundary = (prefix[key] for key in ('status', 'reason', 'boundary'))
    targeted = (status, reason, boundary) == ('OutsideVerifiedScope', 'UnmodeledBranch', 0x0227)
    if targeted:
        source = snapshot['generations']['0356']
        write, = prefix['journal']
        branch = prefix['steps'][-1]
        if (source is None or query['statusGeneration'] != source or write['pc'] != 0x0222
                or write['address'] != 0x0356 or write['beforeGeneration'] != [source]
                or write['afterGeneration'] == source
                or write['afterGeneration'] != prefix['state']['generations']['0356']
                or branch['pc'] != 0x0225 or branch['branchTaken'] is not False or branch['next'] != 0x0227):
            reason = 'ExactFrozenStatusHandoffNotEstablished'
        else:
            handoff = {'entryPc': 0x0227, 'branchPc': 0x0225, 'branchTaken': False,
                       'sourceGeneration': source, 'clearedStatusGeneration': write['afterGeneration'],
                       'reseeded': False}
            next_snapshot = {'inputClass': snapshot['inputClass'], 'assumptions': snapshot['assumptions'],
                             **prefix['state']}
            alternate = alternate_response_selector({'snapshot': next_snapshot, 'context': query['context']})
            status, reason, boundary = (alternate[key] for key in ('status', 'reason', 'boundary'))
    return deepcopy({
        'status': status, 'reason': reason, 'boundary': boundary,
        'sourceScope': 'FrozenStatusPrefixToAlternate0227' if handoff else 'FrozenM2coResult',
        'handoff': handoff, 'prefix': prefix, 'alternate': alternate,
        'orderedWrites': [{'stage': 'FrozenM2co', 'event': event} for event in prefix['journal']] +
        ([] if alternate is None else [{'stage': 'Alternate0227', 'event': event} for event in alternate['journal']]),
    })
