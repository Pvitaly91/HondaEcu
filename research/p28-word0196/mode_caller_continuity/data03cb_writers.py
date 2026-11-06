"""Reviewed indexed ADC-byte assignment using supplied peripheral symbols only."""
from .state import Effects, Boundary, frozen, x1_view

WRITER_SITES = (0x5CA5, 0x5CA7, 0x5CA8, 0x5CA9, 0x5CAB, 0x5CAC, 0x5CAD, 0x5CAF, 0x5CB2, 0x5CB4)


def _indexed_store(effects, pc, base, following):
    address = 0x80 + 8 * effects.r['scb']
    effects.read(pc, address, 16)
    effects.reads[-1].update(space='ARCHITECTURAL_ADDRESS_DEPENDENCY', accessRole='PointingRegisterAlias')
    index = x1_view(effects.state)['value']
    if index is None:
        effects.halt('IndeterminateObligation', 'IndexedAddressNotEstablished', pc)
    if not 0 <= index <= 7:
        effects.halt('OutsideVerifiedScope', 'IndexedAddressOutsideReviewedRange', pc)
    target = base + index
    effects.store(pc, target, [effects.r['al']], 'IndexedStore', 'AL', partial=effects.a_partial(target, ('al',)))
    effects.step(pc, following)


def data03cb_indexed_writer(snapshot):
    effects = Effects(snapshot, 'data03cb_indexed_writer', WRITER_SITES)
    index = None
    try:
        effects.admit(0x5CA5)
        effects.byte_load_symbol(0x5CA5, 0x24, 0x5CA7)
        values = effects.a_values('al')
        effects.set_a_byte('al', {((v & 15) << 4) | v >> 4 for v in values})
        effects.step(0x5CA7, 0x5CA8)
        values = effects.a_values('al')
        effects.r['cf'] = frozen.unique({v & 1 for v in values})
        effects.set_a_byte('al', {v >> 1 for v in values})
        effects.step(0x5CA8, 0x5CA9)
        values = {v & 7 for v in effects.a_values('al')}
        effects.set_a_byte('al', values)
        effects.r['zf'] = frozen.unique({int(v == 0) for v in values})
        index = frozen.unique(values)
        effects.step(0x5CA9, 0x5CAB)
        effects.set_a_byte('ah', {0})
        effects.r['dd'] = 1
        effects.step(0x5CAB, 0x5CAC)
        if effects.r['scb'] is None:
            effects.halt('OutsideVerifiedScope', 'PointerBankNotEstablished', 0x5CAC)
        address = 0x80 + 8 * effects.r['scb']
        effects.store(0x5CAC, address, [effects.r['al'], effects.r['ah']],
            'PointingRegisterWrite', 'A', partial=effects.a_partial(address, ('al', 'ah')))
        effects.step(0x5CAC, 0x5CAD)
        effects.byte_load_symbol(0x5CAD, 0x63, 0x5CAF)
        _indexed_store(effects, 0x5CAF, 0x3CE, 0x5CB2)
        effects.byte_load_symbol(0x5CB2, 0x61, 0x5CB4)
        _indexed_store(effects, 0x5CB4, 0x3C6, 0x5CB7)
        result = effects.finish('IndexedAdcBytesStored', 0x5CB7)
    except Boundary as boundary:
        result = effects.result(boundary.status, boundary.reason, boundary.pc)
    return {**result, 'selectedIndex': index,
            'conditionalData03cbWriterEstablished': result['status'] == 'CompleteConditional' and index == 5}
