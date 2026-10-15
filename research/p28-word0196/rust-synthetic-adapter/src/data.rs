use crate::{AdapterError, Result};
use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;

pub const INVENTORY: [u16; 16] = [
    0x108, 0x109, 0x10a, 0x10b, 0x10c, 0x10d, 0x10e, 0x10f, 0x117, 0x124, 0x128, 0x12a, 0x18e,
    0x18f, 0x196, 0x197,
];
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum DataPath {
    A,
    B,
    C,
    D,
}
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum WriteKind {
    RMW,
    Store,
    LocalRegisterStore,
}
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct DataEvent {
    pub ordinal: u32,
    pub phase: String,
    pub pc: u16,
    pub address: u16,
    pub width: u8,
    pub operation: String,
    pub value: u16,
    pub old_value: Option<u16>,
    pub write_ordinal: Option<u32>,
    pub kind: Option<WriteKind>,
    pub same_value: bool,
    pub constituents: Vec<u8>,
}
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct RawDataEvent {
    pub ordinal: u32,
    pub logical_ordinal: u32,
    pub address: u16,
    pub operation: String,
    pub value: u8,
}
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct AuxiliaryDataEvent {
    pub ordinal: u32,
    pub phase: String,
    pub address: u16,
    pub width: u8,
    pub value: u16,
}

/// Path selects the reviewed permission profile only. An isolated instruction
/// does not assert the corresponding composite path predicate/reachability.
pub struct IndependentDataAccessPolicy {
    path: DataPath,
    memory: BTreeMap<u16, u8>,
    pub journal: Vec<DataEvent>,
    pub raw_journal: Vec<RawDataEvent>,
    pub seed_journal: Vec<AuxiliaryDataEvent>,
    pub diagnostic_journal: Vec<AuxiliaryDataEvent>,
    fault: Option<AdapterError>,
    pending_read: BTreeMap<u16, u32>,
    write_count: u32,
    functional_started: bool,
}
impl IndependentDataAccessPolicy {
    pub fn new(path: DataPath, seeds: &BTreeMap<u16, u8>) -> Result<Self> {
        if seeds.len() != INVENTORY.len() || INVENTORY.iter().any(|a| !seeds.contains_key(a)) {
            return Err(AdapterError::new(
                "IncompleteDataInventory",
                "exact sixteen explicit invented bytes required",
            ));
        }
        let seed_journal = seeds
            .iter()
            .enumerate()
            .map(|(n, (&address, &value))| AuxiliaryDataEvent {
                ordinal: n as u32 + 1,
                phase: "SeedInitializationAccess".into(),
                address,
                width: 8,
                value: value as u16,
            })
            .collect();
        Ok(Self {
            path,
            memory: seeds.clone(),
            journal: vec![],
            raw_journal: vec![],
            seed_journal,
            diagnostic_journal: vec![],
            fault: None,
            pending_read: BTreeMap::new(),
            write_count: 0,
            functional_started: false,
        })
    }
    pub fn read_permission(path: DataPath, address: u16, width: u8) -> bool {
        match (address, width) {
            (0x108 | 0x18e, 8) | (0x196, 16) => true,
            (0x117 | 0x12a | 0x18f, 8) => path != DataPath::A,
            (0x124, 8) => matches!(path, DataPath::C | DataPath::D),
            _ => false,
        }
    }
    pub fn write_permission(path: DataPath, address: u16, width: u8) -> bool {
        width == 8 && Self::allowed_write_kind(path, address).is_some()
    }
    pub fn allowed_write_kind(path: DataPath, address: u16) -> Option<WriteKind> {
        match address {
            0x18e => Some(WriteKind::RMW),
            0x109 if path != DataPath::A => Some(WriteKind::LocalRegisterStore),
            0x117 => Some(if path == DataPath::A {
                WriteKind::Store
            } else {
                WriteKind::RMW
            }),
            0x12a if path == DataPath::D => Some(WriteKind::RMW),
            0x18f if path == DataPath::A => Some(WriteKind::Store),
            0x18f if path == DataPath::D => Some(WriteKind::RMW),
            _ => None,
        }
    }
    fn fail<T>(&mut self, code: &str, detail: impl Into<String>) -> Result<T> {
        let error = AdapterError::new(code, detail);
        if self.fault.is_none() {
            self.fault = Some(error.clone());
        }
        Err(self.fault.clone().unwrap_or(error))
    }
    fn check_live(&self) -> Result<()> {
        if let Some(fault) = &self.fault {
            Err(fault.clone())
        } else {
            Ok(())
        }
    }
    pub fn fault(&self) -> Option<&AdapterError> {
        self.fault.as_ref()
    }
    pub fn begin_functional(&mut self) -> Result<()> {
        self.check_live()?;
        if self.functional_started || !self.journal.is_empty() {
            return self.fail("FunctionalPhaseAlreadyStarted", "one bounded phase only");
        }
        self.functional_started = true;
        Ok(())
    }
    pub fn seed_word(&mut self, address: u16, value: u16) -> Result<()> {
        self.check_live()?;
        if self.functional_started || !(0x80..0xc0).contains(&address) || address & 1 != 0 {
            return self.fail("UnauthorizedSeed", "pointing words setup-only");
        }
        let [low, high] = value.to_le_bytes();
        if self.memory.contains_key(&address) || self.memory.contains_key(&(address + 1)) {
            return self.fail("DuplicateSeed", "pointing bank initialized exactly once");
        }
        self.memory.insert(address, low);
        self.memory.insert(address + 1, high);
        self.seed_journal.push(AuxiliaryDataEvent {
            ordinal: self.seed_journal.len() as u32 + 1,
            phase: "SeedInitializationAccess".into(),
            address,
            width: 16,
            value,
        });
        Ok(())
    }
    pub fn diagnostic_byte(&mut self, address: u16) -> Result<u8> {
        let value = *self.memory.get(&address).ok_or_else(|| {
            AdapterError::new("UnknownDiagnosticAddress", format!("{address:04X}"))
        })?;
        self.diagnostic_journal.push(AuxiliaryDataEvent {
            ordinal: self.diagnostic_journal.len() as u32 + 1,
            phase: "DiagnosticSnapshotRead".into(),
            address,
            width: 8,
            value: value as u16,
        });
        Ok(value)
    }
    pub fn diagnostic_word(&mut self, address: u16) -> Result<u16> {
        let high = address
            .checked_add(1)
            .ok_or_else(|| AdapterError::new("DataOverflow", "diagnostic word"))?;
        let low = self.diagnostic_byte(address)?;
        let high = self.diagnostic_byte(high)?;
        Ok(u16::from_le_bytes([low, high]))
    }
    pub fn inventory_snapshot(&mut self) -> Result<BTreeMap<u16, u8>> {
        INVENTORY
            .iter()
            .map(|&a| Ok((a, self.diagnostic_byte(a)?)))
            .collect()
    }
    pub fn read(&mut self, pc: u16, address: u16, width: u8) -> Result<u16> {
        self.check_live()?;
        if !self.functional_started {
            return self.fail("WrongDataPhase", "functional read before begin");
        }
        if !Self::read_permission(self.path, address, width) {
            return self.fail("UnauthorizedDataRead", format!("{address:04X}/{width}"));
        }
        let ordinal = self.journal.len() as u32 + 1;
        let mut bytes = Vec::new();
        for delta in 0..width / 8 {
            let raw_address = address
                .checked_add(delta as u16)
                .ok_or_else(|| AdapterError::new("DataOverflow", "raw read"))?;
            let value = *self
                .memory
                .get(&raw_address)
                .ok_or_else(|| AdapterError::new("UnknownDataAddress", "raw read"))?;
            self.raw_journal.push(RawDataEvent {
                ordinal: self.raw_journal.len() as u32 + 1,
                logical_ordinal: ordinal,
                address: raw_address,
                operation: "Read".into(),
                value,
            });
            bytes.push(value);
        }
        let value = if width == 8 {
            bytes[0] as u16
        } else {
            u16::from_le_bytes([bytes[0], bytes[1]])
        };
        self.journal.push(DataEvent {
            ordinal,
            phase: "ExecutedFunctionalDataAccess".into(),
            pc,
            address,
            width,
            operation: "Read".into(),
            value,
            old_value: None,
            write_ordinal: None,
            kind: None,
            same_value: false,
            constituents: bytes,
        });
        self.pending_read.insert(address, ordinal);
        Ok(value)
    }
    pub fn write(
        &mut self,
        pc: u16,
        address: u16,
        width: u8,
        value: u16,
        kind: WriteKind,
    ) -> Result<()> {
        self.check_live()?;
        if !self.functional_started {
            return self.fail("WrongDataPhase", "functional write before begin");
        }
        if !Self::write_permission(self.path, address, width) || value > 255 {
            return self.fail("UnauthorizedDataWrite", format!("{address:04X}/{width}"));
        }
        if Self::allowed_write_kind(self.path, address) != Some(kind) {
            return self.fail(
                "WrongDataAccessKind",
                "Store/LocalRegisterStore cannot bypass required RMW read",
            );
        }
        if kind == WriteKind::RMW {
            let proved = matches!((self.pending_read.get(&address),self.journal.last()),
                (Some(ordinal),Some(event)) if *ordinal==event.ordinal && event.operation=="Read"
                    && event.address==address && event.width==8);
            if !proved {
                return self.fail(
                    "RmwReadRequired",
                    "immediately preceding functional read of same byte required",
                );
            }
        }
        if kind == WriteKind::LocalRegisterStore && address != 0x109 {
            return self.fail("WrongLocalAlias", "local store must target r1");
        }
        // This old-value read is explicitly diagnostic, never a functional read.
        let old = self.diagnostic_byte(address)?;
        self.memory.insert(address, value as u8);
        self.write_count += 1;
        let ordinal = self.journal.len() as u32 + 1;
        self.raw_journal.push(RawDataEvent {
            ordinal: self.raw_journal.len() as u32 + 1,
            logical_ordinal: ordinal,
            address,
            operation: "Write".into(),
            value: value as u8,
        });
        self.journal.push(DataEvent {
            ordinal,
            phase: "ExecutedFunctionalDataAccess".into(),
            pc,
            address,
            width,
            operation: "Write".into(),
            value,
            old_value: Some(old as u16),
            write_ordinal: Some(self.write_count),
            kind: Some(kind),
            same_value: old == value as u8,
            constituents: vec![value as u8],
        });
        self.pending_read.remove(&address);
        Ok(())
    }
    pub fn validate_journals(&self) -> Result<()> {
        let invalid = |detail: &str| AdapterError::new("FunctionalJournalMismatch", detail);
        let mut writes = 0;
        let mut raw_cursor = 0;
        for (index, event) in self.journal.iter().enumerate() {
            if event.phase != "ExecutedFunctionalDataAccess" || event.ordinal != index as u32 + 1 {
                return Err(invalid(
                    "diagnostic/seed mixing or missing/reordered ordinal",
                ));
            }
            let count = match (event.operation.as_str(), event.width) {
                ("Read", 8) | ("Write", 8) => 1,
                ("Read", 16) => 2,
                _ => return Err(invalid("unadmitted operation width")),
            };
            let raw = self
                .raw_journal
                .get(raw_cursor..raw_cursor + count)
                .ok_or_else(|| invalid("missing acquired raw bytes"))?;
            for (delta, byte) in raw.iter().enumerate() {
                let expected_address = event
                    .address
                    .checked_add(delta as u16)
                    .ok_or_else(|| invalid("raw DATA address overflow"))?;
                if byte.ordinal != (raw_cursor + delta) as u32 + 1
                    || byte.logical_ordinal != event.ordinal
                    || byte.address != expected_address
                    || byte.operation != event.operation
                {
                    return Err(invalid("raw address/ordinal/LE order mismatch"));
                }
            }
            let bytes: Vec<_> = raw.iter().map(|b| b.value).collect();
            let value = if bytes.len() == 1 {
                bytes[0] as u16
            } else {
                u16::from_le_bytes([bytes[0], bytes[1]])
            };
            if bytes != event.constituents || value != event.value {
                return Err(invalid("raw/logical LE value mismatch"));
            }
            if event.operation == "Write" {
                writes += 1;
                if !Self::write_permission(self.path, event.address, event.width)
                    || Self::allowed_write_kind(self.path, event.address) != event.kind
                {
                    return Err(invalid("address/path-specific write kind mismatch"));
                }
                if event.write_ordinal != Some(writes)
                    || event.old_value.is_none()
                    || event.same_value != (event.old_value == Some(event.value))
                {
                    return Err(invalid("fresh ordinal/old value/same-value identity"));
                }
                if event.kind == Some(WriteKind::RMW) {
                    let prior = index
                        .checked_sub(1)
                        .and_then(|n| self.journal.get(n))
                        .ok_or_else(|| invalid("RMW lacks prior read"))?;
                    if prior.operation != "Read"
                        || prior.address != event.address
                        || prior.width != 8
                        || Some(prior.value) != event.old_value
                    {
                        return Err(invalid("RMW read/write correspondence"));
                    }
                }
            } else if !Self::read_permission(self.path, event.address, event.width)
                || event.write_ordinal.is_some()
                || event.old_value.is_some()
                || event.kind.is_some()
            {
                return Err(invalid("unauthorized read or read mislabeled as write"));
            }
            raw_cursor += count;
        }
        if writes != self.write_count || raw_cursor != self.raw_journal.len() {
            return Err(invalid("deduplicated write or hidden raw event"));
        }
        if self
            .seed_journal
            .iter()
            .any(|e| e.phase != "SeedInitializationAccess")
            || self
                .diagnostic_journal
                .iter()
                .any(|e| e.phase != "DiagnosticSnapshotRead")
        {
            return Err(invalid("auxiliary phase mixing"));
        }
        Ok(())
    }
}
