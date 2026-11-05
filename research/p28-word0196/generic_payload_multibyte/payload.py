"""DD-qualified local byte store and exact Flag/Generic source selection."""
from conditional_flag_mode_shadow.state import need
from length_checksum_dataflow.state import accumulate_increment, reconstruct

CONSTRAINTS = ('ActualEcuEquivalenceNotEstablished', 'NativeReentryEdgeNotEstablished',
               'PhysicalSFNotEstablished', 'PeripheralReceiveLifecycleNotEstablished')


def qualify(result):
    constraints = list(CONSTRAINTS)
    if result['status'] != 'CompleteConditional' and result['reason'] not in constraints:
        constraints.append(result['reason'])
    return {**result, 'unresolvedConstraints': constraints}


def generic_transform(effects):
    # The same encoding with DD1 is a different word form; never force DD0 here.
    if effects.r['dd'] != 0:
        effects.halt('OutsideVerifiedScope', 'ByteStoreDdContextNotEstablished', 0x26C)
    effects.store(0x26C, 0x3F4, [effects.r['al']], source='AL')
    effects.step(0x26C, 0x26D)
    accumulate_increment(effects)
    return effects.finish('GenericWritten', 0x272)


def data_transform(effects, required_role=None):
    need(required_role is None or type(required_role) is str and required_role in ('Flag', 'Generic'),
         'ClosedDataRoleRequired')
    effects.load_byte(0x262, 0x55, 0x264)
    counter = effects.read(0x264, 0x3F5)[0]
    effects.compare_byte(0x264, counter, 2, 0x267)
    generic = effects.branch(0x267, None if effects.r['zf'] is None else effects.r['zf'] == 0, 0x26C, 0x269)
    selected = 'Generic' if generic else 'Flag'
    if required_role is not None and required_role != selected:
        effects.halt('OutsideVerifiedScope', 'DeclaredRoleDoesNotMatchDataSelection', 0x26C if generic else 0x269)
    if generic:
        return generic_transform(effects)
    effects.store(0x269, 0x3F3, [effects.r['al']], source='AL')
    effects.step(0x269, 0x26A)
    effects.step(0x26A, 0x26D, 'Jump', True)
    accumulate_increment(effects)
    return effects.finish('FlagWritten', 0x272)


def generic_payload_body(snapshot):
    return qualify(reconstruct(snapshot, 'generic_payload_body', 0x26C, generic_transform))


def data_body(snapshot):
    return qualify(reconstruct(snapshot, 'data_body', 0x262, data_transform))
