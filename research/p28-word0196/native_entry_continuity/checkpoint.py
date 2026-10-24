"""M2bu checkpoint identity over the unchanged neutral atomic publisher."""
from __future__ import annotations

import json
import os
from pathlib import Path
import stat
import re

from original_rom_execution.checkpoint import canonical, atomic_json as _atomic_json


class CheckpointError(ValueError):
    pass


def local_path(path):
    raw = os.fspath(path)
    if (type(raw) is not str or raw.startswith(("\\\\", "//"))
            or re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", raw) is not None and not re.match(r"^[A-Za-z]:[\\/]", raw)
            or ".." in re.split(r"[\\/]", raw)):
        raise CheckpointError("CheckpointMustBeLocalWithoutSchemeOrTraversal")
    path = Path(os.path.abspath(raw))
    for node in reversed((path, *path.parents)):
        if os.path.lexists(node):
            info = node.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
                raise CheckpointError("CheckpointReparsePathRefused")
    return path.resolve(strict=False)


def atomic_json(path, value, *, replace=False):
    return _atomic_json(local_path(path), value, replace=replace)


def read_checkpoint(path, *, fingerprint=None, corpus_sha256=None):
    raw = local_path(path).read_bytes()
    if len(raw) > 16 * 1024 * 1024:
        raise CheckpointError("CheckpointSizeBound")
    def unique(items):
        result = {}
        for key, value in items:
            if key in result:
                raise CheckpointError("DuplicateCheckpointKey")
            result[key] = value
        return result
    try:
        value = json.loads(raw, object_pairs_hook=unique,
            parse_constant=lambda _: (_ for _ in ()).throw(CheckpointError("NonfiniteCheckpoint")))
    except (ValueError, UnicodeError) as error:
        raise CheckpointError("IncompleteOrInvalidCheckpoint") from error
    if type(value) is not dict or canonical(value) != raw:
        raise CheckpointError("NoncanonicalCheckpoint")
    if value.get("milestone") != "M2bu" or type(value.get("schemaVersion")) is not int or value["schemaVersion"] != 1:
        raise CheckpointError("WrongCheckpointIdentity")
    if fingerprint is not None and value.get("sourceFingerprint") != fingerprint:
        raise CheckpointError("SourceFingerprintChanged")
    if corpus_sha256 is not None and value.get("corpusSha256") != corpus_sha256:
        raise CheckpointError("CorpusIdentityChanged")
    return value
