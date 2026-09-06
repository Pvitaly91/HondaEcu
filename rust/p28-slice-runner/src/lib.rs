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
pub mod instruction_forms;
pub mod operand;
pub mod producer;
pub mod protocol;
pub mod runner;
pub mod stateful;
pub mod stateful_forms;
