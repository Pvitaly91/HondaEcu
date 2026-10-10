"""Invented-only contract/type/address/provenance checks, not target execution.

Values below are invented algebra inputs and proposal corruptions. They are
not ROM instruction streams, native traces, actual runtime state or a target
calling convention. Success never grants code-generation/firmware permission.
"""

from copy import deepcopy
from pathlib import Path
import json
import sys

sys.dont_write_bytecode = True

from validate_target_contract import (
    context_geometry, demand, expect, load_contract, project_host_snapshot,
    validate, verify_ordered_effects, word_from_bytes,
)


def replace(path, value):
    def mutate(contract):
        parent = contract
        for key in path[:-1]:
            parent = parent[key]
        parent[path[-1]] = deepcopy(value)
    return mutate


def base_state():
    return {
        "a": 0xA55A, "psw": 0xBFE2, "pc": 0x556F, "lrb": 0x21,
        "x1": 0x1248, "x2": 0x369C, "dp": 0x2346, "usp": 0x2468,
        "ssp": 0x7FE, "sf": True, "halted": False,
        "local": [0, 17, 34, 51, 68, 85, 102, 119],
        "ram0117": 3, "ram0124": 32, "ram0128": 4, "ram012a": 128,
        "ram018e": 0, "ram018f": 1, "ram0196": [0xEF, 0xBE],
    }


def run_tests(contract):
    cases = []

    def passed(name, kind, vectors=1):
        cases.append({"name": name, "kind": kind, "vectors": vectors,
                      "classification": "InventedContractLogicOnly", "passed": True})

    def positive(name, action):
        action()
        passed(name, "Positive")

    def refusal(name, action):
        try:
            action()
        except ValueError:
            passed(name, "Negative")
            return
        raise ValueError(f"Malformed contract/proposal was accepted: {name}")

    positive("closed_bounded_profile", lambda: validate(contract))
    positive("offline_snapshot_never_native_owner", lambda: expect(
        project_host_snapshot(base_state())["nativeOwner"], False, "Host owner promoted"))
    positive("exact_LRB21_page0100_local0108", lambda: expect(
        context_geometry(0x21, 2), {"localBankBase": 0x108, "currentPage": 0x100,
                                  "scb": 2, "pointingRegisterBankBase": 0x90}, "Wrong bank"))
    positive("alternative_LRB20_alias_architecture_only", lambda: expect(
        context_geometry(0x20, 2)["localBankBase"], 0x100, "Alternative bank alias wrong"))
    positive("AL_AH_are_parts_of_A", lambda: expect(
        [project_host_snapshot(base_state())["al"], project_host_snapshot(base_state())["ah"]],
        [0x5A, 0xA5], "Wrong AL/AH alias"))
    positive("word0196_uses_LE_bytes_not_host_pointer", lambda: expect(
        project_host_snapshot(base_state())["word0196"], 0xBEEF, "Wrong LE word"))
    positive("SF_symbol_location_unknown_not_PSW_or_defaultzero", lambda: expect(
        project_host_snapshot(base_state())["sfNativeCounterpart"],
        "PrimaryConflictUnresolved;NoPhysicalBooleanMapping", "SF mode promoted"))
    positive("halted_not_ordinary_native_register", lambda: expect(
        project_host_snapshot(base_state())["haltedNativeRegister"], False, "Wrong halted mapping"))
    effects = [
        {"site": "5572", "address": 0x18E, "widthBits": 8, "old": 0, "new": 0},
        {"site": "55C1", "address": 0x117, "widthBits": 8, "old": 15, "new": 15},
        {"site": "55C3", "address": 0x18F, "widthBits": 8, "old": 15, "new": 15},
    ]
    positive("same_value_stores_keep_separate_ordered_effects", lambda: verify_ordered_effects(effects, deepcopy(effects)))
    positive("two_native_continuations_not_RT", lambda: expect(
        [r["pc"] for r in contract["firmwareIntegration"]["exit"]["targets"]], [0x5596, 0x55C5], "Wrong exits"))
    positive("compiler_assembler_integration_are_distinct_layers", lambda: expect(
        [contract["compilerAbi"]["status"], contract["toolchains"][0]["classification"],
         contract["firmwareIntegration"]["status"]],
        ["CompilerAbiNotEstablished", "AssemblerTargetSupportDocumented", "FirmwareIntegrationNotEstablished"],
        "Layers conflated"))
    positive("unknown_ABI_values_remain_null_not_zero", lambda: demand(
        all(row["value"] is None for row in contract["compilerAbi"]["unknownFields"]), "Unknown default"))

    mutations = [
        ("host_replay_claimed_actual_native_entry", replace(["firmwareIntegration", "entry", "contextSource"], "HostReplayState")),
        ("basic_block_replaced_by_C_function_entry", replace(["firmwareIntegration", "entry", "classification"], "NativeSubroutineEntry")),
        ("ordinary_C_call_permission", replace(["firmwareIntegration", "entry", "ordinaryCCallAllowed"], True)),
        ("LRB20_replaces_required21", replace(["architectureContract", "bankContext", "requiredLrb"], 0x20)),
        ("local_bank_base0100_for_LRB21", replace(["architectureContract", "bankContext", "localBankBase"], 0x100)),
        ("SCB_forced_to_historical2", replace(["architectureContract", "bankContext", "scbFormula"], "2")),
        ("pointing_bank_wrong_alias", replace(["architectureContract", "bankContext", "historicalPointingStorage"], [0x80, 0x87])),
        ("AH_preservation_waived", replace(["firmwareIntegration", "preservedContext"], contract["firmwareIntegration"]["preservedContext"][1:])),
        ("CF_wrong_mask", replace(["architectureContract", "flagRequirements", 0, "mask"], 0x4000)),
        ("HC_writer_invented", replace(["architectureContract", "flagRequirements", 2, "changes"], ["LB556F"])),
        ("DD_replaced_by_entry_seed", replace(["firmwareIntegration", "entry", "dd"], "HostDD0Required")),
        ("SSP_unknown_defaults_zero", replace(["architectureContract", "stackRequirements", "actualEntryValue"], 0)),
        ("technical7FE_claimed_actual_frame", replace(["architectureContract", "stackRequirements", "frameAvailability"], "Established")),
        ("SSP_safe_internal_RAM_assumed", replace(["architectureContract", "stackRequirements", "unknownSspMayAliasRegistersRamOrSfr"], False)),
        ("native_RT_implicitly_allowed", replace(["firmwareIntegration", "exit", "ordinaryRTAllowed"], True)),
        ("implicit_C_return_instead_continuation", replace(["firmwareIntegration", "exit", "implicitCReturnAllowed"], True)),
        ("wrong_second_continuation", replace(["firmwareIntegration", "exit", "targets", 1, "pc"], 0x5688)),
        ("continuation_CF_forged", replace(["firmwareIntegration", "exit", "targets", 1, "cf"], 0)),
        ("missing_relevant_RAM", lambda x: x["architectureContract"]["ramAccessMap"].pop()),
        ("word0196_big_endian", replace(["architectureContract", "ramAccessMap", 7, "byteOrder"], "BigEndian")),
        ("data_program_space_conflated", replace(["architectureContract", "addressSpaces", "distinct"], False)),
        ("same_value_stores_elided", replace(["firmwareIntegration", "semanticObligations", "sameValueWrites"], "MayElide")),
        ("compiler_reordered_writes_allowed", replace(["firmwareIntegration", "semanticObligations", "compilerReorderingAllowed"], True)),
        ("volatile_claims_full_native_equivalence", replace(["firmwareIntegration", "semanticObligations", "volatileAloneEstablishesEquivalence"], True)),
        ("missing_exact_compiler_target_proof_hidden", replace(["compilerAbi", "nativeCCompiler"], "Verified")),
        ("CC665S_cross_family_200_compatibility", replace(["toolchains", 1, "nx8_200Compatibility"], "Verified")),
        ("assembler_documentation_claims_C_ABI", replace(["toolchains", 0, "compilerAbiEstablished"], True)),
        ("host_struct_size_equals_native_RAM", replace(["compilerAbi", "hostStructIsNativeLayout"], True)),
        ("host_pointer_cast_to_native_address", replace(["compilerAbi", "absoluteHostPointerCastAllowed"], True)),
        ("unverified_archived_tool_executed", replace(["permissions", "unverifiedToolchainExecution"], True)),
        ("documentation_equals_verified_executable", replace(["toolchains", 0, "executableVerified"], True)),
        ("host_annotation_claims_native_runtime_owner", replace(["firmwareIntegration", "provenance", "nativeOwnerAcceptedFromHost"], True)),
        ("second_machine_data_handoff", replace(["firmwareIntegration", "provenance", "secondMachineHandoffAllowed"], True)),
        ("invented_register_prologue", replace(["firmwareIntegration", "entry", "inventedRegisterPrologueAllowed"], True)),
        ("hidden_stack_modification", replace(["architectureContract", "stackRequirements", "hiddenStackWritesAllowed"], True)),
        ("invalid_source_generation_stale_equal_value", replace(["firmwareIntegration", "provenance", "staleEqualValueAccepted"], True)),
        ("source_missing_defaults_zero", replace(["firmwareIntegration", "provenance", "unknownSourceDefaultZero"], True)),
        ("unknown_peripheral_effect_defaults_zero", replace(["firmwareIntegration", "provenance", "unknownPeripheralDefaultZero"], True)),
        ("P2_operation_inside_fragment", replace(["firmwareIntegration", "exit", "p2ExecutionAllowed"], True)),
        ("unsupported_firmware_readiness", replace(["permissions", "firmwareReady"], True)),
        ("false_target_compilation_from_host_build", replace(["permissions", "targetCompilation"], True)),
        ("host_build_claims_target_build", replace(["compilerAbi", "hostCompilationImpliesTargetCompilation"], True)),
        ("customer_ASIC_identity_from_standard_map", replace(["target", "customerAsicIdentity"], "VerifiedFromRomSize")),
        ("SF_nX300_mode_imported_to200", replace(["architectureContract", "stackRequirements", "sfFromCrossFamilyApplied"], True)),
        ("SF_assigned_PSW_reserved_bit", replace(["architectureContract", "registerMappings", 11, "nativeLocation"], "PSW.11")),
        ("halted_becomes_native_register", replace(["architectureContract", "registerMappings", 12, "status"], "ConfirmedArchitecture")),
        ("derived_table_promoted_manufacturer_proof", replace(["evidenceSources", 7, "classification"], "ManufacturerPrimary")),
        ("actual_ROM_count_fabricated", replace(["scope", "actualRomExecutions"], 1)),
        ("target_object_generated", replace(["permissions", "targetObject"], True)),
        ("missing_ABI_dependency", lambda x: x["compilerAbi"]["unknownFields"].pop()),
        ("unknown_ABI_pointer_width_assumed16", replace(["compilerAbi", "unknownFields", 14, "value"], 16)),
        ("unknown_ABI_defaults_zero", replace(["compilerAbi", "unknownIsZero"], True)),
        ("raw_private_native_owner_key", lambda x: x["firmwareIntegration"]["provenance"].update(nativeOwnerId="Invented")),
        ("0197_high_byte_wrong_address", replace(["architectureContract", "ramAccessMap", 7, "highByteAddress"], 0x198)),
        ("odd_word0197_claimed_fault_not_alignment", replace(["architectureContract", "wordAliasMap", "oddWord0197EffectiveAddress"], 0x197)),
        ("alias_geometry_grants_new_access", replace(["architectureContract", "wordAliasMap", "aliasesGrantAccessPermission"], True)),
        ("register_SFR_uses_host_struct_offset", replace(["architectureContract", "registerMappings", 3, "nativeDataAddress"], 2)),
        ("unestablished_target_equivalence_promoted", replace(["scope", "targetMachineCodeEquivalence"], "Established")),
        ("invented_path13_native_witness", replace(["firmwareIntegration", "provenance", "nativePath13Witnesses"], 1)),
        ("native_entry_reseed_permission", replace(["firmwareIntegration", "provenance", "reseedAt556FAllowed"], True)),
        ("Boolean_integer_permission_substitution", replace(["permissions", "firmwareReady"], 0)),
        ("SF_primary_conflict_silently_resolved", replace(["architectureContract", "registerMappings", 11, "evidenceInterpretations"], [])),
        ("SF_host_bool_width_becomes_native_width", replace(["architectureContract", "registerMappings", 11, "nativeWidthBits"], 1)),
        ("hidden_register_compilation_permission", lambda x: x["architectureContract"]["registerMappings"][0].update(targetCompilation=True)),
        ("hidden_RAM_peripheral_permission", lambda x: x["architectureContract"]["ramAccessMap"][0].update(peripheralAccess=True)),
        ("hidden_tool_abi_permission", lambda x: x["toolchains"][0].update(argumentPassing="Invented")),
        ("66207_full_RAM_range_guessed_from_size", replace(["target", "standardDeviceMemory", "MSM66207", "internalRamEnd"], 0x47F)),
        ("physical_word0196_RPM_role_invented", replace(["architectureContract", "ramAccessMap", 7, "physicalRole"], "RPM")),
        ("changed_production_runner_identity", replace(["preservation", "runnerVersion"], "0.44.0")),
        ("CC_arbitrary_T_M66201_claims_200_support", replace(["toolchains", 1, "typeStringEstablishesTargetSupport"], True)),
        ("M66207_DCL_guessed_from_naming", replace(["toolchains", 0, "exactDeviceDcl", "MSM66207"], "Verified")),
        ("DCL_manual_equals_acquired_distribution", replace(["toolchains", 0, "matchingDclAcquired"], True)),
        ("v2_v4_object_formats_assumed_compatible", replace(["toolchains", 0, "objectVersionCompatibility", "v2_to_v4"], "Compatible")),
        ("OH_HEX_conversion_claims_flat_BIN", replace(["toolchains", 0, "conversion", "flatBinEstablished"], True)),
        ("USING_directive_claims_register_initialization", replace(["toolchains", 0, "usingInitializesNativeRegisters"], True)),
        ("assembler_syntax_claims_all15_form_encodings_verified", replace(["toolchains", 0, "full15FormEncodingVerified"], True)),
        ("AH_preservation_prose_allows_compiler_clobber", replace(["architectureContract", "registerMappings", 2, "preservation"], "May clobber AH in compiler prologue")),
        ("HC_liveout_prose_allows_change", replace(["architectureContract", "flagRequirements", 2, "liveOut"], "HC may change")),
        ("DATA0196_owner_prose_accepts_host_generation", replace(["architectureContract", "ramAccessMap", 7, "ownership"], "Host-computed new generation is accepted")),
        ("A_source_promoted_from_derived_assembler", replace(["architectureContract", "registerMappings", 0, "sourceRefs"], ["ASM662"])),
        ("routeA_required_evidence_empty_strings", replace(["codeGenerationRoutes", 0, "requiredEvidence"], ["", "", "", "", "", ""])),
        ("routeA_CC665S500S_to_200_firmware", replace(["codeGenerationRoutes", 0, "route"], "CC665S500S->MSM66201Firmware")),
        ("source_pages_nested_firmware_grant", replace(["evidenceSources", 0, "pages"], [{"firmwareReady": True}])),
        ("source_URL_nested_target_compilation_grant", replace(["evidenceSources", 0, "url"], {"targetCompilation": True})),
        ("register_owner_nested_stack_grant", replace(["architectureContract", "registerMappings", 0, "ownership"], {"hiddenStackWritesAllowed": True})),
        ("route_tools_nested_executable_verification_grant", replace(["codeGenerationRoutes", 0, "foundTools"], [{"executableVerified": True}])),
        ("ASM_core_prose_imports500S_binary_compatibility", replace(["toolchains", 2, "documentedCore"], "nX-8/500S binary compatible with200")),
        ("MAC_host_source_misused_as_manufacturer_proof", replace(["toolchains", 0, "sourceRefs"], ["M2AV"])),
        ("CF_source_from_derived_assembler", replace(["architectureContract", "flagRequirements", 0, "sourceRefs"], ["ASM662"])),
        ("DATA0196_host_source_as_native_owner_proof", replace(["architectureContract", "ramAccessMap", 7, "sourceRefs"], ["M2AV"])),
        ("prior_stack_frame_absence_invented_from_branch_entry", replace(["architectureContract", "stackRequirements", "priorCallFrames"], "Absent")),
        ("logical_bool_domain_claimed_C_storage_size", replace(["architectureContract", "registerMappings", 11, "widthBasis"], "CStorageSizeOneBit")),
    ]
    for name, mutate in mutations:
        malformed = deepcopy(contract)
        mutate(malformed)
        refusal(name, lambda malformed=malformed: validate(malformed))

    for key, value in [("lrb", 0x20), ("ssp", None), ("psw", None), ("pc", 0x5596), ("halted", True)]:
        state = base_state()
        state[key] = value
        refusal(f"replay_refuses_unknown_or_wrong_{key}", lambda state=state: project_host_snapshot(state))
    refusal("reordered_invented_effect_ledger", lambda: verify_ordered_effects(effects, list(reversed(effects))))
    refusal("equal_value_write_merged", lambda: verify_ordered_effects(effects, effects[1:]))
    hidden = deepcopy(effects)
    hidden[0]["nativeOwnerId"] = "Invented"
    refusal("effect_annotation_not_native_authority", lambda: verify_ordered_effects(effects, hidden))
    peripheral = deepcopy(effects)
    peripheral[0]["address"] = 0x24
    refusal("effect_peripheral_address_excluded", lambda: verify_ordered_effects(effects, peripheral))
    swapped = deepcopy(effects)
    swapped[0]["address"] = 0x109
    refusal("site_to_DATA_mapping_cannot_be_cross_product", lambda: verify_ordered_effects(swapped, swapped))
    same_forged_order = list(reversed(effects))
    refusal("expected_ledger_itself_cannot_authorize_wrong_path_order",
            lambda: verify_ordered_effects(same_forged_order, same_forged_order))

    # Independent finite-domain arithmetic identities, not instruction execution.
    for a in range(65536):
        low, high = a % 256, a // 256
        expect(word_from_bytes(low, high), a, "LE byte algebra mismatch")
        expect(((a & 0xFF00) | ((low + 1) % 256)) >> 8, high, "AH preservation identity")
    passed("all_u16_LE_word_and_AL_AH_preservation_identities", "Property", 65536)

    for psw in range(65536):
        geometry = context_geometry(0x21, psw)
        expect(geometry["scb"], psw % 8, "SCB arithmetic mismatch")
        expect(geometry["pointingRegisterBankBase"], 0x80 + 8 * (psw % 8), "PR bank mismatch")
        for name, bit in [("CF", 15), ("ZF", 14), ("HC", 13), ("DD", 12)]:
            mask = next(row["mask"] for row in contract["architectureContract"]["flagRequirements"] if row["name"] == name)
            expect(bool(psw & mask), bool((psw // (2 ** bit)) % 2), "Flag projection mismatch")
    passed("all_PSW_SC_B_and_flag_projection_identities", "Property", 65536)

    banks = list(range(512)) + [0x1000, 0x1FFF, 0x2000, 0x7FFF, 0x8000, 0xFFDF, 0xFFE0, 0xFFFF]
    for lrb in banks:
        for scb in range(8):
            geometry = context_geometry(lrb, scb)
            page_number = (lrb // 32) % 256
            slot_number = lrb % 32
            expect(geometry["currentPage"], page_number * 256, "Page bit-field mismatch")
            expect(geometry["localBankBase"], page_number * 256 + slot_number * 8, "Local bit-field mismatch")
            expect(geometry["pointingRegisterBankBase"], 0x80 + scb * 8, "PR bank independent of LRB")
    passed("LRB_page_local_geometry_all_low9_and_high_boundaries_times8_SCB", "Property", len(banks) * 8)

    retained_mask = (~(0x8000 | 0x4000 | 0x1000)) & 0xFFFF
    for psw in range(65536):
        for cf in [0, 1]:
            # The two exit annotations are CF0/CF1, ZF0/DD0; HC/OtherPSW retained.
            annotated_exit = (psw & retained_mask) | (cf << 15)
            expect(annotated_exit & retained_mask, psw & retained_mask, "Retained PSW annotation mismatch")
            expect(annotated_exit & 0x5000, 0, "Exit ZF/DD annotation mismatch")
            expect((annotated_exit >> 15) & 1, cf, "Exit branch CF annotation mismatch")
    passed("both_exit_flag_annotations_retain_HC_otherPSW_for_all_inputs", "Property", 131072)

    positives = sum(row["kind"] == "Positive" for row in cases)
    negatives = sum(row["kind"] == "Negative" for row in cases)
    properties = sum(row["kind"] == "Property" for row in cases)
    return {
        "milestone": "M2aw", "suite": "bounded-target-contract-invented-only",
        "passed": True, "tests": len(cases), "positiveCases": positives,
        "negativeCases": negatives, "propertyCases": properties,
        "propertyVectors": sum(row["vectors"] for row in cases if row["kind"] == "Property"),
        "failures": 0, "skipped": 0, "inventedOnly": True,
        "actualRomExecutions": 0, "firmwareBin": 0, "targetToolExecutions": 0,
        "nativeAbiEstablishedByTests": False, "cases": cases,
    }


if __name__ == "__main__":
    demand(len(sys.argv) <= 2, "Only one contract JSON path is accepted")
    path = Path(sys.argv[1]) if len(sys.argv) == 2 else Path(__file__).with_name("target_abi_contract.json")
    print(json.dumps(run_tests(load_contract(path)), sort_keys=True))
