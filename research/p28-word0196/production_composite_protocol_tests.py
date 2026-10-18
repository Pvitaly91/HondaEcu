"""M2bq source draft: pure lossless-codec/comparator sensitivity controls.

These tests create no Cpu/Bus/process and do not attest runtime refusals. Their
sources and expected behavior are frozen before the separate actual execution.
"""

from copy import deepcopy
from production_composite_common import first_difference, require
from production_composite_corpus import iter_cases
from production_composite_oracle import expected_case
from production_composite_projection import project, restore, TAG


def run_pure_tests(root):
    tests = []
    iterator = iter_cases(root)
    try:
        request = next(item for item in iterator if item["path"] == "D")
    finally:
        iterator.close()
    expected = expected_case(root, request)
    projected = project(expected)
    require(first_difference(expected, restore(projected)) is None, "FullDeclaredObservationRoundTrip")
    tests.append({"id": "complete-observation-roundtrip", "passed": True})
    complete_ram = [0xA5] * 3968
    complete_ram[0], complete_ram[-1], complete_ram[7] = 0, 255, 164
    snapshot = {"cpu": deepcopy(expected["report"]["entry"]["cpu"]),
                "ram": complete_ram, "ram_range": [128, 4096]}
    require(first_difference(snapshot, restore(project(snapshot))) is None, "EveryRamByteIncludingLastRetained")
    tests.append({"id": "complete-ram-first-last-and-nonseed-byte", "passed": True})
    for name, left, right in (("bool-not-int", True, 1), ("null-not-missing", {"a": None}, {})):
        require(first_difference(left, right) is not None, "StrictTypeAndKeySensitivity:" + name)
        tests.append({"id": name, "passed": True})
    try:
        project({TAG: {}})
    except ValueError:
        tests.append({"id": "reserved-codec-tag-refused", "passed": True})
    else:
        raise ValueError("ReservedCodecTagMustNotBeAccepted")

    def mutation(name, change):
        value = deepcopy(expected)
        change(value)
        mismatch = first_difference(expected, value)
        require(mismatch is not None, "ComparatorMissedMutation:" + name)
        tests.append({"id": name, "passed": True, "firstMismatch": mismatch["field"]})
    mutation("intermediate-cf", lambda value: value["report"]["steps"][1]["after"]["cpu"].__setitem__(
        "cf", not value["report"]["steps"][1]["after"]["cpu"]["cf"]))
    mutation("retained-ah", lambda value: value["report"]["steps"][2]["after"]["cpu"].__setitem__(
        "a", value["report"]["steps"][2]["after"]["cpu"]["a"] ^ 0x100))
    mutation("retained-pointing-last-byte", lambda value: value["report"]["current"]["ram"].__setitem__(63,
        value["report"]["current"]["ram"][63] ^ 1))
    mutation("unseeded-ram-last-byte", lambda value: value["report"]["current"]["ram"].__setitem__(3967, 0))
    mutation("global-seed-inclusive-ordinal", lambda value: value["report"]["audit"]["data_events"][48].__setitem__("ordinal", 0))
    mutation("prior-program-selection-association", lambda value: value["report"]["audit"]["program_events"][0].__setitem__("selected_length", 5))
    mutation("missing-real-program-callback", lambda value: value["report"]["audit"]["program_events"].pop(0))
    mutation("raw-read-order", lambda value: value["report"]["audit"]["raw_data_events"].reverse())
    mutation("extra-after-j-fetch", lambda value: value["report"]["audit"]["program_events"].append(
        {"address": 0x5596, "serviced": True}))
    mutation("false-native-sf-claim", lambda value: value.__setitem__("physical_sf", False))
    from production_composite_negative import comparator_control, comparator_mutations
    specimen = comparator_control(root)
    for changed in comparator_mutations(specimen["expected"]):
        difference = first_difference(specimen["expected"], changed["mutated"])
        require(difference is not None, "ComparatorMissedFrozenRelationMutation:" + changed["id"])
        tests.append({"id": "closed-relation-" + changed["id"], "passed": True,
                      "metadataOnly": False, "firstMismatch": difference["field"]})
    require(len(tests) == 32, "ExactPureCodecAndSemanticComparatorControls")
    return {"classification": "ActualPureCodecAndComparatorSensitivity_NotCpuEvidence", "passed": True,
            "tests": tests, "testCount": len(tests), "cpuInstances": 0, "busInstances": 0,
            "programFetches": 0, "compositeExecutions": 0, "originalRomExecutions": 0}
