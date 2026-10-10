"""M2ay closed reviewed metadata and separate INVENTED safety models.

Does not download, compile, execute, authenticate licenses, or grant permission.
Actual evidence changes require a new reviewed policy, never JSON promotion.
"""
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
BASE = "e5564b24579a71c6a32ca0f71ee48fb0fd8ef548"
PIN = "94612d10370eb4ddf97d4f349168298e1a3da8a0"
FORMS = [
    ("LB A, off N8", 2, "EitherSetsZero", "3-70"),
    ("SLLB A", 1, "RequiresZero", "3-144"),
    ("ROLB off N8", 3, "Independent", "3-120"),
    ("LB A, r0", 1, "EitherSetsZero", "3-70"),
    ("ANDB A, off N8", 2, "RequiresZero", "3-24"),
    ("CMP off N8, #N16", 5, "Independent", "3-38"),
    ("JLT rel8", 2, "Independent", "3-66/67"),
    ("MOVB r1, off N8", 3, "Independent", "3-99"),
    ("ANDB off N8, A", 3, "Independent", "3-25"),
    ("JBS off N8.7, rel8", 3, "Independent", "3-65"),
    ("JBS off N8.5, rel8", 3, "Independent", "3-65"),
    ("ORB off N'8, #N8", 4, "Independent", "3-110"),
    ("ORB A, #N8", 2, "RequiresZero", "3-107"),
    ("LB A, #N8", 2, "EitherSetsZero", "3-70"),
    ("STB A, off N8", 2, "RequiresZero", "3-155"),
]


def demand(condition, message):
    if not condition:
        raise ValueError(message)


def equal(left, right):
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(equal(left[k], right[k]) for k in left)
    if isinstance(left, list):
        return len(left) == len(right) and all(equal(a, b) for a, b in zip(left, right))
    return left == right


def closed(value, names):
    demand(type(value) is dict and set(value) == set(names), "Closed schema required")


def boolean(value):
    demand(type(value) is bool, "Boolean is not integer/string/unknown")


def integer(value, low, high):
    demand(type(value) is int and low <= value <= high, "Bounded exact integer required")


def expected_contract():
    # Filled only with root-reviewed static evidence; no operational success.
    return {
        "schemaVersion": 1, "milestone": "M2ay",
        "profile": "ASM662_Pinned_Static_BuildBlocked",
        "exactBase": BASE,
        "sourceProvenance": {
            "repository": "VIRUXE/asm662", "commit": PIN,
            "tree": "991770bbfeb8f515df5cc3d986aecfc42a3b2a5b",
            "inventoryStatus": "ExactMirrorIdentityVerifiedNotCanonicalUpstreamAuthentication",
            "treeEntries": 67, "treeBlobs": 61, "reviewedTextBlobs": 43,
            "sourceManifestSha256": "eefdffa3c4516163f69dd21366d083970ec701c4136fd92c643794649dfee60e",
            "integrityAuditSha256": "cc7a94ef00a39e0e5ad87a9b3a08eae8cdf480b789718665a717b0b1d280ae70"},
        "licenseEvidence": {
            "OriginalSourceLicenseEvidence": "OriginalAuthorBroadBSDGrant;ExactVariantAndCompleteNoticesUnknown",
            "MirrorLicenseClaim": "UnlicenseAdditionConfirmed;RelicensingAuthorityNotEstablished",
            "ThirdPartyComponentRights": "NotEstablishedForCompleteSourceSet",
            "LocalResearchUseStatus": "BuildBlockedPendingApplicableRights",
            "RedistributionStatus": "NotEstablished;NoPublicThirdPartySource",
            "manifestSha256": "52fb636dece0813970230043b5e6ba67b27ce1ad8f2f30df4c8bfc99eff52e17"},
        "rcsMaterialization": {
            "filesRecovered": 39, "status": "ExplicitTrunkHeadFullTextRecovered;CoherenceSeparate",
            "headBytes": 1792620, "olderDeltaVersionsMaterialized": 0,
            "parserValidation": "IndependentByteGrammarAndWholeDeltatextRegex;9Positive16RefusalFixtures",
            "standardRcsToolUsed": False, "keywordExpansion": "None",
            "manifestSha256": "19cfe3552e83c7dd8e1539cb664ef01eef02c6c22192c98dac9a77ef1da9b8f4"},
        "sourceIntegrity": {
            "coherentBuildTree": False, "status": "CoherentSourceReconstructionBlocked",
            "originalInputsPresent": 11, "missingOriginalInputs": 0,
            "generatedIntermediatesAbsentButDeclaredOutputs": 5,
            "generatedArtifactsVerified": False, "staleGeneratedArtifacts": 4,
            "mismatch": "TableHeadTBR_CachedGeneratedTRB;NotEmittedByteMismatch",
            "dependencyManifestSha256": "be4b507aad22d186dde369545c1d2c5baa6cb3e5acd42f7e222d396c595f4ec7"},
        "buildDependencies": {
            "status": "PartiallyEstablished;TrustedFlexYaccNotEstablished",
            "msvcFileVersion": "19.42.34435.0", "nmakeFileVersion": "14.42.34435.0",
            "perlObservedVersion": "5.38.2", "flexVersion": None, "yaccVersion": None,
            "historicalCommandsExecuted": False,
            "inventorySha256": "cae34fd9ff8196d81b948887a6a5b1c22f39ac0358573314b2d043b7df28a20e"},
        "safetyAudit": {
            "status": "UnsafeExecutionPathConfirmed", "firstFinding": "UnrestrictedPRELOADExternalRead",
            "findings": 11, "observedExploit": False, "upstreamPatched": False,
            "manifestSha256": "30285d3af4f355edaf403b378e6a9f4d62ec6901193f48175c261b6b123db62f",
            "mitigation": "SeparateProposalOnlyNotImplemented",
            "proposalSha256": "49057907992923d00386ccb2711443dc66b96f5ef45a0f6f17975fbaa8a15f45"},
        "buildVerification": {"status": "NotRun", "builds": 0, "executableSha256": None,
                              "reproducibility": "NotEvaluated", "preflight": "BuildPreflightBlocked"},
        "syntheticOutputVerification": {"status": "NotRun", "outputs": 0,
                                        "classification": "SyntheticAssemblerOutputNotFirmwareBIN",
                                        "generatedFormsCompared": 0, "mismatches": None},
        "primaryOpcodeExpectations": {
            "status": "PrimaryEncodingExpectationEstablished", "exactForms": 15,
            "independence": "ManufacturerManualNotASMTableOrDecoderOrOracle",
            "manifestSha256": "a268815a0c04a4e2f0fccb64021ead26e1cbdaa02c1cc435d816f7d35fa2ab44",
            "verifiedGeneratedForms": 0},
        "capabilities": [dict(form=form, length=length, dd=dd, primaryPage=page,
                             DerivedTableRowPresent=True,
                             CoherentAssemblerGrammarAvailable=False,
                             HostAssemblerSmokePassed=False, PrimaryEncodingVerified=False,
                             TargetSemanticsVerified=False)
                         for form, length, dd, page in FORMS],
        "actualRuntimeExecution": {"status": "NativeExecutionNotObserved", "runtimeVerified": False,
                                   "assemblerExecutions": 0, "actualRomExecutions": 0},
        "firmwareReadiness": {"ready": False, "status": "TargetCodeGenerationNotReady",
                              "productionObjects": 0, "firmwareBin": 0},
        "permissions": {"hostExecution": False, "sourceBuild": False,
                        "syntheticAssembly": False, "romAssembly": False,
                        "thirdPartyRedistribution": False, "hardware": False, "gui": False},
        "preservation": {"runner": "0.43.0", "protocol": 1, "fixIdentities": 38,
                         "m2av": "BoundedSourceLevelEquivalenceEstablished",
                         "m2aw": "TargetArchitectureContextContractEstablished",
                         "m2ax": "VendorAcquisitionResearchBlocked",
                         "compilerAbi": "NotEstablished", "m2ah": "STOPbefore5722",
                         "data019b2Owner": "NotEstablished", "wdt3c": "Unresolved",
                         "jgtC8": "Unresolved", "cal2689Rt5c80": "NotRun",
                         "resetFullboot": "Blocked", "scheduler": "NotEstablished",
                         "irq": "NotInjected", "timer": "NotModeled",
                         "physicalFuelTimeDegrees": "Unavailable",
                         "status": "PcInspectionOnly/NotFlashReady"},
        "result": {"classification": "M2ay ASM662 Build/Encoding ResearchBlocked",
                   "firstBlocker": "LicenseApplicabilityUnresolvedForCompleteSourceSet"},
    }


def validate(contract):
    demand(equal(contract, expected_contract()), "Not exact reviewed M2ay policy; input claims cannot establish facts")
    return dict(milestone="M2ay", passed=True, profile=contract["profile"], forms=15,
                primaryExpectations=15, generatedFormsVerified=0, runtimeVerified=False,
                buildExecutions=0, assemblerExecutions=0, actualRomExecutions=0,
                executionPermission=False, firmwareReady=False, targetObjects=0, firmwareBin=0)


def parse_contract(raw):
    demand(type(raw) is bytes and len(raw) <= 65536, "Bounded UTF-8 bytes required")
    def unique(pairs):
        result = {}
        for key, value in pairs:
            demand(key not in result, "Duplicate JSON key")
            result[key] = value
        return result
    value = json.loads(raw, object_pairs_hook=unique,
                       parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Nonfinite JSON")))
    demand(raw == (json.dumps(value, indent=2, ensure_ascii=True) + "\n").encode(),
           "Canonical UTF-8/LF/two-space serialization required")
    return value


def load_contract(path):
    return parse_contract(Path(path).read_bytes())


def classify_preflight_model(record):
    """Hypothetical gate algebra only; never authenticates claims or grants use."""
    gates = ["sourcePinned", "rightsApplicable", "rcsIndependentlyValidated", "coherentTree",
             "generatedSourcesChecked", "dependenciesTrusted", "commandsAudited", "boundsSafe",
             "pathsSafe", "diagnosticsFatal", "overlapsRejected", "ddChecked", "isolated",
             "networkAbsent", "privateInputsAbsent", "resourceLimits"]
    closed(record, ["scope", "gates", "claims"])
    demand(record["scope"] == "InventedPolicyModel", "Actual-source claims not allowed in model")
    closed(record["gates"], gates)
    for value in record["gates"].values():
        boolean(value)
    demand(equal(record["claims"], {"runtimeVerified": False, "buildVerified": False,
                                   "firmwareReady": False, "executionPermission": False}),
           "Mock facts cannot promote execution/build/runtime")
    blockers = [gate for gate in gates if not record["gates"][gate]]
    return dict(scope="InventedPolicyModel", classification="ModelBlocked" if blockers else
                "ModelPreflightSatisfiedNotExecutionPermission", blockers=blockers,
                runtimeVerified=False, buildVerified=False, executionPermission=False, firmwareReady=False)


def check_write_model(pc, length, occupied):
    """Safe invented write acceptance, not a simulation of upstream C behavior."""
    integer(pc, 0, 32768)
    integer(length, 1, 32768)
    demand(length <= 32768 - pc, "Output bounds exceeded")
    demand(type(occupied) is list and len(occupied) <= 32768, "Bounded occupied intervals required")
    for interval in occupied:
        demand(type(interval) is list and len(interval) == 2, "Exact interval required")
        start, end = interval
        integer(start, 0, 32767)
        integer(end, start + 1, 32768)
        demand(pc + length <= start or pc >= end, "Overlapping output write")
    return {"scope": "InventedPolicyModel", "accepted": True, "end": pc + length,
            "executionPermission": False}


def check_expression_model(op, left, right):
    integer(left, -2147483648, 2147483647)
    integer(right, -2147483648, 2147483647)
    demand(op in {"+", "-", "*", "/", "%", "<<", ">>"}, "Unsupported operation")
    if op in {"/", "%"}:
        demand(right != 0 and not (left == -2147483648 and right == -1), "Undefined division")
        quotient = (abs(left) // abs(right)) * (-1 if (left < 0) != (right < 0) else 1)
        result = quotient if op == "/" else left - quotient * right
    elif op in {"<<", ">>"}:
        integer(right, 0, 31)
        demand(left >= 0, "Signed negative shift refused")
        result = left << right if op == "<<" else left >> right
    else:
        result = left + right if op == "+" else left - right if op == "-" else left * right
    integer(result, -2147483648, 2147483647)
    return result


def check_smoke_model(record):
    """Invented transcript validation; cannot certify any real assembler output."""
    closed(record, ["scope", "exitCode", "diagnostics", "output", "expected", "regionStart", "unusedByte",
                   "fileAccesses", "dd", "requiredDd", "expectedIndependent", "claims"])
    demand(record["scope"] == "InventedPolicyModel", "Only invented transcript allowed")
    integer(record["exitCode"], -255, 255)
    demand(record["exitCode"] == 0 and record["diagnostics"] == "", "Any diagnostic is failure")
    demand(record["fileAccesses"] == ["auditedSyntheticInputRead", "freshSyntheticOutputWrite"],
           "Unexpected, private, preload or unsafe file access")
    demand(record["expectedIndependent"] is True, "Same-table/decoder/output expectation refused")
    integer(record["dd"], 0, 1)
    demand(record["requiredDd"] is None or type(record["requiredDd"]) is int
           and record["requiredDd"] in {0, 1} and record["dd"] == record["requiredDd"], "DD mismatch")
    demand(equal(record["claims"], {"actualBuildVerified": False, "actualRuntimeVerified": False,
                                   "targetSemanticsVerified": False, "firmwareReady": False}),
           "Model transcript is not actual execution or native semantics")
    output, expected = record["output"], record["expected"]
    demand(type(output) is list and len(output) == 32768, "Exact flat synthetic extent required")
    demand(type(expected) is list and 1 <= len(expected) <= 16, "Narrow invented region required")
    for byte in output + expected:
        integer(byte, 0, 255)
    start = record["regionStart"]
    integer(start, 0, 32768 - len(expected))
    demand(output[start:start + len(expected)] == expected, "Exact bytes differ")
    integer(record["unusedByte"], 0, 255)
    demand(all(byte == record["unusedByte"] for byte in output[:start] + output[start + len(expected):]),
           "Unused bytes differ from independently specified filler")
    return dict(scope="InventedPolicyModel", modelMatches=True, actualRuntimeVerified=False,
                generatedFormsVerified=0, targetSemanticsVerified=False, firmwareReady=False)


if __name__ == "__main__":
    demand(len(sys.argv) <= 2, "Accepts at most one contract path")
    path = Path(sys.argv[1]) if len(sys.argv) == 2 else Path(__file__).with_name("asm662_source_verification.json")
    print(json.dumps(validate(load_contract(path)), sort_keys=True))
