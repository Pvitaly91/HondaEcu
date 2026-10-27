"""Sixteen technical CAL entries with one initial software-selector snapshot."""
from collections import Counter
from copy import deepcopy
from native_cal_rt_continuity import corpus as previous

MODE='OriginalRomBytes_TechnicalPostReturnSelectorContinuity'
PUBLIC_MODE='PublicSyntheticPostReturnSelectorContinuityRegression'
PROVENANCE,CONTROL_PROVENANCE=previous.PROVENANCE,previous.CONTROL_PROVENANCE
UNKNOWN_SF,DATA0196_OWNER=deepcopy(previous.UNKNOWN_SF),previous.DATA0196_OWNER
ENTRY_PC,BODY_BASE,RETURN_PC=previous.ENTRY_PC,previous.BODY_BASE,previous.RETURN_PC
PUBLIC_CALLER,PUBLIC_BASE,PUBLIC_RETURN=previous.PUBLIC_CALLER,previous.PUBLIC_BASE,previous.PUBLIC_RETURN
PUBLIC_PC_DELTA=previous.PUBLIC_PC_DELTA
STACK_SLOTS,INVENTORY=previous.STACK_SLOTS,previous.INVENTORY
PUBLIC_DATA={**previous.PUBLIC_DATA,0x013C:0x0140}
BUDGETS,TERMINALS={'A':49},{'A':0x064C}
POST_PCS=(0x063E,0x0640,0x0641,0x0643,0x0646,0x0647,0x0648,0x064A)
SELECTOR_CLASSIFICATION='RawSoftwareSnapshot0..3_OnceOnly_InitialGenerationNone'


def scalar_case(case):
    value=deepcopy(case);value.pop('selector_snapshot',None)
    value['mode'],value['budget']=previous.MODE,41
    return value


def validate_case(case):
    if type(case) is not dict or case.get('mode')!=MODE or type(case.get('budget')) is not int or case['budget']!=49:
        raise ValueError('ClosedPostReturnSelector49TechnicalCaseRequired')
    snapshot=case.get('selector_snapshot')
    if (type(snapshot) is not dict or set(snapshot)!={'value','classification'}
            or type(snapshot['value']) is not int or snapshot['value'] not in range(4)
            or snapshot['classification']!=SELECTOR_CLASSIFICATION):
        raise ValueError('OnceOnlyInitialSelector0Through3WithoutNativeGenerationRequired')
    previous.validate_case(scalar_case(case))
    return True


def iter_cases():
    for index,original in enumerate(previous.iter_cases()):
        case=deepcopy(original)
        case.update(case_id=case['case_id'].replace('m2by-','m2bz-',1),family='post-return-once-selector-native-writer',
            mode=MODE,budget=49,selector_snapshot={'value':index//4,'classification':SELECTOR_CLASSIFICATION})
        validate_case(case)
        yield case


def wire_case(case,program_kind='private'):
    validate_case(case)
    if program_kind not in ('private','public_fixture'):raise ValueError('ClosedM2bzProgramKindRequired')
    value=previous.wire_case(scalar_case(case),program_kind)
    value['budget']=49;value['selector_snapshot']=deepcopy(case['selector_snapshot'])
    return value


def coverage(cases=None):
    cases=list(iter_cases()) if cases is None else list(cases)
    for case in cases:validate_case(case)
    initial=Counter(c['selector_snapshot']['value'] for c in cases)
    bits=[(c['selector_snapshot']['value']&1,bool(c['data'][str(0x0128)]&(1<<(c['selector_snapshot']['value']&1)))) for c in cases]
    return {'cases':len(cases),'paths':dict(Counter(c['path'] for c in cases)),
        'retirements':sum(c['budget'] for c in cases),'selectorCounts':dict(initial),
        'selectorTransitions':dict(Counter(f"{c['selector_snapshot']['value']}->{(c['selector_snapshot']['value']+1)&3}" for c in cases)),
        'ssps':sorted({c['entry']['ssp'] for c in cases}),'hostSfVariants':sorted({c['internal_sf'] for c in cases}),
        'sbrTargetBitOldStateCounts':{f'{bit}:{int(old)}':bits.count((bit,old)) for bit,old in sorted(set(bits))},
        'initialDATA013CNativeOwnerEstablished':False,'nextEventSelectorHandoffEstablished':False,'physicalSfKnown':False}
