# P28-304 public evidence ledger

## Scope and reading rules

This file records **research leads**, not verified calibration definitions. The principal PGMFI page says “304stock.bin is assumed for rom map”; it does not publish a cryptographic hash for that baseline, identify the market/transmission/ECU label represented by the file, or provide a reproducible validation log. Accordingly:

- every address below is scoped only to the page's assumed `304stock.bin` code base;
- a RAM/data-space address is not a raw-ROM file offset;
- an inclusive range is transcribed as a range, not silently reshaped into a table;
- a label such as “mBar scale” is not a conversion formula;
- a published bypass is not a verified algorithm or a safe recommendation;
- no address is inherited by another P28, P30, P72, or P07 revision;
- all current entries remain `public-documentation`, candidate/read-only, and unavailable to CLI patching.

Access date for all sources: **2026-09-04**.

## Source provenance

### GitHub sources pinned to exact revisions

| ID | Source and pinned revision | Purpose and what it supports | Known limitations | Oracle? | Specifically tested on P28-304? |
|---|---|---|---|---|---|
| `PGMFI-P28` | [hondabase/files-archive at `06d2eb0d9b37c6b1bd001254203790751457b4a7`](https://github.com/hondabase/files-archive/tree/06d2eb0d9b37c6b1bd001254203790751457b4a7), specifically [P28.html](https://github.com/hondabase/files-archive/blob/06d2eb0d9b37c6b1bd001254203790751457b4a7/pgmfiorg/twiki/bin/view/Library/P28.html) (blob `b4830bdd4f22ea0029291c8a2806751e04cd16aa`) | Preserved PGMFI community ROM/RAM map. It explicitly says the map assumes `304stock.bin` and supplies the addresses transcribed below. | TWiki revision r1.8 is dated 2005-07-26; this is community documentation, not Honda documentation. No baseline hash, test protocol, table encoding/shape, or checksum algorithm is supplied. Several rows use tentative wording. | **No.** It is documentation evidence, not a program that independently transforms the local baseline. | **Claimed scope only.** The page assumes `304stock.bin`, but does not provide an independently reproducible P28-304 test record. |
| `PGMFI-RPM16` | Same repository/commit; [OBD1_16bitRPM.html](https://github.com/hondabase/files-archive/blob/06d2eb0d9b37c6b1bd001254203790751457b4a7/pgmfiorg/twiki/bin/view/Library/OBD1_16bitRPM.html) (blob `8c66795455ee61a35684f43ff74a8986aac56dfa`) | States `RPM = 1,875,000 / raw` and says OBD1 16-bit values are little-endian. P28.html links it from RAM current RPM. | Broad OBD1 assertion; it supplies no P28-304 trace, zero-input behavior, rounding rule, or atomic RAM-read procedure. | No. | No reproducible P28-304 test is included. |
| `PGMFI-RPM8` | Same repository/commit; [OBD1_8bitLowCamRPM.html](https://github.com/hondabase/files-archive/blob/06d2eb0d9b37c6b1bd001254203790751457b4a7/pgmfiorg/twiki/bin/view/Library/OBD1_8bitLowCamRPM.html) (blob `627572ff82526c2e0eef83833ea49868ec0b810e`) | P28.html links it from `0x6543`. It presents two piecewise 8-bit low-cam RPM calculations. | The page says input is “0 to 256” despite an 8-bit label, says the two integer approaches differ, and contains an explicit editorial dispute over exactness. There is no unambiguous inverse encoding/rounding contract. | No. | No reproducible P28-304 test is included. |
| `ASM662` | [VIRUXE/asm662 at `94612d10370eb4ddf97d4f349168298e1a3da8a0`](https://github.com/VIRUXE/asm662/tree/94612d10370eb4ddf97d4f349168298e1a3da8a0) | Assembler/disassembler toolkit for OKI 66201/66207/66301 and a shared opcode description. It can support future instruction-level static checks. | Correct decoding does not identify calibration meaning, revision, conversion, checksum coverage, or physical behavior. Its README does not record a P28-304/hash-specific validation. | **No** as an editor oracle; **yes** as one static-analysis aid when used reproducibly. | No. |
| `GHIDRA-66207` | [VIRUXE/ghidra-oki66207 at `fe88d013bb73922ddd38808d765fac2d3ebac9cc`](https://github.com/VIRUXE/ghidra-oki66207/tree/fe88d013bb73922ddd38808d765fac2d3ebac9cc) | Ghidra processor module for OKI 66201/66207/66301. Its README describes separate program/data spaces, a P28 language variant, instruction semantics, and cross-checking against `dasm662` on an OEM P28 ROM. | The README does not identify the checked P28 by hash or as P28-304. It lists modeling limitations and explicitly is not cycle-exact. Decompiled output still requires analyst proof of each claimed parameter. | **No** as an editor oracle; **yes** as a static-analysis aid. | No; “OEM P28” is not revision-specific evidence. |
| `HONDAECU-EMU` | [VIRUXE/hondaecu-cli at `85b30752473ca9979e4ad9b307ea05a30c0b3d1e`](https://github.com/VIRUXE/hondaecu-cli/tree/85b30752473ca9979e4ad9b307ea05a30c0b3d1e) | Experimental Rust OKI MSM66207/P28 emulator and inspection suite. It can support future controlled traces of candidate data/code references. | Its README states that it is not a physical-ECU validator and lists incomplete timing, peripheral, output, and board behavior. Examples identify P28-230/custom ROMs; some ROM-backed tests skip without private images. | **No** as an editor oracle; **yes** as an emulator observation source only after a pinned, reproducible experiment. | No P28-304/hash-specific experiment is documented in the cited revision. |

### Official editor pages

| ID | Source | Purpose and what it supports | Known limitations | Oracle? | Specifically tested on P28-304? |
|---|---|---|---|---|---|
| `CROME-OFFICIAL` | [Crome official site](https://crome.io/) | Describes Crome as an OBD1 Honda ROM editor; explicitly lists P28/P30/P72 ROMs, RPM/VTEC adjustments, table/graph editing, plugins, and datalogging. On the access date it listed stable version 1.7.6, released 2026-02-02. | The page provides no P28-304 hash, offsets, encodings, checksum algorithm, save-normalization behavior, or claim that all editions/revisions behave identically. | **Yes, conditionally:** a manually controlled, exact-version local run can produce `crome-observed` evidence. The website alone cannot. | No public P28-304 result on the cited page; local golden files are still required. |
| `HTS-OFFICIAL` | [Honda Tuning Suite official site](https://hondatuningsuite.com/) | Describes HTS as free for OBD1 and lists fuel/timing manipulation, cut-off/calibration, and VTEC. The newest release article listed on the access date was 2.22, dated 2023-05-25. | The landing page does not identify P28-304, offsets, encodings, checksum behavior, or no-op save changes. The listed-news version is not necessarily the locally installed version. | **Yes, conditionally:** a manually controlled, exact-version local run can produce `hts-observed` evidence. The website alone cannot. | No public P28-304 result on the cited page; local golden files are still required. |

“Oracle” here means an independent, reproducible observation under the workflows in this repository. It does not mean absolute truth or bench validation.

Licensing note: the archived PGMFI page's footer identifies CC BY-NC-SA 1.0 for contributed material; the pinned `asm662` README describes its original code as BSD-style licensed; the pinned Ghidra module and emulator identify the Unlicense. HondaEcu only paraphrases evidence and links to these sources—it does not copy their code, an OEM ROM, or a complete disassembly. License review is still required before any future code reuse.

## Transcribed P28-304 leads

All offsets are hexadecimal. “CLI write?” answers whether M0 permits `hondaecu patch` to write the item under the experimental profile. **Every answer is No.** Candidate metadata may be visible through profile inspection, but unsupported encodings are not safely decoded by `read` or encoded by `patch`.

### Runtime RAM/data-space leads

These are runtime data addresses, not offsets in a 32 KiB ROM file.

| Parameter/area | Claimed address | Claimed format | Source | Scope | Validation level | Remaining confirmation | CLI write? |
|---|---:|---|---|---|---|---|---|
| Current RPM | DATA/RAM `0x00C4` | 2 bytes; linked page says unsigned 16-bit little-endian period and `RPM = 1,875,000 / raw` | `PGMFI-P28`, `PGMFI-RPM16` | P28 map assuming `304stock.bin`; formula page speaks broadly about OBD1 | `public-documentation` | Prove code producer/consumer, byte-consistent sampling, raw zero handling, integer/engineering rounding, and a P28-304 trace | No—raw-ROM CLI does not access live RAM |
| MAP | DATA/RAM `0x00BB` | 1 byte; note says 0–5 V corresponds to `0x00`–`0xFF` | `PGMFI-P28` | P28 map assuming `304stock.bin` | `public-documentation` | Prove direction and exact scaling/rounding, identify where/how RAM is populated, correlate with calibrated input and static references | No—raw-ROM CLI does not access live RAM |
| VSS | DATA/RAM `0x00CC` | 1 byte; unit labelled km/h; no conversion stated | `PGMFI-P28` | P28 map assuming `304stock.bin` | `public-documentation` | Determine raw-to-km/h formula, saturation/rounding, producer/consumers, and controlled trace/bench correlation | No—raw-ROM CLI does not access live RAM |
| ECT | DATA/RAM `0x00D9` | 1 byte; no units or conversion stated | `PGMFI-P28` | P28 map assuming `304stock.bin` | `public-documentation` | Determine lookup/conversion, thermistor/calibration relationship, producer/consumers, and controlled trace/bench correlation | No—raw-ROM CLI does not access live RAM |
| VTEC-enable runtime flag | DATA/RAM bit `0x0216.4` | 1 bit; page says it is set when ROM byte `0x60E6 != 0x00` | `PGMFI-P28` | P28 map assuming `304stock.bin` | `public-documentation` | Confirm bit-address convention and set/clear code path statically, then observe with pinned emulator/bench | No—raw-ROM CLI does not access live RAM |

### ROM scalar/control-flow leads

| Parameter/area | Claimed file offset | Claimed format | Source | Scope | Validation level | Remaining confirmation | CLI write? |
|---|---:|---|---|---|---|---|---|
| VTEC enable | `0x60E6` | 1 byte; `0xFF` enable, `0x00` disable | `PGMFI-P28` | P28 map assuming `304stock.bin` | `public-documentation` | Verify exact P28-304 identity and all code references; compare isolated no-op/three-case editor behavior where available | No—candidate/read-only |
| VTEC coolant check | `0x1292` | 1 byte; page labels `0x44` enable and `0xFF` disable | `PGMFI-P28` | P28 map assuming `304stock.bin` | `public-documentation` | Static analysis is essential: the linked VSS-check listing places `0x44` as an immediate operand in an ECT comparison spanning `0x128F..0x1292`, so this may be a threshold-byte patch rather than a Boolean flag. Determine encoding and effects | No—candidate/read-only |
| VTEC VSS check | `0x60FA` | 1 byte; `0x00` enable, `0xFF` disable | `PGMFI-P28`; linked `DisableVtecVSSCheckP28.html` at the same pinned commit | P28 map assuming `304stock.bin` | `public-documentation` | Confirm every reference and control-flow effect for the exact baseline; isolate editor behavior and show that the change does not overlap normalization/checksum/plugin regions | No—candidate/read-only |
| VTEC crossover block | `0x6542..0x6549` | 8 one-byte locations are labelled crossover; the page says `0x6543` “seems like the only one” to change and links the disputed 8-bit low-cam RPM page | `PGMFI-P28`, `PGMFI-RPM8` | P28 map assuming `304stock.bin` | `public-documentation` | Use at least three values in both editors, resolve exact encoding and inverse/rounding, prove which bytes are active via static analysis, and explain all eight bytes. The linked formula dispute blocks implementation | No—candidate/read-only and `Unsupported` encoding |
| Checksum jump routine | `0x2BAD`, 6 bytes | Control-flow/code region; page suggests changing it to three shown bytes `03 B6 2B` to disable checksum | `PGMFI-P28` | P28 map assuming `304stock.bin` | `public-documentation` | Identify routine entry/exit, covered regions, stored checksum bytes, arithmetic, exclusions, initialization, and pass/fail branch with static analysis plus fixtures. Reconcile the six-byte region with the three-byte patch description | No—separate checksum evidence, never a calibration parameter |

The checksum lead does **not** identify a checksum algorithm. M0 therefore reports `ChecksumStatus.Unknown`, does not apply the bypass, and marks affected output not flash-ready.

### Axis and table-region leads

The source gives byte lengths/ranges and labels but no cell encoding, mathematical conversion, ordering, shape, or rounding. Even where 10-byte axes and 200-byte regions suggest a grid, this document does not promote that inference to a definition.

| Parameter/area | Claimed file offset/range | Claimed format | Source | Scope | Validation level | Remaining confirmation | CLI write? |
|---|---:|---|---|---|---|---|---|
| Low-cam MAP axis | `0x7000`, 10 bytes | Labelled “Low Cam mBar Scale”; per-element format/conversion unspecified | `PGMFI-P28` | P28 map assuming `304stock.bin` | `public-documentation` | Establish cell width/count, units semantics, conversion, ordering, references, and editor one-cell/full-axis behavior | No—candidate/read-only |
| High-cam MAP axis | `0x700A`, 10 bytes | Labelled “High Cam mBar Scale”; per-element format/conversion unspecified | `PGMFI-P28` | P28 map assuming `304stock.bin` | `public-documentation` | Same as low-cam MAP axis; also prove independent high-cam selection | No—candidate/read-only |
| Low-cam RPM axis | `0x7014`, 20 bytes | Labelled “Low Cam Rpm Scale”; per-element format/conversion unspecified | `PGMFI-P28` | P28 map assuming `304stock.bin` | `public-documentation` | Establish cell width/count, exact formula/rounding, ordering, references, and editor one-cell/full-axis behavior | No—candidate/read-only |
| High-cam RPM axis | `0x7028`, 20 bytes | Labelled “High Cam Rpm Scale”; per-element format/conversion unspecified | `PGMFI-P28` | P28 map assuming `304stock.bin` | `public-documentation` | Same as low-cam RPM axis; do not assume the disputed low-cam scalar formula applies | No—candidate/read-only |
| Low-cam fuel table | `0x7050..0x7117`, 200 bytes inclusive | Region only; the page attributes it to a third-party spreadsheet; cell encoding/shape unspecified | `PGMFI-P28` | P28 map assuming `304stock.bin` | `public-documentation` | Prove boundaries/references, dimensions/order, cell formula/rounding, axis association, and isolated one-cell plus full-table editor diffs | No—candidate/read-only |
| High-cam fuel table | `0x7122..0x71E9`, 200 bytes inclusive | Region only; the page attributes it to a third-party spreadsheet; cell encoding/shape unspecified | `PGMFI-P28` | P28 map assuming `304stock.bin` | `public-documentation` | Same checks as low-cam fuel; also prove high-cam selection | No—candidate/read-only |
| Low-cam ignition/timing table | `0x72E4..0x73AB`, 200 bytes inclusive | Region only; cell encoding/shape/units unspecified | `PGMFI-P28` | P28 map assuming `304stock.bin` | `public-documentation` | Prove boundaries/references, dimensions/order, signedness and degree convention, formula/rounding, axes, and one-cell/full-table diffs | No—candidate/read-only |
| High-cam ignition/timing table | `0x73AC..0x7473`, 200 bytes inclusive | Region only; cell encoding/shape/units unspecified | `PGMFI-P28` | P28 map assuming `304stock.bin` | `public-documentation` | Same checks as low-cam timing; also prove high-cam selection | No—candidate/read-only |

## Explicitly absent from the cited map

The requested initial Crome/HTS series includes `rev_limit_rpm`, but P28.html does not identify a rev-limiter offset or formula. It must begin as an oracle discovery target, not a P28-304 profile parameter with a guessed offset.

## What can change this ledger

- Controlled Crome cases may add `crome-observed`; controlled HTS cases may add `hts-observed`.
- Matching cases made from the exact same baseline may add `cross-editor-confirmed` only after conversion and rounding also agree.
- Reproducible `dasm662`/Ghidra work may add `static-analysis-confirmed` to the narrowly demonstrated claim.
- A pinned emulator trace may add `emulator-observed`, with model limitations attached.
- Bench and vehicle status require future, separately authorized procedures.

No tool observation updates a profile automatically. Evidence changes are reviewed, explicit commits; third-party executables, OEM ROM bytes, complete disassemblies, Ghidra databases, and editor-generated ROMs remain private and untracked.
