"""M2br private draft: actual immutable M2bj emitter plus closed tiny profiles.

The full command exists only in ephemeral host memory/stdin. Returned receipts
contain identities and instruction extent hashes, never a full PROGRAM payload.
The independent oracle is a comparison authority, never executable input.
"""

from copy import deepcopy
from hashlib import sha256
from production_transfer_common import (
    COMPOSITE_SHA, PROVENANCE, bq_modules, profile_instruction, require, segment_identities,
)

ROLE_TO_ID = {"Caller": "Caller", "Composite": "Composite", "ContinuationBelow": "BelowContinuation",
              "ContinuationNotBelow": "NotBelowContinuation"}


def segment_claim(role):
    profile = next(row for row in segment_identities() if row["role"] == role)
    return {"id": ROLE_TO_ID[role], "base": profile["base"], "end_exclusive": profile["end_exclusive"],
            "sha256": profile["sha256"], "provenance": PROVENANCE}


def program_claims():
    return [segment_claim(role) for role in ("Caller", "Composite", "ContinuationBelow", "ContinuationNotBelow")]


def emitted_program(root):
    with bq_modules(root) as modules:
        composite_command, composite_receipt = modules["production_composite_emission"].emitted_program(root)
    require(composite_receipt["sha256"] == COMPOSITE_SHA
            and composite_receipt["independent_primary_checked"] == 20, "ActualUnchangedM2bjEmissionFirst")
    # Fixed tiny instructions were independently established before this code:
    # manufacturer J03/adrL/adrH and LB77/N8. No arbitrary stream is accepted.
    caller, below, not_below = (profile_instruction(role) for role in
                                ("Caller", "ContinuationBelow", "ContinuationNotBelow"))
    metadata = {"caller": segment_claim("Caller"), "below": segment_claim("ContinuationBelow"),
                "not_below": segment_claim("ContinuationNotBelow")}
    command = {**composite_command,
               "caller_bytes": list(caller), "below_bytes": list(below), "not_below_bytes": list(not_below),
               "transfer_metadata": metadata}
    receipt = {"classification": "ActualInMemoryEmissionAndClosedInventedProfiles_NoCpu",
               "composite": composite_receipt, "segments": program_claims(),
               "full_payload_persisted": False, "persistent_binary_outputs": 0,
               "program_padding_bytes": 0, "original_rom_executions": 0,
               "caller_tiny_primary_sha256": sha256(caller).hexdigest(),
               "below_tiny_primary_sha256": sha256(below).hexdigest(),
               "not_below_tiny_primary_sha256": sha256(not_below).hexdigest(),
               "native_downstream_claim": False, "firmware_ready": False}
    return command, deepcopy(receipt)
