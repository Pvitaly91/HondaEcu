"""Closed M2ba documentary policy; invented models are never license grants.

No network, source loading, archive extraction, build, instruction encoding or
external messages. A new actual grant requires independent review and a new
reviewed profile, not input flags. Model results never authenticate a document.
"""

import sys

sys.dont_write_bytecode = True

import hashlib
import json
from pathlib import Path

REVIEWED_PROFILE_SHA256 = "7163c40e3397500bb875d44ffed8fbf916d73e1351452ac63160bd7e2997a148"
COMPONENTS = ("AndyOwnSource", "DocOriginalTable", "ModifiedTable", "BisonGenerated",
              "FlexGenerated", "ByaccGenerated", "MirrorChanges")
GATES = ("sourceIdentityVerified", "grantOwnerMatched", "revisionScopeVerified",
         "modify", "localBuild", "redistribute", "noticesRetained")
CLAIMS = {"actualRightsVerified": False, "executionPermission": False,
          "runtimeVerified": False, "encoderImplemented": False,
          "firmwareReady": False, "targetBytes": 0}


def demand(condition, message):
    if not condition:
        raise ValueError(message)


def equal(actual, expected):
    if type(actual) is not type(expected):
        return False
    if isinstance(actual, dict):
        return actual.keys() == expected.keys() and all(equal(actual[k], expected[k]) for k in actual)
    if isinstance(actual, list):
        return len(actual) == len(expected) and all(equal(a, b) for a, b in zip(actual, expected))
    return actual == expected


def closed_keys(value, keys, message):
    demand(type(value) is dict and set(value) == set(keys), message)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        demand(key not in result, "Duplicate JSON key")
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError("Non-finite JSON constant: " + value)


def parse_json(text):
    demand(type(text) is str and len(text) <= 1048576, "Bounded JSON text required")
    return json.loads(text, object_pairs_hook=unique_object, parse_constant=reject_constant)


def load_contract(path):
    path = Path(path)
    if path.is_dir():
        path = path / "doc_contribution_provenance.json"
    demand(path.stat().st_size <= 1048576, "Contract exceeds bound")
    return parse_json(path.read_text(encoding="utf-8"))


def reviewed_json_types(value, depth=0):
    """Reject coercible Python containers/numeric types in the reviewed profile."""
    demand(depth <= 64, "Profile nesting exceeds bound")
    if type(value) is dict:
        demand(all(type(key) is str for key in value), "Profile keys must be strings")
        for child in value.values():
            reviewed_json_types(child, depth + 1)
    elif type(value) is list:
        for child in value:
            reviewed_json_types(child, depth + 1)
    else:
        demand(type(value) in {str, int, bool, type(None)}, "Non-reviewed JSON scalar/container type")


def profile_digest(contract):
    demand(type(contract) is dict, "Contract object required")
    reviewed_json_types(contract)
    try:
        raw = json.dumps(contract, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError("Non-JSON contract") from error
    demand(len(raw) <= 1048576, "Canonical contract exceeds bound")
    return hashlib.sha256(raw).hexdigest()


def validate(contract):
    demand(profile_digest(contract) == REVIEWED_PROFILE_SHA256, "Unreviewed documentary profile")
    demand(equal(contract["schemaVersion"], 1), "Schema type mismatch")
    demand(equal(contract["milestone"], "M2ba"), "Wrong milestone")
    demand(all(type(value) is int and value == 0 for key, value in contract["operations"].items()
               if key not in {"encoderImplemented", "runtimeVerified"}), "Operation counter promotion")
    return {"milestone": "M2ba", "domain": "Provenance", "passed": True, "profileValidated": True,
            "rights": "DocContributionRightsNotEstablished", "historicalRoute": "HistoricalASM662Blocked",
            "recommendedRoute": "PrimaryManualDerivedIndependentEncoderRoute",
            "authenticatesActualRights": False, "executionPermission": False,
            "runtimeVerified": False, "encoderImplemented": False,
            "actualRomExecutions": 0, "assemblerExecutions": 0, "targetBytes": 0, "firmwareBin": 0}


def classify_model(model):
    """Classify explicitly invented component claims; never grant real rights."""
    closed_keys(model, {"scope", "sourceSetId", "components", "projectBSDStatement",
                        "mirrorUnlicenseClaim", "generatedSkeletonException", "claims"}, "Model root not closed")
    demand(equal(model["scope"], "InventedRightsPolicyModel"), "Actual rights claims refused")
    demand(equal(model["sourceSetId"], "invented:source-set"), "Invented identifier required")
    demand(equal(model["claims"], CLAIMS), "Operational or actual rights claims refused")
    for key in ("projectBSDStatement", "mirrorUnlicenseClaim", "generatedSkeletonException"):
        demand(type(model[key]) is bool, "Typed documentary-claim flag required")
    closed_keys(model["components"], COMPONENTS, "Missing, duplicate or unknown component")
    blockers = []
    for component in COMPONENTS:
        row = model["components"][component]
        closed_keys(row, {"owner", "grant", *GATES}, "Component fields not closed")
        demand(equal(row["owner"], "invented:owner:" + component), "Real or unmatched owner refused")
        demand(type(row["grant"]) is str and row["grant"] in {"Unknown", "InventedExplicitComponentGrant"},
               "Only invented grant vocabulary allowed")
        if row["grant"] == "Unknown":
            blockers.append(component + ":ComponentGrantNotEstablished")
        for gate in GATES:
            demand(type(row[gate]) is bool, "Component gate must be boolean")
            if not row[gate]:
                blockers.append(component + ":" + gate + "NotEstablished")
    return {"scope": "InventedRightsPolicyModel",
            "classification": "ModelRequirementsSatisfiedOnly" if not blockers else "ModelBlocked",
            "blockers": blockers, "authenticatesActualRights": False,
            "executionPermission": False, "runtimeVerified": False,
            "encoderImplemented": False, "targetBytes": 0, "firmwareBin": 0}


def main():
    demand(len(sys.argv) <= 2, "Usage: validate_doc_contribution.py [contract-or-directory]")
    path = Path(sys.argv[1]) if len(sys.argv) == 2 else Path(__file__).with_name("doc_contribution_provenance.json")
    print(json.dumps(validate(load_contract(path)), sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, TypeError, KeyError, RecursionError) as error:
        print(json.dumps({"milestone": "M2ba", "domain": "Provenance", "error": str(error)}), file=sys.stderr)
        raise SystemExit(1)
