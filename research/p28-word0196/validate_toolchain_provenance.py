"""Metadata-only M2ax acceptance policy, never a tool loader or execution permit.

The public profile records reviewed documentary evidence and missing artifacts.
It is deliberately closed: a future actual acquisition requires independent
review and a new profile, not editing a status to Verified. The separate model
classifier accepts INVENTED records only. Its results test gate logic; they do
not authenticate bytes, licenses, vendor identity, encodings or native behavior.
No network, archive extraction, executable loading, assembly or ROM is used.
"""

from pathlib import Path
import json
import re
import sys


MAC_URL = "https://datasheet.datasheetarchive.com/originals/library/Datasheets-UEA1/DSAFRAZ0014345.pdf"
MAC_HASH = "ab616efc40babc07d28f44e2e46f8fe53e6c0ddb4edbe948bb02c8ac098b4f2d"
IM_URL = "https://mycomputerninja.com/~jon/www.pgmfi.org/twiki/pub/Library/66kAssemblerDocs/Oki_66201_Instruction_Manual.pdf"
IM_HASH = "f6e423ac0bd15378754e30c35ed426415ec219e360c68e817ab451df72142271"
COMPONENTS = ("RAS66K", "RL66K", "LIB66K", "OH66K", "MP")
FORM_PROFILE = (
    (747, "LB A, off N8", 2, "R", "3-70", ["556F", "5592"]),
    (2198, "SLLB A", 1, "0", "3-144", ["5571"]),
    (1862, "ROLB off N8", 3, "U", "3-120", ["5572"]),
    (739, "LB A, r0", 1, "R", "3-70", ["5575"]),
    (333, "ANDB A, off N8", 2, "0", "3-24", ["5576"]),
    (498, "CMP off N8, #N16", 5, "U", "3-38", ["5578"]),
    (719, "JLT rel8", 2, "U", "3-66", ["557D"]),
    (1504, "MOVB r1, off N8", 3, "U", "3-99", ["557F"]),
    (349, "ANDB off N8, A", 3, "U", "3-25", ["5582", "558B"]),
    (716, "JBS off N8.7, rel8", 3, "U", "3-65", ["5585"]),
    (714, "JBS off N8.5, rel8", 3, "U", "3-65", ["5588"]),
    (1678, "ORB off N'8, #N8", 4, "U", "3-110", ["558E"]),
    (1619, "ORB A, #N8", 2, "0", "3-107", ["5594"]),
    (738, "LB A, #N8", 2, "R", "3-70", ["55BF"]),
    (2301, "STB A, off N8", 2, "0", "3-155", ["55C1", "55C3"]),
)
PERMISSIONS = {
    "archiveToolExecution": False, "targetAssembly": False, "targetObject": False,
    "relocatableObject": False, "absoluteObject": False, "hexOrSRecord": False,
    "firmwareBin": False, "romReplacement": False, "nativeTrampoline": False,
    "productionHarnessUse": False, "hardware": False, "gui": False,
    "vendorMessage": False, "firmwareReady": False,
}
SAFETY = {
    "manualIsSoftwareDistribution": False,
    "searchSnippetIsAcquiredBytes": False,
    "hashEstablishesAuthenticityOrLicense": False,
    "filenameEstablishesDeviceIdentity": False,
    "documentationIsRuntimeOrEncodingProof": False,
    "dclRecognitionIsOpcodeProof": False,
    "asm662IsManufacturerPrimary": False,
    "hostCompilationIsNativeCodeGeneration": False,
    "unknownIsZero": False,
    "rightsUnknownBlocksUse": True,
    "unresolvedIntegrityBlocksAcceptance": True,
    "duplicateBytesAreIndependentSources": False,
    "embeddedTimestampEstablishesVersion": False,
    "crossDeviceDclInterchangeable": False,
    "v2ObjectsCompatibleWithV4": False,
    "repairedOrRepackedArchiveIsOriginalDistribution": False,
    "validatorAuthenticatesExternalClaims": False,
    "classificationGrantsExecutionPermission": False,
}
BLOCKERS = [
    "AuthenticMAC66Kv4DistributionNotAcquired",
    "PackageProvenanceNotEstablished",
    "UsageRightsNotEstablished",
    "ArchiveIntegrityAndCompletenessNotEstablished",
    "VersionMatchedRAS_RL_LIB_OH_MPNotAcquired",
    "M66201DclBytesAndTargetIdentityNotEstablished",
    "DclFormatAndVersionCompatibilityNotEstablished",
    "ReleaseSpecificDependenciesNotEstablished",
    "AssemblerRuntimeNotVerified",
    "ExactGeneratedEncodingNotVerified",
    "GeneratedNativeBehaviorNotVerified",
    "FirmwareIntegrationNotEstablished",
]


def demand(condition, message):
    if not condition:
        raise ValueError(message)


def equal(value, expected):
    if type(value) is not type(expected):
        return False
    if isinstance(value, dict):
        return value.keys() == expected.keys() and all(equal(value[k], expected[k]) for k in value)
    if isinstance(value, list):
        return len(value) == len(expected) and all(equal(a, b) for a, b in zip(value, expected))
    return value == expected


def expect(value, expected, message):
    demand(equal(value, expected), message)


def keys(value, required, message):
    demand(type(value) is dict and set(value) == set(required), message)


def text(value, message):
    demand(type(value) is str and bool(value) and len(value) <= 2048, message)


def choice(value, options, message):
    demand(type(value) is str and value in options, message)


def boolean(value, message):
    demand(type(value) is bool, message)


def digest(value, message):
    demand(type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None, message)


def capability_rows():
    """Independently pinned metadata; no assembler input or opcode bytes."""
    return [
        {"patternIndex": index, "form": form, "instructionLength": length,
         "ddMode": dd, "historicalSites": sites, "primaryInstructionPage": page,
         "documentedAssemblerCapability": "DocumentedSyntaxAndNX8_200CoreSupportOnly",
         "documentarySources": ["MAC1993", "IM1991", "M2AV"],
         "deviceDclSpecificCapability": "NotEstablished",
         "toolRuntimeVerified": False, "exactGeneratedEncodingVerified": False,
         "generatedNativeBehaviorVerified": False,
         "historicalNativeEvidence": "M2avBoundedSourceObservationsUnchanged;NotGeneratedCodeProof"}
        for index, form, length, dd, page, sites in FORM_PROFILE
    ]


def validate(contract):
    keys(contract, {"schemaVersion", "contractKind", "profile", "target", "scope", "sources",
                    "package", "acquisition", "components", "archive", "dcl", "versionCompatibility",
                    "dependencies", "capabilities", "safetyPolicy", "permissions", "result",
                    "preservation"}, "Contract root is not closed M2ax metadata")
    expect(contract["schemaVersion"], 1, "Unsupported schema")
    expect(contract["contractKind"], "ToolchainProvenanceResearchOnly", "Not an execution contract")
    expect(contract["profile"], "MAC66K4_M66201_DocumentationOnly_NoArtifacts", "Unreviewed acquisition profile")
    expect(contract["target"], {"manufacturer": "OKI", "core": "nX-8/200", "device": "MSM66201",
                              "typeDirective": "TYPE(M66201)", "customerAsicApplicability": "NotEstablished",
                              "m66207DclInterchangeability": "NotEstablished"}, "Wrong target or automatic cross-device substitution")
    expect(contract["scope"], {"fragment": "word0196SoftwareAlternate556F", "entryPc": 0x556F,
                             "stopBeforePcs": [0x5596, 0x55C5], "instructionSites": 18, "forms": 15,
                             "actualOriginalRomExecutions": 0, "targetAssemblerExecutions": 0,
                             "targetLinkerExecutions": 0, "targetObjects": 0, "firmwareBin": 0}, "Execution/generation scope promotion")
    expect(contract["sources"], [
        {"id": "MAC1993", "kind": "ManufacturerManual", "document": "E2Y0002-29-62",
         "edition": "ThirdEditionNovember1993", "documentedPackageVersion": "4.XX",
         "url": MAC_URL, "sha256": MAC_HASH,
         "pages": ["1-1", "1-5", "1-7", "2-2", "3-32..3-33", "4-22", "4-23..4-24", "4-242", "5-1..5-32", "7-3..7-12"],
         "scope": "DocumentedCapabilitiesOnly;NotSoftwareDistributionOrRuntimeProof"},
        {"id": "IM1991", "kind": "ManufacturerInstructionManual", "document": "MSM66201InstructionManual",
         "edition": "FirstEditionSeptember1991", "url": IM_URL, "sha256": IM_HASH,
         "scope": "ReviewedInstructionSemanticsOnly;NotToolGeneratedEncodingOrNativeBehaviorProof"},
        {"id": "M2AV", "kind": "RepositoryBoundedHostEquivalence", "document": "docs/M2AV_WORD0196_STRUCTURED_C_EQUIVALENCE.md",
         "scope": "UnchangedHistoricalSourceLevelEquivalence;NotTargetToolchainProof"},
    ], "Evidence substituted, relabeled or promoted")
    expect(contract["package"], {"name": "MAC66K", "documentedVersion": "4.XX", "actualVersion": None,
                               "actualVersionStatus": "NotEstablished", "publisher": "OKI",
                               "distributionOriginalFilename": None, "distributionSha256": None}, "Unknown package identity/version became invented proof")
    expect(contract["acquisition"], {"status": "VendorPackageNotAcquired", "candidateFound": False,
                                   "actualArtifacts": [], "provenanceStatus": "PackageProvenanceNotEstablished",
                                   "usageRights": "UsageRightsNotEstablished",
                                   "license": None, "licenseEvidence": None,
                                   "candidateUrlsAreNotAcquisitionProof": True}, "Candidate/manual/search/unknown license became acquired verified package")
    expect(contract["components"], [
        {"name": name, "status": "NotAcquired", "originalFilename": None, "sha256": None,
         "actualVersion": None, "versionEvidence": None, "objectFormat": None,
         "sourceProvenance": "NotEstablished", "usageRights": "UsageRightsNotEstablished"}
        for name in COMPONENTS
    ], "Missing component, fabricated executable/version or proprietary artifact")
    expect(contract["archive"], {"format": None, "sha256": None, "integrity": "NotEstablished",
                               "crc": "NotEstablished", "completeness": "NotEstablished",
                               "affectedMembers": None, "unaffectedMembers": None,
                               "directoryTraversalCheck": "NotRunNoAcquiredPackage",
                               "duplicates": None, "repaired": False, "repacked": False}, "Archive integrity/completeness asserted without bytes")
    expect(contract["dcl"], {"selectionName": "M66201", "documentaryExpectedFilename": "M66201.DCL",
                           "namingBasis": "TYPEArgumentPlusDotDCL;DocumentedRuleNotObservedFile",
                           "actualFilename": None, "sha256": None,
                           "status": "NotAcquired", "format": None, "formatStatus": "DclFormatNotEstablished",
                           "magic": None, "targetIdentity": None, "targetIdentityStatus": "DclTargetIdentityNotEstablished",
                           "version": None, "versionCompatibility": "NotEstablished",
                           "registerMap": None, "programDataRestrictions": None,
                           "deviceInstructionRestrictions": None, "manufacturerReference": None,
                           "modified": None, "m66207DclAcquired": False,
                           "m66207DclCompatibility": "NotEstablished"}, "Inferred filename/DCL identity/format/map/interchangeability")
    expect(contract["versionCompatibility"], {"status": "PackageVersionMatchIncomplete", "assemblerLinker": "NotEstablished",
                                            "librarianConverter": "NotEstablished", "dclAssembler": "NotEstablished",
                                            "v2AndV4ObjectFormats": "ExplicitlyIncompatible",
                                            "binaryObjectSchema": "NotEstablished"}, "Unproved version/object/DCL match")
    expect(contract["dependencies"], {"documentedRequirement": "MatchingDeviceControlFileRequiredForTYPE",
                                     "documentedDiskFiles": ["RAS66K.EXE", "RL66K.EXE", "LIB66K.EXE", "OH66K.EXE",
                                                             "MP.EXE", "M66XXX.DCL", "MAC66K.DOC", "DCL66K.DOC"],
                                     "documentedDclFamilyFormat": "Text;ActualM66201BytesNotAcquired",
                                     "diskFilesSource": {"source": "MAC1993", "page": "2-2"},
                                     "missingInvalidDclError": "ExitCode3DclOrFatalDocumented;NotExecuted",
                                     "dclErrorSource": {"source": "MAC1993", "printedPage": "4-22", "pdfPage": 105},
                                     "actualReleaseFiles": None, "actualReleaseFilesStatus": "NotEstablished",
                                     "configurationFiles": None, "configurationStatus": "NotEstablished",
                                     "releaseNotes": None, "installationInstructions": None}, "Dependencies fabricated or waived")
    expect(contract["capabilities"], capability_rows(), "Five evidence layers/form metadata changed or merged")
    expect(contract["safetyPolicy"], SAFETY, "Safety/source/rights/integrity policy weakened")
    expect(contract["permissions"], PERMISSIONS, "Forbidden runtime/generation/integration permission")
    expect(contract["result"], {"classification": "M2axToolchainAcquisitionResearchBlocked",
                              "assemblerTargetSupport": "AssemblerTargetSupportDocumented",
                              "runtime": "AssemblerRuntimeNotVerified", "toolExecution": "ToolExecutionNotRun",
                              "assemblyGeneration": "TargetAssemblyGenerationNotRun", "objects": "TargetObjectNotGenerated",
                              "codeGeneration": "TargetCodeGenerationNotReady",
                              "integration": "FirmwareIntegrationNotEstablished", "remainingBlockers": BLOCKERS}, "Result contradicts missing evidence or removes blocker")
    expect(contract["preservation"], {"runnerVersion": "0.43.0", "protocol": 1, "fixIdentities": 38,
                                     "m2av": "BoundedSourceLevelEquivalenceEstablishedWithinUnchangedScope",
                                     "m2aw": "TargetArchitectureContextContractEstablishedWithinUnchangedScope",
                                     "sf": "PrimaryConflictUnresolved", "compilerAbi": "CompilerAbiNotEstablished",
                                     "irSha256": "4fdbd6b7dbdd8f48d5a43e123ca93a33a003c22556a0c40b5296d5f409e085c4",
                                     "targetContractSha256": "1e8b20872693c0a7dcfbcfc867b85c55c3a759eef616651d6760c08b9dd5af66"}, "Historical contract/runtime/ABI altered")
    return {"milestone": "M2ax", "passed": True, "inventedOnly": True, "actualProfile": contract["profile"],
            "forms": len(FORM_PROFILE), "evidenceLevels": 5, "actualArtifacts": 0,
            "targetCodeGenerationReady": False, "runtimeVerified": False,
            "targetAssemblerExecutions": 0, "targetLinkerExecutions": 0, "targetToolExecutions": 0, "actualRomExecutions": 0,
            "targetObjects": 0, "firmwareBin": 0}


def classify_model(record):
    """Closed INVENTED gate algebra. Even complete models are not actual proof.

    Independent individual numeric versions are distinct from release match:
    compatibleRelease binds each mock component/DCL to its mock release.
    Real individual versions cannot be inferred from package4.XX, and no real
    acquisition is accepted by this invented classifier.
    EvidenceId values below are mock labels, not documentary attestations. Every
    return is explicitly model-only; no tool execution or production permission
    can be represented. Bad evidence yields blockers, never operational success.
    """
    keys(record, {"scope", "package", "archive", "components", "dcl", "dependencies", "claims"}, "Model root schema not closed")
    expect(record["scope"], "InventedPolicyModel", "Actual assets are not allowed in model tests")
    package = record["package"]
    keys(package, {"version", "core", "origin", "originKnown", "bytesAcquired", "usageRights", "rightsEvidence",
                   "versionEvidence", "independence"}, "Model package schema not closed")
    for name in ["version", "core", "origin", "usageRights", "rightsEvidence", "versionEvidence", "independence"]:
        text(package[name], "Model package requires explicit typed metadata")
    for name in ["originKnown", "bytesAcquired"]:
        boolean(package[name], "Model bool cannot be int/string")
    archive = record["archive"]
    keys(archive, {"format", "crc", "traversalSafe", "complete", "repaired", "repacked"}, "Model archive schema not closed")
    for name in ["format", "crc"]:
        text(archive[name], "Model archive metadata must be text")
    for name in ["traversalSafe", "complete", "repaired", "repacked"]:
        boolean(archive[name], "Model archive bool required")
    components = record["components"]
    keys(components, COMPONENTS, "Exactly five required vendor components must be represented")
    for row in components.values():
        keys(row, {"present", "version", "versionEvidence", "compatibleRelease", "objectFormat", "sourceKind", "sha256", "evidenceId"}, "Model component schema not closed")
        boolean(row["present"], "Component present must be bool")
        for name in ["version", "versionEvidence", "compatibleRelease", "objectFormat", "sourceKind", "evidenceId"]:
            text(row[name], "Component metadata must be typed text")
        digest(row["sha256"], "Invalid model digest")
        demand(row["evidenceId"].startswith("mock:"), "Only mock evidence identities are permitted")
    dcl = record["dcl"]
    keys(dcl, {"present", "filename", "target", "formatEstablished", "modified", "versionCompatible",
               "compatibleRelease", "identityEvidence", "sourceKind", "sha256", "evidenceId"}, "Model DCL schema not closed")
    for name in ["present", "formatEstablished", "modified", "versionCompatible"]:
        boolean(dcl[name], "Model DCL bool required")
    for name in ["filename", "target", "compatibleRelease", "identityEvidence", "sourceKind", "evidenceId"]:
        text(dcl[name], "Model DCL metadata must be text")
    digest(dcl["sha256"], "Invalid model DCL digest")
    demand(dcl["evidenceId"].startswith("mock:"), "Only mock DCL evidence identity allowed")
    dependencies = record["dependencies"]
    keys(dependencies, {"diskFilesManifest", "postManualChanges", "dclFormatExplanation", "releaseRestrictions"},
         "Known dependency records cannot be omitted")
    for value in dependencies.values():
        boolean(value, "Model dependency record check must be bool")
    claims = record["claims"]
    expect(claims, {"runtimeVerified": False, "targetAssemblySupported": False, "listingVerified": False,
                    "hostCompilationIsNative": False, "targetObjectCreated": False, "firmwareReady": False},
           "Invented model cannot assert operational success/generation/firmware")
    blockers = []
    def gate(condition, status):
        if not condition:
            blockers.append(status)
    gate(re.fullmatch(r"4\.[0-9]+", package["version"]) is not None, "WrongPackageVersion")
    gate(package["core"] == "nX-8/200", "WrongTargetFamily")
    gate(package["originKnown"] and package["origin"] == "MockVendorDistribution", "PackageProvenanceNotEstablished")
    gate(package["bytesAcquired"], "AcquiredBytesNotEstablished")
    gate(package["versionEvidence"] == "MockIndependentReleaseManifest", "PackageVersionMatchIncomplete")
    gate(package["independence"] == "MockIndependentPublisherRecords", "IndependentProvenanceNotEstablished")
    gate(package["usageRights"] == "ModelUsePermitted" and package["rightsEvidence"] == "MockExplicitTerms",
         "UsageRightsNotEstablished")
    gate(archive["format"] in {"ZIP", "7z", "TAR"}, "UnsupportedArchiveFormat")
    gate(archive["crc"] == "Verified" if archive["format"] in {"ZIP", "7z"} else
         archive["crc"] == "NotApplicable" and archive["format"] == "TAR", "ArchiveIntegrityFailedOrUnknown")
    gate(archive["traversalSafe"], "DirectoryTraversalRisk")
    gate(archive["complete"], "ArchiveCompletenessNotEstablished")
    gate(not archive["repaired"] and not archive["repacked"], "OriginalDistributionNotEstablished")
    for name, row in components.items():
        gate(row["present"], "Missing" + name)
        gate(re.fullmatch(r"[0-9]+\.[0-9]+", row["version"]) is not None
             and row["compatibleRelease"] == package["version"]
             and row["versionEvidence"] == "MockIndependentReleaseManifest",
             "PackageVersionMatchIncomplete:" + name)
        gate(row["objectFormat"] == "MAC66Kv4", "ObjectFormatIncompatible:" + name)
        gate(row["sourceKind"] == "MockVendorPackage", "VendorComponentProvenanceNotEstablished:" + name)
    gate(dcl["present"], "MissingDcl")
    gate(dcl["target"] == "MSM66201" and dcl["identityEvidence"] == "MockIndependentDeviceManifest", "DclTargetIdentityNotEstablished")
    gate(dcl["formatEstablished"], "DclFormatNotEstablished")
    gate(not dcl["modified"], "ModifiedDclRejected")
    gate(dcl["versionCompatible"] and dcl["compatibleRelease"] == package["version"], "DclVersionMatchIncomplete")
    gate(dcl["sourceKind"] == "MockVendorPackage", "DclProvenanceNotEstablished")
    for name, established in dependencies.items():
        gate(established, "ReleaseDependencyNotEstablished:" + name)
    rows = list(components.values()) + [dcl]
    gate(len({r["sha256"] for r in rows}) == len(rows) and len({r["evidenceId"] for r in rows}) == len(rows),
         "DuplicateArtifactsNotIndependent")
    return {"scope": "InventedPolicyModel", "classification": "ModelBlocked" if blockers else "ModelVersionMatchedArtifactsOnly",
            "blockers": blockers, "authenticatesActualArtifacts": False, "runtimeVerified": False,
            "targetCodeGenerationReady": False, "executionPermission": False, "firmwareReady": False}


def parse_contract(raw):
    demand(type(raw) is bytes, "Contract input must be UTF-8 bytes")
    def unique_pairs(pairs):
        result = {}
        for key, value in pairs:
            demand(key not in result, "Duplicate JSON property")
            result[key] = value
        return result
    contract = json.loads(raw, object_pairs_hook=unique_pairs,
                          parse_constant=lambda value: (_ for _ in ()).throw(ValueError("Non-finite JSON number")))
    expect(raw, (json.dumps(contract, indent=2, ensure_ascii=True) + "\n").encode("utf-8"), "Noncanonical UTF-8/LF/two-space JSON")
    return contract


def load_contract(path):
    return parse_contract(Path(path).read_bytes())


if __name__ == "__main__":
    demand(len(sys.argv) <= 2, "Accepts only one contract path")
    path = Path(sys.argv[1]) if len(sys.argv) == 2 else Path(__file__).with_name("toolchain_provenance_contract.json")
    print(json.dumps(validate(load_contract(path)), sort_keys=True))
