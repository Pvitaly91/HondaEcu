"""Closed M2bb research contract, separate from encoder and expected-byte oracle.

This validates reviewed metadata/source bindings only. It never imports the
encoder or oracle, emits instructions, executes target code, downloads a source
package or promotes metadata flags into runtime/admission authority. Actual
synthetic assertions and independent review receipts must precede profile seal.
"""

import sys

sys.dont_write_bytecode = True

import ast
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REVIEWED_PROFILE_SHA256 = "996b362280acf0cd9b115b46e1dcc27274b6dc997b8221350c225743187a99e4"
EXACT_BASE = "4f8ee4cd2c4988ef868d5f51d570a6bb96f57a1e"
EXPECTED_FORM_IDS = (
    "lb-a-page", "sllb-a", "rolb-page", "lb-a-r0", "andb-a-page",
    "cmp-page-imm16", "jlt-rel8", "movb-r1-page", "andb-page-a",
    "jbs-page-bit7", "jbs-page-bit5", "orb-page-imm8", "orb-a-imm8",
    "lb-a-imm8", "stb-a-page",
)
EXPECTED_SOURCE_FILES = ("independent_encoder.py", "independent_encoder_tests.py", "independent_encoder_oracle.py")
ENCODER_IMPORTS = {"__future__", "dataclasses", "enum", "typing"}
FORBIDDEN_CALLS = {"open", "exec", "eval", "compile", "__import__", "input", "print"}
FORBIDDEN_MODULES = {"os", "pathlib", "subprocess", "socket", "urllib", "requests", "ctypes", "importlib", "json", "pickle"}
FROM_SYMBOLS = {
    "__future__": {"annotations"},
    "dataclasses": {"dataclass", "field", "fields", "is_dataclass"},
    "enum": {"Enum", "unique"},
    "typing": {"TypeAlias", "Union", "Tuple", "Final", "TypeGuard", "Literal"},
}
FORBIDDEN_METHODS = {"open", "read", "read_bytes", "read_text", "write", "write_bytes", "write_text",
                     "system", "popen", "run", "Popen", "exec_module", "load", "loads", "dump", "dumps",
                     "__setattr__", "__delattr__"}


def demand(condition, message):
    if not condition:
        raise ValueError(message)


def equal(actual, expected):
    if type(actual) is not type(expected):
        return False
    if isinstance(actual, dict):
        return actual.keys() == expected.keys() and all(equal(actual[k], expected[k]) for k in actual)
    if isinstance(actual, list):
        return len(actual) == len(expected) and all(equal(a, b) for a, b in zip(actual, expected))
    return actual == expected


def reviewed_json_types(value, depth=0):
    demand(depth <= 64, "Profile nesting exceeds bound")
    if type(value) is dict:
        demand(all(type(key) is str for key in value), "Profile keys must be strings")
        for child in value.values():
            reviewed_json_types(child, depth + 1)
    elif type(value) is list:
        for child in value:
            reviewed_json_types(child, depth + 1)
    else:
        demand(type(value) in {str, int, bool, type(None)}, "Non-reviewed JSON type")


def parse_contract(raw):
    demand(type(raw) is bytes and len(raw) <= 1048576, "Bounded UTF8 JSON bytes required")
    def pairs(items):
        result = {}
        for key, value in items:
            demand(key not in result, "Duplicate JSON key")
            result[key] = value
        return result
    def invalid_constant(value):
        raise ValueError("Non-finite JSON constant: " + value)
    return json.loads(raw.decode("utf-8"), object_pairs_hook=pairs, parse_constant=invalid_constant)


def load_contract(path):
    path = Path(path)
    if path.is_dir():
        path = path / "independent_encoder_contract.json"
    demand(path.stat().st_size <= 1048576, "Contract exceeds bound")
    return parse_contract(path.read_bytes())


def profile_digest(record):
    demand(type(record) is dict, "Contract object required")
    reviewed_json_types(record)
    raw = json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
    demand(len(raw) <= 1048576, "Canonical contract exceeds bound")
    return hashlib.sha256(raw).hexdigest()


def audit_encoder_source(raw):
    """Bounded static purity guard, not target semantic proof or arbitrary code runner."""
    demand(type(raw) is bytes and len(raw) <= 131072, "Bounded encoder source required")
    tree = ast.parse(raw.decode("utf-8"), filename="independent_encoder.py")
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                demand(alias.name in ENCODER_IMPORTS and alias.name not in FORBIDDEN_MODULES, "Unreviewed encoder import")
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            demand(node.level == 0 and node.module in ENCODER_IMPORTS, "Unreviewed encoder from-import")
            demand(all(alias.name != "*" for alias in node.names), "Wildcard import refused")
            demand(all(alias.name in FROM_SYMBOLS[node.module] for alias in node.names), "Unreviewed from-import symbol")
            imports.append(node.module)
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            demand(node.func.id not in FORBIDDEN_CALLS, "Encoder file/process/dynamic execution interface refused")
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            demand(node.func.attr not in FORBIDDEN_METHODS, "Encoder I/O/process/serialization/mutation method refused")
        elif isinstance(node, (ast.AsyncFunctionDef, ast.Await, ast.Yield, ast.YieldFrom, ast.Global, ast.Nonlocal)):
            raise ValueError("Encoder stateful/asynchronous interface refused")
    functions = [node.name for node in tree.body if isinstance(node, ast.FunctionDef)]
    demand("encode_instruction" in functions, "Typed encoder function absent")
    classes = {node.name: node for node in tree.body if isinstance(node, ast.ClassDef)}
    required = {"FormId", "ErrorCode", "EncoderRequest", "EncodedInstruction", "ExplicitError",
                "AccumulatorA", "Register0", "Register1", "PageOffset8", "EvenPageOffset8",
                "Immediate8", "Immediate16", "PageBit7", "PageBit5", "TargetPC16"}
    demand(required <= classes.keys(), "Typed encoder API class absent")
    for name in required - {"FormId", "ErrorCode"}:
        decorators = classes[name].decorator_list
        frozen_slots = any(isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                           and node.func.id == "dataclass"
                           and {kw.arg: getattr(kw.value, "value", None) for kw in node.keywords}.get("frozen") is True
                           and {kw.arg: getattr(kw.value, "value", None) for kw in node.keywords}.get("slots") is True
                           for node in decorators)
        demand(frozen_slots, "Typed API must retain frozen slots: " + name)
    return {"pureSourceGuardPassed": True, "imports": sorted(set(imports)),
            "noEncoderOrOracleExecution": True, "notComprehensiveSecurityOrTargetProof": True}


def validate(record, research_directory=HERE):
    demand(profile_digest(record) == REVIEWED_PROFILE_SHA256, "Unreviewed M2bb contract/profile claims")
    demand(equal(record["exactBase"], EXACT_BASE), "Wrong exact base")
    demand(tuple(row["id"] for row in record["exactForms"]) == EXPECTED_FORM_IDS, "Closed15form identities changed")
    demand(equal(record["stage"], "Observed15FormSyntheticEncodingAndIndependentReviewPassed"), "Final observed profile required")
    bindings = record["implementationSourceBindings"]
    demand(type(bindings) is list and tuple(row["file"] for row in bindings) == EXPECTED_SOURCE_FILES,
           "Exact reviewed source bindings required")
    research_directory = Path(research_directory)
    for row in bindings:
        raw = (research_directory / row["file"]).read_bytes()
        demand(len(raw) == row["bytes"] and hashlib.sha256(raw).hexdigest() == row["sha256"], "Source hash/length changed")
        if row["file"] == "independent_encoder.py":
            audit_encoder_source(raw)
    return {"milestone": "M2bb", "domain": "EncoderContract", "passed": True, "forms": 15,
            "stage": record["stage"], "sourceBindingsVerified": True,
            "profileClaimsGrantRuntimeAuthority": False, "runtimeVerified": False,
            "encoderImplemented": True, "actualTargetExecution": "NotObserved",
            "actualRomExecutions": 0, "ASM662Executions": 0, "persistentMachineCodeFiles": 0,
            "targetObjects": 0, "firmwareBin": 0}


def main():
    demand(len(sys.argv) <= 2, "Usage: validate_independent_encoder_contract.py [contract-or-directory]")
    path = Path(sys.argv[1]) if len(sys.argv) == 2 else HERE / "independent_encoder_contract.json"
    record = load_contract(path)
    directory = path if path.is_dir() else path.parent
    print(json.dumps(validate(record, directory), sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, TypeError, OSError, RecursionError, SyntaxError, KeyError) as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1)
