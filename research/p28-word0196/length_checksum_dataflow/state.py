"""Safe reuse of the frozen M2cn partial-state and ordered-effect contract."""
import re

from conditional_flag_mode_shadow.state import Boundary, Effects, validate


def require(value, reason):
    if value is not True:
        raise ValueError(reason)


def identifier(value):
    return type(value) is str and re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,31}', value) is not None


def reconstruct(snapshot, procedure, entry, body, stage_id=None):
    if stage_id is not None:
        require(identifier(stage_id), 'TypedUniqueStageIdentifierRequired')
        procedure += '@' + stage_id
    effects = Effects(snapshot, procedure)
    try:
        effects.admit(entry)
        return body(effects)
    except Boundary as boundary:
        return effects.result(boundary.status, boundary.reason, boundary.pc)


def arithmetic(left, right):
    if left is None or right is None:
        return {'al': None, 'cf': None, 'zf': None, 'hc': None}
    value = (left + right) & 255
    return {'al': value, 'cf': int(left + right > 255), 'zf': int(value == 0),
            'hc': int((left & 15) + (right & 15) > 15)}


def write_r7(effects):
    effects.store(0x270, 0x3F7, [2], 'ImmediateStore', 'Literal')
    effects.step(0x270, 0x272)


def accumulate_increment(effects):
    previous = effects.read(0x26D, 0x3F6)[0]
    addition = arithmetic(previous, effects.r['al'])
    effects.r.update({k: addition[k] for k in ('cf', 'zf', 'hc')})
    effects.store(0x26D, 0x3F6, [addition['al']], 'RMW', 'DATA03F6+AL')
    effects.step(0x26D, 0x26F)
    previous = effects.read(0x26F, 0x3F5)[0]
    value = None if previous is None else (previous + 1) & 255
    effects.r.update(zf=None if value is None else int(value == 0),
                     hc=None if previous is None else int(previous & 15 == 15))
    effects.store(0x26F, 0x3F5, [value], 'RMW', 'DATA03F5+1')
    effects.step(0x26F, 0x270)
    write_r7(effects)
