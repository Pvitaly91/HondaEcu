"""Invented-only M2ba provenance refusal/model tests; never source operations.

Independent expected gates below distinguish project statements, contributor
grants and generated-skeleton exceptions. Complete mock records still grant no
actual license, execution permission, encoding or target readiness.
"""

import copy
import hashlib
import itertools
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
import validate_doc_contribution as policy

COMPONENTS = ("AndyOwnSource", "DocOriginalTable", "ModifiedTable", "BisonGenerated",
              "FlexGenerated", "ByaccGenerated", "MirrorChanges")
GATES = ("sourceIdentityVerified", "grantOwnerMatched", "revisionScopeVerified",
         "modify", "localBuild", "redistribute", "noticesRetained")
HERE = Path(__file__).resolve().parent
RESEARCH = Path(sys.argv[1]) if len(sys.argv) == 2 else HERE
POSITIVE = NEGATIVE = PROPERTIES = VECTORS = 0


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def positive(condition, message):
    global POSITIVE
    check(condition, message)
    POSITIVE += 1


def refusal(action, message):
    global NEGATIVE
    try:
        action()
    except ValueError:
        NEGATIVE += 1
    else:
        raise AssertionError(message)


def invented():
    return {"scope": "InventedRightsPolicyModel", "sourceSetId": "invented:source-set",
            "components": {name: {"owner": "invented:owner:" + name,
                                  "grant": "InventedExplicitComponentGrant",
                                  **{gate: True for gate in GATES}} for name in COMPONENTS},
            "projectBSDStatement": False, "mirrorUnlicenseClaim": False,
            "generatedSkeletonException": False,
            "claims": {"actualRightsVerified": False, "executionPermission": False,
                       "runtimeVerified": False, "encoderImplemented": False,
                       "firmwareReady": False, "targetBytes": 0}}


def leaves(value, path=()):
    if type(value) is dict and value:
        for key, item in value.items():
            yield from leaves(item, path + (key,))
    elif type(value) is list and value:
        for index, item in enumerate(value):
            yield from leaves(item, path + (index,))
    else:
        yield path, value


def replace(record, path, value):
    target = record
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value


def containers(value, path=()):
    if type(value) is dict:
        for key, item in value.items():
            yield from containers(item, path + (key,))
    elif type(value) is list:
        yield path, value
        for index, item in enumerate(value):
            yield from containers(item, path + (index,))


def no_authority(result):
    return (result["authenticatesActualRights"] is False and
            result["executionPermission"] is False and result["runtimeVerified"] is False and
            result["encoderImplemented"] is False and type(result["targetBytes"]) is int and
            result["targetBytes"] == 0 and result["firmwareBin"] == 0)


def main():
    global PROPERTIES, VECTORS
    check(len(sys.argv) <= 2, "Usage: doc_contribution_tests.py [research-directory]")
    base = policy.load_contract(RESEARCH / "doc_contribution_provenance.json")
    actual = policy.validate(copy.deepcopy(base))
    positive(no_authority(actual), "Profile cannot create rights or operations")
    positive(actual["rights"] == "DocContributionRightsNotEstablished", "Doc rights promoted")
    positive(actual["historicalRoute"] == "HistoricalASM662Blocked", "Historical route promoted")
    positive(actual["recommendedRoute"] == "PrimaryManualDerivedIndependentEncoderRoute", "Wrong route")
    positive(base["originalRelease"]["initialByteIdentical"] == 35 and
             base["originalRelease"]["initialChanged"] == 1 and
             base["originalRelease"]["fullTreeByteIdentical"] is False, "False exact-tree identity")
    reordered = json.loads(json.dumps(base, sort_keys=True))
    positive(policy.validate(reordered) == actual, "Object order changes policy")
    positive(tuple(row["id"] for row in base["components"]) == COMPONENTS, "Wrong component coverage")
    for filename, digest in (
        ("word0196_ir.json", "4fdbd6b7dbdd8f48d5a43e123ca93a33a003c22556a0c40b5296d5f409e085c4"),
        ("target_abi_contract.json", "1e8b20872693c0a7dcfbcfc867b85c55c3a759eef616651d6760c08b9dd5af66"),
    ):
        positive(hashlib.sha256((RESEARCH / filename).read_bytes()).hexdigest() == digest,
                 "Historical contract changed: " + filename)
    complete = policy.classify_model(invented())
    positive(complete["classification"] == "ModelRequirementsSatisfiedOnly" and no_authority(complete),
             "Complete invented evidence became actual license")
    for component in COMPONENTS:
        model = invented()
        model["components"][component]["grant"] = "Unknown"
        result = policy.classify_model(model)
        positive(result["classification"] == "ModelBlocked" and
                 component + ":ComponentGrantNotEstablished" in result["blockers"] and no_authority(result),
                 "Unknown component grant accepted")
    for path, value in leaves(base):
        for replacement in (None, False, True, 0, 1, -1, 0.0, 1.0, "", "ForgedGrant", [], {}):
            if policy.equal(value, replacement):
                continue
            changed = copy.deepcopy(base)
            replace(changed, path, replacement)
            refusal(lambda: policy.validate(changed), "Changed profile accepted: " + repr(path))
    for key in base:
        changed = copy.deepcopy(base)
        del changed[key]
        refusal(lambda: policy.validate(changed), "Missing profile field accepted")
    for path, value in containers(base):
        changed = copy.deepcopy(base)
        replace(changed, path, tuple(value))
        refusal(lambda: policy.validate(changed), "Tuple silently coerced to reviewed list")
    extra = copy.deepcopy(base)
    extra["permissionOverride"] = True
    refusal(lambda: policy.validate(extra), "Extra policy override accepted")
    for text in ('{"x":1,"x":2}', '{"x":NaN}', '{"x":Infinity}', '{"x":-Infinity}',
                 '{} trailing', '{"x":1,}', '/*comment*/{}', ' ' * 1048577):
        refusal(lambda: policy.parse_json(text), "Unsafe JSON accepted")
    for path, value in leaves(invented()):
        for replacement in (None, 0, 1, "RealLicenseGrant", [], {}):
            if policy.equal(value, replacement):
                continue
            changed = invented()
            replace(changed, path, replacement)
            refusal(lambda: policy.classify_model(changed), "Wrong model type/authority accepted")
    for key in invented():
        changed = invented()
        del changed[key]
        refusal(lambda: policy.classify_model(changed), "Incomplete model accepted")
    for component in COMPONENTS:
        changed = invented()
        del changed["components"][component]
        refusal(lambda: policy.classify_model(changed), "Missing component accepted")
    changed = invented()
    changed["components"]["UnknownContributor"] = {}
    refusal(lambda: policy.classify_model(changed), "Unknown contributor accepted")
    for claim in invented()["claims"]:
        changed = invented()
        changed["claims"][claim] = 1 if claim == "targetBytes" else True
        refusal(lambda: policy.classify_model(changed), "Operational mock claim accepted")
    # Exhaustive independent grant truth table: documentary flags never stand in
    # for permission from any of the seven independent component owners.
    for grant_bits in itertools.product((False, True), repeat=7):
        for documentary_bits in itertools.product((False, True), repeat=3):
            model = invented()
            for component, present in zip(COMPONENTS, grant_bits):
                model["components"][component]["grant"] = "InventedExplicitComponentGrant" if present else "Unknown"
            for key, value in zip(("projectBSDStatement", "mirrorUnlicenseClaim", "generatedSkeletonException"), documentary_bits):
                model[key] = value
            result = policy.classify_model(model)
            check((result["classification"] == "ModelRequirementsSatisfiedOnly") == all(grant_bits),
                  "Project/skeleton/mirror statement masked component grant")
            check(no_authority(result), "Grant truth table authorized real operation")
            VECTORS += 1
    PROPERTIES += 1
    # Every component's seven independent scope/notice/permission gates, at all
    # documentary flag combinations, must remain conjunctive and fail closed.
    for component in COMPONENTS:
        for gate_bits in itertools.product((False, True), repeat=7):
            for documentary_bits in itertools.product((False, True), repeat=3):
                model = invented()
                for gate, value in zip(GATES, gate_bits):
                    model["components"][component][gate] = value
                for key, value in zip(("projectBSDStatement", "mirrorUnlicenseClaim", "generatedSkeletonException"), documentary_bits):
                    model[key] = value
                result = policy.classify_model(model)
                check((result["classification"] == "ModelRequirementsSatisfiedOnly") == all(gate_bits),
                      "Scope/notice gate incorrectly omitted")
                check(no_authority(result), "Scope truth table authorized execution")
                VECTORS += 1
    PROPERTIES += 1
    report = {"milestone": "M2ba", "domain": "Provenance", "passed": True,
              "logicalCases": POSITIVE + NEGATIVE + PROPERTIES,
              "positive": POSITIVE, "negative": NEGATIVE, "properties": PROPERTIES,
              "propertyVectors": VECTORS, "failed": 0, "skipped": 0,
              "runtimeVerified": False, "encoderImplemented": False, "actualRomExecutions": 0,
              "assemblerExecutions": 0, "targetBytes": 0, "firmwareBin": 0}
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
