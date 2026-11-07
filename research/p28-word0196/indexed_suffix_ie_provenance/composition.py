"""Append only the first shadow load to the frozen indexed prefix."""
from enclosing_caller_return.indexed_caller import indexed_acquisition_caller
from enclosing_caller_return.state import input_class, need, shape

from .suffix import indexed_suffix_pre_ie
from .wire import result


def indexed_suffix_composition(query):
    shape(query, ('inputClass', 'prefixQuery', 'shadow'), 'ClosedIndexedSuffixCompositionRequired')
    input_class(query['inputClass'])
    prefix_query = query['prefixQuery']
    shape(prefix_query, ('inputClass', 'callerPc', 'snapshot', 'entryEstablished'), 'ClosedIndexedPrefixRequired')
    need(query['inputClass'] == prefix_query['inputClass'], 'MatchingIndexedPrefixInputClassRequired')
    prefix = indexed_acquisition_caller(prefix_query)
    suffix = None
    if prefix['status'] == 'CompleteConditional' and prefix['boundary'] == 0x5CB7:
        suffix = indexed_suffix_pre_ie({'inputClass': query['inputClass'], 'shadow': query['shadow'],
                                       'snapshot': {'inputClass': query['inputClass'],
                                                    'assumptions': prefix_query['snapshot']['assumptions'],
                                                    **prefix['state']}})
    last = prefix if suffix is None else suffix
    return result(last['status'], source_scope=sorted(set(prefix['sourceScope']) | {0x5CB7, 0x5CB9}),
                  state=last['state'], stop=prefix['exactStopBoundary'] if suffix is None else suffix['stopBoundary'],
                  reads=prefix['reads'] + ([] if suffix is None else suffix['reads']),
                  writes=prefix['journal'] + ([] if suffix is None else suffix['orderedWrites']),
                  generations=(prefix['state']['generations'] if suffix is None else suffix['generations']),
                  intermediate=prefix['intermediateStates'] + ([] if suffix is None else suffix['intermediateStates']),
                  obligations=() if suffix is None else suffix['formalObligations'],
                  branches=[{'pc': step['pc'], 'taken': step['branchTaken'], 'next': step['next']}
                            for step in prefix['steps'] if step['kind'] == 'Branch'],
                  unresolved=last['unresolvedConstraints'], reason=last['reason'], frozenPrefixResult=prefix,
                  preIeResult=suffix, postIeComposed=False)
