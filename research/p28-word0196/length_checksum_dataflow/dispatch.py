"""Structured verified dispatch; selected source bodies are distinct boundaries."""
from conditional_flag_mode_shadow.flag import _body as frozen_flag_body

from . import checksum, header, length
from .state import arithmetic, reconstruct, require

ROLES = frozenset(('Header', 'Length', 'Flag', 'Checksum'))
ENTRIES = {'Header': 0x275, 'Length': 0x27F, 'Flag': 0x262, 'Checksum': 0x284}


def select(effects):
    effects.load_byte(0x255, 0x3F7, 0x256)
    if effects.branch(0x256, None if effects.r['zf'] is None else effects.r['zf'] == 1, 0x275, 0x258):
        return 'Header'
    effects.load_byte(0x258, 0x3F5, 0x259)
    effects.compare_byte(0x259, effects.r['al'], 1, 0x25B)
    if effects.branch(0x25B, None if effects.r['zf'] is None else effects.r['zf'] == 1, 0x27F, 0x25D):
        return 'Length'
    effects.r.update(arithmetic(effects.r['al'], 1))
    effects.step(0x25D, 0x25F)
    operand = effects.read(0x25F, 0x3F2)[0]
    effects.compare_byte(0x25F, effects.r['al'], operand, 0x260)
    if effects.branch(0x260, None if effects.r['zf'] is None else effects.r['zf'] == 1, 0x284, 0x262):
        return 'Checksum'
    return 'Flag'


def dispatch(snapshot):
    def body(effects):
        role = select(effects)
        return effects.finish(role + 'Selected', ENTRIES[role])
    return reconstruct(snapshot, 'dispatch', 0x255, body)


def parser_step(snapshot, *, stage_id=None, required_role=None):
    require(required_role is None or type(required_role) is str and required_role in ROLES,
            'ClosedConditionalRoleRequired')

    def body(effects):
        mode = effects.read_bit(0x21F, 0x356, 1)
        if effects.branch(0x21F, None if mode is None else mode == 0, 0x29D, 0x222):
            effects.halt('OutsideVerifiedScope', 'UnmodeledBranch', 0x29D)
        effects.bit(0x222, 0x356, 6, 0, 0x225)
        if not effects.branch(0x225, None if effects.r['zf'] is None else effects.r['zf'] == 1, 0x255, 0x227):
            effects.halt('OutsideVerifiedScope', 'UnmodeledBranch', 0x227)
        role = select(effects)
        if required_role is not None and role != required_role:
            effects.halt('OutsideVerifiedScope', 'DeclaredRoleDoesNotMatchDispatch', ENTRIES[role])
        transform = {'Header': header.transform, 'Length': length.transform,
                     'Checksum': checksum.transform, 'Flag': frozen_flag_body}[role]
        return transform(effects)

    return reconstruct(snapshot, 'parser_step', 0x21F, body, stage_id)
