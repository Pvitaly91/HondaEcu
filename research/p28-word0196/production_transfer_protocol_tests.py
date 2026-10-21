"""M2br private draft: twelve pure schema/codec/digest controls, no Cpu/Bus.

Calling run is an actual host-only check after the formal freeze. Importing this
source performs no tests, output, expected-stream generation or target work.
The32 full-record semantic mutations are a separately counted runtime comparator
control; they never add58negative or5470positive Cpu sessions.
"""

from copy import deepcopy
from production_transfer_common import bq_modules, bounded_json, canonical, first_difference, require, profile_instruction
from production_transfer_oracle import architecture_digest, data_digest

TEST_NAMES = ("primitive-json", "duplicate-key-refusal", "float-refusal", "nonfinite-refusal",
              "lossless-full-ram", "reserved-ram-tag-refusal", "boolean-is-not-integer", "array-order",
              "null-is-not-missing", "architecture-digest-covers-flags-and-counters", "data-digest-covers-unseeded-tail",
              "primary-tiny-program-profiles")


def _refusal(action, reason):
    try:
        action()
    except ValueError as observed:
        require(reason in str(observed), "ActualPureRefusalReason:" + str(observed))
        return
    raise ValueError("ExpectedPureRefusalNotObserved:" + reason)


def run(root):
    results = []
    for name in TEST_NAMES:
        if name == "primitive-json":
            require(bounded_json(canonical({"a": [0, True, None, "ASCII"]})) == {"a": [0, True, None, "ASCII"]}, name)
        elif name == "duplicate-key-refusal": _refusal(lambda: bounded_json(b'{"a":1,"a":2}'), "DuplicateJsonKey")
        elif name == "float-refusal": _refusal(lambda: bounded_json(b'{"a":1.0}'), "ClosedPrimitiveJsonDepthAndType")
        elif name == "nonfinite-refusal": _refusal(lambda: bounded_json(b'{"a":NaN}'), "NonFiniteJson")
        elif name in ("lossless-full-ram", "reserved-ram-tag-refusal"):
            with bq_modules(root) as modules:
                codec = modules["production_composite_projection"]
                if name == "lossless-full-ram":
                    ram = [0xA5] * 3968
                    ram[0], ram[31], ram[-1] = 0, 255, 1
                    require(first_difference(ram, codec.decode_ram(codec.encode_ram(ram))) is None, name)
                else:
                    _refusal(lambda: codec.project({codec.TAG: {}}), "ReservedLosslessTag")
        elif name == "boolean-is-not-integer": require(first_difference(True, 1) is not None, name)
        elif name == "array-order": require(first_difference([1, 2], [2, 1]) is not None, name)
        elif name == "null-is-not-missing": require(first_difference({"a": None}, {}) is not None, name)
        elif name in ("architecture-digest-covers-flags-and-counters", "data-digest-covers-unseeded-tail"):
            snapshot = {"cpu": {"pc": 0x1000, "a": 0x55AA, "ssp": 0x1357, "lrb": 0x21,
                                "zf": False, "cf": True, "hc": False, "dd": True, "sf": False,
                                "psw_other": 0x137, "cycles": 7, "instructions": 1, "halted": False},
                        "ram": [0xA5] * 3968, "ram_range": [0x80, 0x1000]}
            changed = deepcopy(snapshot)
            if name.startswith("architecture"):
                original = architecture_digest(snapshot)
                changed["cpu"]["cycles"] += 1
                require(architecture_digest(changed) != original, name + ":cycles")
                changed = deepcopy(snapshot)
                changed["cpu"]["cf"] = False
                require(architecture_digest(changed) != original, name + ":carry")
            else:
                changed["ram"][-1] ^= 1
                require(data_digest(snapshot) != data_digest(changed), name)
        elif name == "primary-tiny-program-profiles":
            require(profile_instruction("Caller") == bytes((3, 0, 16))
                    and profile_instruction("ContinuationBelow") == bytes((119, 0))
                    and profile_instruction("ContinuationNotBelow") == bytes((119, 165)), name)
        results.append({"name": name, "passed": True})
    return {"classification": "ActualPureHostSchemaCodecDigestControls_NoTargetCpuOrBus", "passed": True,
            "tests": results, "count": len(results), "targetCpuInstances": 0, "busInstances": 0,
            "programExecutions": 0, "originalRomExecutions": 0}
