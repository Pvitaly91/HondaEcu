"""M2bq source draft: bounded, source-bound research utilities; no CPU work.

Loading these helpers never starts a process or generates an expected stream.
The immutable M2bk/M2bn modules are reference sources, not active production
source identities. Their pins must not be rewritten when production changes.
"""

from contextlib import contextmanager
from hashlib import sha256
import importlib
from functools import lru_cache
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True

SCHEMA_VERSION = 1
BASE_SHA = "ecc32ea7b65020075f8403a4d4c81cdce4d0f0ad"
COMPOSITE_SHA = "91ffb46922def91764f5d4da166ef2cfc9834ed0effcc051d3f97246fa147ab1"
PROGRAM_BASE = 0x1000
PROGRAM_END = 0x1033
DATA_INVENTORY = tuple(range(0x108, 0x110)) + (0x117, 0x124, 0x128, 0x12A, 0x18E, 0x18F, 0x196, 0x197)
PROVENANCE = "InventedOnly_NoNativeGenerationOwner"
IMMUTABLE_REFERENCE_PINS = {
    "synthetic_composite_execution_corpus.py": "984880103f60c214cc45c6a058ac5bf5aa2c8fa04add7c2131f70fa1f447318d",
    "synthetic_composite_execution_oracle.py": "bfd5bbdd1baa2b1bca04b8d29086b448a9cea6d796195a88aac0ae54786fe54d",
    "synthetic_execution_protocol_oracle.py": "6448541d61e1bdfad9578c73f34260f45271dfb2df0247cfe2fc9072f8e9c4ba",
    "synthetic_composite_primary_oracle.py": "b3aecd90e3ef159b9aeec04ec6a46324a245bdcfb23a5ef80ad8d3d11b921c47",
    "typed_lowering_oracle.py": "2e7b613813e81cf54ea6ee17c378344800022454f8d0074af15ecec586a77e4a",
    "word0196_equivalent.c": "4b189d4ed3e97e0d197f6c558755cf056a89c1dc7122653c5c557e7ab62d76d3",
    "word0196_equivalent.h": "df8da1511708fb29cb747981a959544e549a67a9a982e15586b5c12ce8826f0e",
    "word0196_ir.json": "4fdbd6b7dbdd8f48d5a43e123ca93a33a003c22556a0c40b5296d5f409e085c4",
    "synthetic_composite_emitter.py": "499b250bfe0fd1267fc448eda4375661f81499ca806a8c52ac139c132cda09fc",
}


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def canonical(value):
    return json.dumps(value, ensure_ascii=True, allow_nan=False, sort_keys=True,
                      separators=(",", ":")).encode("ascii")


def _closed_pairs(rows):
    result = {}
    for key, value in rows:
        require(key not in result, "DuplicateJsonKey:" + key)
        result[key] = value
    return result


def bounded_json(raw, limit=2 * 1024 * 1024):
    require(type(raw) is bytes and len(raw) <= limit, "BoundedJsonByteInput")
    result = json.loads(raw.decode("utf-8", "strict"), object_pairs_hook=_closed_pairs,
                        parse_constant=lambda _: (_ for _ in ()).throw(ValueError("NonFiniteJson")))
    def visit(value, depth):
        require(depth <= 64, "BoundedJsonDepth")
        require(type(value) in (dict, list, str, int, bool, type(None)), "PrimitiveJsonType")
        if type(value) is dict:
            require(all(type(key) is str for key in value), "JsonStringKeys")
            for item in value.values():
                visit(item, depth + 1)
        elif type(value) is list:
            for item in value:
                visit(item, depth + 1)
    visit(result, 0)
    return result


def binding(root, relative):
    require(type(relative) is str and "\\" not in relative, "CanonicalRelativeSourcePath")
    path = Path(relative)
    require(not path.is_absolute() and ".." not in path.parts, "NoSourceTraversal")
    canonical_root = Path(root).resolve()
    absolute = canonical_root / path
    resolved = absolute.resolve(strict=True)
    require(resolved.is_relative_to(canonical_root) and resolved == absolute,
            "BoundSourceMustNotEscapeOrTraverseParentLinks:" + relative)
    require(absolute.is_file() and not absolute.is_symlink(), "RegularBoundSource:" + relative)
    before = absolute.stat()
    digest, size = sha256(), 0
    with absolute.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            size += len(chunk)
            digest.update(chunk)
    after = absolute.stat()
    require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
            == (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
            and size == before.st_size and absolute.resolve(strict=True) == resolved,
            "BoundSourceChangedDuringHash:" + relative)
    return {"path": relative, "bytes": size, "sha256": digest.hexdigest()}


def reference_bindings(root):
    rows = []
    for name, digest in IMMUTABLE_REFERENCE_PINS.items():
        row = binding(root, "research/p28-word0196/" + name)
        require(row["sha256"] == digest, "ImmutableReferenceSourceChanged:" + name)
        rows.append(row)
    return rows


@lru_cache(maxsize=4)
def _verified_reference_directory(root):
    # Cache only immutable reference-code admission within one invocation.
    # The driver freshly verifies the full graph and these pins before and
    # after runtime; a source change can never obtain a successful summary.
    reference_bindings(root)
    return (Path(root).resolve() / "research/p28-word0196").resolve()


@contextmanager
def reference_modules(root):
    """Use only the explicitly pinned old modules; reject a sys.modules alias.

    Their import graph is also bound by the new full source manifest/freeze.
    This utility does not claim the listed old pins bind the new production API.
    """
    directory = _verified_reference_directory(str(Path(root).resolve()))
    names = ("synthetic_composite_execution_corpus", "synthetic_execution_protocol_oracle",
             "synthetic_composite_primary_oracle", "synthetic_composite_execution_oracle")
    old_path = list(sys.path)
    try:
        sys.path.insert(0, str(directory))
        loaded = {}
        for name in names:
            if name in sys.modules:
                require(Path(sys.modules[name].__file__).resolve() == directory / (name + ".py"),
                        "ReferenceModulePathAlias:" + name)
            loaded[name] = importlib.import_module(name)
        yield loaded
    finally:
        sys.path[:] = old_path


def first_difference(expected, actual, path="$", depth=0):
    require(depth <= 64, "ComparisonDepth")
    if type(expected) is not type(actual):
        return {"field": path, "reason": "ExactTypeMismatch", "expected": expected, "actual": actual}
    if type(expected) is dict:
        if set(expected) != set(actual):
            return {"field": path, "reason": "ClosedKeysMismatch",
                    "expectedKeys": sorted(expected), "actualKeys": sorted(actual)}
        for key in sorted(expected):
            difference = first_difference(expected[key], actual[key], path + "." + key, depth + 1)
            if difference is not None:
                return difference
    elif type(expected) is list:
        if len(expected) != len(actual):
            return {"field": path, "reason": "OrderedLengthMismatch",
                    "expectedLength": len(expected), "actualLength": len(actual)}
        for index, (left, right) in enumerate(zip(expected, actual)):
            difference = first_difference(left, right, path + f"[{index}]", depth + 1)
            if difference is not None:
                return difference
    elif expected != actual:
        return {"field": path, "reason": "ValueMismatch", "expected": expected, "actual": actual}
    return None
