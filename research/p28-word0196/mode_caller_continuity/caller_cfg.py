"""Bounded configuration and symbolic-reader callers, using frozen accepted child functions."""
from stbuf_stcon_transmit_source.configuration import stcon_configuration
from stbuf_stcon_transmit_source.source_inventory import CONFIG_SITES
from tx_ack_configuration_provenance.reader_cfg import tx_configuration_reader, READER_SITES
from .reader_continuation import continue_reader
from .state import Effects, Boundary, project, frozen

CONFIGURATION_SITES = tuple(sorted((*CONFIG_SITES, 0x2869, 0x288E)))
READER_CALLER_SITES = tuple(sorted((*READER_SITES, 0x3FCC, 0x3FCE, 0x3FD0, 0x3FD2, 0x3FB1, 0x3FF7)))


def configuration_caller(snapshot):
    effects = Effects(snapshot, 'configuration_caller', CONFIGURATION_SITES)
    try:
        effects.admit(0x2869)
        if effects.r['lrb'] != 0x41:
            effects.halt('OutsideVerifiedScope', 'LocalPage02cdNotEstablished', 0x2869)
        effects.store(0x2869, 0x2CD, [0x32], 'ImmediateStore', 'Literal')
        effects.step(0x2869, 0x286D)
        child = stcon_configuration(project(effects.snapshot(), configuration=True))
        effects.absorb(child)
        if child['status'] != 'CompleteConditional':
            return effects.result(child['status'], child['reason'], child['boundary'])
        effects.dp(0x288E, 0x4700, 0x2891)
        return effects.finish('ConfigurationIntentsPreparedBeforeExternalRead', 0x2891)
    except Boundary as boundary:
        return effects.result(boundary.status, boundary.reason, boundary.pc)


def configuration_reader_caller(snapshot):
    effects = Effects(snapshot, 'configuration_reader_caller', READER_CALLER_SITES)
    try:
        effects.admit(0x3FCC)
        effects.byte_load_symbol(0x3FCC, 0x58, 0x3FCE)
        values = {v & 0x5F for v in effects.a_values('al')}
        effects.set_a_byte('al', values)
        effects.r['zf'] = frozen.unique({int(v == 0) for v in values})
        effects.step(0x3FCE, 0x3FD0)
        effects.compare_values(0x3FD0, values, 0x10, 0x3FD2)
        zf = effects.r['zf']
        if effects.branch(0x3FD2, None if zf is None else zf == 0, 0x3FB1, 0x3FD4):
            return continue_reader(effects, 0x3FB1)
        child = tx_configuration_reader(project(effects.snapshot()))
        effects.absorb(child)
        if child['status'] != 'CompleteConditional':
            return effects.result(child['status'], child['reason'], child['boundary'])
        return continue_reader(effects, child['boundary'])
    except Boundary as boundary:
        return effects.result(boundary.status, boundary.reason, boundary.pc)
