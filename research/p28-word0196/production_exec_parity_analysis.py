"""Source-bound production capability audit; no CPU execution or target payload.

This module deliberately separates source facts from runtime observations. It
cannot upgrade a hidden journal or a single step to composite execution proof.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PRODUCTION = "rust/p28-slice-runner/src/"
SOURCE_PINS = {
    "cpu.rs": "b12a0b3388a7d34201888a0a6f948263dcf1c7bebca1801056e176d871184d3b",
    "bus.rs": "556dceff088ecdfac7f05469a03251896c81fdb1979394bdbae4c59e1b30445a",
    "decoder.rs": "1120cc37cee9ec23f1f596c72ff8dd5bf372204495d2b5e00cc044dfe2ea3aa4",
    "exec.rs": "e7ef7d04fb28c838b20c52f352c89fc7ea8780d5a2e1d19f7178dec5109324aa",
    "operand.rs": "c3e7b418b81b4fa0becfa2ec2be741a4b0929994831ebb89e829698d289bb48f",
    "full_decoder.rs": "77697d4b0e3c90372326156bf1a8544486d07f4aa8f93c67cf9e5f2af6c7eff1",
    "runner.rs": "c93026e5d1152bdb8196d9a67a6dc071fd704000351b13db668eab1bff255727",
}


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def binding(relative):
    data = (ROOT / relative).read_bytes()
    return {"path": relative, "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest()}


def anchor(filename, function, needle):
    """Exact source line binding, not a runtime assertion about hidden events."""
    relative = PRODUCTION + filename
    lines = (ROOT / relative).read_text(encoding="utf-8").splitlines()
    starts = [index for index, line in enumerate(lines)
              if "fn " + function + "(" in line]
    require(len(starts) == 1, "NonUniqueFunction:" + relative + ":" + function)
    start = starts[0]
    end = next((index for index in range(start + 1, len(lines))
                if "fn " in lines[index]), len(lines))
    matches = [index + 1 for index in range(start, end) if needle in lines[index]]
    require(len(matches) == 1, "NonUniqueSourceAnchor:" + relative + ":" + needle)
    return {"source": binding(relative), "function": function,
            "line": matches[0], "exactLine": lines[matches[0] - 1].strip()}


def source_audit():
    sources = []
    for name, expected in SOURCE_PINS.items():
        actual = binding(PRODUCTION + name)
        require(actual["sha256"] == expected, "ProductionSourceChanged:" + name)
        sources.append(actual)
    rows = [
        {"capability": "SingleStepExecution",
         "classification": "DirectlyExecutableUnchanged",
         "runtimeStatus": "RequiresActualDifferentialRun",
         "evidence": [anchor("exec.rs", "step", "pub fn step(cpu:")],
         "limitation": "Finite invented single steps do not execute the M2bj composite."},
        {"capability": "NonzeroBaseProgramSegment",
         "classification": "RequiresSourceOrApiChanges",
         "runtimeStatus": "SeparateInventedCanaryBoundaryCheckRequired",
         "evidence": [anchor("bus.rs", "peek_code_u8", "self.rom.get(address).copied()"),
                      anchor("bus.rs", "fetch_code_u8", "match self.rom.get(address as usize) {")],
         "limitation": "ROM index is the absolute address; no base-offset segment API.",
         "minimalFutureChange": "Checked segment-base translation; no prefix padding or wrapping."},
        {"capability": "ProductionDecoderProbes",
         "classification": "AvailableButInsufficientlyObservable",
         "runtimeStatus": "ObservationNotAvailable",
         "evidence": [anchor("exec.rs", "step", "decode(cpu.dd, |i| bus.peek_code_u8"),
                      anchor("bus.rs", "program_reads", "pub fn program_reads(&self)")],
         "limitation": "The internal callback is not exposed; absent bytes become zero. PROGRAM table-data reads are not decoder probes.",
         "minimalFutureChange": "Strict bounded decoding callback with separately observable probe events."},
        {"capability": "IndependentDataReadWritePolicy",
         "classification": "RequiresSourceOrApiChanges",
         "runtimeStatus": "ObservationNotAvailable",
         "evidence": [anchor("bus.rs", "configure_scoped_access", "pub fn configure_scoped_access("),
                      anchor("bus.rs", "check_data_access", ".is_some_and(|ranges| !ranges.iter().any(|r| address >= r[0] && address < r[1]))")],
         "limitation": "A single data_ranges membership check applies to both operations.",
         "minimalFutureChange": "Distinct path-specific read and write policies, without widening diagnostics."},
        {"capability": "OrderedDataEffectsAndSameValueOccurrence",
         "classification": "AvailableButInsufficientlyObservable",
         "runtimeStatus": "ObservationNotAvailable",
         "evidence": [anchor("bus.rs", "end_native_accesses", "pub(crate) fn end_native_accesses("),
                      anchor("bus.rs", "end_write_journal", "pub(crate) fn end_write_journal(")],
         "limitation": "Crate-private journals cannot be used by an external path-dependent harness. Final snapshots do not reveal read order or same-value write occurrence.",
         "minimalFutureChange": "Public opt-in phase-separated logical/raw access and write events."},
        {"capability": "ErrorStateAtomicity",
         "classification": "DirectlyExecutableUnchanged",
         "runtimeStatus": "SeparateActualPartialStateCheckRequired",
         "evidence": [anchor("exec.rs", "step", "cpu.pc = pc + d.len as u16;"),
                      anchor("exec.rs", "step", "ex.run(parsed)?;")],
         "limitation": "PC/counters advance before operand execution; some failures retain partial state. No atomic-refusal claim."},
        {"capability": "CompositeEntryBudgetAndExternalExit",
         "classification": "NotEstablished",
         "runtimeStatus": "ProductionCompositeNotRun",
         "evidence": [anchor("runner.rs", "execute_in_state_observed", "fn execute_in_state_observed("),
                      anchor("exec.rs", "step", "pub fn step(cpu:")],
         "limitation": "One CPU/one seed/one step is enforced here, but mapping, independent effects and strict fetch observation block full production-composite attestation.",
         "minimalFutureChange": "Separately reviewed bounded loop plus all mapping/observation/policy prerequisites."},
    ]
    return {
        "classification": "ExistingProductionSourceCapabilityAudit_NotCompositeRuntime",
        "sourceBindings": sources,
        "capabilities": rows,
        "futureOptions": {
            "A": {"architecture": "NarrowOptInProductionApi",
                  "implemented": False,
                  "assessment": "Preferred future route if separately authorized: explicit opt-in mapping, strict fetches, independent DATA permissions and public phase journals, with formally updated source bindings and unchanged default workflows."},
            "B": {"architecture": "SeparatelyCompiledSourceBoundExecutorFork",
                  "implemented": False,
                  "assessment": "Feasible only with equivalent Bus coupling and independently verified unchanged semantic bodies. Copying step alone cannot expose concrete private Bus internals; it creates ongoing source-identity proof obligations."},
        },
        "productionBusCompositeIntegration": "NotEstablished",
        "firmwareReady": False,
    }


def validate_authority_claims(claim):
    """Reject evidence-level substitutions even when arithmetic fields agree."""
    require(claim["executionMechanism"] == "p28_slice_runner::exec::step",
            "DecoderOnlyIsNotProductionExecution")
    require(claim["actualProductionStepCalls"] > 0,
            "ProductionExecutionNotObserved")
    require(claim["hiddenProgramProbes"] == "ObservationNotAvailable",
            "HiddenDecoderEventsCannotBeReconstructed")
    require(claim["hiddenDataJournal"] == "ObservationNotAvailable",
            "InferredDataJournalIsNotObserved")
    require(claim["sameValueStoreOccurrence"] == "ObservationNotAvailable",
            "FinalMemoryIsNotSameValueOccurrenceJournal")
    require(claim["productionCompositeIntegration"] == "NotEstablished",
            "SingleStepIsNotCompositeIntegration")
    require(claim["originalRomExecutions"] == 0 and claim["nativeRejoins"] == 0
            and claim["targetArtifacts"] == 0 and claim["firmwareReady"] is False,
            "RuntimeAuthorityExceeded")
    return True
