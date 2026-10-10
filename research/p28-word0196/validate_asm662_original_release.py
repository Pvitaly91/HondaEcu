"""M2az reviewed static evidence; no downloads, extraction, build or permission.

Invented archive fixtures and gate models are not real release receipts.
The actual profile is pinned to independent private audits, not input assertions.
"""
import io
import json
from pathlib import Path
import re
import sys
import tarfile
import zipfile
import zlib

sys.dont_write_bytecode = True
BASE = "c6cb67cad0d8c207c837648ca6de0ab7bd7ec310"
PIN = "94612d10370eb4ddf97d4f349168298e1a3da8a0"
RELEASES = [
    ("0.9", "asm662 version 0.9", "asm662-0.9.tar.gz", "2003-07-08", 188873,
     "2471660d08fe827af9ed1582354804eb7c16e82775bb8b6e5190317a253e5444", "GzipTar", 56, 48, 0, True),
    ("Win32 1.0", "v1.0 win32", "asm662-win32-v1.0.zip", "2003-07-11", 215910,
     "92a05e8666723c78f77c384c75fd3e98b3c13d11a5dbf5176cacf40865c83638", "ZIP", 7, 7, 2, False),
    ("Win32 1.1", "v1.1 win32", "asm662-win32-v1.1.zip", "2003-07-28", 206013,
     "929d96a336fa8133112741b129ffff2b0ff7b7962a6ddaf4caa8cab54096da93", "ZIP", 2, 2, 2, False),
    ("Win32 1.2", "win32 v1.2", "asm662-win32-v1.2.zip", "2003-10-08", 221582,
     "a9e16ddb146224940ec3588de29d304454b21515eca94575b77051db9349a0ed", "ZIP", 7, 7, 2, False),
]
GATES = ["bytesObserved", "containerVerified", "membersSafe", "sourceComplete",
         "componentLicenseNotices", "docRights", "originalRightsScope", "generatedInputsMatch",
         "rcsCorrespondence", "independentProvenance", "rightsNotProjectInferred", "rightsNotMirrorInferred"]


def demand(condition, message):
    if not condition:
        raise ValueError(message)


def equal(a, b):
    if type(a) is not type(b):
        return False
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(equal(a[k], b[k]) for k in a)
    if isinstance(a, list):
        return len(a) == len(b) and all(equal(x, y) for x, y in zip(a, b))
    return a == b


def profile():
    return {
        "schemaVersion": 1, "milestone": "M2az", "exactBase": BASE,
        "profile": "OfficialASM66209Acquired_Static_ComponentRightsBlocked",
        "releases": [dict(version=v, url="https://sourceforge.net/projects/pgmfi/files/asm662/"
                          + folder.replace(" ", "%20") + "/" + name + "/download",
                          filename=name, documentaryDate=date, bytes=size, sha256=sha,
                          acquired=True, archiveFormat=fmt, integrity="Verified", members=count,
                          regularFiles=files, archivedExecutables=binaries, sourcePresent=source,
                          officialListingChecksums="MD5_SHA1_SHA256Match;SamePublisherNotIndependentLineage",
                          binaryMaterialization=False, execution=False)
                     for v, folder, name, date, size, sha, fmt, count, files, binaries, source in RELEASES],
        "provenance": {"status": "OfficialCurrentDistributionAndCVSMetadataVerified;NoDetachedHistoricalSignatureClaim",
                       "specificUploader": None, "acquisitionManifestSha256": "e28086df3fd5a4c1354901f43c5c825ac61427f34fec08a4d1a9b41c66a784a9"},
        "originalSource": {"identity": "Official0.9_20030708", "originalInputCount": 10,
                           "missingOriginalInputs": 0, "complete": True,
                           "coherence": "BoundedStaticInputAndTRBConsistency;FullRegeneratedEqualityNotVerified",
                           "preloadImplementation": False, "preloadReservedToken": True,
                           "deviceRegisterMap": "NoLater66207RegsHeader;NotDeviceEquivalenceProof",
                           "dependencyManifestSha256": "d2c4a32cc0495e62dc5a2f91131cdecc6cc0d9832ab8626ed794ed932e6adae8",
                           "boundedCoherenceManifestSha256": "830956d04a0dcd02b36cf72b757a69369463b0d42654e16cc23ad33b502a6f23"},
        "licensing": {"OriginalProjectBSDStatementVerified": True,
                      "OriginalReleaseLicenseTextVerified": False,
                      "OriginalReleaseBSDCoverageVerified": False,
                      "author": "Andy Sloane/a1k0n", "exactBsdVariant": None,
                      "ComponentLicenseVerified": "Bison1.75OutputExceptionWithinExactGeneratedFiles;OtherCoverageUnresolved",
                      "ThirdPartyRightsVerified": False, "DocContributionRightsEstablished": False,
                      "MirrorRelicensingAuthorityEstablished": False,
                      "LocalBuildRightsEstablished": False, "PublicRedistributionRightsEstablished": False,
                      "legalProhibitionProved": False,
                      "manifestSha256": "fd0d5f06cc5a689478dfb072a65cb3ec474dc80579bdd634550f3088bd47fea6",
                      "docProvenanceSha256": "cd93ef57f38ef0a47010a278c46ed02a828cfc54d4314e4057ef6a482b632a81"},
        "correspondence": {"m2ayCommit": PIN, "matchedComponents": 32, "byteIdentical": 10,
                           "changed": 22, "mixedRevisionsAllowed": False,
                           "manifestSha256": "9da09ff36190777ab8c72494dbb30ce3d51fd038d39a298410f4f2e8dc93b6bf"},
        "chronology": {"original09": "TRB;NoImplementedPRELOAD;Bison1.75",
                       "preloadIntroduction": "RCSParser1.3_Main1.3_20030711",
                       "tableRename": "RCS1.9_20060205_TRBtoTBR",
                       "m2ayCachedGenerated": "2004TRB;Byacc1.9;NotRegeneratedFor2006Table",
                       "runtimeInference": False,
                       "manifestSha256": "756c7ebcade68415eb39009ef3e91d017185773cd682a3a7e8ca294c62818d52"},
        "security": {"original09": "NoPreloadPath;OtherUnsafeArithmeticDiagnosticsIOAndDDRemain",
                     "m2ayResultUnchanged": "UnsafeExecutionPathConfirmed",
                     "mitigation": "BuildSecurityMitigationDesigned;BuildSecurityMitigationNotImplemented",
                     "preferredPreload": "A_CompletelyDisabled", "patchesApplied": 0,
                     "designSha256": "881b2cd24736e13631ece8eecab92c4cb95193451a64a776d68510e81eb9971f",
                     "sourceFindingsSha256": "a4ffb4af7ac058667499a4829fc5c90307de369363c77cf4e280336ce1005b07"},
        "buildAuthorization": {"status": "ForbiddenInM2az;FuturePrerequisitesUnresolved", "permission": False,
                               "compilerExecuted": False, "generatorExecuted": False, "makeExecuted": False,
                               "builds": 0, "buildLogs": None, "executableSha256": None},
        "runtime": {"status": "AssemblerExecutionNotRun", "runtimeVerified": False,
                    "assemblerExecutions": 0, "actualRomExecutions": 0, "nativeHistoryCreated": False},
        "syntheticOutput": {"status": "AssemblerEncodingNotVerified", "outputs": 0,
                            "generatedFormsCompared": 0, "mismatches": None},
        "firmware": {"ready": False, "status": "TargetCodeGenerationNotReady",
                     "targetBytes": 0, "objects": 0, "firmwareBin": 0},
        "preservation": {"m2av": "BoundedSourceLevelEquivalenceEstablished",
                         "m2aw": "TargetArchitectureContextContractEstablished",
                         "m2ax": "MAC66KAcquisitionResearchBlocked", "m2ay": "ASM662BuildEncodingResearchBlocked",
                         "runner": "0.43.0", "protocol": 1, "fixIdentities": 38,
                         "compilerAbi": "NotEstablished", "wdt3c": "Unresolved", "jgtC8": "Unresolved",
                         "resetCalFullboot": "BlockedNotRun", "m2ah": "STOPbefore5722",
                         "data019b2Owner": "NotEstablished", "strictM2i": "Blocked",
                         "irq": "NotInjected", "timer": "NotModeled", "scheduler": "NotEstablished",
                         "guiHardware": "NotRun", "flash": "PcInspectionOnly/NotFlashReady"},
        "result": {"classification": "M2az Original Source/License ResearchBlocked",
                   "firstBlocker": "DocContributionRightsNotEstablished"},
    }


def validate(record):
    demand(equal(record, profile()), "Not exact reviewed M2az evidence; JSON cannot establish rights or permission")
    return dict(milestone="M2az", passed=True, acquiredArchives=4, original09Acquired=True,
                executionPermission=False, runtimeVerified=False, firmwareReady=False,
                actualAsm662Executions=0, actualBuilds=0, syntheticAssemblerOutputs=0,
                targetBytes=0, actualRomExecutions=0, firmwareBin=0)


def parse_contract(raw):
    demand(type(raw) is bytes and len(raw) <= 65536, "Bounded UTF8 bytes required")
    def pairs(items):
        result = {}
        for key, value in items:
            demand(key not in result, "Duplicate JSON key")
            result[key] = value
        return result
    value = json.loads(raw, object_pairs_hook=pairs,
                       parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Nonfinite number")))
    demand(raw == (json.dumps(value, indent=2) + "\n").encode(), "Canonical UTF8/LF/two-space JSON required")
    return value


def load_contract(path):
    with Path(path).open("rb") as stream:
        return parse_contract(stream.read(65537))


def classify_model(record):
    demand(type(record) is dict and set(record) == {"scope", "gates", "claims"}, "Closed model required")
    demand(record["scope"] == "InventedDocumentaryPolicyModel", "Mock package is not real source acquisition")
    demand(type(record["gates"]) is dict and set(record["gates"]) == set(GATES), "Closed proof prerequisites")
    demand(all(type(v) is bool for v in record["gates"].values()), "Typed boolean model gates")
    demand(equal(record["claims"], {"actualAcquisition": False, "legalApproval": False,
                                   "buildVerified": False, "runtimeVerified": False,
                                   "targetEncodingVerified": False, "nativeHistory": False,
                                   "firmwareReady": False, "mitigationImplemented": False,
                                   "executionPermission": False}), "Model is not actual documentary/runtime authority")
    blockers = [g for g in GATES if not record["gates"][g]]
    return dict(scope="InventedDocumentaryPolicyModel", classification="ModelBlocked" if blockers else
                "ModelPrerequisitesDocumentedNotLegalOrBuildAuthorization", blockers=blockers,
                actualAcquisition=False, legalApproval=False, executionPermission=False,
                runtimeVerified=False, firmwareReady=False)


def safe_path(name):
    demand(type(name) is str and name and "\0" not in name and not name.startswith(("/", "\\"))
           and "\\" not in name and ":" not in name
           and not any(ord(c) < 32 or c in '<>"|?*' for c in name), "Absolute/UNC/drive/ADS/control path")
    pieces = name.rstrip("/").split("/")
    demand(all(p not in {"", ".", ".."} and not p.endswith((".", " "))
               and not re.match(r"^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)", p, re.I)
               for p in pieces), "Traversal/reserved/ambiguous path")
    return "/".join(pieces).casefold()


def inspect_invented_archive(raw):
    """Actual bounded container checks on invented in-memory fixtures only.

    Never writes/extracts files or returns a real release acquisition receipt.
    Strict fixtures reject binaries; historical binary inventories are separate.
    """
    demand(type(raw) is bytes and len(raw) <= 1048576, "Fixture compressed limit")
    try:
        if raw.startswith(b"\x1f\x8b"):
            inflater = zlib.decompressobj(31)
            data = inflater.decompress(raw, 4194305)
            demand(len(data) <= 4194304 and inflater.eof and not inflater.unused_data
                   and not inflater.unconsumed_tail, "Gzip CRC/ISIZE/extent or concatenation failure")
            demand(len(data) % 512 == 0 and len(data) >= 1024 and data[-1024:] == b"\0" * 1024,
                   "TAR extent/end markers")
            archive = tarfile.open(fileobj=io.BytesIO(data), mode="r:")
            members = list(archive)
            kind = "tar"
        elif raw.startswith((b"PK\x03\x04", b"PK\x05\x06")):
            end = raw.rfind(b"PK\x05\x06", max(0, len(raw) - 65557))
            demand(end >= 0 and end + 22 <= len(raw)
                   and end + 22 + int.from_bytes(raw[end + 20:end + 22], "little") == len(raw)
                   and raw[end + 4:end + 8] == b"\0" * 4, "ZIP trailing payload/multidisk/EOCD extent")
            archive = zipfile.ZipFile(io.BytesIO(raw))
            members = archive.infolist()
            demand(int.from_bytes(raw[end + 8:end + 10], "little") == len(members)
                   == int.from_bytes(raw[end + 10:end + 12], "little"), "ZIP EOCD entry count")
            cd_size = int.from_bytes(raw[end + 12:end + 16], "little")
            cd_start = int.from_bytes(raw[end + 16:end + 20], "little")
            demand(cd_start + cd_size == end and archive.start_dir == cd_start,
                   "ZIP central directory extent/prefix")
            zip_cursor = 0
            for entry in sorted(members, key=lambda item: item.header_offset):
                demand(entry.header_offset == zip_cursor and raw[zip_cursor:zip_cursor + 4] == b"PK\x03\x04"
                       and entry.extract_version <= 20, "ZIP prefix/concatenation/unsupported local header")
                header = raw[zip_cursor:zip_cursor + 30]
                demand(len(header) == 30 and int.from_bytes(header[6:8], "little") == entry.flag_bits
                       and not entry.flag_bits & 8 and int.from_bytes(header[8:10], "little") == entry.compress_type
                       and int.from_bytes(header[14:18], "little") == entry.CRC
                       and int.from_bytes(header[18:22], "little") == entry.compress_size
                       and int.from_bytes(header[22:26], "little") == entry.file_size,
                       "ZIP local/central metadata mismatch or data descriptor")
                name_size = int.from_bytes(header[26:28], "little")
                extra_size = int.from_bytes(header[28:30], "little")
                local_name = raw[zip_cursor + 30:zip_cursor + 30 + name_size]
                demand(local_name.decode("utf-8" if entry.flag_bits & 2048 else "cp437") == entry.filename,
                       "ZIP local/central name mismatch")
                zip_cursor += 30 + name_size + extra_size + entry.compress_size
            demand(zip_cursor == cd_start, "Hidden ZIP region before central directory")
            kind = "zip"
        else:
            raise ValueError("HTML/unsupported magic is not an archive")
        demand(0 < len(members) <= 64, "Fixture member count")
        seen, total, tar_end = {}, 0, 0
        with archive:
            for member in members:
                name = member.name if kind == "tar" else member.filename
                canonical = safe_path(name)
                demand(canonical not in seen, "Duplicate/conflicting/case-colliding member")
                if kind == "tar":
                    demand(member.isfile() or member.isdir(), "Symlink/hardlink/device/special member")
                    demand(member.offset == tar_end and member.offset_data == tar_end + 512,
                           "Hidden/extended TAR metadata not supported in strict fixture")
                    tar_end = member.offset_data + ((member.size + 511) // 512) * 512
                    directory, size = member.isdir(), member.size
                else:
                    mode = member.external_attr >> 16
                    demand(mode & 0o170000 in {0, 0o100000, 0o040000} and not member.flag_bits & 1,
                           "ZIP link/special/encrypted member")
                    directory, size = member.is_dir(), member.file_size
                    demand(mode & 0o170000 == 0 or bool(mode & 0o170000 == 0o040000) == directory,
                           "ZIP mode/name directory contradiction")
                demand(all(not canonical.startswith(prior + "/") or is_directory
                           for prior, is_directory in seen.items()), "Parent member is a file")
                demand(directory or not any(prior.startswith(canonical + "/") for prior in seen),
                       "File conflicts with existing child")
                seen[canonical] = directory
                demand(0 <= size <= 1048576, "Fixture individual size")
                total += size
                demand(total <= 4194304, "Fixture expanded size")
                if directory:
                    demand(size == 0, "Directory has payload")
                    continue
                stream = archive.extractfile(member) if kind == "tar" else archive.open(member)
                with stream:
                    content = stream.read(1048577)
                demand(len(content) == size, "Member length/CRC failure")
                demand(not content.startswith((b"MZ", b"\x7fELF", b"PK\x03\x04", b"\x1f\x8b",
                                                b"Rar!", b"7z\xbc\xaf\x27\x1c", b"BZh", b"\xfd7zXZ\0"))
                       and not (len(content) >= 262 and content[257:262] == b"ustar")
                       and not name.lower().endswith((".exe", ".com", ".dll", ".zip", ".gz", ".tar",
                                                      ".tgz", ".7z", ".rar", ".bz2", ".xz")),
                       "Unexpected binary/nested archive fixture")
            if kind == "tar":
                demand(len(data) - tar_end >= 1024 and not any(data[tar_end:]),
                       "Nonzero hidden TAR suffix or absent end markers")
    except (OSError, EOFError, zlib.error, tarfile.TarError, zipfile.BadZipFile) as error:
        raise ValueError("Damaged invented container") from error
    return dict(scope="InventedArchiveSafetyFixture", modelContainerValid=True, members=len(members),
                actualArchivesAcquired=0, executionPermission=False, runtimeVerified=False)


if __name__ == "__main__":
    demand(len(sys.argv) <= 2, "At most one contract path")
    path = Path(sys.argv[1]) if len(sys.argv) == 2 else Path(__file__).with_name("asm662_original_release_contract.json")
    print(json.dumps(validate(load_contract(path)), sort_keys=True))
