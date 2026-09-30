//! Bounded seeded byte execution. No engine simulation or compact-code formula.

pub mod acquisition;
pub mod bus;
pub mod chain;
pub mod chain_forms;
pub mod checksum;
pub mod cpu;
pub mod decoder;
pub mod exec;
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
pub mod post_store;
pub mod producer;
pub mod protocol;
pub mod runner;
pub mod shared_calibration;
pub mod stateful;
pub mod stateful_forms;
pub mod vtec_fuel;
