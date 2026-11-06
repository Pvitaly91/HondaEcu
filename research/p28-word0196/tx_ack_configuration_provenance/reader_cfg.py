"""The reviewed short-circuit reader, over explicitly supplied symbolic SFR values."""
from .state import Effects, Boundary, frozen

READER_SITES = (0x3FD4, 0x3FD7, 0x3FD9, 0x3FDB, 0x3FDD, 0x3FDF, 0x3FE1,
                0x3FE3, 0x3FE5, 0x3FE7, 0x3FE9, 0x3FEB, 0x3FEF, 0x3FF1, 0x3FF5)


def tx_configuration_reader(snapshot):
    effects = Effects(snapshot, 'tx_configuration_reader', READER_SITES)
    try:
        effects.admit(0x3FD4)
        effects.dp(0x3FD4, 0x356, 0x3FD7)
        effects.pointer_dependency(0x3FD7)
        effects.r['cf'] = effects.read_bit(0x3FD7, 0x356, 1)
        effects.step(0x3FD7, 0x3FD9)
        cf = effects.r['cf']
        if effects.branch(0x3FD9, None if cf is None else cf == 0, 0x3FF7, 0x3FDB):
            return effects.finish('GuardBypass', 0x3FF7)
        rows = ((0x3FDB, 0x4A, 0x3FDD, 0xF3, 0x3FDF, 0x12, 0x3FE1, 0x3FE3, 'MismatchSTTMC'),
                (0x3FE3, 0x50, 0x3FE5, 0x7F, 0x3FE7, 0x1C, 0x3FE9, 0x3FEB, 'MismatchSTCON'))
        for pc, address, mask_pc, mask, cmp_pc, literal, branch_pc, following, outcome in rows:
            if effects.input['assumptions']['ordinaryByteSemantics'] is not True:
                effects.halt('OutsideVerifiedScope', 'OrdinaryByteSemanticsNotEstablished', pc)
            values = effects.symbolic_readback(pc, address)
            effects.set_a_byte('al', values)
            effects.r.update(dd=0, zf=frozen.unique({int(v == 0) for v in values}))
            effects.step(pc, mask_pc)
            values = {v & mask for v in effects.a_values('al')}
            effects.set_a_byte('al', values)
            effects.r['zf'] = frozen.unique({int(v == 0) for v in values})
            effects.step(mask_pc, cmp_pc)
            effects.compare_values(cmp_pc, values, literal, branch_pc)
            zf = effects.r['zf']
            if effects.branch(branch_pc, None if zf is None else zf == 0, 0x3FB1, following):
                return effects.finish(outcome, 0x3FB1)
        for pc, address, literal, branch_pc, following, outcome in (
            (0x3FEB, 0x54, 0x8C, 0x3FEF, 0x3FF1, 'MismatchSRCON'),
            (0x3FF1, 0x49, 0xDF, 0x3FF5, 0x3FF7, 'MismatchSTTMR')):
            effects.compare_values(pc, effects.symbolic_readback(pc, address), literal, branch_pc)
            zf = effects.r['zf']
            if effects.branch(branch_pc, None if zf is None else zf == 0, 0x3FB1, following):
                return effects.finish(outcome, 0x3FB1)
        return effects.finish('AllConfigurationChecksMatch', 0x3FF7)
    except Boundary as boundary:
        return effects.result(boundary.status, boundary.reason, boundary.pc)
