"""Closed source bindings and the ten reviewed effects before the STBUF boundary."""
from copy import deepcopy

BASE = 'ac4086aec3cea32d0e76d6732d9998cbd75bbb28'
SITES = (0x2980, 0x2983, 0x2985, 0x2988, 0x298A, 0x298B, 0x298E, 0x298F, 0x2991, 0x2994)
SOURCE_BINDING = {
    'baseSha': BASE,
    'continuationSourceSha256': 'c9bccc09dc1fa95bc3f1ea4c7e382a1b74982214bacbe905b45a6a8e5ca65379',
    'stbufSourceSha256': 'f436ca49a8e0491e78ac307425cb28893095a4dda8b0d8837c689ca7050d732c',
    'manualSha256': 'f6e423ac0bd15378754e30c35ed426415ec219e360c68e817ab451df72142271',
    'entry': 0x2980, 'stop': 0x2995, 'sites': list(SITES),
    'boundaryForm': 'STB A,N8', 'boundaryLength': 2, 'boundaryAddress': 0x51, 'boundaryDD': 0}
ROWS = (
    (0x2980, 'MOV DP, #N16', 3, 'U', '3-86', 'DP=0356'),
    (0x2983, 'SB [DP].6', 2, 'U', '3-127', 'DATA0356.6=1;ZF=!oldbit6'),
    (0x2985, 'MOV DP, #N16', 3, 'U', '3-86', 'DP=03F5'),
    (0x2988, 'LB A, #N8', 2, 'R', '3-70', 'AL=2;DD0;ZF0'),
    (0x298A, 'STB A, [DP]', 1, '0', '3-155', 'DATA03F5=AL'),
    (0x298B, 'MOV DP, #N16', 3, 'U', '3-86', 'DP=03F1'),
    (0x298E, 'LB A, [DP]', 1, 'R', '3-70', 'AL=DATA03F1;DD0;ZF=isZero(AL)'),
    (0x298F, 'ANDB A, #N8', 2, '0', '3-24', 'AL=AL&1F;ZF=isZero(AL)'),
    (0x2991, 'MOV DP, #N16', 3, 'U', '3-86', 'DP=03F6'),
    (0x2994, 'STB A, [DP]', 1, '0', '3-155', 'DATA03F6=AL'),
    (0x2995, 'STB A, N8', 2, '0', '3-155', 'BoundaryOnly_NotPerformed'))


def inventory():
    return [{'pc': pc, 'pcHex': f'{pc:04X}', 'form': form, 'length': length,
             'ddMode': dd, 'printedPage': page, 'primarySource': 'ISA1991',
             'effect': effect, 'successors': [pc + length],
             'effectScope': ('FormalBoundaryOnly_NotPerformed' if pc == 0x2995 else
                             'ConditionalReviewedInstructionEffect_NotDecodedOrRetiredHere')}
            for pc, form, length, dd, page, effect in ROWS]


def binding():
    return deepcopy(SOURCE_BINDING)


def binding_matches(value, expected=None):
    expected = SOURCE_BINDING if expected is None else expected
    if type(value) is not type(expected):
        return False
    if type(expected) is dict:
        return set(value) == set(expected) and all(binding_matches(value[k], v) for k, v in expected.items())
    if type(expected) is list:
        return len(value) == len(expected) and all(binding_matches(a, b) for a, b in zip(value, expected))
    return value == expected
