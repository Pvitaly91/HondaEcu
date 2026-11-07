"""Static source boundaries for the closed 7DF5-to-608F corridor."""
from native_data0217_011f_bridge.helper_cfg import NODE_ROWS

ENTRY = 0x7DF5
STOP = 0x608F


def _bounded_nodes():
    inventory = {pc: (form, length, successors) for pc, form, length, successors in NODE_ROWS}
    pending, result = [ENTRY], {}
    while pending:
        pc = pending.pop()
        if pc == STOP or pc in result:
            continue
        result[pc] = inventory[pc]
        pending.extend(inventory[pc][2])
    return result


NODES = _bounded_nodes()
CORRIDOR_SCOPE = tuple(sorted(NODES))


def following(pc):
    _, _, (successor,) = NODES[pc]
    return successor


def branch_targets(pc):
    _, length, successors = NODES[pc]
    fallthrough = pc + length
    taken, = (successor for successor in successors if successor != fallthrough)
    return taken, fallthrough
