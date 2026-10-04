//! Bounded seeded byte execution. No engine simulation or compact-code formula.

pub mod acquisition;
pub mod bus;
pub mod chain;
pub mod chain_forms;
pub mod checksum;
pub mod common_result_consumer;
pub mod cpu;
pub mod data0136_handoff;
#[cfg(test)]
mod data0136_handoff_tests;
pub mod data0136_technical;
#[cfg(test)]
mod data0136_technical_tests;
pub mod decoder;
pub mod division_decision;
#[cfg(test)]
mod division_decision_tests;
pub mod exec;
pub mod p2_latch;
#[cfg(test)]
mod p2_latch_tests;
pub mod quartet_handoff;
#[cfg(test)]
mod quartet_handoff_tests;
#[cfg(test)]
mod software_word_provenance_tests;
pub mod word0196_alternate;
#[cfg(test)]
mod word0196_alternate_tests;
pub mod word0196_handoff;
#[cfg(test)]
mod word0196_handoff_tests;
// Preserve the pinned generated opcode table verbatim.
#[rustfmt::skip]
pub mod full_decoder;
pub mod adaptive;
pub mod adaptive_fuel;
pub mod fuel;
pub mod fuel_additive;
pub mod fuel_calculation;
pub mod fuel_factor;
pub mod idle;
pub mod idle_contexts;
pub mod ignition;
pub mod ignition_correction;
pub mod ignition_selector;
pub mod instruction_forms;
pub mod limiter;
pub mod limiter_fuel;
pub mod operand;
pub mod post_selection_critical;
pub mod post_store;
pub mod post_store_consumer;
pub mod producer;
pub mod protocol;
pub mod runner;
pub mod shared_calibration;
pub mod stateful;
pub mod stateful_forms;
pub mod vtec_fuel;
