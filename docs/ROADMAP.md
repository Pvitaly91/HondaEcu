# Roadmap

Progress through these milestones is evidence-gated. A later milestone does not weaken the ROM handling policy or allow offsets to be copied across revisions.

## M0 — P28-304 core and validation harness

- ROM core
- CLI
- profiles
- diff
- patch reports
- Crome/HTS oracle harness

## M1 — First cross-editor-verified scalars

- cross-editor verified P28-304 rev limiter
- cross-editor verified VTEC crossover
- verified checksum, or a clearly documented blocked status

## M2 — Calibration maps

- low/high-cam fuel maps
- low/high-cam ignition maps
- RPM/MAP axes
- one-cell and full-table validation

## M3 — Desktop GUI

- desktop GUI
- table and graph views
- undo/redo
- patch preview

The GUI must use `HondaEcu.Core` and must not duplicate encoding, identity, patch, or verification logic.

## M4 — Additional OBD1 profiles

- additional P28/P30/P72-family profiles
- strict revision identification

Each revision receives explicit evidence and identity rules; similar size or family name is insufficient.

## M5 — P07 research

- P07 main-CPU research
- structural matching P07-303 against P28-304
- P07-specific definitions
- no automatic assumption of compatible offsets
