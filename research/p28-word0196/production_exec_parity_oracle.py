"""M2bo independent architectural oracle and strict whole-record comparator.

The 16 arithmetic/flag effects below are manufacturer/M2bk/M2av rules checked
against every immutable M2bm literal before any production execution. Frozen
decoder identities and synthetic counters are separate source/table bindings;
neither claims hardware timing. Hidden production journals are never fabricated.
"""

from copy import deepcopy
from hashlib import sha256
from pathlib import Path

import production_exec_parity_corpus as corpus

FORM_IDENTITIES = {
    "lb-a-page": (747, "LB A, off N8", 2),
    "sllb-a": (2198, "SLLB A", 1),
    "rolb-page": (1862, "ROLB off N8", 3),
    "lb-a-r0": (739, "LB A, r0", 1),
    "andb-a-page": (333, "ANDB A, off N8", 2),
    "cmp-page-imm16": (498, "CMP off N8, #N16", 5),
    "jlt-rel8": (719, "JLT rel8", 2),
    "movb-r1-page": (1504, "MOVB r1, off N8", 3),
    "andb-page-a": (349, "ANDB off N8, A", 3),
    "jbs-page-bit7": (716, "JBS off N8.7, rel8", 3),
    "jbs-page-bit5": (714, "JBS off N8.5, rel8", 3),
    "orb-page-imm8": (1678, "ORB off N'8, #N8", 4),
    "orb-a-imm8": (1619, "ORB A, #N8", 2),
    "lb-a-imm8": (738, "LB A, #N8", 2),
    "stb-a-page": (2301, "STB A, off N8", 2),
    "j-address": (684, "J addr16", 3),
}
SOURCE_BINDINGS = {
    "research/p28-word0196/synthetic_composite_execution_oracle.py":
        "bfd5bbdd1baa2b1bca04b8d29086b448a9cea6d796195a88aac0ae54786fe54d",
    "research/p28-word0196/synthetic_execution_protocol_oracle.py":
        "6448541d61e1bdfad9578c73f34260f45271dfb2df0247cfe2fc9072f8e9c4ba",
    "research/p28-word0196/word0196_equivalent.c":
        "4b189d4ed3e97e0d197f6c558755cf056a89c1dc7122653c5c557e7ab62d76d3",
    "research/p28-word0196/word0196_ir.json":
        "4fdbd6b7dbdd8f48d5a43e123ca93a33a003c22556a0c40b5296d5f409e085c4",
    "rust/p28-slice-runner/src/cpu.rs":
        "b12a0b3388a7d34201888a0a6f948263dcf1c7bebca1801056e176d871184d3b",
    "rust/p28-slice-runner/src/decoder.rs":
        "1120cc37cee9ec23f1f596c72ff8dd5bf372204495d2b5e00cc044dfe2ea3aa4",
    "rust/p28-slice-runner/src/full_decoder.rs":
        "77697d4b0e3c90372326156bf1a8544486d07f4aa8f93c67cf9e5f2af6c7eff1",
    "rust/p28-slice-runner/src/bus.rs":
        "556dceff088ecdfac7f05469a03251896c81fdb1979394bdbae4c59e1b30445a",
    "rust/p28-slice-runner/src/exec.rs":
        "e7ef7d04fb28c838b20c52f352c89fc7ea8780d5a2e1d19f7178dec5109324aa",
}
CAPABILITIES = {
    "decoder_callbacks": "ObservationNotAvailable",
    "ordered_data_journal": "ObservationNotAvailable",
    "raw_data_journal": "ObservationNotAvailable",
    "same_value_write_occurrence": "ObservationNotAvailable",
    "program_instruction_fetch_journal": "ObservationNotAvailable",
    "data_final_state": "ObservedByPublicDiagnosticReads",
    "data_permissions": "ProductionDefaultRam_NotIndependentReadWritePolicy",
}
PROJECTION_RULES = {
    "classification": "FullAvailableProductionSingleStepObservation_NoHiddenJournalReconstruction",
    "platformExclusions": [],
    "comparison": "StrictTypes_ExactKeys_OrderedArrays_AllDeclaredFields",
    "ram": {"startInclusive": 128, "endExclusive": 4096, "scratchByte": 165,
            "seedOrder": ["ExplicitScratch", "InventedDataBytes", "All32PointingWordsLE"]},
    "pcRelocation": {"physicalBase": 0, "logicalBase": 4096,
                     "relativeAndFallthrough": "AddLogicalBase", "absoluteDirectJ": "Unchanged"},
    "cpu": "EveryPublicCpuFieldIncludingRawPswOtherAndBothSyntheticCounters",
    "decode": "EveryReturnedDecodedFieldIncludingAllSevenTypedOperandFieldsAndDdOption",
    "stateExpectation": "Manufacturer_M2bk_M2av_Rules_ReproducedAgainstAll51PreResultM2bmLiterals",
    "decoderAndCycleExpectation": "FrozenM2avIR_M2bnIdentityTable_ReviewedDecoderAccounting_NotHardwareTiming",
    "unavailableObservations": deepcopy(CAPABILITIES),
    "sameValueWrites": "ExpectedEffectRetained_FinalStateObserved_WriteOccurrenceNotObservable",
    "physicalSf": "MeaningStorageWidthAndHardwareValueUnknown_InternalBooleanPairedOnly",
    "scope": "MicroprobeScope_NotCompositePathReachability",
    "fullProductionComposite": "NotEstablished",
}


def source_bindings():
    root = Path(__file__).resolve().parents[2]
    result = corpus.source_bindings()
    for relative, expected in SOURCE_BINDINGS.items():
        actual = sha256((root / relative).read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError("IndependentOracleSourceBindingMismatch:" + relative)
        result[relative] = actual
    return result


def _difference(expected, actual, path="$"):
    if type(expected) is not type(actual):
        return {"field": path, "expected": expected, "actual": actual}
    if isinstance(expected, dict):
        if set(expected) != set(actual):
            return {"field": path + ".keys", "expected": sorted(expected), "actual": sorted(actual)}
        for key in sorted(expected):
            result = _difference(expected[key], actual[key], path + "." + key)
            if result is not None:
                return result
    elif isinstance(expected, list):
        if len(expected) != len(actual):
            return {"field": path + ".length", "expected": len(expected), "actual": len(actual)}
        for index, (left, right) in enumerate(zip(expected, actual)):
            result = _difference(left, right, f"{path}[{index}]")
            if result is not None:
                return result
    elif expected != actual:
        return {"field": path, "expected": expected, "actual": actual}
    return None


def compare(expected, actual):
    result = _difference(expected, actual)
    if result is not None:
        result = {"case_id": expected.get("case_id"), "form": expected.get("form"),
                  "decoded_index": (expected.get("decode") or {}).get("index"), **result}
    return result


def validate_request(request):
    """Independent static admission, before any production Cpu is constructed."""
    required = {"case_id", "fixture_id", "family", "form", "bytes", "guards",
                "content_digest", "entry", "data", "internal_sf", "physical_entry_pc",
                "scratch", "budget", "expected_decoded_index", "expected_length"}
    if set(request) != required:
        raise ValueError("RequestFieldsMismatch")
    rows = {row["id"]: row for row in corpus.sealed_cases()}
    row = rows.get(request["fixture_id"])
    if row is None or row["form"] != request["form"]:
        raise ValueError("SealedFixtureFormMismatch")
    if request["bytes"] != [int(value, 16) for value in row["bytesHex"]]:
        raise ValueError("SealedFixtureBytesMismatch")
    length = row["length"]
    if len(request["bytes"]) != length or length != FORM_IDENTITIES[row["form"]][2]:
        raise ValueError("InstructionLengthMismatch")
    if type(request["expected_length"]) is not int or request["expected_length"] != length:
        raise ValueError("DeclaredInstructionLengthMismatch")
    if type(request["expected_decoded_index"]) is not int or request["expected_decoded_index"] != FORM_IDENTITIES[row["form"]][0]:
        raise ValueError("DeclaredDecodedIndexMismatch")
    guards = [0xA5 if index % 2 == 0 else 0x5A for index in range(6 - length)]
    if request["guards"] != guards or request["content_digest"] != sha256(bytes(request["bytes"] + guards)).hexdigest():
        raise ValueError("MicrosegmentDigestOrGuardMismatch")
    entry = request["entry"]
    if not corpus.is_representable(entry["psw"]):
        raise ValueError("NotRepresentableByCurrentCanonicalRustCpu")
    if entry["dd"] and request["form"] in corpus.DD_ZERO_FORMS:
        raise ValueError("ExactFormDdMismatch")
    if request["physical_entry_pc"] != 0 or entry["pc"] != 4096:
        raise ValueError("ExplicitMicroprobePcRelocationRequired")
    if request["budget"] != 1 or request["scratch"] != corpus.SCRATCH:
        raise ValueError("OneStepOrInventedScratchMismatch")
    if type(request["internal_sf"]) is not bool or entry["sf"] != corpus.UNKNOWN_SF:
        raise ValueError("SfUncertaintyRequired")
    if entry["provenance"] != corpus.PROVENANCE or entry["halted"] is not False:
        raise ValueError("InventedEntryRequired")
    expected_data = {str(int(address, 16)) for address in corpus.fixture()["common_data"]}
    if set(request["data"]) != expected_data or any(type(value) is not int or not 0 <= value <= 255 for value in request["data"].values()):
        raise ValueError("InventoriedByteDataRequired")
    check = deepcopy(entry)
    corpus.own_aliases(check, request["data"])
    if _difference(check, entry) is not None:
        raise ValueError("ConflictingCpuOrLocalAliases")
    if entry["lrb"] != 33 or not 0 <= entry["ssp"] <= 65535:
        raise ValueError("LrbOrSspMismatch")
    if len(entry["pointing_banks"]) != 8 or any(set(bank) != {"x1", "x2", "dp", "usp"} or
            any(type(value) is not int or not 0 <= value <= 65535 for value in bank.values())
            for bank in entry["pointing_banks"]):
        raise ValueError("All32PointingWordsRequired")
    return None


def expected_decode(request):
    form, code, dd = request["form"], request["bytes"], request["entry"]["dd"]
    index, mnemonic, length = FORM_IDENTITIES[form]
    fields = {"n8": 0, "n8_alt": 0, "n16": 0, "n16_alt": 0,
              "s8": 0, "addr16": 0, "rel8": 0}
    if form in ("lb-a-page", "andb-a-page", "rolb-page", "movb-r1-page",
                "andb-page-a", "cmp-page-imm16", "stb-a-page"):
        fields["n8"] = code[1]
    if form in ("lb-a-imm8", "orb-a-imm8"):
        fields["n8"] = code[1]
    if form == "orb-page-imm8":
        fields.update(n8_alt=code[1], n8=code[3])
    if form == "cmp-page-imm16":
        fields["n16"] = code[3] + 256 * code[4]
    if form in ("jlt-rel8", "jbs-page-bit7", "jbs-page-bit5"):
        byte = code[-1]
        fields["rel8"] = byte if byte < 128 else byte - 256
        if form != "jlt-rel8":
            fields["n8"] = code[1]
    if form == "j-address":
        fields["addr16"] = code[1] + 256 * code[2]
    transfer = False if form in ("lb-a-page", "lb-a-r0", "lb-a-imm8") else None
    return {"form": form, "mnemonic": mnemonic, "index": index, "len": length,
            "dd_before": dd, "dd_after": dd if transfer is None else transfer,
            **fields, "dd_after_option": transfer, "cycles": 2 * length + int(form == "j-address")}


def reference_effect(request):
    """Independent single-instruction expected effects, not an actual executor."""
    before = deepcopy(request["entry"])
    before["pc"] = request["physical_entry_pc"]
    after, data = deepcopy(before), deepcopy(request["data"])
    decode = expected_decode(request)
    form, al, psw = request["form"], before["al"], before["psw"]
    after["pc"] += decode["len"]
    reads, writes, branch = [], [], None

    def flag(mask, value):
        nonlocal psw
        psw = (psw | mask) if value else (psw & ~mask)

    def read(address, width=8):
        constituents = [data[str(address + index)] for index in range(width // 8)]
        value = sum(byte << (8 * index) for index, byte in enumerate(constituents))
        reads.append([f"{address:04X}", width, f"{value:0{width // 4}X}",
                      [f"{byte:02X}" for byte in constituents]])
        return value

    def write(address, value, kind):
        old = data[str(address)]
        writes.append([f"{address:04X}", f"{old:02X}", f"{value:02X}",
                       len(writes) + 1, kind, old == value])
        data[str(address)] = value

    page = 0x100
    if form in ("lb-a-page", "lb-a-r0", "lb-a-imm8"):
        al = decode["n8"] if form == "lb-a-imm8" else read(0x108 if form == "lb-a-r0" else page + decode["n8"])
        flag(0x4000, al == 0)
        flag(0x1000, False)
    elif form == "sllb-a":
        flag(0x8000, bool(al & 128))
        al = (al << 1) & 255
    elif form == "rolb-page":
        address = page + decode["n8"]
        value = read(address)
        result = ((value << 1) | int(before["cf"])) & 255
        flag(0x8000, bool(value & 128))
        write(address, result, "RMW")
    elif form == "andb-a-page":
        al &= read(page + decode["n8"])
        flag(0x4000, al == 0)
    elif form == "cmp-page-imm16":
        value = read(page + decode["n8"], 16)
        flag(0x8000, value < decode["n16"])
        flag(0x4000, value == decode["n16"])
    elif form == "jlt-rel8":
        branch = before["cf"]
    elif form == "movb-r1-page":
        write(0x109, read(page + decode["n8"]), "LocalRegisterStore")
    elif form == "andb-page-a":
        address = page + decode["n8"]
        result = read(address) & al
        write(address, result, "RMW")
        flag(0x4000, result == 0)
    elif form in ("jbs-page-bit7", "jbs-page-bit5"):
        branch = bool(read(page + decode["n8"]) & (128 if form == "jbs-page-bit7" else 32))
    elif form == "orb-page-imm8":
        address = page + decode["n8_alt"]
        result = read(address) | decode["n8"]
        write(address, result, "RMW")
        flag(0x4000, result == 0)
    elif form == "orb-a-imm8":
        al |= decode["n8"]
        flag(0x4000, al == 0)
    elif form == "stb-a-page":
        write(page + decode["n8"], al, "Store")
    elif form == "j-address":
        after["pc"] = decode["addr16"]
    else:
        raise ValueError("UnreviewedReferenceForm")
    if branch:
        after["pc"] = (after["pc"] + decode["rel8"]) & 65535
    corpus.own_aliases(after, data, (before["a"] & 0xFF00) | al, psw)
    return {"before": before, "after": after, "after_data": data, "reads": reads,
            "writes": writes, "branch": branch, "decode": decode,
            "cycles": decode["cycles"] + (4 if branch else 0)}


def expected_ram(request, data=None):
    ram = [request["scratch"]] * (corpus.RAM_END - corpus.RAM_START)
    for address, value in (request["data"] if data is None else data).items():
        ram[int(address) - corpus.RAM_START] = value
    for bank, row in enumerate(request["entry"]["pointing_banks"]):
        for slot, name in enumerate(("x1", "x2", "dp", "usp")):
            address = bank * 8 + slot * 2
            ram[address], ram[address + 1] = row[name] & 255, row[name] >> 8
    return ram


def raw_cpu(snapshot, sf, cycles=0, instructions=0):
    fields = ("pc", "a", "ssp", "lrb", "zf", "cf", "hc", "dd", "halted")
    return {**{name: snapshot[name] for name in fields}, "sf": sf,
            "psw_other": snapshot["psw"] & 0x0337, "cycles": cycles,
            "instructions": instructions}


def expected_case(request):
    validate_request(request)
    result = reference_effect(request)
    before, after, sf = result["before"], result["after"], request["internal_sf"]
    conditional = result["branch"] is not None
    return {"kind": "production_observation", "accepted": True, "error": None,
            "case_id": request["case_id"], "fixture_id": request["fixture_id"],
            "family": request["family"], "form": request["form"],
            "provenance": corpus.PROVENANCE, "scope": PROJECTION_RULES["scope"],
            "before": before, "after": after, "before_ram": expected_ram(request),
            "after_ram": expected_ram(request, result["after_data"]),
            "ram_range": [corpus.RAM_START, corpus.RAM_END],
            "cpu_before": raw_cpu(before, sf),
            "cpu_after": raw_cpu(after, sf, result["cycles"], 1),
            "decode": result["decode"], "physical_entry_pc": 0, "logical_entry_pc": 4096,
            "pc_relocation": {"physical_base": 0, "logical_base": 4096,
                              "relative_and_fallthrough": "AddLogicalBase",
                              "absolute_direct_j": "PreserveActualAbsoluteTarget"},
            "step_calls": 1, "successful_step_calls": 1, "failed_step_calls": 0,
            "cpu_instances": 1, "bus_instances": 1,
            "internal_sf_before": sf, "internal_sf_after": sf,
            "branch_taken": result["branch"],
            "branch_observation": "DerivedFromObservedPc" if conditional else "NotApplicable",
            "external_transfer": after["pc"] if request["form"] == "j-address" else None,
            "production_program_data_reads": [], "observation_capabilities": deepcopy(CAPABILITIES),
            "production_exec_runtime_observed": True,
            "production_bus_composite_integration": "NotEstablished",
            "original_rom_executions": 0, "production_composite_executions": 0,
            "firmware_ready": False}


def reproduce_sealed_literals():
    """Full independent arithmetic/read/write reproduction of all51 literals."""
    contexts = corpus.build_base_contexts()[:51]
    literals = corpus.sealed_cases()
    for request, literal in zip(contexts, literals):
        validate_request(request)
        result, expected = reference_effect(request), literal["expected"]
        after = result["after"]
        logical_pc = after["pc"] if literal["form"] == "j-address" else after["pc"] + 4096
        actual_literal = {"pc": f"{logical_pc:04X}", "a": f"{after['a']:04X}",
                          "psw": f"{after['psw']:04X}", "reads": result["reads"],
                          "writes": result["writes"], "branchTaken": result["branch"],
                          "external": literal["form"] == "j-address"}
        mismatch = _difference(expected, actual_literal)
        if mismatch:
            return {"case_id": request["case_id"], "form": request["form"], **mismatch}
        # Literal-owned writes additionally build the entire expected RAM and
        # every alias/context field independently of the arithmetic oracle.
        literal_data = deepcopy(request["data"])
        for write in expected["writes"]:
            literal_data[str(int(write[0], 16))] = int(write[2], 16)
        literal_after = deepcopy(result["before"])
        literal_after["pc"] = int(expected["pc"], 16) - (0 if literal["form"] == "j-address" else 4096)
        corpus.own_aliases(literal_after, literal_data, int(expected["a"], 16), int(expected["psw"], 16))
        for field, left, right in (("completeSnapshot", literal_after, after),
                                   ("completeData", literal_data, result["after_data"]),
                                   ("completeRam", expected_ram(request, literal_data),
                                    expected_ram(request, result["after_data"]))):
            mismatch = _difference(left, right, "$." + field)
            if mismatch:
                return {"case_id": request["case_id"], "form": request["form"], **mismatch}
    return None


def expected_capabilities(template=None):
    """Two separate expected failure observations, frozen without executing Cpu.

    These expectations describe source-bound production API limitations, not
    manufacturer semantics or successful microprobe parity. The operand fault
    deliberately uses LRB0 coherent SFR aliases instead of DATA0108 aliases.
    """
    template = corpus.build_corpus()[0] if template is None else template
    validate_request(template)
    records = []
    for mapping in (True, False):
        before = deepcopy(template["entry"])
        psw = 0xECCB if mapping else 0xFCCB
        corpus.own_aliases(before, template["data"], 0xA581, psw)
        before.update(pc=4096 if mapping else 0, lrb=33 if mapping else 0, ssp=0x37A1,
                      halted=False)
        if not mapping:
            before["local_r"] = [0xA1, 0x37, 0, 0, 0xCB, 0xFC, 0x81, 0xA5]
            before["local_er"] = [0x37A1, 0, 0xFCCB, 0xA581]
        after = deepcopy(before)
        if not mapping:
            after.update(pc=2, a=0xA500, al=0)
            after["local_r"] = [0xA1, 0x37, 0, 0, 0xCB, 0xFC, 0, 0xA5]
            after["local_er"] = [0x37A1, 0, 0xFCCB, 0xA500]
        program = [0xA5] * 51 if mapping else [0xF4, 0x17, 0xA5, 0x5A, 0xA5, 0x5A]
        error = {"kind": "MemoryAccess", "space": "code" if mapping else "data",
                 "address": 4096 if mapping else 23, "operation": "fetch" if mapping else "read",
                 "pc": None, "byte": None, "mnemonic": None}
        peeks = [{"address": address, "value": 0xA5 if address < 51 else None,
                  "phase": "ExplicitPublicInspectionBeforeStep",
                  "observation": "NotProductionDecoderCallback"}
                 for address in (0, 50, 51, 4096)] if mapping else []
        records.append({"kind": "capability_observation",
                        "capability_id": "zero-based-program-mapping" if mapping else "non-atomic-data-error",
                        "classification": "SyntheticProgramMappingCapabilityNotEstablished" if mapping
                        else "ProductionErrorStateObserved_NotAtomicRefusal",
                        "positive_parity_case": False, "before": before, "after": after,
                        "before_ram": expected_ram(template), "after_ram": expected_ram(template),
                        "ram_range": [128, 4096], "cpu_before": raw_cpu(before, False),
                        "cpu_after": raw_cpu(after, False, 0 if mapping else 4, 0 if mapping else 1),
                        "program": {"identity": "InventedOpaqueCanary51_NotM2bj" if mapping else
                                    "M2bmFrozenLbPage_F417_GuardsA55AA55A",
                                    "zero_based_rom_length": len(program),
                                    "content_sha256": sha256(bytes(program)).hexdigest(),
                                    "prefix_padding_bytes": 0, "is_m2bj_composite": False},
                        "public_peeks": peeks, "error": error,
                        "step_calls": 1, "successful_step_calls": 0, "failed_step_calls": 1,
                        "cpu_instances": 1, "bus_instances": 1,
                        "instruction_counter_delta": 0 if mapping else 1,
                        "successful_instruction_retirements": 0, "production_program_data_reads": [],
                        "observation_capabilities": deepcopy(CAPABILITIES),
                        "actual_decoder_returned": False, "atomic_refusal_claimed": False,
                        "production_bus_composite_integration": "NotEstablished",
                        "production_composite_executions": 0, "original_rom_executions": 0,
                        "firmware_ready": False})
    return records


def admission_mutations(cases=None):
    """Finite meaningful malformed requests; the real boundary must refuse."""
    cases = corpus.build_corpus() if cases is None else cases
    template = cases[0]
    result = []

    def add(identifier, code, mutate, base=template, rehash=False):
        request = deepcopy(base)
        request["case_id"] = "negative-" + identifier
        mutate(request)
        if rehash:
            request["content_digest"] = sha256(bytes(request["bytes"] + request["guards"])).hexdigest()
        result.append({"id": identifier, "request": request, "expected_error_code": code})

    add("unsupported-form", "MalformedRequest", lambda row: row.update(form="not-a-reviewed-form"))
    sll = next(row for row in cases if row["form"] == "sllb-a")
    add("coherent-wrong-dd", "WrongDdAdmission",
        lambda row: corpus.own_aliases(row["entry"], row["data"], psw=row["entry"]["psw"] | 0x1000), sll)
    add("wrong-length", "WrongInstructionLength", lambda row: row.update(expected_length=5))
    add("wrong-decoded-index", "WrongExpectedDecodedIndex", lambda row: row.update(expected_decoded_index=748))
    add("wrong-opcode", "MicrofixtureBindingMismatch",
        lambda row: row["bytes"].__setitem__(0, row["bytes"][0] ^ 1), rehash=True)
    add("wrong-operand", "MicrofixtureBindingMismatch",
        lambda row: row["bytes"].__setitem__(1, row["bytes"][1] ^ 1), rehash=True)
    add("conflicting-al", "ConflictingCpuAliases", lambda row: row["entry"].update(al=0))
    add("conflicting-ah", "ConflictingCpuAliases", lambda row: row["entry"].update(ah=0))
    add("unsupported-psw", "NotRepresentableByCurrentCanonicalRustCpu",
        lambda row: corpus.own_aliases(row["entry"], row["data"], psw=row["entry"]["psw"] & ~8))
    add("wrong-local-seed", "ConflictingLocalAliases",
        lambda row: row["data"].__setitem__(str(0x108), row["data"][str(0x108)] ^ 1))
    add("wrong-local-r-alias", "ConflictingLocalAliases",
        lambda row: row["entry"]["local_r"].__setitem__(0, row["entry"]["local_r"][0] ^ 1))
    add("wrong-local-er-alias", "ConflictingLocalAliases",
        lambda row: row["entry"]["local_er"].__setitem__(0, row["entry"]["local_er"][0] ^ 256))
    add("wrong-physical-pc", "WrongOneStepScope", lambda row: row.update(physical_entry_pc=4096))
    add("wrong-logical-pc", "WrongOneStepScope", lambda row: row["entry"].update(pc=0))
    add("wrong-budget", "WrongOneStepScope", lambda row: row.update(budget=16))
    add("wrong-lrb", "InvalidEntryScope", lambda row: row["entry"].update(lrb=0))
    add("wrong-scb-alias", "ConflictingCpuAliases", lambda row: row["entry"].update(scb=7))
    add("wrong-otherpsw-alias", "ConflictingCpuAliases", lambda row: row["entry"].update(other_psw=0))
    add("invented-sf-value", "SfUncertaintyRequired", lambda row: row["entry"]["sf"].update(value=True))
    add("invented-sf-meaning", "SfUncertaintyRequired", lambda row: row["entry"]["sf"].update(meaning="invented"))
    add("halted-entry", "InvalidEntryScope", lambda row: row["entry"].update(halted=True))
    add("missing-data", "IncompleteDataInventory", lambda row: row["data"].pop(str(0x117)))
    add("wrong-fixture", "UnknownMicrofixture", lambda row: row.update(fixture_id="not-a-sealed-fixture"))
    add("wrong-guard", "MicrofixtureBindingMismatch",
        lambda row: row["guards"].__setitem__(0, row["guards"][0] ^ 1), rehash=True)
    return result


def _replace_path(value, path, replacement):
    """Copy only ancestors of one leaf; large RAM siblings remain untouched."""
    if not path:
        return replacement
    result = value.copy()
    result[path[0]] = _replace_path(value[path[0]], path[1:], replacement)
    return result


def semantic_mutations(request, actual):
    """Mutate an actual successful record, never manufacture runtime evidence."""
    expected = expected_case(request)
    first = compare(expected, actual)
    if first is not None:
        raise ValueError("SensitivityRequiresAlreadyMatchingActualRecord:" + str(first))
    paths = []
    for name in ("pc", "a", "ssp", "lrb", "zf", "cf", "hc", "dd", "sf",
                 "psw_other", "cycles", "instructions", "halted"):
        paths.append(("cpu_after", name))
    for name in ("pc", "a", "al", "ah", "psw", "cf", "zf", "hc", "dd",
                 "other_psw", "lrb", "scb", "ssp", "halted", "provenance"):
        paths.append(("after", name))
    for name in ("index", "mnemonic", "len", "dd_before", "dd_after", "n8",
                 "n8_alt", "n16", "n16_alt", "s8", "addr16", "rel8",
                 "dd_after_option", "cycles", "form"):
        paths.append(("decode", name))
    paths.extend(("after", "local_r", index) for index in range(8))
    paths.extend(("after", "local_er", index) for index in range(4))
    paths.extend(("after", "pointing_banks", bank, name)
                 for bank in range(8) for name in ("x1", "x2", "dp", "usp"))
    for name in ("before_ram", "after_ram"):
        paths.extend((name, index) for index in (0, 63, 0x108 - 128, 3967))
    paths.extend((name,) for name in ("step_calls", "successful_step_calls", "failed_step_calls",
                                     "cpu_instances", "bus_instances", "internal_sf_before",
                                     "internal_sf_after", "production_exec_runtime_observed",
                                     "production_bus_composite_integration", "original_rom_executions",
                                     "production_composite_executions", "firmware_ready"))
    paths.extend(("observation_capabilities", name) for name in CAPABILITIES)
    paths.append(("pc_relocation", "absolute_direct_j"))
    paths.append(("after", "sf", "meaning"))
    paths.append(("branch_taken",))
    paths.append(("external_transfer",))
    records = []
    for path in paths:
        old = actual
        for key in path:
            old = old[key]
        replacement = (not old if type(old) is bool else old + 1 if type(old) is int
                       else "ControlledSemanticMutation" if old is None else old + "_changed")
        changed = _replace_path(actual, path, replacement)
        mismatch = compare(expected, changed)
        if mismatch is None:
            raise AssertionError("SemanticMutationNotDetected:" + repr(path))
        records.append({"id": "semantic-" + "-".join(map(str, path)), "firstMismatch": mismatch})
    for identifier, altered in (
            ("extra-key", {**actual, "unreviewed_observation": True}),
            ("missing-key", {key: value for key, value in actual.items() if key != "cpu_after"}),
            ("integer-not-boolean", _replace_path(actual, ("after", "cf"), int(actual["after"]["cf"]))),
            ("data-ram-length", _replace_path(actual, ("after_ram",), actual["after_ram"][:-1])),
            ("invented-journal", {**actual, "ordered_data_journal": []})):
        mismatch = compare(expected, altered)
        if mismatch is None:
            raise AssertionError("StructuralMutationNotDetected:" + identifier)
        records.append({"id": identifier, "firstMismatch": mismatch})
    return records
