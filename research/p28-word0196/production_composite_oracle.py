"""M2bq source draft: full independent reference values and Bus protocol.

Architectural effects are obtained only from immutable M2bk reference_case
(primary manufacturer semantics + M2av C11/IR + M2bd obligations). The separate
Bus/decoder protocol model describes expected observations; it is not a target
CPU interpreter. It neither calls Rust nor imports the new production module.
No new Cpu output may define these expected values.
"""

from copy import deepcopy
from hashlib import sha256
from production_composite_common import (
    COMPOSITE_SHA, DATA_INVENTORY, PROVENANCE, reference_modules, require,
)
from production_composite_topology import expected_program_events

RAM_BEGIN, RAM_END, SCRATCH = 0x80, 0x1000, 0xA5
FORM_IDS = {
    "556F": "lb-a-page", "5571": "sllb-a", "5572": "rolb-page",
    "5575": "lb-a-r0", "5576": "andb-a-page", "5578": "cmp-page-imm16",
    "557D": "jlt-rel8", "557F": "movb-r1-page", "5582": "andb-page-a",
    "5585": "jbs-page-bit7", "5588": "jbs-page-bit5", "558B": "andb-page-a",
    "558E": "orb-page-imm8", "5592": "lb-a-page", "5594": "orb-a-imm8",
    "55BF": "lb-a-imm8", "55C1": "stb-a-page", "55C3": "stb-a-page",
    "DirectJ_NotBelow": "j-address", "DirectJ_Below": "j-address",
}
SCHEMA = {"architecture": "ImmutableM2bkReference_M2avC11IR_M2bdDataflow_ManufacturerRules",
          "busProtocol": "IndependentExpectedLogicalRawSeedDiagnosticEvents_NotObservedEvents",
          "programTopology": "SeparateFrozenDecoderObservationModel",
          "ram": "All3968BytesIncludingUnseededA5", "sf": "InternalBooleanOnly_NativeMeaningUnknown",
          "cycles": "UnchangedSourceAccounting_NotPhysicalTimingOrM2avCycleEquivalence",
          "scope": "InventedOnly_NoOriginalROM_NoNativeRejoin_NoFirmware"}


def logical_id(row):
    value = row["logicalId"]
    return value if type(value) is str else f"{value:04X}"


def reference_case(root, request):
    with reference_modules(root) as modules:
        legacy = modules["synthetic_composite_execution_oracle"]
        result = modules["synthetic_execution_protocol_oracle"].reference_case(legacy._reference_input(request))
    require(result["path"] == request["path"], "CorpusPathMatchesIndependentEntryPredicate")
    return result


def architectural_projection(root, request):
    """Shared old/new semantic layer; all production-only fields checked apart.

    This is expected data only. It is deliberately not labelled an actual M2bn
    execution, nor does reference_case's NotRun status become an observation.
    """
    result = reference_case(root, request)
    with reference_modules(root) as modules:
        old = modules["synthetic_composite_execution_oracle"]
        logical, raw, spans = old._data_events(result)
        steps = [{"index": row["step"], "node_identity": logical_id(row),
                  "before": old._snapshot(row["stateBefore"]),
                  "after": old._snapshot(row["stateAfter"]),
                  "decode": old._decode(row), "branch_taken": row["branchTaken"],
                  "logical_span": [bounds[0], bounds[1]], "raw_span": [bounds[2], bounds[3]]}
                 for row, bounds in zip(result["trace"], spans)]
        return {"case_key": [request["case_id"], request["internal_sf"]], "path": result["path"],
                "entry": old._snapshot(result["entryState"]),
                "terminal": old._snapshot(result["terminalState"]),
                "initial_data": deepcopy(request["data"]),
                "terminal_data": {str(int(k, 16)): v for k, v in result["terminalData"].items()},
                "steps": steps, "logical_events": logical, "raw_events": raw,
                "instruction_count": result["instructionCount"], "direct_j_count": 1,
                "terminal_pc": result["terminalPc"], "internal_sf": request["internal_sf"],
                "native_sf": deepcopy(request["entry"]["sf"]), "provenance": PROVENANCE}


def raw_cpu(state, internal_sf, cycles=0, instructions=0):
    return {"pc": state["pc"], "a": state["a"], "ssp": state["ssp"], "lrb": state["lrb"],
            **{name: bool(state[name]) for name in ("zf", "cf", "hc", "dd")},
            "sf": internal_sf, "psw_other": state["otherPsw"] & 0x0337,
            "cycles": cycles, "instructions": instructions, "halted": state["halted"]}


class ExpectedDataProtocol:
    """Generic expected memory acquisition protocol, not an ISA dispatcher.

    The only functional events passed here are the independent reference's
    already-calculated ordered reads/writes. Seed and diagnostic operations are
    separate; write ordinals include seed writes exactly as the Bus API does.
    """
    def __init__(self):
        self.memory = [SCRATCH] * (RAM_END - RAM_BEGIN)
        self.logical, self.raw, self.diagnostics = [], [], []
        self.write_ordinal = self.raw_write_ordinal = 0

    def event(self, pc, index, address, width, operation, value=None, phase="Functional"):
        require(type(width) is int and width in (8, 16), "ExpectedExactAccessWidth")
        require(operation in ("Read", "Write") and RAM_BEGIN <= address
                and address + width // 8 <= RAM_END, "ExpectedInventoriedRamAccess")
        ordinal, write = len(self.logical), operation == "Write"
        prior = sum(self.memory[address - RAM_BEGIN + offset] << (8 * offset) for offset in range(width // 8))
        observed = value if write else prior
        require(type(observed) is int and 0 <= observed < 1 << width, "ExpectedWidthValue")
        self.logical.append({"ordinal": ordinal, "phase": phase, "pc": pc,
                             "instruction_index": index, "address": address, "width": width,
                             "operation": operation, "requested_value": value if write else None,
                             "value": observed, "old_value": prior if write else None,
                             "write_ordinal": self.write_ordinal if write else None,
                             "same_value": prior == value if write else None, "serviced": True, "refusal": None})
        if write:
            self.write_ordinal += 1
        for offset in range(width // 8):
            location = address + offset
            raw_old = self.memory[location - RAM_BEGIN]
            byte = (observed >> (8 * offset)) & 255
            self.raw.append({"ordinal": len(self.raw), "logical_ordinal": ordinal, "address": location,
                             "operation": operation, "requested_value": byte if write else None,
                             "value": byte, "old_value": raw_old if write else None,
                             "write_ordinal": self.raw_write_ordinal if write else None,
                             "same_value": raw_old == byte if write else None, "serviced": True, "refusal": None})
            if write:
                self.raw_write_ordinal += 1
                self.memory[location - RAM_BEGIN] = byte
        return observed, prior

    def seed(self, request):
        require(tuple(sorted(int(key) for key in request["data"])) == DATA_INVENTORY, "ExactSixteenDataSeeds")
        for address, value in sorted(request["data"].items(), key=lambda item: int(item[0])):
            self.event(0x1000, None, int(address), 8, "Write", value, "Seed")
        for bank, row in enumerate(request["entry"]["pointing_banks"]):
            for slot, name in enumerate(("x1", "x2", "dp", "usp")):
                self.event(0x1000, None, 0x80 + 8 * bank + 2 * slot, 16, "Write", row[name], "Seed")
        require((len(self.logical), len(self.raw), self.write_ordinal, self.raw_write_ordinal)
                == (48, 80, 48, 80), "SingleCompleteInitialization")

    def snapshot(self, state, internal_sf, cycles, instructions):
        self.diagnostics.append({"ordinal": len(self.diagnostics), "kind": "RawRamSnapshot",
                                 "range": [RAM_BEGIN, RAM_END], "byte_count": RAM_END - RAM_BEGIN})
        return {"cpu": raw_cpu(state, internal_sf, cycles, instructions),
                "ram": list(self.memory), "ram_range": [RAM_BEGIN, RAM_END]}


def expected_execution_components(root, request):
    """Independently derive all state/effects and expected acquisition ranges.

    The final public raw-report envelope is assembled only from these values
    and reviewed fixed API protocol constants; it must never take actual output
    as an input. No expected stream is created merely by importing this file.
    """
    result = reference_case(root, request)
    program, program_spans = expected_program_events(root, result)
    data = ExpectedDataProtocol()
    data.seed(request)
    sf, cycles, retired = request["internal_sf"], 0, 0
    entry = data.snapshot(result["entryState"], sf, cycles, retired)
    steps = []
    with reference_modules(root) as modules:
        old = modules["synthetic_composite_execution_oracle"]
        primary = modules["synthetic_composite_primary_oracle"]
        for row, program_span in zip(result["trace"], program_spans):
            node = logical_id(row)
            decode = old._decode(row)
            before = data.snapshot(row["stateBefore"], sf, cycles, retired)
            logical_start, raw_start = len(data.logical), len(data.raw)
            for read in row["dataReads"]:
                actual_value, _ = data.event(row["syntheticPc"], decode["index"], read["address"],
                                            read["widthBits"], "Read")
                require(actual_value == read["value"], "ReferenceReadVersusIndependentMemory")
            for write in row["dataWrites"]:
                _, old_value = data.event(row["syntheticPc"], decode["index"], write["address"],
                                         8, "Write", write["value"])
                require(old_value == write["oldValue"], "ReferenceWriteOldValueVersusIndependentMemory")
            instruction_cycles = 2 * row["length"] + int(node.startswith("DirectJ_"))
            cycles += instruction_cycles + (4 if row["branchTaken"] is True else 0)
            retired += 1
            after = data.snapshot(row["stateAfter"], sf, cycles, retired)
            index = next(i for i, candidate in enumerate(primary.NODES)
                         if (candidate.node_id if type(candidate.node_id) is str
                             else f"{candidate.node_id:04X}") == node)
            decoded = {key: value for key, value in decode.items() if key != "form"}
            decoded.update({"dd_after_option": False if node in ("556F", "5575", "5592", "55BF") else None,
                            "cycles": instruction_cycles, "n16_alt": 0, "s8": 0})
            outcome = {"pc_before": row["syntheticPc"], "pc_after": row["stateAfter"]["pc"],
                       "decoded_index": decoded["index"], "mnemonic": decoded["mnemonic"],
                       "len": decoded["len"], "decoded": decoded,
                       "selected_extent": [row["syntheticPc"], row["syntheticPc"] + row["length"]],
                       "selected_extent_sha256": sha256(primary.expected_instruction(index)).hexdigest(),
                       "retired": True, "external_exit": result["terminalPc"] if node.startswith("DirectJ_") else None}
            steps.append({"index": retired, "node_identity": node, "form": FORM_IDS[node],
                          "before": before, "after": after, "outcome": outcome,
                          "program_span": program_span, "logical_span": [logical_start, len(data.logical)],
                          "raw_span": [raw_start, len(data.raw)]})
    current = data.snapshot(result["terminalState"], sf, cycles, retired)
    return {"reference": result, "entry": entry, "current": current, "steps": steps,
            "program_events": program, "data_events": data.logical, "raw_data_events": data.raw,
            "diagnostic_events": data.diagnostics, "retired": retired, "cycles": cycles,
            "terminal_pc": result["terminalPc"], "path": result["path"],
            "expected_only": True, "composite_sha256": COMPOSITE_SHA}


def expected_permissions(path):
    """Independent union display; actual composite admission is per instruction.

    These are not caller-supplied rights. Exact per-step access obligations are
    independently checked by the reference trace and the raw-report equality.
    """
    require(path in "ABCD" and len(path) == 1, "ClosedReferencePath")
    reads = [(0x108, 8), (0x18E, 8), (0x196, 16)]
    writes = [(0x18E, True), (0x117, path != "A")]
    if path == "A":
        writes.append((0x18F, False))
    else:
        reads.extend(((0x117, 8), (0x12A, 8), (0x18F, 8)))
        writes.append((0x109, False))
        if path in "CD":
            reads.append((0x124, 8))
        if path == "D":
            writes.extend(((0x18F, True), (0x12A, True)))
    return {"reads": [{"address": address, "width": width} for address, width in sorted(reads)],
            "writes": [{"access": {"address": address, "width": 8}, "rmw_required": rmw}
                       for address, rmw in sorted(writes)],
            "raw_reads": sorted({address + offset for address, width in reads for offset in range(width // 8)}),
            "raw_writes": sorted(address for address, _ in writes)}


def expected_case(root, request):
    parts = expected_execution_components(root, request)
    count, terminal = parts["retired"], parts["terminal_pc"]
    audit = {"entry_pc": 4096, "current_pc": terminal,
             "program_base": 4096, "program_end_exclusive": 4147, "program_sha256": COMPOSITE_SHA,
             "program_events": parts["program_events"], "data_events": parts["data_events"],
             "raw_data_events": parts["raw_data_events"], "diagnostic_events": parts["diagnostic_events"],
             "data_admission_refusals": [], "permissions": expected_permissions(parts["path"]),
             "phase": "Sealed", "budget": 16, "successful_retirements": count,
             "step_calls": count, "execution_calls": count, "shared_execution_calls": count,
             "sealed": True, "terminal_reason": "ActualDirectJCompleted", "external_exit": terminal,
             "first_fault": None}
    report = {"mode": "ClosedM2bjComposite", "program_node_count": 20, "path": parts["path"],
              "entry": parts["entry"], "current": parts["current"], "steps": parts["steps"],
              "direct_j_count": 1, "completed": True, "audit": audit}
    return {"kind": "composite_observation", "case_id": request["case_id"], "family": request["family"],
            "internal_sf": request["internal_sf"], "accepted": True, "error": None, "report": report,
            "actual_successful_step_returns": count, "cpu_instances": 1, "bus_instances": 1,
            "data_initializations": 1, "functional_transitions": 1, "composite_execution_attempts": 1,
            "full_production_composite_executions": 1,
            "original_rom_executions": 0, "firmware_ready": False}


def semantic_snapshot(snapshot):
    """Derive aliases/PSW only from actual captured CPU and all captured RAM.

    No expected state, initial seed or reference result is consulted here.
    Native SF meaning remains unknown; the actual internal boolean is checked
    separately against the paired experiment and full raw CpuState equality.
    """
    cpu, ram = snapshot["cpu"], snapshot["ram"]
    require(snapshot["ram_range"] == [RAM_BEGIN, RAM_END] and len(ram) == RAM_END - RAM_BEGIN,
            "CompleteCapturedRamBeforeAliasProjection")
    psw = (cpu["psw_other"] & 0x0337) | 0x0CC8 | (int(cpu["dd"]) << 12) \
        | (int(cpu["hc"]) << 13) | (int(cpu["zf"]) << 14) | (int(cpu["cf"]) << 15)
    local = [ram[address - RAM_BEGIN] for address in range(0x108, 0x110)]
    banks = []
    for bank in range(8):
        banks.append({name: ram[bank * 8 + slot * 2] + 256 * ram[bank * 8 + slot * 2 + 1]
                      for slot, name in enumerate(("x1", "x2", "dp", "usp"))})
    return {"pc": cpu["pc"], "a": cpu["a"], "al": cpu["a"] & 255, "ah": cpu["a"] >> 8,
            "psw": psw, **{name: cpu[name] for name in ("cf", "zf", "hc", "dd")},
            "other_psw": psw & 4095, "lrb": cpu["lrb"], "scb": psw & 7, "ssp": cpu["ssp"],
            "pointing_banks": banks, "local_r": local,
            "local_er": [local[2 * index] + 256 * local[2 * index + 1] for index in range(4)],
            "halted": cpu["halted"], "provenance": PROVENANCE,
            "sf": {"status": "SFMeaningStorageNotEstablished", "value": None,
                   "meaning": None, "storage": None, "width_bits": None}}


def actual_architectural_projection(actual):
    """Explicit shared projection; raw production fields are ALSO compared.

    Rebased ordinals are visibly a reference-layer convention only. The full
    raw canonical stream retains their actual seed-inclusive global values.
    """
    report, audit = actual["report"], actual["report"]["audit"]
    functional = [row for row in audit["data_events"] if row["phase"] == "Functional"]
    ids = {row["ordinal"]: index + 1 for index, row in enumerate(functional)}
    raw = [row for row in audit["raw_data_events"] if row["logical_ordinal"] in ids]
    raw_by_parent = {}
    for row in raw:
        raw_by_parent.setdefault(row["logical_ordinal"], []).append(row["value"])
    logical = []
    for row in functional:
        write = row["operation"] == "Write"
        kind = None
        if write:
            kind = "LocalRegisterStore" if row["pc"] == 0x1010 else \
                "Store" if row["pc"] in (0x102C, 0x102E) else "RMW"
        logical.append({"ordinal": ids[row["ordinal"]], "phase": "ExecutedFunctionalDataAccess",
                        "pc": row["pc"], "address": row["address"], "width": row["width"],
                        "operation": row["operation"], "value": row["value"], "old_value": row["old_value"],
                        "write_ordinal": row["write_ordinal"] - 48 + 1 if write else None,
                        "kind": kind, "same_value": row["same_value"] if write else False,
                        "constituents": raw_by_parent[row["ordinal"]]})
    raw_projection = [{"ordinal": index + 1, "logical_ordinal": ids[row["logical_ordinal"]],
                       "address": row["address"], "operation": row["operation"], "value": row["value"]}
                      for index, row in enumerate(raw)]
    steps = []
    for row in report["steps"]:
        outcome, decode = row["outcome"], row["outcome"]["decoded"]
        branch = (outcome["pc_after"] != outcome["pc_before"] + outcome["len"]) \
            if row["form"] in ("jlt-rel8", "jbs-page-bit7", "jbs-page-bit5") else None
        steps.append({"index": row["index"], "node_identity": row["node_identity"],
                      "before": semantic_snapshot(row["before"]), "after": semantic_snapshot(row["after"]),
                      "decode": {"form": row["form"], **{key: decode[key] for key in
                                 ("mnemonic", "index", "len", "dd_before", "dd_after", "n8", "n8_alt", "n16", "addr16", "rel8")}},
                      "branch_taken": branch,
                      "logical_span": [value - 48 for value in row["logical_span"]],
                      "raw_span": [value - 80 for value in row["raw_span"]]})
    data_at = lambda snapshot: {str(address): snapshot["ram"][address - RAM_BEGIN] for address in DATA_INVENTORY}
    return {"case_key": [actual["case_id"], actual["internal_sf"]], "path": report["path"],
            "entry": semantic_snapshot(report["entry"]), "terminal": semantic_snapshot(report["current"]),
            "initial_data": data_at(report["entry"]), "terminal_data": data_at(report["current"]),
            "steps": steps, "logical_events": logical, "raw_events": raw_projection,
            "instruction_count": audit["successful_retirements"], "direct_j_count": report["direct_j_count"],
            "terminal_pc": audit["current_pc"], "internal_sf": report["current"]["cpu"]["sf"],
            "native_sf": semantic_snapshot(report["current"])["sf"], "provenance": PROVENANCE}
