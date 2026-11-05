"""Preserve accepted dispatch predicates, extending only the reviewed data branch."""
from length_checksum_dataflow import checksum, header, length
from length_checksum_dataflow.dispatch import dispatch as frozen_dispatch, select
from length_checksum_dataflow.state import reconstruct, require

from .payload import data_transform, qualify

ROLES = frozenset(('Header', 'Length', 'Flag', 'Generic', 'Checksum'))
ENTRIES = {'Header': 0x275, 'Length': 0x27F, 'Checksum': 0x284, 'Flag': 0x262}


def dispatch(snapshot):
    result = frozen_dispatch(snapshot)
    if result['outcome'] == 'FlagSelected':
        result['outcome'] = 'DataSelected'
    return qualify(result)


def parser_step(snapshot, *, stage_id=None, required_role=None):
    require(required_role is None or type(required_role) is str and required_role in ROLES,
            'ClosedConditionalRoleRequired')

    def transform(effects):
        mode = effects.read_bit(0x21F, 0x356, 1)
        if effects.branch(0x21F, None if mode is None else mode == 0, 0x29D, 0x222):
            effects.halt('OutsideVerifiedScope', 'UnmodeledBranch', 0x29D)
        effects.bit(0x222, 0x356, 6, 0, 0x225)
        if not effects.branch(0x225, None if effects.r['zf'] is None else effects.r['zf'] == 1, 0x255, 0x227):
            effects.halt('OutsideVerifiedScope', 'UnmodeledBranch', 0x227)
        selected = select(effects)
        if selected == 'Flag':
            if required_role not in (None, 'Flag', 'Generic'):
                effects.halt('OutsideVerifiedScope', 'DeclaredRoleDoesNotMatchDispatch', 0x262)
            return data_transform(effects, required_role)
        if required_role is not None and required_role != selected:
            effects.halt('OutsideVerifiedScope', 'DeclaredRoleDoesNotMatchDispatch', ENTRIES[selected])
        return {'Header': header.transform, 'Length': length.transform,
                'Checksum': checksum.transform}[selected](effects)

    return qualify(reconstruct(snapshot, 'parser_step', 0x21F, transform, stage_id))
