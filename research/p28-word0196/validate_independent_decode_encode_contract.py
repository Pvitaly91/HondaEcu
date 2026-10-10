"""Independent closed M2bc metadata/source guard, not a decoder or byte oracle.

Only public M2bb types may be imported by the decoder; no inverse encoder logic,
tables, encoder calls or expected-vector generation. Actual observed receipts
must precede a positive profile seal; metadata never grants target execution.
"""
import sys

sys.dont_write_bytecode = True

import ast
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REVIEWED_PROFILE_SHA256 = "b771ba33a97230dd42cc96620c23f6c6cd8e8c3895fc97117de1407492b8e7c3"
EXACT_BASE = "106e66e54bc07340dd62e3f8d206c96ee419d7ed"
DRAFT_STAGE = "DecoderNotImplemented_SpecificationOnly"
VERIFIED_STAGE = "Observed15FormDecodeEncodeCompatibilityVerified"
FORM_IDS = ("lb-a-page", "sllb-a", "rolb-page", "lb-a-r0", "andb-a-page", "cmp-page-imm16",
            "jlt-rel8", "movb-r1-page", "andb-page-a", "jbs-page-bit7", "jbs-page-bit5",
            "orb-page-imm8", "orb-a-imm8", "lb-a-imm8", "stb-a-page")
SHARED_TYPES = {"FormId", "AccumulatorA", "Register0", "Register1", "PageOffset8", "EvenPageOffset8",
                "Immediate8", "Immediate16", "PageBit7", "PageBit5", "TargetPC16"}
FROM_SYMBOLS = {"__future__": {"annotations"}, "dataclasses": {"dataclass", "field"},
                "enum": {"Enum", "unique"}, "typing": {"TypeAlias"}, "independent_encoder": SHARED_TYPES}
FORBIDDEN_NAMES = {"encode_instruction", "_FORM_SHAPES", "FULL_OPCODES", "independent_encoder_oracle",
                   "independent_decoder_primary_oracle", "independent_encoder_tests", "__import__",
                   "exec", "eval", "compile", "open", "input", "print", "globals", "locals", "vars", "getattr", "setattr"}
FORBIDDEN_METHODS = {"open", "read", "read_text", "read_bytes", "write", "write_text", "write_bytes",
                     "run", "system", "popen", "Popen", "exec_module", "__setattr__", "__delattr__"}
FORBIDDEN_REFLECTION = {"__globals__", "__code__", "__closure__", "__dict__", "__mro__", "__subclasses__", "__bases__"}
SOURCE_FILES = ("independent_decoder.py", "independent_decoder_primary_oracle.py", "independent_decoder_tests.py")


def demand(condition, message):
    if not condition:
        raise ValueError(message)


def equal(actual, expected):
    if type(actual) is not type(expected):
        return False
    if isinstance(actual, dict):
        return actual.keys() == expected.keys() and all(equal(actual[key], expected[key]) for key in actual)
    if isinstance(actual, list):
        return len(actual) == len(expected) and all(equal(a, b) for a, b in zip(actual, expected))
    return actual == expected


def reviewed_types(value, depth=0):
    demand(depth <= 64, "Contract nesting exceeds bound")
    if type(value) is dict:
        demand(all(type(key) is str for key in value), "String keys required")
        for child in value.values():
            reviewed_types(child, depth + 1)
    elif type(value) is list:
        for child in value:
            reviewed_types(child, depth + 1)
    else:
        demand(type(value) in {str, int, bool, type(None)}, "Unreviewed JSON type")


def parse_contract(raw):
    demand(type(raw) is bytes and len(raw) <= 1048576, "Bounded UTF8 JSON bytes required")
    def pairs(items):
        result = {}
        for key, value in items:
            demand(key not in result, "Duplicate JSON key")
            result[key] = value
        return result
    def nonfinite(value):
        raise ValueError("Non-finite JSON constant: " + value)
    return json.loads(raw.decode("utf-8"), object_pairs_hook=pairs, parse_constant=nonfinite)


def load_contract(path):
    path = Path(path)
    if path.is_dir():
        path = path / "independent_decode_encode_contract.json"
    demand(path.stat().st_size <= 1048576, "Contract exceeds bound")
    return parse_contract(path.read_bytes())


def profile_digest(record):
    demand(type(record) is dict, "Contract object required")
    reviewed_types(record)
    raw = json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
    demand(len(raw) <= 1048576, "Canonical contract exceeds bound")
    return hashlib.sha256(raw).hexdigest()


def audit_decoder_source(raw):
    """Static dependency/purity guard only; never imports or executes decoder."""
    demand(type(raw) is bytes and len(raw) <= 131072, "Bounded decoder source required")
    tree = ast.parse(raw.decode("utf-8"), filename="independent_decoder.py")
    shared_imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            raise ValueError("Decoder direct module imports refused; reviewed symbols only")
        if isinstance(node, ast.ImportFrom):
            demand(node.level == 0 and node.module in FROM_SYMBOLS, "Unreviewed decoder from-import")
            demand(all(alias.name in FROM_SYMBOLS[node.module] and alias.asname is None for alias in node.names),
                   "Unreviewed, wildcard or aliased decoder import")
            if node.module == "independent_encoder":
                shared_imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.Name):
            demand(node.id not in FORBIDDEN_NAMES, "Forbidden inverse encoder/dynamic/I/O dependency")
        elif isinstance(node, ast.Attribute):
            demand(node.attr not in FORBIDDEN_NAMES, "Forbidden qualified encoder/table dependency")
            demand(node.attr not in FORBIDDEN_REFLECTION | FORBIDDEN_METHODS, "Decoder reflection/I/O alias refused")
        elif isinstance(node, ast.Constant) and type(node.value) is str:
            demand(node.value not in {"encode_instruction", "_FORM_SHAPES", "FULL_OPCODES"} | FORBIDDEN_REFLECTION,
                   "Decoder indirect inverse-encoding/reflection lookup refused")
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            demand(node.func.attr not in FORBIDDEN_METHODS, "Decoder state/I/O/process method refused")
        elif isinstance(node, (ast.AsyncFunctionDef, ast.Await, ast.Yield, ast.YieldFrom, ast.Global, ast.Nonlocal)):
            raise ValueError("Decoder stateful/asynchronous interface refused")
    demand(len(shared_imports) == 11 and set(shared_imports) == SHARED_TYPES, "Exactly11 shared type imports required")
    functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
    demand("decode_instruction" in functions, "Pure typed decoder function absent")
    classes = {node.name: node for node in tree.body if isinstance(node, ast.ClassDef)}
    required = {"DecoderRequest", "DecodedInstruction", "ExplicitDecodeError", "DecodeErrorCode",
                "DecodeInputClassification", "DDEffect"}
    demand(required <= classes.keys(), "Decoder typed API class absent")
    for name in ("DecoderRequest", "DecodedInstruction", "ExplicitDecodeError"):
        decorators = classes[name].decorator_list
        frozen_slots = any(isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "dataclass"
                           and {kw.arg: getattr(kw.value, "value", None) for kw in node.keywords}.get("frozen") is True
                           and {kw.arg: getattr(kw.value, "value", None) for kw in node.keywords}.get("slots") is True
                           for node in decorators)
        demand(frozen_slots, "Decoder classes must be frozen/slotted: " + name)
    return {"passed": True, "sharedTypeSymbols": sorted(shared_imports), "encoderFunctionOrTableReferenced": False,
            "decoderOrOracleExecutedByGuard": False, "scope": "StaticDependencyAndPurityGuard_NotComprehensiveSecurityOrISAProof"}


def validate(record, research_directory=HERE):
    demand(profile_digest(record) == REVIEWED_PROFILE_SHA256, "Unreviewed M2bc profile or promoted claims")
    demand(equal(record["exactBase"], EXACT_BASE), "Wrong exact base")
    demand(tuple(row["id"] for row in record["exactForms"]) == FORM_IDS, "Closed15form identities changed")
    directory = Path(research_directory)
    preserved = record["preservedM2bb"]
    for filename, key in (("independent_encoder.py", "encoderSha256"), ("independent_encoder_oracle.py", "encoderOracleSha256"),
                          ("independent_encoder_tests.py", "encoderTestsSha256"), ("independent_encoder_contract.json", "encoderContractSha256"),
                          ("validate_independent_encoder_contract.py", "encoderValidatorSha256")):
        demand(hashlib.sha256((directory / filename).read_bytes()).hexdigest() == preserved[key], "HistoricalM2bb source changed")
    demand(type(record["stage"]) is str and record["stage"] in {DRAFT_STAGE, VERIFIED_STAGE}, "Exact reviewed stage required")
    implemented = record["stage"] == VERIFIED_STAGE
    decoder_guard_passed = False
    if implemented:
        rows = record["decoderSourceBindings"]
        demand(type(rows) is list and tuple(row["file"] for row in rows) == SOURCE_FILES, "Exact own decoder source bindings required")
        for row in rows:
            raw = (directory / row["file"]).read_bytes()
            demand(len(raw) == row["bytes"] and hashlib.sha256(raw).hexdigest() == row["sha256"], "Decoder source hash/length changed")
            if row["file"] == "independent_decoder.py":
                decoder_guard_passed = audit_decoder_source(raw)["passed"] is True
        demand(decoder_guard_passed, "Current decoder static guard failed")
    return {"milestone": "M2bc", "domain": "DecodeEncodeContract", "passed": True, "forms": 15,
            "stage": record["stage"], "decoderImplemented": implemented, "M2bbSourcesPreserved": True,
            "decoderSourceBindingsVerified": implemented, "staticDecoderGuardPassed": decoder_guard_passed,
            "actualTargetExecution": "NotObserved", "runtimePermission": False, "NativeExecutionVerified": False,
            "actualRomExecutions": 0, "ASM662Executions": 0, "persistentMachineCodeFiles": 0,
            "targetObjects": 0, "firmwareBin": 0, "roundTripAloneEstablishesISA": False}


def main():
    demand(len(sys.argv) <= 2, "Usage: validate_independent_decode_encode_contract.py [contract-or-directory]")
    path = Path(sys.argv[1]) if len(sys.argv) == 2 else HERE / "independent_decode_encode_contract.json"
    directory = path if path.is_dir() else path.parent
    print(json.dumps(validate(load_contract(path), directory), sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, TypeError, OSError, KeyError, RecursionError, SyntaxError) as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1)
