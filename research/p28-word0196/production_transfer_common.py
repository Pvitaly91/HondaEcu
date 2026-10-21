"""M2br private source draft: closed, source-bound research utilities.

No module import starts a process, constructs a target Cpu/Bus, generates a
canonical stream, or writes a file. Retained sources are historical authorities,
not aliases for the new production source graph or actual execution evidence.
"""

from contextlib import contextmanager
from hashlib import sha256
import importlib
from functools import lru_cache
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
BASE_BQ = "d5431f446d1951ee311aedc7961139ba28224a9f"
BASE_BP = "ecc32ea7b65020075f8403a4d4c81cdce4d0f0ad"
BASE_BO = "1ceec589ee8586727fb16a39fd15875444d6feab"
MANUAL_SHA = "f6e423ac0bd15378754e30c35ed426415ec219e360c68e817ab451df72142271"
COMPOSITE_SHA = "91ffb46922def91764f5d4da166ef2cfc9834ed0effcc051d3f97246fa147ab1"
PROVENANCE = "InventedOnly_NoNativeGenerationOwner"
RESEARCH = "research/p28-word0196/"
RAM_BEGIN, RAM_END, RAM_FILL = 0x80, 0x1000, 0xA5
DATA_INVENTORY = tuple(range(0x108, 0x110)) + (0x117, 0x124, 0x128, 0x12A, 0x18E, 0x18F, 0x196, 0x197)
PROFILES = (
    {"role": "Caller", "base": 0x0FF0, "end_exclusive": 0x0FF3,
     "form": "j-address", "target": 0x1000, "immediate": None, "primary_pdf_page": 116},
    {"role": "Composite", "base": 0x1000, "end_exclusive": 0x1033,
     "length": 51, "nodes": 20, "sha256": COMPOSITE_SHA},
    {"role": "ContinuationNotBelow", "base": 0x5596, "end_exclusive": 0x5598,
     "form": "lb-a-imm8", "target": None, "immediate": 0xA5, "primary_pdf_page": 124},
    {"role": "ContinuationBelow", "base": 0x55C5, "end_exclusive": 0x55C7,
     "form": "lb-a-imm8", "target": None, "immediate": 0, "primary_pdf_page": 124},
)

# These immutable M2bq and earlier sources were personally read before authoring
# the new expectations. New execution outputs are never an expectation input.
REFERENCE_PINS = {
    "production_composite_common.py": "249aee8bd4b68166dd8b40ced58f9d7b02c1ed8bc87703c361c4dd9778ff8222",
    "production_composite_corpus.py": "ca6f92fba9fec620e58c607e2576c667073cee1bf5eff3190b90326f0ce6f27c",
    "production_composite_oracle.py": "02393d4c17ff9883a721486e0715bde410686f13f4d2209eab2ed830b45bcc91",
    "production_composite_topology.py": "f6337c8e8694cecb082f8750520ab9475711e3bbe945f09814675b8944196a6b",
    "production_composite_projection.py": "395a5e3f86566111b279491f8cca794d404b398176a255c94ab3d8aa0a468590",
    "production_composite_emission.py": "5983d0452c4d42d6739b5d6198a2bc39bb3995dc16a81d44c8d982f7d4cc3bf6",
    "production_composite_records.py": "30634d7dd469434a9f47415f05b8c98642e9b9352b87c280e05c9d14d139e115",
    "synthetic_composite_execution_corpus.py": "984880103f60c214cc45c6a058ac5bf5aa2c8fa04add7c2131f70fa1f447318d",
    "synthetic_composite_execution_oracle.py": "bfd5bbdd1baa2b1bca04b8d29086b448a9cea6d796195a88aac0ae54786fe54d",
    "synthetic_execution_protocol_oracle.py": "6448541d61e1bdfad9578c73f34260f45271dfb2df0247cfe2fc9072f8e9c4ba",
    "synthetic_composite_primary_oracle.py": "b3aecd90e3ef159b9aeec04ec6a46324a245bdcfb23a5ef80ad8d3d11b921c47",
    "typed_lowering_oracle.py": "2e7b613813e81cf54ea6ee17c378344800022454f8d0074af15ecec586a77e4a",
    "word0196_equivalent.c": "4b189d4ed3e97e0d197f6c558755cf056a89c1dc7122653c5c557e7ab62d76d3",
    "word0196_equivalent.h": "df8da1511708fb29cb747981a959544e549a67a9a982e15586b5c12ce8826f0e",
    "word0196_ir.json": "4fdbd6b7dbdd8f48d5a43e123ca93a33a003c22556a0c40b5296d5f409e085c4",
    "synthetic_composite_emitter.py": "499b250bfe0fd1267fc448eda4375661f81499ca806a8c52ac139c132cda09fc",
    "direct_j_primary_oracle.py": "91793837663e8d0341ce0d4e224fc97e256c549409807ea9b43e8d9266f55f39",
    "independent_encoder_oracle.py": "6575f802c0703da087f1f06fdff095dcf4c4b948b7fe59e8fb35972210cb6361",
    "independent_encoder_design.json": "9403279ed7570f1cb36280954a0f3249d41de2d64ae767b840649b066c625be9",
    "direct_j_contract.json": "1be70eb96f4c75c8f42729f2b41aacc2f43b4923c3db0aacccd1b5bc2a2a8c35",
    "external_continuation_contract.json": "bce975c6427e0ab9294af8227933f0b2553efa13a47b89383f53fc4ac6138660",
}


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def canonical(value):
    return json.dumps(value, ensure_ascii=True, allow_nan=False, sort_keys=True,
                      separators=(",", ":")).encode("ascii")


def bounded_json(raw, limit=16 * 1024 * 1024):
    require(type(raw) is bytes and len(raw) <= limit, "BoundedJsonInput")
    def pairs(items):
        value = {}
        for key, item in items:
            require(key not in value, "DuplicateJsonKey:" + key)
            value[key] = item
        return value
    result = json.loads(raw.decode("utf-8", "strict"), object_pairs_hook=pairs,
                        parse_constant=lambda _: (_ for _ in ()).throw(ValueError("NonFiniteJson")))
    def check(value, depth):
        require(depth <= 64 and type(value) in (dict, list, str, int, bool, type(None)),
                "ClosedPrimitiveJsonDepthAndType")
        if type(value) is dict:
            require(all(type(k) is str for k in value), "JsonStringKeys")
            for item in value.values():
                check(item, depth + 1)
        elif type(value) is list:
            for item in value:
                check(item, depth + 1)
    check(result, 0)
    return result


def first_difference(expected, actual, path="$", depth=0):
    require(depth <= 64, "ComparisonDepth")
    if type(expected) is not type(actual):
        return {"field": path, "reason": "ExactTypeMismatch", "expected": expected, "actual": actual}
    if type(expected) is dict:
        if set(expected) != set(actual):
            return {"field": path, "reason": "ClosedKeysMismatch",
                    "expectedKeys": sorted(expected), "actualKeys": sorted(actual)}
        for key in sorted(expected):
            found = first_difference(expected[key], actual[key], path + "." + key, depth + 1)
            if found is not None:
                return found
    elif type(expected) is list:
        if len(expected) != len(actual):
            return {"field": path, "reason": "OrderedLengthMismatch",
                    "expectedLength": len(expected), "actualLength": len(actual)}
        for index, (left, right) in enumerate(zip(expected, actual)):
            found = first_difference(left, right, path + f"[{index}]", depth + 1)
            if found is not None:
                return found
    elif expected != actual:
        return {"field": path, "reason": "ValueMismatch", "expected": expected, "actual": actual}
    return None


def binding(root, relative):
    require(type(relative) is str and "\\" not in relative, "CanonicalRelativeBinding")
    fragment = Path(relative)
    require(not fragment.is_absolute() and ".." not in fragment.parts, "NoBindingTraversal")
    base = Path(root).resolve()
    path = base / fragment
    resolved = path.resolve(strict=True)
    require(resolved.is_relative_to(base) and resolved == path and path.is_file()
            and not path.is_symlink(), "ClosedRegularBinding:" + relative)
    before = path.stat()
    digest, total = sha256(), 0
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
            total += len(chunk)
    after = path.stat()
    require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
            == (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
            and total == before.st_size and path.resolve(strict=True) == resolved,
            "BindingChangedDuringRead:" + relative)
    return {"path": relative, "bytes": total, "sha256": digest.hexdigest()}


def reference_bindings(root):
    rows = []
    for name, digest in REFERENCE_PINS.items():
        row = binding(root, RESEARCH + name)
        require(row["sha256"] == digest, "ImmutableHistoricalReference:" + name)
        rows.append(row)
    return rows


@contextmanager
def bq_modules(root):
    directory = _verified_reference_directory(str(Path(root).resolve()))
    names = ("production_composite_common", "production_composite_corpus",
             "production_composite_oracle", "production_composite_topology",
             "production_composite_projection", "production_composite_records",
             "production_composite_emission")
    previous = list(sys.path)
    try:
        sys.path.insert(0, str(directory))
        result = {}
        for name in names:
            if name in sys.modules:
                require(Path(sys.modules[name].__file__).resolve() == directory / (name + ".py"),
                        "HistoricalModuleAlias:" + name)
            result[name] = importlib.import_module(name)
        yield result
    finally:
        sys.path[:] = previous


@lru_cache(maxsize=4)
def _verified_reference_directory(root):
    # Cache only admission of immutable source code within one invocation.
    # The driver must FRESHLY bind every reference at freeze/runtime boundaries;
    # changed source can never receive a successful final summary.
    reference_bindings(root)
    return (Path(root).resolve() / RESEARCH).resolve()


def profile_instruction(role):
    """Tiny manufacturer-derived instruction only; never the composite payload."""
    require(role in ("Caller", "ContinuationBelow", "ContinuationNotBelow"), "ClosedTinyProfile")
    return b"\x03\x00\x10" if role == "Caller" else bytes((0x77, 0 if role == "ContinuationBelow" else 0xA5))


def segment_identities():
    result = []
    for profile in PROFILES:
        row = dict(profile)
        if row["role"] != "Composite":
            row["length"] = row["end_exclusive"] - row["base"]
            row["sha256"] = sha256(profile_instruction(row["role"])).hexdigest()
        result.append(row)
    return result
