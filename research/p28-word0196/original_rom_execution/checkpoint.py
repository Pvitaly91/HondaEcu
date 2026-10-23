"""Atomic source-bound milestone checkpoint and immutable JSON receipt helpers.

This module has no CPU, ROM, network or automatic scheduling capability.
"""
from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
import tempfile


class CheckpointError(ValueError):
    """Incomplete or mismatched saved state must never authorize a resume."""


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8") + b"\n"


def atomic_json(path, value, *, replace=False):
    """Publish a complete fsynced JSON object, never a partially written target.

    Replacement is explicit and reserved for the mutable checkpoint. Immutable
    receipts use no-replace publication: Windows rename or POSIX hard link.
    """
    path = Path(path)
    if path.is_symlink():
        raise CheckpointError("OutputSymlinkRefused")
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = canonical(value)
    descriptor, temporary = tempfile.mkstemp(prefix=".m2bt-json-", dir=path.parent)
    temporary = Path(temporary)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        if replace:
            os.replace(temporary, path)
        elif os.name == "nt":
            # Windows rename is atomic and refuses an existing destination.
            # Unlike hard links it also works in restricted Windows workspaces.
            os.rename(temporary, path)
        else:
            os.link(temporary, path)
        return {"bytes": len(encoded), "sha256": sha256(encoded).hexdigest()}
    finally:
        if temporary.exists():
            temporary.unlink()


def read_checkpoint(path, *, fingerprint=None, corpus_sha256=None):
    """Require complete canonical JSON and matching source/corpus before resume."""
    raw = Path(path).read_bytes()
    try:
        value = json.loads(raw)
    except (ValueError, UnicodeError) as error:
        raise CheckpointError("IncompleteCheckpoint") from error
    if not isinstance(value, dict) or canonical(value) != raw:
        raise CheckpointError("NoncanonicalCheckpoint")
    if value.get("milestone") != "M2bt" or value.get("schemaVersion") != 1:
        raise CheckpointError("WrongCheckpointIdentity")
    if fingerprint is not None and value.get("sourceFingerprint") != fingerprint:
        raise CheckpointError("SourceFingerprintChanged")
    if corpus_sha256 is not None and value.get("corpusSha256") != corpus_sha256:
        raise CheckpointError("CorpusIdentityChanged")
    return value
