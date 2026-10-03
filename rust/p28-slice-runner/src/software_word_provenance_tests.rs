//! Invented memory-only programs. No OEM routine/caller or native M2u operation.
use crate::{bus::Bus, cpu::Cpu, exec::step, protocol::Request, runner::run_request};

fn execute(cpu: &mut Cpu, bus: &mut Bus, count: usize) -> Vec<[u32; 5]> {
    bus.begin_native_accesses();
    for _ in 0..count {
        bus.set_native_pc(cpu.pc);
        step(cpu, bus).unwrap();
        assert!(bus.take_fault().is_none());
    }
    bus.end_native_accesses()
}

#[test]
fn invented_word_producer_native_read_register_transfer_and_divisor_read() {
    // Native MOV DP,#0300; L A,#321; ST [DP]; L [DP]; MOV er2,A;
    // CLR er0; L A,#1026; DIV. All source constants are invented.
    let mut bus = Bus::new(
        vec![
            0x62, 0, 3, 0x67, 0x41, 1, 0xD2, 0xE2, 0x46, 0x8A, 0x44, 0x15, 0x67, 2, 4, 0x90, 0x37,
        ],
        0,
    );
    let mut cpu = Cpu::new();
    cpu.lrb = 0x43;
    let ledger = execute(&mut cpu, &mut bus, 8);
    let source: Vec<_> = ledger.iter().filter(|a| a[1] == 0x300).collect();
    assert_eq!(
        source,
        vec![&[6, 0x300, 16, 1, 321], &[7, 0x300, 16, 0, 321]]
    );
    assert!(ledger.contains(&[8, 0x21C, 16, 1, 321]));
    assert!(ledger.contains(&[15, 0x21C, 16, 0, 321]));
    assert_eq!(cpu.a, 3);
    assert_eq!(cpu.pc, 17);
}

#[test]
fn invented_two_same_value_native_stores_remain_separate_and_next_event_holds() {
    // Sequential same-value stores followed by a read, on the SAME CPU/RAM.
    let mut bus = Bus::new(vec![0x62, 0, 3, 0x67, 0x41, 1, 0xD2, 0xD2, 0xE2], 0);
    let mut cpu = Cpu::new();
    let first = execute(&mut cpu, &mut bus, 4);
    let writes: Vec<_> = first
        .iter()
        .filter(|a| a[1] == 0x300 && a[3] == 1)
        .collect();
    assert_eq!(
        writes,
        vec![&[6, 0x300, 16, 1, 321], &[7, 0x300, 16, 1, 321]]
    );
    let second = execute(&mut cpu, &mut bus, 1);
    assert_eq!(
        second
            .iter()
            .filter(|a| a[1] == 0x300)
            .copied()
            .collect::<Vec<_>>(),
        vec![[8, 0x300, 16, 0, 321]]
    );
    assert!(second.iter().all(|a| a[3] == 0));
}

#[test]
fn invented_partial_producer_keeps_completed_word_without_skipping_unknown_form() {
    let mut bus = Bus::new(vec![0x62, 0, 3, 0x67, 0x41, 1, 0xD2, 0xFF], 0);
    let mut cpu = Cpu::new();
    let prefix = execute(&mut cpu, &mut bus, 3);
    assert!(prefix.contains(&[6, 0x300, 16, 1, 321]));
    // Strict test harness stops here: BRK/hardware entry is not an admitted continuation.
    assert_eq!(cpu.pc, 7);
    assert_eq!(bus.read_data_u16(0x300), 321);
    assert_eq!(cpu.instructions, 3);
}

#[test]
fn unestablished_m2u_operation_version_and_ready_source_are_refused() {
    let base = serde_json::json!({"protocolVersion":1,"operation":"fuelData0136ProducerChain",
        "images":[{"id":"invented","rom":[0]}],"allowAssumptions":[],"scratchPatterns":[0]});
    let request: Request = serde_json::from_value(base.clone()).unwrap();
    assert_eq!(run_request(request).unwrap_err(), "unsupported operation");
    let mut version = base.clone();
    version["protocolVersion"] = 2.into();
    assert_eq!(
        run_request(serde_json::from_value(version).unwrap()).unwrap_err(),
        "unsupported protocol version"
    );
    let mut ready = base;
    ready["producerReadyValue"] = 321.into();
    assert!(serde_json::from_value::<Request>(ready).is_err());
}
