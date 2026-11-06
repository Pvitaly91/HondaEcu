"""Verified mode prefix/suffix around an immutable call to the accepted M2ct producer."""
from tx_ack_configuration_provenance.mode_producer import mode_bit1_producer, PRODUCER_SITES
from .state import Effects, Boundary, project, frozen

MODE_SITES = tuple(sorted((*PRODUCER_SITES, 0x60BD, 0x60C0, 0x60D7, 0x60DA, 0x60DD, 0x60E0, 0x60E3)))


def mode_producer_extended(snapshot):
    effects = Effects(snapshot, 'mode_producer_extended', MODE_SITES, mode=True)
    entry = snapshot['entry']
    try:
        effects.admit(0x60BD if entry == 'At60BD' else 0x60C9 if entry == 'Compare3cb' else 0x60D2)
        if entry == 'At60BD':
            if effects.r['lrb'] != 0x41:
                effects.halt('OutsideVerifiedScope', 'LocalBank0208NotEstablished', 0x60BD)
            effects.read(0x60BD, 0x208)
            values = frozen.candidates(effects.state['memory']['0208'], effects.state['knownBits'], '0208')
            effects.compare_values(0x60BD, values, 0, 0x60C0)
            zf = effects.r['zf']
            if not effects.branch(0x60C0, None if zf is None else zf == 1, 0x60C9, 0x60C2):
                effects.halt('OutsideVerifiedScope', 'ProgramTableSourceNotAdmitted', 0x60C2)
            entry = 'Compare3cb'
        child = mode_bit1_producer({**project(effects.snapshot()), 'entry': entry})
        effects.absorb(child)
        if child['status'] != 'CompleteConditional':
            return effects.result(child['status'], child['reason'], child['boundary'])
        effects.literal_a_word(0x60D7, 0x700, 0x60DA)
        if effects.r['lrb'] is None or effects.r['lrb'] & 0x1FE0 != 0x40:
            effects.halt('OutsideVerifiedScope', 'LocalPage0216NotEstablished', 0x60DA)
        bit = effects.read_bit(0x60DA, 0x216, 3)
        if not effects.branch(0x60DA, None if bit is None else bit == 1, 0x60E0, 0x60DD):
            effects.literal_a_word(0x60DD, 0x500, 0x60E0)
        effects.dp(0x60E0, 0x382, 0x60E3)
        effects.pointer_dependency(0x60E3)
        effects.store(0x60E3, 0x382, [effects.r['al'], effects.r['ah']], 'Store', 'A',
                      partial=effects.a_partial(0x382, ('al', 'ah')))
        effects.step(0x60E3, 0x60E4)
        return effects.finish('ConditionalModeWordPrepared', 0x60E4)
    except Boundary as boundary:
        return effects.result(boundary.status, boundary.reason, boundary.pc)
