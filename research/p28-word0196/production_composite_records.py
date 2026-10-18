"""M2bq source draft: complete expected wire headers/control records.

Only compile-time source identities and pure arithmetic are used here. Actual
records still have to come from the separately built Rust process and compare
with every field; these records do not attest that a process has run.
"""

from hashlib import sha256
from production_composite_common import BASE_SHA, COMPOSITE_SHA, binding

HEADER_PATHS = tuple("rust/p28-slice-runner/" + name for name in (
    "src/cpu.rs", "src/bus.rs", "src/decoder.rs", "src/full_decoder.rs", "src/exec.rs",
    "src/audit.rs", "src/audit_bus.rs", "src/audit_composite.rs", "src/audit_composite_tests.rs",
    "src/audit_sha256.rs", "src/audit_tests.rs", "src/lib.rs", "src/operand.rs", "src/runner.rs",
    "src/protocol.rs", "src/main.rs", "Cargo.toml", "Cargo.lock")) + tuple(
        "research/p28-word0196/rust-production-composite/" + name for name in
        ("Cargo.toml", "Cargo.lock", "src/main.rs", "src/capabilities.rs", "closed_inputs.json")) + (
            "research/p28-word0196/rust-synthetic-adapter/src/sha256.rs",)


def header(root):
    return {"kind": "composite_header", "schema_version": 1, "exact_m2bp_base": BASE_SHA,
            "source_bindings": [binding(root, name) for name in HEADER_PATHS],
            "closed_inputs_sha256": binding(root, "research/p28-word0196/rust-production-composite/closed_inputs.json")["sha256"],
            "mechanism": "ContinuousProductionCpuBusStrictDecoderSharedExec_ClosedM2bj51Only",
            "feature": "p28-word0196-audit", "default_enabled": False, "program_base": 4096,
            "program_end_exclusive": 4147, "program_sha256": COMPOSITE_SHA,
            "closed_positive_inputs": 5470, "closed_smoke_inputs": 4, "cpu_instances": 0, "bus_instances": 0,
            "original_rom_executions": 0, "firmware_ready": False}


def program_admission():
    return {"kind": "program_admission", "accepted": True, "base": 4096, "end_exclusive": 4147,
            "length": 51, "nodes": 20, "forms": 16, "dd_streams_identical": True,
            "sha256": COMPOSITE_SHA, "cpu_instances": 0, "bus_instances": 0, "original_rom_executions": 0}


def psw_sweep():
    digest, representable = sha256(), 0
    for value in range(65536):
        accepted = value & 0x0CC8 == 0x0CC8
        digest.update(value.to_bytes(2, "little") + bytes([accepted]))
        representable += int(accepted)
    return {"kind": "psw_sweep", "inputs": 65536, "representable": representable,
            "incompatible": 65536 - representable, "classification_sha256": digest.hexdigest(),
            "cpu_instances": 0, "bus_instances": 0, "step_calls": 0}


def summary():
    return {"kind": "composite_summary", "positive_composite_executions": 5470,
            "positive_cpu_instances": 5470, "positive_bus_instances": 5470,
            "data_initializations": 5470, "functional_transitions": 5470,
            "successful_retirements": 73784, "program_admissions": 1,
            "smoke_composite_executions": 4, "smoke_cpu_instances": 4, "smoke_bus_instances": 4,
            "smoke_successful_retirements": 54,
            "psw_admission_sweep": True, "negative_capabilities_observed": True,
            "negative_records": 33, "original_rom_executions": 0, "firmware_ready": False}
