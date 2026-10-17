"""Complete pre-runtime expectations for the 35 finite M2bp capabilities.

This module never invokes Rust, Cpu, Bus, a target decoder, or an executor.
The successful direct-J and partial-LB architectural values come from the
unchanged M2bo primary/IR reference.  The separately declared event protocol
below predicts interface observations, including failed attempts; it is not a
second instruction interpreter or manufacturer evidence.  No actual record is
accepted as input when constructing expected records.

Call expected_capabilities(frozen_closed_inputs, frozen_patterns) before the
first new runtime and seal its complete output.  Compare every key, type, RAM
byte, event and array position afterwards; there are no canonical exclusions.
"""

from copy import deepcopy
from hashlib import sha256

import production_exec_parity_oracle as historical_reference
import production_optin_oracle as observation_protocol


BASE = 0x1000
RAM_START, RAM_END = 0x80, 0x1000
CLASSIFICATION = "ActualProductionInterfaceCapabilityObservation"
CONSTRUCTOR_CLASSIFICATION = "ActualProductionConstructorAdmission"
MODEL_CLASSIFICATION = "ExpectedOnly_PreRuntimeFrozenCapabilityProtocol_NotObservations"
CAPABILITY_IDS = (
    "mapping-first", "mapping-last", "mapping-before-base",
    "mapping-end-exclusive", "mapping-negative", "mapping-address-overflow",
    "mapping-outside-16-bit", "invalid-segment-base",
    "invalid-segment-overflow", "invalid-empty-segment",
    "wrong-actual-program-digest", "unsupported-sfr-rights",
    "invalid-word-constituent-overflow", "raw-read-widening",
    "raw-write-widening", "strict-decoder-out-of-range-probe",
    "strict-missing-selected-byte", "wrong-selected-form-identity",
    "wrong-selected-operand-identity", "forbidden-data-read",
    "forbidden-data-write", "readonly-data0196-write",
    "rmw-write-without-read", "word-high-read-refused",
    "word-high-write-refused-partial-low", "same-value-fresh-store-ordinals",
    "actual-rmw-read-then-write", "actual-le16-logical-and-raw",
    "partial-production-operand-error", "execution-after-fault",
    "fetch-after-real-direct-j-seal", "extra-retirement-after-budget",
    "data-write-after-seal", "seed-after-functional-refused",
    "diagnostic-not-rmw-read",
)


def fault(code, address, detail):
    return {"code": code, "address": address, "detail": detail}


def sealed_fault():
    return fault("SessionSealed", None,
                 "no functional or PROGRAM access after terminal seal")


def logical_read_fault(address):
    return fault("LogicalReadDenied", address,
                 "independent exact logical width/address read right")


def logical_write_fault(address):
    return fault("LogicalWriteDenied", address,
                 "independent exact logical width/address write right")


def rmw_fault(address):
    return fault("RmwReadMissing", address,
                 "actual earlier functional read required, not a diagnostic or seed")


def rights(reads=(), writes=(), *, raw_reads=None, raw_writes=None):
    """Independent literal interface contract, never derived from actual logs."""
    reads = [{"address": a, "width": w} for a, w in sorted(reads)]
    writes = [{"access": {"address": a, "width": w}, "rmw_required": rmw}
              for a, w, rmw in sorted(writes)]
    return {"reads": reads, "writes": writes,
            "raw_reads": sorted({r["address"] + delta for r in reads
                                 for delta in range(r["width"] // 8)})
            if raw_reads is None else list(raw_reads),
            "raw_writes": sorted({r["access"]["address"] + delta for r in writes
                                  for delta in range(r["access"]["width"] // 8)})
            if raw_writes is None else list(raw_writes)}


class ExpectedMachine:
    """A frozen observation-protocol builder, not an instruction executor.

    Every operation below is chosen by one finite capability experiment.
    There is no opcode dispatch, caller-selected stream, or effect execution.
    """

    def __init__(self, item, permissions, *, program=None, seed=True):
        self.item = item
        self.request = item["request"]
        self.data = observation_protocol.ExpectedDataProtocol(self.request)
        if seed:
            self.data.seed()
        self.cpu = historical_reference.raw_cpu(self.request["entry"],
                                               self.request["internal_sf"])
        self.cpu["pc"] = BASE
        self.program = (self.request["bytes"] + self.request["guards"]
                        if program is None else program)
        self.permissions = deepcopy(permissions)
        self.events = []
        self.admission_refusals = []
        self.phase = "Setup"
        self.index = None
        self.selected_length = None
        self.step_calls = self.execution_calls = self.retirements = 0
        self.sealed = False
        self.terminal_reason = self.external_exit = self.first_fault = None

    def snapshot(self):
        return {"cpu": deepcopy(self.cpu), "ram": self.data.snapshot(),
                "ram_range": [RAM_START, RAM_END]}

    def latch(self, error):
        if self.first_fault is None:
            self.first_fault = deepcopy(error)
        return deepcopy(self.first_fault)

    def begin(self):
        self.phase = "Functional"

    def program_event(self, address, purpose, *, error=None, selected_length=None,
                      association=None):
        offset = address - BASE
        event = {"ordinal": len(self.events), "pc": self.cpu["pc"],
                 "address": address,
                 "segment_offset": offset if 0 <= offset < len(self.program) else None,
                 "instruction_offset": offset if 0 <= offset <= 0xffffffff else None,
                 "acquired_purpose": purpose,
                 "selection_association": association,
                 "selected_length": selected_length,
                 "serviced": error is None,
                 "refusal": self.latch(error) if error is not None else None}
        self.events.append(event)

    def denied_data(self, address, width, operation, error, *, value=None):
        error = self.latch(error)
        self.data.logical.append({
            "ordinal": len(self.data.logical), "phase": "Functional", "pc": BASE,
            "instruction_index": self.index, "address": address, "width": width,
            "operation": operation, "requested_value": value,
            "value": None, "old_value": None, "write_ordinal": None,
            "same_value": None, "serviced": False, "refusal": error})
        return error

    def successful_data(self, address, width, operation, value=None):
        return self.data.event(address, width, operation, value,
                               index=self.index)

    def partial_word(self, address, *, write=False, value=None):
        """One actual low constituent is serviced; high is refused pre-service.

        The enclosing logical operation is explicitly incomplete and has no
        completed logical write ordinal. A serviced low write is retained in
        RAM and has its own fresh raw ordinal; there is no rollback claim.
        """
        operation = "Write" if write else "Read"
        ordinal = len(self.data.logical)
        old = self.data.memory[address] | (self.data.memory[address + 1] << 8)
        error = fault("RawWriteDenied" if write else "RawReadDenied", address + 1,
                      "independent constituent right checked before service")
        self.data.logical.append({
            "ordinal": ordinal, "phase": "Functional", "pc": BASE,
            "instruction_index": self.index, "address": address, "width": 16,
            "operation": operation, "requested_value": value if write else None,
            "value": None, "old_value": old if write else None,
            "write_ordinal": None, "same_value": None,
            "serviced": False, "refusal": deepcopy(error)})
        low_old = self.data.memory[address]
        low = value & 255 if write else low_old
        self.data.raw.append({
            "ordinal": len(self.data.raw), "logical_ordinal": ordinal,
            "address": address, "operation": operation,
            "requested_value": low if write else None, "value": low,
            "old_value": low_old if write else None,
            "write_ordinal": self.data.raw_write_ordinal if write else None,
            "same_value": low == low_old if write else None,
            "serviced": True, "refusal": None})
        if write:
            self.data.raw_write_ordinal += 1
            self.data.memory[address] = low
        self.data.raw.append({
            "ordinal": len(self.data.raw), "logical_ordinal": ordinal,
            "address": address + 1, "operation": operation,
            "requested_value": (value >> 8) & 255 if write else None,
            "value": None, "old_value": None, "write_ordinal": None,
            "same_value": None, "serviced": False,
            "refusal": self.latch(error)})
        return error

    def successful_selection(self, patterns):
        self.step_calls += 1
        self.phase = "Executing"
        self.events.extend(observation_protocol.program_events(self.request, patterns))
        self.selected_length = self.request["expected_length"]

    def strict_failed_selection(self, patterns):
        """Callback topology only: refuse the first attempted missing byte.

        Candidate traversal is independently source-bound to the matching
        protocol; no selected instruction or CPU effect is inferred on error.
        """
        self.step_calls += 1
        self.phase = "Executing"
        dd = self.cpu["dd"]

        def fixed(token):
            return len(token) == 2 and all(c in "0123456789abcdefABCDEF" for c in token)

        def acquire(offset):
            address = BASE + offset
            error = None if offset < len(self.program) else fault(
                "ProgramOutsideSegment", address,
                "strict immutable segment has no zero fallback or prefix")
            self.program_event(address, "DecoderProbe", error=error)
            return None if error is not None else self.program[offset]

        first = acquire(0)
        candidates = [(index, row) for index, row in enumerate(patterns)
                      if row[1] and fixed(row[1][0]) and int(row[1][0], 16) == first]
        candidates.sort(key=lambda item: (-sum(fixed(token) for token in item[1][1]),
                                          -len(item[1][1])))
        for _index, (_mnemonic, tokens, mode) in candidates:
            if mode == "1" and not dd or mode == "0" and dd:
                continue
            for offset, token in enumerate(tokens):
                byte = acquire(offset)
                if byte is None:
                    return deepcopy(self.first_fault)
                if fixed(token) and int(token, 16) != byte:
                    break
            else:
                raise ValueError("CapabilityExpectedStrictMissingCallbackButMatcherCompleted")
        raise ValueError("CapabilityExpectedStrictMissingCallbackButNoMatcherReadIt")

    def report(self):
        return deepcopy({
            "entry_pc": BASE, "current_pc": self.cpu["pc"],
            "program_base": BASE, "program_end_exclusive": BASE + len(self.program),
            "program_sha256": sha256(bytes(self.program)).hexdigest(),
            "program_events": self.events, "data_events": self.data.logical,
            "raw_data_events": self.data.raw, "diagnostic_events": self.data.diagnostics,
            "data_admission_refusals": self.admission_refusals,
            "permissions": self.permissions, "phase": self.phase, "budget": 1,
            "successful_retirements": self.retirements, "step_calls": self.step_calls,
            "execution_calls": self.execution_calls,
            "shared_execution_calls": self.execution_calls,
            "sealed": self.sealed, "terminal_reason": self.terminal_reason,
            "external_exit": self.external_exit, "first_fault": self.first_fault})

    def capture(self, identifier, operation):
        before = self.snapshot()
        result, error = operation(self)
        after = self.snapshot()
        return {"id": identifier, "classification": CLASSIFICATION,
                "before": before, "after": after,
                "result": result, "error": error, "audit": self.report(),
                "cpu_instances": 1, "bus_instances": 1,
                "production_composite_executions": 0, "original_rom_executions": 0}


def constructor_record(identifier, error):
    return {"id": identifier, "classification": CONSTRUCTOR_CLASSIFICATION,
            "accepted": False, "error": error, "cpu_instances": 0,
            "bus_instances": 0, "actual_step_calls": 0}


def expected_capabilities(closed_inputs, patterns):
    """Return the exact whole expected wire record, without runtime input."""
    def template(form):
        return next(row for row in closed_inputs if row["request"]["form"] == form
                    and row["expected_admission"] == "Accepted")

    def live(form, permissions):
        return ExpectedMachine(template(form), permissions)

    lb = template("lb-a-page")
    records = []
    for identifier, address in (
            ("mapping-first", 4096), ("mapping-last", 4146),
            ("mapping-before-base", 4095), ("mapping-end-exclusive", 4147),
            ("mapping-negative", -1), ("mapping-address-overflow", (1 << 63) - 1),
            ("mapping-outside-16-bit", 65536)):
        machine = ExpectedMachine(lb, rights(), program=[0xa5] * 51, seed=False)

        def mapping(s, address=address):
            error = None if BASE <= address < BASE + 51 else fault(
                "ProgramOutsideSegment", address,
                "strict immutable segment has no zero fallback or prefix")
            s.program_event(address, "DiagnosticProgramProbe", error=error)
            return (0xa5, None) if error is None else (None, error)

        records.append(machine.capture(identifier, mapping))

    for identifier, error in (
            ("invalid-segment-base", fault("InvalidProgramSegment", 0xffffffff,
                "nonempty checked 16-bit address space; no padding")),
            ("invalid-segment-overflow", fault("InvalidProgramSegment", 65535,
                "nonempty checked 16-bit address space; no padding")),
            ("invalid-empty-segment", fault("InvalidProgramSegment", 4096,
                "nonempty checked 16-bit address space; no padding")),
            ("wrong-actual-program-digest", fault("ProgramDigestMismatch", 4096,
                "actual immutable bytes must match exact SHA-256")),
            ("unsupported-sfr-rights", fault("UnsupportedDataPermission", 0x17,
                "no SFR/CPU alias silently represented as RAM")),
            ("invalid-word-constituent-overflow", fault("DataAddressOverflow", 65536,
                "checked constituent address")),
            ("raw-read-widening", fault("RawPermissionWidening", None,
                "raw read/write rights may only be narrowed independently")),
            ("raw-write-widening", fault("RawPermissionWidening", None,
                "raw read/write rights may only be narrowed independently"))):
        records.append(constructor_record(identifier, error))

    for identifier, byte in (("strict-decoder-out-of-range-probe", 0xc4),
                             ("strict-missing-selected-byte", 0xf4)):
        machine = ExpectedMachine(lb, rights(), program=[byte], seed=False)

        def strict(s):
            s.begin()
            return None, s.strict_failed_selection(patterns)

        records.append(machine.capture(identifier, strict))

    for identifier in ("wrong-selected-form-identity", "wrong-selected-operand-identity"):
        machine = ExpectedMachine(lb, observation_protocol.permissions(lb["profile"], "lb-a-page"))

        def wrong(s):
            s.begin()
            s.successful_selection(patterns)
            error = s.latch(fault("SelectedInstructionMismatch", BASE,
                "actual production selection/operands differ from frozen exact identity"))
            return None, error

        records.append(machine.capture(identifier, wrong))

    def denied_read(s):
        s.begin()
        return None, s.denied_data(0x117, 8, "Read", logical_read_fault(0x117))

    records.append(live("lb-a-page", rights()).capture("forbidden-data-read", denied_read))

    def denied_write(s):
        s.begin()
        return None, s.denied_data(0x117, 8, "Write", logical_write_fault(0x117), value=0x55)

    records.append(live("lb-a-page", rights(((0x117, 8),))).capture(
        "forbidden-data-write", denied_write))

    def readonly(s):
        s.begin()
        return None, s.denied_data(0x196, 16, "Write", logical_write_fault(0x196), value=0xbeef)

    records.append(live("cmp-page-imm16", rights(((0x196, 16),))).capture(
        "readonly-data0196-write", readonly))

    def missing_rmw(s, *, diagnostic=False):
        s.begin()
        if diagnostic:
            s.snapshot()
        return None, s.denied_data(0x18e, 8, "Write", rmw_fault(0x18e),
                                   value=0x55 if diagnostic else 0x33)

    rmw_rights = rights(((0x18e, 8),), ((0x18e, 8, True),))
    records.append(live("rolb-page", rmw_rights).capture("rmw-write-without-read", missing_rmw))

    def high_read(s):
        s.begin()
        return None, s.partial_word(0x196)

    records.append(live("cmp-page-imm16", rights(((0x196, 16),), raw_reads=[0x196])).capture(
        "word-high-read-refused", high_read))

    def high_write(s):
        s.begin()
        return None, s.partial_word(0x108, write=True, value=0xbeef)

    records.append(live("cmp-page-imm16", rights((), ((0x108, 16, False),),
                                                raw_reads=[], raw_writes=[0x108])).capture(
        "word-high-write-refused-partial-low", high_write))

    def same_value(s):
        s.begin()
        value = s.successful_data(0x117, 8, "Read")
        s.successful_data(0x117, 8, "Write", value)
        s.successful_data(0x117, 8, "Write", value)
        return {"value": value}, None

    records.append(live("lb-a-page", rights(((0x117, 8),), ((0x117, 8, False),))).capture(
        "same-value-fresh-store-ordinals", same_value))

    def actual_rmw(s):
        s.begin()
        value = s.successful_data(0x18e, 8, "Read")
        s.successful_data(0x18e, 8, "Write", value)
        return {"old": value, "new": value}, None

    records.append(live("rolb-page", rmw_rights).capture("actual-rmw-read-then-write", actual_rmw))

    def le16(s):
        s.begin()
        return s.successful_data(0x196, 16, "Read"), None

    records.append(live("cmp-page-imm16", rights(((0x196, 16),))).capture(
        "actual-le16-logical-and-raw", le16))

    def partial_operand(s):
        s.begin()
        s.successful_selection(patterns)
        s.index = s.request["expected_decoded_index"]
        s.execution_calls = 1
        # The unchanged production execution body increments PC/counters before
        # operands, and a refused read returns zero to that body before its
        # post-run memory fault check. Use the old independent LB rule for the
        # resulting AL/ZF, but retain incoming DD: the post-run transfer is not
        # reached on error. No successful retirement or atomic rollback claim.
        operand = 0x100 + s.request["bytes"][1]
        error = s.denied_data(operand, 8, "Read", logical_read_fault(operand))
        reference_input = deepcopy(s.request)
        reference_input["physical_entry_pc"] = BASE
        reference_input["data"][str(operand)] = 0
        result = historical_reference.reference_effect(reference_input)
        s.cpu = historical_reference.raw_cpu(result["after"], s.request["internal_sf"],
                                             result["cycles"], 1)
        s.cpu["dd"] = s.request["entry"]["dd"]
        return None, error

    records.append(live("lb-a-page", rights()).capture(
        "partial-production-operand-error", partial_operand))

    def after_fault(s):
        s.begin()
        error = s.denied_data(0x117, 8, "Read", logical_read_fault(0x117))
        # begin_step observes the existing latch before phase/decode and still
        # records that the caller made one real step API invocation.
        s.step_calls += 1
        return {"first_error": error, "second_error": deepcopy(error)}, None

    records.append(live("lb-a-page", rights()).capture("execution-after-fault", after_fault))

    j_item = template("j-address")
    for identifier, later in (("fetch-after-real-direct-j-seal", "fetch"),
                              ("extra-retirement-after-budget", "step"),
                              ("data-write-after-seal", "write")):
        machine = ExpectedMachine(j_item, observation_protocol.permissions(j_item["profile"], "j-address"))

        def direct_j(s, later=later):
            s.begin()
            s.successful_selection(patterns)
            s.index = s.request["expected_decoded_index"]
            expected = observation_protocol.expected_case(s.item, patterns)
            s.cpu = deepcopy(expected["after"]["cpu"])
            s.execution_calls = s.retirements = 1
            s.sealed, s.phase = True, "Sealed"
            s.external_exit = s.cpu["pc"]
            s.terminal_reason = "ActualDirectJCompleted"
            error = sealed_fault()
            if later == "fetch":
                s.program_event(s.external_exit, "DiagnosticProgramProbe", error=error,
                                selected_length=s.selected_length)
            else:
                if later == "step":
                    s.step_calls += 1
                else:
                    # The public API guard sees and refuses this real request
                    # before calling Bus. It is not a logical/raw Bus event.
                    s.admission_refusals.append({
                        "ordinal": 0, "classification": "PreBusApiAdmissionRefusal",
                        "phase": "Sealed", "pc": s.cpu["pc"], "address": 0x117,
                        "width": 8, "operation": "Write", "requested_value": 0x55,
                        "production_bus_called": False, "serviced": False,
                        "refusal": deepcopy(error)})
                s.latch(error)
            return {"actual_retirement": expected["outcome"], "later_result": None,
                    "later_error": error}, None

        records.append(machine.capture(identifier, direct_j))

    def late_seed(s):
        s.begin()
        return None, s.latch(fault("SeedOutsideSetup", 0x117,
                                   "single initialization phase only"))

    records.append(live("lb-a-page", rights()).capture("seed-after-functional-refused", late_seed))
    records.append(live("rolb-page", rmw_rights).capture(
        "diagnostic-not-rmw-read", lambda s: missing_rmw(s, diagnostic=True)))

    actual_ids = tuple(row["id"] for row in records)
    if actual_ids != CAPABILITY_IDS or len(records) != 35:
        raise ValueError("CapabilityExpectedClosedInventoryMismatch")
    return {"kind": "capability_observations", "records": records,
            "opaque_51_byte_canary_is_m2bj": False, "opaque_canary_executions": 0,
            "full_production_composite_executions": 0, "original_rom_executions": 0,
            "firmware_ready": False}


def compare(expected, actual):
    """Strict recursive comparator: exact scalar types/keys/array order."""
    return observation_protocol.difference(expected, actual)
