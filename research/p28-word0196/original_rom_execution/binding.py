"""Bounded pre-runtime working-source join to the immutable M2bs Git tree.

No archive inventory, source normalization, ROM opening or CPU execution occurs.
Three previously sealed local XML representations can be retained explicitly;
they are never claimed to be byte-identical to Git or to affect Rust execution.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path

from original_rom_execution import source_guard as guard

ROOT = Path(__file__).resolve().parents[3]
# Exact physical alternatives from the immutable M2bs scoped receipt400428a...,
# not new expected values inferred from a current working-tree difference.
PHYSICAL_REPRESENTATIONS = {
    "src/HondaEcu.Cli/HondaEcu.Cli.csproj": (
        "b5e9372b53d8836656780a395a17584d50df0007d128b37815874afd19fb561d", 705,
        "2ad76dfce17ac60cb5ce90dfaff6cd0170d9c54b7784850fd27e819a9a3bacc2"),
    "src/HondaEcu.Core/HondaEcu.Core.csproj": (
        "b540adba501c839ec1d75143e106dfb9dd5593d9ff7cdd036af82c25c9387053", 218,
        "e151f959964eb450a5b86b72765e3f9c505645fa9516eae485743d2b43911c8e"),
    "tests/HondaEcu.Cli.Tests/HondaEcu.Cli.Tests.csproj": (
        "e9868bd94f0fcfd57b3efefd967a23717318a6087b80145d238fbd74288330a4", 867,
        "7b0bfab120eb271a0cd67a0ec2f850c00881a21b3a47b681023e8b225bd032a7"),
}


def working_source_join(root=ROOT, *, allow_saved_physical=False):
    root = Path(root).resolve()
    inventory = guard.tree(root, guard.BASE)
    guard.need(len(inventory) == guard.BASE_SOURCE_COUNT, "ExactM2bsSourceMembership")
    blobs = guard.contents(root, (inventory,))
    base = {name: guard.Blob(mode, blobs[oid]) for name, (mode, oid) in inventory.items()}
    changes = guard.RUST_DELTA_PATHS | {guard.WORKFLOW}
    active, physical_exceptions = {}, []
    for name in sorted(set(base) | guard.NEW_PATHS):
        path = root / name
        guard.need(not path.is_symlink() and path.is_file()
                   and path.resolve() == path, "PhysicalSourcePathRequired")
        raw = path.read_bytes()
        guard.need(len(raw) <= guard._OLD.MAX_BLOB_BYTES,
                   "BoundedWorkingSourceBlob")
        if name in changes or name in guard.NEW_PATHS:
            active[name] = guard.Blob("100644", raw)
        else:
            expected = base[name]
            if raw != expected.data:
                alternative = PHYSICAL_REPRESENTATIONS.get(name)
                observed = (sha256(expected.data).hexdigest(), len(raw), sha256(raw).hexdigest())
                guard.need(allow_saved_physical is True and alternative == observed,
                           "UnreviewedPhysicalBaselineDifference:" + name)
                physical_exceptions.append({"path": name, "bytes": len(raw),
                                            "sha256": observed[2],
                                            "rawGitSha256": observed[0],
                                            "classification": "RetainedM2bsPhysicalXml_NotRustInput"})
            active[name] = expected
    result = guard.compare_trees(base, active)
    dirty = guard.git(root, "diff", "--name-only", "HEAD").decode("utf-8").splitlines()
    guard.need(set(dirty) <= changes | guard.NEW_PATHS, "UnrelatedTrackedSourceChanges")
    result.update({"schemaVersion": 1, "milestone": "M2bt", "exactBase": guard.BASE,
                   "classification": "PreRuntimeWorkingSourceJoin_NotCommittedOrCpuProof",
                   "gitRawBaseAndExplicitCurrentSources": True,
                   "retainedPhysicalRepresentations": physical_exceptions,
                   "physicalWorkingTreeMatchesRawSourceBindings": not physical_exceptions,
                   "sourceNormalizationOrHistoricalManifestRewrite": False})
    return result
