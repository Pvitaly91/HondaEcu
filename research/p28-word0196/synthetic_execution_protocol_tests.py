"""Independent M2bk static protocol tests; no CPU or byte-stream execution.

Expected values come from the separately authored reference oracle and literal
reviewed C11/IR facts below, never from analyzer output.  A trace is a proposed
static expectation, not an observation of any ECU or synthetic CPU run.
"""
import ast
import copy
import hashlib
import json
import sys
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

import synthetic_execution_protocol_analysis as analysis
import synthetic_execution_protocol_oracle as oracle


WORDS = (0, 191, 192, 193, 255, 256, 65535)
PATHS = {
    "A": (21871, 21873, 21874, 21877, 21878, 21880, 21885,
          21951, 21953, 21955, "DirectJ_Below"),
    "B": (21871, 21873, 21874, 21877, 21878, 21880, 21885,
          21887, 21890, 21893, 21906, 21908, "DirectJ_NotBelow"),
    "C": (21871, 21873, 21874, 21877, 21878, 21880, 21885,
          21887, 21890, 21893, 21896, 21906, 21908, "DirectJ_NotBelow"),
    "D": (21871, 21873, 21874, 21877, 21878, 21880, 21885,
          21887, 21890, 21893, 21896, 21899, 21902, 21906, 21908,
          "DirectJ_NotBelow"),
}
COUNTS = {"A": (11, 5, 3, 21957), "B": (13, 9, 3, 21910),
          "C": (14, 10, 3, 21910), "D": (16, 12, 5, 21910)}
NODES = {
    21871: (4096, 2, "lb-a-page"),
    21873: (4098, 1, "sllb-a"),
    21874: (4099, 3, "rolb-page"),
    21877: (4102, 1, "lb-a-r0"),
    21878: (4103, 2, "andb-a-page"),
    21880: (4105, 5, "cmp-page-imm16"),
    21885: (4110, 2, "jlt-rel8"),
    21887: (4112, 3, "movb-r1-page"),
    21890: (4115, 3, "andb-page-a"),
    21893: (4118, 3, "jbs-page-bit7"),
    21896: (4121, 3, "jbs-page-bit5"),
    21899: (4124, 3, "andb-page-a"),
    21902: (4127, 4, "orb-page-imm8"),
    21906: (4131, 2, "lb-a-page"),
    21908: (4133, 2, "orb-a-imm8"),
    "DirectJ_NotBelow": (4135, 3, "j-address"),
    21951: (4138, 2, "lb-a-imm8"),
    21953: (4140, 2, "stb-a-page"),
    21955: (4142, 2, "stb-a-page"),
    "DirectJ_Below": (4144, 3, "j-address"),
}
DATA_KEYS = ("0108", "0109", "010A", "010B", "010C", "010D", "010E", "010F",
             "0117", "0124", "0128", "012A", "018E", "018F", "0196", "0197")
WRITE_IDS = {"A": (21874, 21953, 21955), "B": (21874, 21887, 21890),
             "C": (21874, 21887, 21890),
             "D": (21874, 21887, 21890, 21899, 21902)}
READ_IDS = {"A": (21871, 21874, 21877, 21878, 21880),
            "B": (21871, 21874, 21877, 21878, 21880, 21887, 21890, 21893, 21906),
            "C": (21871, 21874, 21877, 21878, 21880, 21887, 21890, 21893,
                  21896, 21906),
            "D": (21871, 21874, 21877, 21878, 21880, 21887, 21890, 21893,
                  21896, 21899, 21902, 21906)}
PROVENANCE = "InventedOnly_NoNativeGenerationOwner"
EXPECTED_CLASS = "StaticExpectedTrace_NoExecutionObservation"


def check(condition, label):
    if not condition:
        raise AssertionError(label)  # Fixed metadata only, never machine bytes.


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=True).encode()).hexdigest()


def _no_io(*args, **kwargs):
    raise AssertionError("Static protocol attempted forbidden execution or I/O")


def invoke(function, *args):
    """Pure call guard: filesystem/process/CPU APIs are not part of this API."""
    before = digest(args)
    with ExitStack() as stack:
        for name in ("builtins.open", "pathlib.Path.open", "os.open", "os.system",
                     "subprocess.run", "subprocess.Popen"):
            stack.enter_context(patch(name, _no_io))
        result = function(*args)
    check(digest(args) == before, "Caller inputs must remain unchanged")
    return result


def path_for(scenario):
    data = scenario["data"]
    word = data["0196"] + 256 * data["0197"]
    return "A" if word < 192 else "B" if data["012A"] & 128 else \
        "C" if data["0124"] & 32 else "D"


def manual_assertions(scenario, case):
    """Literal reviewed obligations, independent of analyzer implementation."""
    path = path_for(scenario)
    insns, reads, writes, target = COUNTS[path]
    data, entry = scenario["data"], scenario["entry"]
    check(case["classification"] == EXPECTED_CLASS and case["path"] == path,
          "Static classification and independently selected path")
    check(case["scenarioId"] == scenario["id"], "Scenario identity")
    check((case["instructionCount"], case["readCount"], case["writeCount"],
           case["terminalPc"]) == (insns, reads, writes, target),
          "Literal path counts and terminal target")
    check(case["originalInstructionCount"] == insns - 1, "Exactly one added direct J")
    check(case["directJCount"] == 1, "Exactly one expected external transfer")
    check(case["actualSyntheticExecution"] == "NotRun" and
          case["externalExitObservation"] == "SyntheticExternalExitObservationNotRun",
          "Expected protocol never claims runtime evidence")
    check(case["historicalPathWitness"] ==
          ("StaticPrimaryAndInventedCoverage" if path == "C" else
           "HistoricalCorpusHasOriginalPathWitness_NotNewObservation"),
          "Path C must not acquire historical native witnesses")
    check(tuple(step["logicalId"] for step in case["trace"]) == PATHS[path],
          "Literal instruction path, including direct J")
    check(tuple(row["logicalId"] for row in case["orderedReads"]) == READ_IDS[path],
          "Literal read order and short-circuit suppression")
    check(tuple(row["logicalId"] for row in case["orderedWrites"]) == WRITE_IDS[path],
          "Literal write order, including same-value writes")
    check(case["orderedReads"] == [row for step in case["trace"] for row in step["dataReads"]]
          and case["orderedWrites"] ==
          [row for step in case["trace"] for row in step["dataWrites"]],
          "Flattened effects retain order and completeness")
    check(len(case["trace"]) == insns and len(case["programFetches"]) == insns,
          "Bounded trace and selected PROGRAM extents")
    check(len(case["orderedReads"]) == reads and len(case["orderedWrites"]) == writes,
          "Effect counts are actual list lengths")
    check(tuple(sorted(case["terminalData"])) == DATA_KEYS, "Closed DATA inventory")
    rotated = ((data["018E"] << 1) | (data["018E"] >> 7)) & 255
    mask = data["0108"] & rotated
    expected_data = copy.deepcopy(data)
    expected_data["018E"] = rotated
    if path == "A":
        expected_data["0117"] = expected_data["018F"] = 15
        final_al = 15
    else:
        expected_data["0109"] = data["0117"]
        expected_data["0117"] = data["0117"] & mask
        if path == "D":
            expected_data["018F"] = data["018F"] & mask
            expected_data["012A"] = data["012A"] | 1
        final_al = expected_data["018F"] | 240
    check(case["terminalData"] == expected_data, "Independent closed-form RAM result")
    terminal = case["terminalState"]
    check((terminal["pc"], terminal["al"], terminal["ah"], terminal["a"], terminal["cf"],
           terminal["zf"], terminal["dd"]) ==
          (target, final_al, entry["ah"], (entry["a"] & 65280) | final_al,
           int(path == "A"), 0, 0), "Independent terminal A/CF/ZF/DD result")
    check(terminal["locals"] == [expected_data[key] for key in DATA_KEYS[:8]],
          "Physical local byte aliases")
    check(terminal["er"] == [terminal["locals"][2 * n] +
                              256 * terminal["locals"][2 * n + 1] for n in range(4)],
          "Little-endian local word aliases")
    previous = case["entryState"]
    check(previous["pc"] == 4096 and previous["dd"] == entry["dd"],
          "Entry PC and incoming DD are explicit")
    for ordinal, step in enumerate(case["trace"], 1):
        pc, length, form = NODES[step["logicalId"]]
        check((step["step"], step["syntheticPc"], step["length"], step["form"])
              == (ordinal, pc, length, form), "Literal boundary and exact form")
        check(step["stateBefore"] == previous and step["stateBefore"]["pc"] == pc,
              "Contiguous typed state transitions")
        previous = step["stateAfter"]
        for key in ("ah", "hc", "otherPsw", "lrb", "scb", "ssp", "pointingBanks", "sf", "halted"):
            check(previous[key] == entry[key], "Retained context: " + key)
        check(previous["dd"] == 0, "First LB establishes DD0 for every later step")
        check(step["provenance"] == PROVENANCE, "Invented trace provenance")
        fetch = case["programFetches"][ordinal - 1]
        check(fetch == {"step": ordinal, "space": "PROGRAM", "start": pc,
                        "endExclusive": pc + length,
                        "classification": "ExpectedSelectedInstructionExtent_NotObserved"},
              "Selected extent is an expectation, not a fetch observation")
        check(4096 <= fetch["start"] < fetch["endExclusive"] <= 4147,
              "No expected continuation fetch or PROGRAM padding")
    check(previous == terminal, "Terminal state is the last expected transition")
    for row in case["orderedReads"]:
        check(row["space"] == "DATA" and row["provenance"] == PROVENANCE,
              "Read space and provenance")
        check(row["address"] != 192, "Code-owned00C0 is never DATA read")
        if row["logicalId"] == 21880:
            check(row["address"] == 406 and row["widthBits"] == 16 and
                  row["bytes"] == [data["0196"], data["0197"]] and
                  row["value"] == data["0196"] + 256 * data["0197"],
                  "Word CMP reads0196 little-endian independently of DD")
    for ordinal, row in enumerate(case["orderedWrites"], 1):
        check(row["ordinal"] == ordinal and row["widthBits"] == 8 and
              row["space"] == "DATA" and row["provenance"] == PROVENANCE,
              "Fresh ordered byte-write identity")
        check(row["sameValue"] == (row["oldValue"] == row["value"]),
              "Same-value write is retained, not silently elided")
    if path == "B":
        check(all(row["address"] != 292 for row in case["orderedReads"]),
              "First JBS taken suppresses every DATA0124 read")
    first_rol = next(step for step in case["trace"] if step["logicalId"] == 21874)
    check(first_rol["stateBefore"]["cf"] == data["018E"] >> 7 and
          first_rol["dataWrites"][0]["value"] == rotated,
          "SLL-to-ROL carry dependency, not unrelated incoming CF")
    direct = case["trace"][-1]
    check(direct["externalTransfer"] == "AbstractExternalContinuation_ExpectedOnly" and
          direct["branchTaken"] is None and not direct["dataReads"] and
          not direct["dataWrites"], "Direct J has no stack or DATA effects")
    for key in direct["stateBefore"]:
        if key != "pc":
            check(direct["stateBefore"][key] == direct["stateAfter"][key],
                  "Direct J preserves all non-PC state")


def _step(case, logical_id):
    return next(step for step in case["trace"] if step["logicalId"] == logical_id)


def _refusal(function, args, label):
    before = digest(args)
    caught = []
    for _ in range(2):
        try:
            invoke(function, *args)
        except analysis.ProtocolError as error:
            record = {"code": error.code, "location": error.location, "stage": error.stage}
            check(all(type(value) is str and value for value in record.values()),
                  "Closed deterministic error identity: " + label)
            check(not hasattr(error, "expected_case") and not hasattr(error, "trace") and
                  not hasattr(error, "encoded_bytes"), "No partial success or machine payload")
            caught.append(record)
        else:
            raise AssertionError("Required refusal missing: " + label)
    check(caught[0] == caught[1] and digest(args) == before,
          "Atomic repeatable refusal and caller preservation: " + label)
    return {"category": label, **caught[0]}


def _trace_negative(ir, composition, contract, scenario, label, mutate):
    expected = invoke(oracle.reference_case, scenario)
    proposed = copy.deepcopy(expected)
    mutate(proposed)
    check(proposed != expected, "Negative must change the proposed semantic object: " + label)
    return _refusal(analysis.validate_expected_trace,
                    (ir, composition, contract, scenario, proposed), label)


def _assert_ast_safe(tree):
    forbidden = {"subprocess", "ctypes", "cffi", "socket", "requests", "urllib", "importlib"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            check(not any(alias.name.split(".")[0] in forbidden for alias in node.names),
                  "No process, CPU, native or network imports")
        if isinstance(node, ast.ImportFrom):
            check((node.module or "").split(".")[0] not in forbidden,
                  "No process, CPU, native or network imports")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            check(node.func.id not in {"eval", "exec", "compile", "__import__", "open"},
                  "No dynamic evaluation or unbounded filesystem calls")


def _source_policy():
    """Static source boundary guard; never use production Rust as an oracle."""
    findings = []
    for module in (analysis, oracle):
        source = Path(module.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        _assert_ast_safe(tree)
        if module is oracle:
            check("synthetic_execution_protocol_analysis" not in source,
                  "Reference oracle cannot import analyzer")
        findings.append({"file": Path(module.__file__).name,
                         "sha256": hashlib.sha256(source.encode()).hexdigest(),
                         "cpuInvocations": 0})
    fixtures = ("import subprocess", "import ctypes", "from socket import socket",
                "eval('1')", "exec('x=1')", "__import__('ctypes')", "open('not-opened')")
    for source in fixtures:
        # Malicious fixtures are syntax trees only: never compile/eval/exec/import.
        try:
            _assert_ast_safe(ast.parse(source))
        except AssertionError:
            pass
        else:
            raise AssertionError("AST-only source-policy fixture must be refused")
    findings.append({"classification": "AstParseOnlyForbiddenSourceFixtures",
                     "refusals": len(fixtures), "executedFixtures": 0})
    return findings


def _sync_effects(case):
    case["orderedReads"] = [row for step in case["trace"] for row in step["dataReads"]]
    case["orderedWrites"] = [row for step in case["trace"] for row in step["dataWrites"]]
    case["readCount"], case["writeCount"] = len(case["orderedReads"]), len(case["orderedWrites"])


def _set_data(scenario, **values):
    scenario["data"].update(values)
    local = [scenario["data"][key] for key in DATA_KEYS[:8]]
    scenario["localAliases"] = {"r": local,
                                "er": [local[2*n] + 256*local[2*n+1] for n in range(4)]}


def _carry_and_same_value_controls(ir, composition, contract):
    scenarios = []
    for value in (0, 128, 255):
        for incoming_cf in (0, 1):
            scenario = oracle.make_scenario(192, 128, 0, 1, 0)
            scenario["id"] = "carry-control-" + str(value) + "-" + str(incoming_cf)
            scenario["entry"]["cf"] = incoming_cf
            scenario["entry"]["psw"] = ((scenario["entry"]["psw"] & 32767) |
                                          (incoming_cf << 15))
            _set_data(scenario, **{"018E": value})
            scenarios.append(scenario)
    same_a = oracle.make_scenario(0, 0, 0, 0, 0)
    same_a["id"] = "same-value-below-stores"
    _set_data(same_a, **{"018E": 0, "0117": 15, "018F": 15})
    scenarios.append(same_a)
    same_d = oracle.make_scenario(192, 0, 0, 1, 0)
    same_d["id"] = "same-value-all-five-writers"
    _set_data(same_d, **{"0108": 255, "0109": 255, "018E": 255,
                         "0117": 255, "018F": 255, "012A": 1})
    scenarios.append(same_d)
    controls = []
    for scenario in scenarios:
        expected = invoke(oracle.reference_case, scenario)
        manual_assertions(scenario, expected)
        actual = invoke(analysis.analyze_protocol, ir, composition, contract, scenario)
        check(actual == expected, "Independent carry/same-value expected-case equality")
        if scenario["id"] == "same-value-all-five-writers":
            check(all(row["sameValue"] for row in expected["orderedWrites"]),
                  "All five same-value write events are retained")
        if scenario["id"] == "same-value-below-stores":
            check(all(row["sameValue"] for row in expected["orderedWrites"]),
                  "Same-value ROL and both constant stores remain fresh events")
        controls.append({"id": scenario["id"], "path": expected["path"],
                         "expectedDigest": digest(expected), "exactEquality": True,
                         "sameValueWrites": sum(row["sameValue"] for row in expected["orderedWrites"])})
    check(len(controls) == 8, "Bounded independent carry and same-value controls")
    return controls, same_a


def _negative_tests(ir, composition, contract):
    controls, same_a = _carry_and_same_value_controls(ir, composition, contract)
    scenarios = {"A": oracle.make_scenario(0, 0, 0, 0, 0),
                 "B": oracle.make_scenario(192, 128, 0, 1, 1),
                 "C": oracle.make_scenario(192, 0, 32, 0, 2),
                 "D": oracle.make_scenario(192, 0, 0, 1, 3),
                 "Signed": oracle.make_scenario(65535, 0, 0, 0, 0)}
    semantic, metadata = [], []

    def input_negative(label, mutate, domain="TypedInput", metadata_only=False):
        scenario = copy.deepcopy(scenarios["D"])
        mutate(scenario)
        row = _refusal(analysis.analyze_protocol, (ir, composition, contract, scenario), label)
        row["domain"] = domain
        (metadata if metadata_only else semantic).append(row)

    def trace_negative(label, path, mutate, domain="ExpectedStateOrEffect", metadata_only=False):
        scenario = same_a if path == "SameA" else scenarios[path]
        row = _trace_negative(ir, composition, contract, scenario, label, mutate)
        row["domain"] = domain
        (metadata if metadata_only else semantic).append(row)

    input_negative("IncorrectEntryPc", lambda s: s["entry"].__setitem__("pc", 4097))
    input_negative("WrongLrb", lambda s: s["entry"].__setitem__("lrb", 32))
    input_negative("WrongScbDerivation", lambda s: s["entry"].__setitem__("scb", (s["entry"]["scb"] + 1) % 8))
    input_negative("InventedSfSemantics", lambda s: s["entry"].__setitem__(
        "sf", {"status": "InventedKnownNativeMeaning", "value": 0}), "AuthorityClaim", True)
    input_negative("RegisterAliasMismatch", lambda s: s["localAliases"]["er"].__setitem__(
        0, s["localAliases"]["er"][0] ^ 256))

    trace_negative("MissingAhPreservation", "D", lambda c: _step(c, 21871)["stateAfter"].__setitem__(
        "ah", _step(c, 21871)["stateAfter"]["ah"] ^ 1))
    trace_negative("SspModification", "D", lambda c: _step(c, 21874)["stateAfter"].__setitem__(
        "ssp", _step(c, 21874)["stateAfter"]["ssp"] ^ 2))

    def alignment(case):
        _step(case, 21880)["dataReads"][0]["address"] = 407
        _sync_effects(case)
    trace_negative("WrongDataWordAlignment", "D", alignment, "DataAddressWidth")

    def extra_read(case, logical, address, space="DATA"):
        step = _step(case, logical)
        step["dataReads"].append({"step": step["step"], "logicalId": logical,
                                  "syntheticPc": step["syntheticPc"], "space": space,
                                  "address": address, "widthBits": 8, "value": 0,
                                  "bytes": [0], "provenance": PROVENANCE})
        _sync_effects(case)
    trace_negative("Immediate00C0TreatedAsRam", "D", lambda c: extra_read(c, 21880, 192),
                   "DataAddressWidth")

    def wrong_space(case):
        _step(case, 21880)["dataReads"][0]["space"] = "PROGRAM"
        _sync_effects(case)
    trace_negative("ProgramDataSpaceConfusion", "D", wrong_space, "AddressSpace")

    def compare_carry(case):
        state = _step(case, 21880)["stateAfter"]
        state["cf"] ^= 1
        state["psw"] ^= 32768
    trace_negative("IncorrectCmpSignedness", "Signed", compare_carry, "UnsignedWordComparison")
    trace_negative("CarryInversion", "A", compare_carry, "CarryDependency")
    trace_negative("JltWrongFlag", "D", lambda c: _step(c, 21885).__setitem__(
        "branchTaken", True), "ControlFlow")  # Word00C0: ZF1, CF0; JLT must not use ZF.

    def omit_rol_carry(case):
        step = _step(case, 21874)
        old = step["dataReads"][0]["value"]
        check(old & 128, "ROL negative requires preceding SLL carry1")
        step["dataWrites"][0]["value"] = (old << 1) & 255
        step["dataWrites"][0]["sameValue"] = old == ((old << 1) & 255)
        _sync_effects(case)
    rol_scenario = copy.deepcopy(scenarios["D"])
    _set_data(rol_scenario, **{"018E": 128})
    rol_row = _trace_negative(ir, composition, contract, rol_scenario,
                              "RolWithoutIncomingCf", omit_rol_carry)
    semantic.append({**rol_row, "domain": "CarryDependency"})
    trace_negative("FirstGateFalsePositive", "D", lambda c: _step(c, 21893).__setitem__(
        "branchTaken", True), "ControlFlow")
    trace_negative("SecondGateEvaluatedWhenFirstTrue", "B", lambda c: extra_read(c, 21893, 292),
                   "ShortCircuitReadEffect")

    def remove_equal_write(case):
        step = _step(case, 21874)
        check(step["dataWrites"][0]["sameValue"], "Negative requires a genuine same-value store")
        step["dataWrites"].clear()
        _sync_effects(case)
    trace_negative("MissingSameValueWrite", "SameA", remove_equal_write, "OrderedWriteEffect")

    def swap_writes(case):
        case["orderedWrites"][0], case["orderedWrites"][1] = \
            case["orderedWrites"][1], case["orderedWrites"][0]
    trace_negative("WrongWriteOrder", "D", swap_writes, "OrderedWriteEffect")

    def remove_rmw(case):
        _step(case, 21890)["dataReads"].clear()
        _sync_effects(case)
    trace_negative("MissingRmw", "D", remove_rmw, "ReadModifyWriteEffect")
    trace_negative("UnexpectedDataRead", "D", lambda c: extra_read(c, 21871, 296),
                   "DataInventory")

    def extra_writer(case):
        step = _step(case, 21880)
        step["dataWrites"].append({"step": step["step"], "logicalId": 21880,
                                   "syntheticPc": step["syntheticPc"], "space": "DATA",
                                   "address": 406, "widthBits": 8, "oldValue": 192,
                                   "value": 193, "ordinal": 2, "sameValue": False,
                                   "kind": "Store", "provenance": PROVENANCE})
        _sync_effects(case)
    trace_negative("ExtraDataWriter", "D", extra_writer, "DataInventory")

    def change_terminal(case, target):
        case["trace"][-1]["stateAfter"]["pc"] = target
        case["terminalState"]["pc"] = target
        case["terminalPc"] = target
    trace_negative("JTargetsSwapped", "A", lambda c: change_terminal(c, 21910), "ControlFlow")
    trace_negative("JFallsThrough", "D", lambda c: change_terminal(c, 4138), "ControlFlow")

    def external_fetch(case):
        case["programFetches"].append({"step": len(case["trace"]) + 1,
                                       "space": "PROGRAM", "start": 21910,
                                       "endExclusive": 21911,
                                       "classification": "ExpectedSelectedInstructionExtent_NotObserved"})
    trace_negative("FetchAfterExternalJ", "D", external_fetch, "ExitTrapFetchBoundary")
    trace_negative("InfiniteLoop", "D", lambda c: _step(c, 21885)["stateAfter"].__setitem__(
        "pc", 4110), "ControlFlow")
    trace_negative("PathCFalselyHistoricalNative", "C", lambda c: c.__setitem__(
        "historicalPathWitness", "HistoricalNativeValidated"), "AuthorityClaim", True)
    trace_negative("SyntheticTraceClaimedActualEcu", "D", lambda c: c.__setitem__(
        "classification", "ActualECUExecutionObserved"), "AuthorityClaim", True)
    trace_negative("RuntimeEvidenceClaimedFromJson", "D", lambda c: c.__setitem__(
        "actualSyntheticExecution", "VerifiedFromJson"), "AuthorityClaim", True)
    _contract_negative_tests(ir, composition, contract, scenarios["D"], semantic, metadata)
    categories = [row["category"] for row in semantic + metadata]
    check(len(categories) == 36 and len(set(categories)) == 36,
          "Exactly36 distinct mandatory negative categories")
    return semantic, metadata, controls


def _contract_negative_tests(ir, composition, contract, scenario, semantic, metadata):
    mutations = (
        ("WrongSyntheticBase", "ProgramGeometry", False,
         lambda c: c["program"].update(base=4097, endExclusive=4148)),
        ("WrongCompositeSha", "SourceIdentity", False,
         lambda c: c["program"].__setitem__("sha256", "0" * 64)),
        ("WrongProgramLength", "ProgramGeometry", False,
         lambda c: c["program"].update(length=52, endExclusive=4148)),
        ("MissingDdVariant", "ContextDomain", False,
         lambda c: c["entryContexts"].__setitem__("incomingDD", [0])),
        ("InstructionBudgetOverrun", "BoundedControlFlow", False,
         lambda c: c["instructionBudget"].update(maximum=15, safetyBound=15)),
        ("OriginalRomExecutionClaimed", "AuthorityClaim", True,
         lambda c: c["authority"].__setitem__("actualRomExecutions", 1)),
        ("UnknownProgramMapDeclaredVerified", "AuthorityClaim", True,
         lambda c: c["program"].__setitem__("mappingCapability", "SyntheticProgramMappingVerified")),
        ("FirmwareReadyPromotion", "AuthorityClaim", True,
         lambda c: c["authority"].__setitem__("firmwareReady", True)),
    )
    for label, domain, metadata_only, mutate in mutations:
        proposed = copy.deepcopy(contract)
        mutate(proposed)
        check(proposed != contract, "Contract mutation must materially change an input")
        row = _refusal(analysis.analyze_protocol, (ir, composition, proposed, scenario), label)
        row["domain"] = domain
        (metadata if metadata_only else semantic).append(row)


def _reviewed_model_negative_tests(ir, composition, contract):
    """Supplemental semantic/CFG input corruption, not metadata relabeling."""
    scenario = oracle.make_scenario(192, 0, 0, 0, 0)
    rows = []

    def mutate_ir(label, pc, change):
        proposed = copy.deepcopy(ir)
        instruction = next(node for node in proposed["instructions"] if node["pc"] == pc)
        change(instruction)
        check(proposed != ir, "Reviewed IR corruption must change a semantic input")
        row = _refusal(analysis.analyze_protocol, (proposed, composition, contract, scenario), label)
        rows.append({**row, "domain": "ReviewedIrSemanticOrCfgInput"})

    mutate_ir("ReviewedIrAhDestruction", 21871,
              lambda n: n["effects"][0].__setitem__("preserveHighByte", False))
    mutate_ir("ReviewedIrLostCmpCarry", 21880,
              lambda n: n.__setitem__("flagsWritten", ["ZF"]))
    mutate_ir("ReviewedIrWrongJltSource", 21885,
              lambda n: n.__setitem__("flagsRead", ["ZF"]))
    mutate_ir("ReviewedIrMissingRolCarryInput", 21874,
              lambda n: n.__setitem__("flagsRead", []))
    mutate_ir("ReviewedIrLoopBackedge", 21885,
              lambda n: n.__setitem__("successors", [21885, 21887]))
    mutate_ir("ReviewedIrEagerSecondGate", 21893,
              lambda n: n.__setitem__("successors", [21896, 21896]))
    return rows


def run_tests(ir, composition, contract):
    """Run bounded static expected-state/trace proofs, never target execution."""
    source_policy = _source_policy()
    cases = []
    coverage = {path: 0 for path in PATHS}
    variant_states = set()
    for word in WORDS:
        for gate_a in (0, 128):
            for gate_b in (0, 32):
                for dd in (0, 1):
                    for variant in range(4):
                        scenario = oracle.make_scenario(word, gate_a, gate_b, dd, variant)
                        check(scenario["classification"] == PROVENANCE and
                              scenario["entry"]["dd"] == dd, "Invented scenario context")
                        expected = invoke(oracle.reference_case, scenario)
                        manual_assertions(scenario, expected)
                        actual = invoke(analysis.analyze_protocol, ir, composition, contract, scenario)
                        check(actual == expected, "Whole expected-case equality against independent oracle")
                        check(invoke(analysis.validate_expected_trace, ir, composition, contract,
                                     scenario, expected) == expected,
                              "Complete proposed expected trace accepted without execution")
                        manual_assertions(scenario, actual)
                        coverage[expected["path"]] += 1
                        variant_states.add((scenario["entry"]["ah"], scenario["entry"]["scb"],
                                            scenario["entry"]["hc"], scenario["data"]["018E"]))
                        cases.append({"scenario": scenario["id"], "path": expected["path"],
                                      "dd": dd, "word": word,
                                      "expectedDigest": digest(expected), "exactEquality": True})
    check(len(cases) == 224 and all(coverage.values()), "Closed224-case four-path inventory")
    check(len(variant_states) >= 4, "Independent varied AH/HC/SCB/carry contexts")
    semantic_negatives, metadata_negatives, controls = _negative_tests(ir, composition, contract)
    reviewed_negatives = _reviewed_model_negative_tests(ir, composition, contract)
    return {"milestone": "M2bk", "classification": "StaticProtocolVerification_NoExecutionObservation",
            "passed": True, "failed": 0, "skipped": 0,
            "positiveCases": len(cases), "pathCoverage": coverage,
            "wholeExpectedCaseEquality": len(cases), "positive": cases,
            "semanticNegativeCases": len(semantic_negatives), "semanticNegatives": semantic_negatives,
            "metadataNegativeCases": len(metadata_negatives), "metadataNegatives": metadata_negatives,
            "reviewedModelNegativeCases": len(reviewed_negatives),
            "reviewedModelNegatives": reviewed_negatives,
            "carryAndSameValueControls": controls, "sourcePolicy": source_policy,
            "actualSyntheticExecution": "NotRun", "CPUExecutions": 0, "actualROMExecutions": 0,
            "targetObjects": 0, "targetHEX": 0, "FirmwareBIN": 0,
            "partialOutputs": 0}


def main():
    if len(sys.argv) != 1:
        raise SystemExit("Static tests accept no external paths or execution arguments.")
    root = Path(__file__).resolve().parent
    ir = json.loads((root / "word0196_ir.json").read_text(encoding="utf-8"))
    composition = json.loads((root / "synthetic_composite_contract.json").read_text(encoding="utf-8"))
    contract = json.loads((root / "synthetic_execution_protocol_contract.json").read_text(encoding="utf-8"))
    result = run_tests(ir, composition, contract)
    print("M2BK_PROTOCOL_TESTS_JSON=" + json.dumps(result, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
