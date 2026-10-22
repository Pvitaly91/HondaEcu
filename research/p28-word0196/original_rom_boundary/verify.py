"""Explicit private candidate identity and bounded static extent verification.

No CPU, Bus, target execution, firmware output, archive discovery, networking or
input writes. An original candidate is recognized through separately selected
historical source bindings, not its filename, length or a synthetic byte stream.
"""
from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
import re

from original_rom_boundary.decode import DecodeFailure, decode_extent

ROOT = Path(__file__).resolve().parents[3]
CONTRACT = Path(__file__).with_name("contract.json")
MAX_SOURCE = 64 * 1024 * 1024
STATUSES = (
    "OriginalRomExecutionNotObserved", "ActualNativeDownstreamRejoinNotEstablished",
    "NativeSchedulerNotEstablished", "PhysicalSFNotEstablished",
    "NativeStackSafetyNotEstablished", "PeripheralStateOwnershipNotEstablished",
    "SafeROMPlacementNotEstablished", "TargetProgramEquivalenceNotEstablished",
    "FirmwareIntegrationNotEstablished",
)


class BoundaryError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def need(condition, code):
    if condition is not True:
        raise BoundaryError(code)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii") + b"\n"


def strict_json(raw):
    def pairs(items):
        value = {}
        for key, item in items:
            need(key not in value, "DuplicateJsonKey")
            value[key] = item
        return value
    try:
        return json.loads(raw.decode("utf-8-sig"), object_pairs_hook=pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(
                              BoundaryError("NonfiniteJson")))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise BoundaryError("MalformedJson") from error


def closed(value, keys, code):
    need(type(value) is dict and set(value) == set(keys), code)


def local_path(value):
    name = os.fspath(value)
    need(type(name) is str and not name.startswith(("\\\\", "//"))
         and re.match(r"^[A-Za-z]+://", name) is None, "NetworkSourceRequiresControlledRestore")
    return Path(name)


def file_binding(path):
    candidate = local_path(path).resolve(strict=True)
    with candidate.open("rb") as stream:
        before = os.fstat(stream.fileno())
        need(before.st_size <= MAX_SOURCE, "SelectedSourceSizeBound")
        raw = stream.read(MAX_SOURCE + 1)
        after = os.fstat(stream.fileno())
    need(len(raw) == before.st_size and _stamp(before) == _stamp(after), "SelectedSourceChanged")
    return {"path": str(candidate), "bytes": len(raw), "sha256": sha256(raw).hexdigest()}


def _stamp(stat):
    return stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns


def read_bound(row):
    closed(row, ("path", "bytes", "sha256"), "ClosedSourceBinding")
    need(type(row["path"]) is str and type(row["bytes"]) is int
         and 0 < row["bytes"] <= MAX_SOURCE and type(row["sha256"]) is str
         and re.fullmatch(r"[0-9a-f]{64}", row["sha256"]) is not None,
         "SourceBindingDomain")
    candidate = local_path(row["path"])
    try:
        with candidate.open("rb") as stream:
            before = os.fstat(stream.fileno())
            raw = stream.read(row["bytes"] + 1)
            after = os.fstat(stream.fileno())
        need(_stamp(before) == _stamp(after) and _stamp(after) == _stamp(candidate.stat()),
             "SelectedSourceChanged")
        need(len(raw) == row["bytes"] and sha256(raw).hexdigest() == row["sha256"],
             "SelectedSourceIdentityMismatch")
        return raw
    except OSError as error:
        raise BoundaryError("SelectedSourceUnavailable") from error


class ReadOnlyImage:
    """One bounded immutable snapshot, plus a separate post-validation fence."""
    def __init__(self, path, size, digest):
        need(type(size) is int and size == 32768 and type(digest) is str
             and re.fullmatch(r"[0-9a-f]{64}", digest) is not None, "CandidateIdentityDomain")
        self.path = local_path(path)
        try:
            with self.path.open("rb") as stream:
                self.before = os.fstat(stream.fileno())
                self.data = stream.read(size + 1)
                after = os.fstat(stream.fileno())
            need(_stamp(self.before) == _stamp(after) == _stamp(self.path.stat()),
                 "RomSourceChanged")
        except OSError as error:
            raise BoundaryError("RomInputUnavailable") from error
        need(len(self.data) == size and self.before.st_size == size, "RomSizeMismatch")
        need(sha256(self.data).hexdigest() == digest, "RomSourceIdentityMismatch")
        self.identity = {"bytes": size, "sha256": digest}

    def assert_unchanged(self):
        try:
            with self.path.open("rb") as stream:
                before = os.fstat(stream.fileno())
                raw = stream.read(self.identity["bytes"] + 1)
                after = os.fstat(stream.fileno())
            need(_stamp(self.before) == _stamp(before) == _stamp(after) == _stamp(self.path.stat())
                 and raw == self.data, "RomSourceChanged")
        except OSError as error:
            raise BoundaryError("RomSourceChanged") from error
        return True


def preflight_outputs(rom, output_paths):
    targets = []
    source = local_path(rom).resolve(strict=False)
    for value in output_paths:
        target = local_path(value).resolve(strict=False)
        need(target != source, "OutputWouldOverwriteRom")
        try:
            need(not (target.exists() and source.exists() and os.path.samefile(target, source)),
                 "OutputWouldOverwriteRom")
        except OSError as error:
            raise BoundaryError("OutputAliasNotEstablished") from error
        need(target.suffix.lower() == ".json" and not target.exists(), "FreshJsonOutputRequired")
        need(target not in targets, "OutputAliasesAnotherOutput")
        current = target.parent
        while current != current.parent:
            if current.exists():
                info = current.lstat()
                need(not current.is_symlink() and not getattr(info, "st_file_attributes", 0) & 0x400,
                     "OutputReparseAncestor")
            current = current.parent
        targets.append(target)
    return targets


def load_contract():
    contract = strict_json(CONTRACT.read_bytes())
    need(type(contract["schemaVersion"]) is int and contract["schemaVersion"] == 1 and contract["milestone"] == "M2bs"
         and contract["entryPc"] == 0x556F and contract["stopBeforePcs"] == [0x5596, 0x55C5]
         and len(contract["instructionExtents"]) == 27 and len(contract["algorithmPcs"]) == 18,
         "ClosedNativeScope")
    for binding in contract["sourceBindings"]:
        read_bound({**binding, "path": str(ROOT / binding["path"])})
    return contract


def listing_extents(raw, pcs):
    """Read selected old listing extents only; never infer a whole-ROM decode."""
    result = {}
    pattern = re.compile(r"; ([0-9A-F]{4}) ([01]) [0-9A-F]+ [0-9A-F]+ ([0-9A-F]+)\s*$")
    for line in raw.decode("utf-8", "strict").splitlines():
        match = pattern.search(line)
        if match and int(match[1], 16) in pcs:
            pc = int(match[1], 16)
            need(pc not in result, "DuplicateFrozenListingBoundary")
            payload = bytes.fromhex(match[3])
            result[pc] = {"bytes": payload, "listingDd": int(match[2]),
                          "sha256": sha256(payload).hexdigest()}
    need(set(result) == set(pcs), "MissingFrozenListingBoundary")
    return result


def verify_expected_extent(payload, row, dd):
    need(type(dd) is int and dd in row["allowedIncomingDd"], "ExpectedDdMismatch")
    try:
        actual = decode_extent(payload, row["pc"], dd)
    except DecodeFailure as error:
        raise BoundaryError("InstructionDecodeRefused_" + error.code) from error
    for key in ("pc", "formId", "length", "typedOperands", "successors"):
        need(actual[key] == row[key], "RomInstructionSemanticMismatch_" + key)
    need(actual["nextPc"] == row["pc"] + row["length"], "InstructionNextPcMismatch")
    for key in ("dataReads", "dataWrites"):
        projection = [{name: value[name] for name in ("address", "widthBits")} for value in actual[key]]
        need(projection == row[key], "RomInstructionSemanticMismatch_" + key)
    for wanted, observed in (("flagsRead", "read"), ("flagsWritten", "written"),
                             ("flagsSelectionRead", "selectionRead")):
        need(sorted(row.get(wanted, [])) == sorted(actual["flagEffects"][observed]),
             "RomInstructionSemanticMismatch_" + wanted)
    return actual


def verify_extents(image, contract, frozen=None):
    need(type(image) is bytes, "ImmutableSnapshotRequired")
    inventory = contract["instructionExtents"]
    need(len({row["pc"] for row in inventory}) == len(inventory), "DuplicateInstructionBoundary")
    observed, checks, selected_bytes = [], 0, 0
    for row in inventory:
        pc, length = row["pc"], row["length"]
        need(type(pc) is int and type(length) is int and pc >= 0 and 1 <= length <= 5
             and pc + length <= len(image), "ExtentOutsideImage")
        payload = image[pc:pc + length]
        if frozen is not None:
            need(type(frozen[pc]["listingDd"]) is int
                 and frozen[pc]["listingDd"] in row["allowedIncomingDd"], "FrozenListingDdMismatch")
            need(payload == frozen[pc]["bytes"] and len(payload) == len(frozen[pc]["bytes"]),
                 "ROM_SOURCE_MISMATCH")
        variants = [verify_expected_extent(payload, row, dd) for dd in row["allowedIncomingDd"]]
        checks += len(variants)
        selected_bytes += length
        observed.append({"pc": pc, "length": length, "extentSha256": sha256(payload).hexdigest(),
                         "opcodeFirstByte": payload[0], "interpretations": variants,
                         "listingDd": None if frozen is None else frozen[pc]["listingDd"]})
    return {"passed": True, "instructionExtents": observed, "extentCount": len(observed),
            "ddInterpretationChecks": checks, "selectedInstructionBytes": selected_bytes,
            "instructionExecutionCount": 0}


def verify_cfg(contract, extents):
    rows = {row["pc"]: row for row in contract["instructionExtents"]}
    need(extents["passed"] is True and extents["instructionExecutionCount"] == 0
         and len(extents["instructionExtents"]) == len(rows)
         and {row["pc"] for row in extents["instructionExtents"]} == set(rows),
         "ActualExtentInterpretationsRequiredForCfg")
    for row in extents["instructionExtents"]:
        expected = rows[row["pc"]]
        need(len(row["interpretations"]) == len(expected["allowedIncomingDd"])
             and all(item["successors"] == expected["successors"]
                     and item["formId"] == expected["formId"]
                     and item["length"] == expected["length"] for item in row["interpretations"]),
             "ActualDecodedCfgDiffersFromIndependentExpected")
    algorithm = set(contract["algorithmPcs"])
    need(0x556F in algorithm and set(contract["paths"]) == {"A", "B", "C", "D"}, "NativeCfgScope")
    result = {}
    for name, count in (("A", 10), ("B", 12), ("C", 13), ("D", 15)):
        path = contract["paths"][name]
        need(len(path) == count and len(set(path)) == count and path[0] == 0x556F
             and set(path) <= algorithm, "NativeCfgPathInventory")
        for left, right in zip(path, path[1:]):
            need(right in rows[left]["successors"], "NativeCfgBrokenEdge")
        stop = 0x55C5 if name == "A" else 0x5596
        need(rows[path[-1]]["successors"] == [stop], "NativeCfgStopBeforeMismatch")
        result[name] = {"nativePcs": path, "instructionCount": count, "stopBeforePc": stop,
                        "historicalNativeWitnessClaimedByStaticCfg": False}
    need(set().union(*(set(path) for path in contract["paths"].values())) == algorithm,
         "AllAlgorithmSitesCoveredByStaticPaths")
    need(set(rows[0x5578]["dataReads"][0]) == {"address", "widthBits"}
         and rows[0x5578]["dataReads"] == [{"address": 0x196, "widthBits": 16}],
         "WordCompareNotImmediateDataRead")
    for pc, form in ((0x5596, "andb-zero-a"), (0x55C5, "orb-zero-a")):
        need(rows[pc]["formId"] == form and rows[pc]["dataReads"] == [{"address": 0x24, "widthBits": 8}]
             and rows[pc]["dataWrites"] == [{"address": 0x24, "widthBits": 8}], "FirstPeripheralBoundary")
    return {"passed": True, "paths": result, "entryPc": 0x556F,
            "stopBeforePcs": [0x5596, 0x55C5], "continuationsDecodedOnly": True,
            "continuationInstructionsExecuted": 0, "p2Value": None,
            "nativeFrame": None, "nativeScheduler": None}


def load_profile(path):
    profile = strict_json(local_path(path).read_bytes())
    closed(profile, ("schemaVersion", "milestone", "profileId", "baselineBinding", "dossier",
                     "listing", "historical", "provenanceClassification"), "ClosedPrivateProfile")
    need(type(profile["schemaVersion"]) is int and profile["schemaVersion"] == 1 and profile["milestone"] == "M2bs"
         and profile["profileId"] == "p28-304"
         and profile["provenanceClassification"] == "ArchiveByteContinuityCandidate_FactoryOriginUnknown",
         "WrongCandidateProfile")
    binding = strict_json(read_bound(profile["baselineBinding"]))
    need(binding["formatVersion"] == 1 and binding["profileId"] == "p28-304"
         and binding["modelId"] == "p28-compact-v1" and binding["expectedSize"] == 32768,
         "HistoricalBaselineBindingMismatch")
    dossier = read_bound(profile["dossier"]).decode("utf-8", "strict")
    digest = binding["romHash"]["sha256"].lower()
    need(digest.upper() in dossier.upper() and "unknown origin" in dossier.lower(),
         "DossierSourceContinuityNotEstablished")
    return profile, binding


def verify_original_rom(rom, profile_path):
    profile_before, contract_before = file_binding(profile_path), file_binding(CONTRACT)
    contract = load_contract()
    profile, binding = load_profile(profile_path)
    image = ReadOnlyImage(rom, binding["expectedSize"], binding["romHash"]["sha256"].lower())
    listing = listing_extents(read_bound(profile["listing"]),
                              {row["pc"] for row in contract["instructionExtents"]})
    extents = verify_extents(image.data, contract, listing)
    cfg = verify_cfg(contract, extents)
    from original_rom_boundary.historical import reconcile_historical
    historical = reconcile_historical(profile["historical"], image.identity["sha256"])
    need(historical["passed"] is True, "HistoricalReconciliationFailed")
    selected_fences = [profile[key] for key in ("baselineBinding", "dossier", "listing")]
    selected_fences += list(profile["historical"].values())
    selected_fences += [{**row, "path": str(ROOT / row["path"])} for row in contract["sourceBindings"]]
    for row in selected_fences:
        read_bound(row)
    image.assert_unchanged()
    need(file_binding(profile_path) == profile_before and file_binding(CONTRACT) == contract_before,
         "VerificationInputsChanged")
    public = {"schemaVersion": 1, "milestone": "M2bs", "passed": True,
              "classification": "LocalOriginalRomReadOnlyVerification",
              "romSource": {"identityVerified": True, "factoryAuthenticity": "Unknown",
                            "provenanceClassification": profile["provenanceClassification"]},
              "extentCount": extents["extentCount"], "ddInterpretationChecks": extents["ddInterpretationChecks"],
              "selectedInstructionBytes": extents["selectedInstructionBytes"],
              "extents": [{"pc": row["pc"], "length": row["length"], "sha256": row["extentSha256"],
                           "forms": [value["formId"] for value in row["interpretations"]]}
                          for row in extents["instructionExtents"]],
              "cfg": cfg, "historical": historical["publicSummary"],
              "romUnchanged": True, "originalRomExecutions": 0, "hardwareExecutions": 0,
              "firmwareBinaryObjectHexCount": 0, "firmwareReady": False, "retainedStatuses": list(STATUSES)}
    return {"schemaVersion": 1, "milestone": "M2bs", "passed": True,
            "classification": "LocalOriginalRomReadOnlyVerification_PrivateEvidence",
            "rom": {"path": str(Path(rom).resolve()), **image.identity},
            "profile": profile_before, "sourceBindings": {
                key: profile[key] for key in ("baselineBinding", "dossier", "listing")},
            "contract": contract_before, "extents": extents, "cfg": cfg,
            "historical": historical, "inputBeforeAfterEqual": True,
            "selectedSourceFinalFences": selected_fences,
            "readOnlyMode": "rb_only_CompleteBeforeAfterByteAndIdentityFence",
            "publicSummary": public, "originalRomExecutions": 0,
            "hardwareExecutions": 0, "firmwareReady": False}
