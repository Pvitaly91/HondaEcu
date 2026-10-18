# M2bq — Full Production Synthetic Composite Execution

Design/specification and source-review aid, not an execution receipt or an acceptance report. New M2bq runtime, QA, cross-platform, CI and delivery results are **NOTRUN / unverified** here. Expected counts below must not be relabeled as observations. The present copy is prepared under the private document-drafts directory for review before any public promotion.

Repository: `Pvitaly91/HondaEcu`.

Exact historical M2bp base: `ecc32ea7b65020075f8403a4d4c81cdce4d0f0ad`.

M2bq branch: `codex/p28-word0196-full-production-composite-m2bq`.

The scope is one invented, closed, previously encoded M2bj fragment executed continuously by the existing production CPU mechanism. It is not original-ROM execution, firmware integration, a general instruction loader or an ECU simulator claim.

## 1. Three explicit source and evidence scopes

| Scope | Exact source identity | Intended use |
| --- | --- | --- |
| Historical M2bo | `1ceec589ee8586727fb16a39fd15875444d6feab` | Unmodified historical validators and independent historical reference scope. |
| Pinned M2bp | `ecc32ea7b65020075f8403a4d4c81cdce4d0f0ad` | Unmodified M2bp default and one-step opt-in validators, contracts and source bindings. |
| Active M2bq | Explicit descendant/source transition from the M2bp base; final SHA not yet established | New closed continuous composite mode, active default differential and active one-step compatibility. |

These are separate physical trees with exact source bindings. An old validator must not be made to accept active M2bq files through rewritten historical pins, aliases or a generic newline exemption. Existing old reports remain historical evidence in their original source/runtime-HEAD roles.

The new `production_composite_source_manifest.json` and `production_composite_contract.json` are intended to bind this transition. The planned modified historical paths are `.github/workflows/build.yml`, `rust/p28-slice-runner/src/audit.rs` and `audit_bus.rs`. New production components are `audit_composite.rs` and `audit_composite_tests.rs`; the closed research harness and reference modules are separately inventoried new sources. Final exact identities and complete new-path membership remain to be materialized and reviewed.

Production `exec.rs`, the instruction dispatcher/body/tail, CPU semantics, decoder semantics, runner version `0.43.0`, protocol `1` and the 38 ordered protocol identities are preservation obligations, not intended changes. The existing `p28-word0196-audit` feature remains opt-in; default features must not enable it.

## 2. Closed PROGRAM authority

Only the already reviewed M2bj emitter may supply the invented PROGRAM segment:

- Base `0x1000`; end exclusive `0x1033`; length 51 bytes.
- SHA-256 `91ffb46922def91764f5d4da166ef2cfc9834ed0effcc051d3f97246fa147ab1`.
- Twenty exact instruction nodes, sixteen distinct forms, identical DD0/DD1 byte streams.
- Relocated conditional deltas `+26`, `+10`, `+7`; two direct-J continuation identities `0x5596` and `0x55C5`.
- Typed forms, operands, node boundaries, DD requirements, successors, provenance and terminal authority checked together, not only a digest label.

The proposed `ClosedCompositeProgram::admit_emission` admits the immutable segment and its closed metadata. The complete payload may exist in host memory and the one-shot harness input, but is not serialized as a full raw payload vector or generated target object, HEX, firmware BIN or persistent payload file. All declared actual `ProgramEvent` fields are retained: ordinal, PC, address, offset, purpose, association, selected length, serviced status and refusal. That schema has no byte-value field. Bytes are acquired through the real Bus; the actual 51-byte emission SHA and actual selected-extent SHA bind their values. No field is retroactively omitted or invented, and DATA events retain their declared actual values. Source-bound seed JSON contains invented states, not PROGRAM bytes.

PROGRAM and DATA remain distinct address spaces. There is no padding-based mapping to `0x1000`, original ROM loading, executable continuation bytes or arbitrary replacement stream. Each real decode must receive its bytes through the production PROGRAM observation boundary.

## 3. Separate API and continuous lifecycle

The existing `Session::new` / one-step API keeps its original behavior: one successful retirement seals it even if its supplied budget is 16. M2bq must not silently convert this API into a multi-step executor.

The proposed separate `Session::new_closed_composite` boundary owns one production `Cpu`, one production `Bus`, one DATA initialization and one transition to Functional phase for the entire route. `Session::step_composite` uses actual architectural PC and current DD to select and validate the next closed node. It then uses the production checked decoder and shared `exec::execute_decoded`; there is no copied ISA dispatcher or independent replacement execution engine.

No expected PC, AL, PSW, DATA or writer result is assigned into the CPU between instructions. The oracle cannot choose the runtime path or repair state. `CompositeSeeds` validates the complete invented input and derives the gate path from those inputs rather than accepting caller-selected broad rights.

The successful instruction budget is at most 16, checked before another decode/fetch. Nonterminal retirements return to Functional phase with the same state. Only the actual final direct J to the permitted continuation seals the session. The architectural terminal PC is retained, but no fetch at either external continuation is permitted. A second J, unexpected successor, fallthrough, extra step, reseed, external probe or post-terminal DATA access is a refusal, not a continuation experiment.

The first fault is sticky. Already observed partial CPU/RAM effects, attempted accesses, refusal details and journals remain evidence. This boundary does not promise atomic rollback of a failed instruction or route.

## 4. Entry state, DATA and intermediate obligations

Entry PC is `0x1000`; both incoming DD variants are required. First LB establishes DD0. Retained context includes LRB `0x0021`, page `0x0100`, local register RAM `0x0108..0x010F`, SCB derived from incoming PSW, SSP, AH, pointing-register banks and the declared nonmodified PSW state. Unknown SF meaning/storage is not invented.

The closed byte inventory is DATA `0x0108..0x010F`, `0x0117`, `0x0124`, `0x0128`, `0x012A`, `0x018E`, `0x018F`, `0x0196`, `0x0197`. The word at `0x0196/0197` is little-endian and read-only within this fragment; `0x00C0` is a code-owned immediate, not a DATA read. Invented seeds remain `InventedOnly_NoNativeGenerationOwner`.

The PSW admission condition is `(psw & 0x0CC8) == 0x0CC8`. The expected admission-only sweep classifies all 65,536 words as 2,048 representable and 63,488 incompatible. Incompatible PSW is refused before CPU construction; it is not normalized to a different input.

DATA rights are specific to path, actual PC, selected form, address, width and direction. Same-instruction RMW requires the successful read from that instruction's current span. Initialization, previous-instruction reads, failed reads or an unrelated address cannot supply RMW credit. The r1 store and ordinary STB are not mislabeled as RMW. Same-value stores remain present, with writer identity and order intact.

PROGRAM callback records retain global ordinals, current-step spans, access purpose, selected node and actual decode association. Associating a later decode must not rewrite an earlier PROGRAM event. Instruction fetch observations and functional DATA reads are distinct inventories.

## 5. Independent expectations before new CPU execution

Before any new composite CPU instance, including the four initial smoke controls, freeze the ordered invented inputs, reviewed source identities, topology, expected intermediate and terminal states, ordered effects, complete record schemas, expected canonical streams, negative definitions and comparator specimen/mutations.

Expected architecture comes from the reviewed M2bk/M2av/M2bd source/reference obligations and unchanged M2bn pure corpus/oracle. The new production CPU output is not an expected-value generator. A separately specified observation protocol supplies expected Bus/API events; host C11 equality alone is not manufacturer instruction-semantics evidence.

A freeze file is a binding, not execution authority. Root review and the requested runtime workflow are still necessary. Any source/input/expected-stream change after freeze invalidates that execution attempt; expected values must not be revised to match a failure.

## 6. Planned positive coverage, counted in separate lanes

| Path | Input gate | Expected retirements | Functional reads | Functional writes | Terminal PC |
| --- | --- | ---: | ---: | ---: | --- |
| A | `DATA0196 < 0x00C0` | 11 | 5 | 3 | `0x55C5` |
| B | NotBelow; `DATA012A.7 = 1` | 13 | 9 | 3 | `0x5596` |
| C | NotBelow; first gate clear; `DATA0124.5 = 1` | 14 | 10 | 3 | `0x5596` |
| D | NotBelow; both gate bits clear | 16 | 12 | 5 | `0x5596` |

Path B suppresses the DATA0124 read. D retains its additional ordered RMW effects. Path C is not promoted to a historical native original-ROM witness.

Before the smoke lane, two separate executable-boundary guards must refuse `--rom /invented/no-file.rom` and an unknown stdin `execute_bytes` operation containing one invented `0xA5` byte. They are expected to exit nonzero before constructing any Cpu/Bus. The stdin case retains its emitted header and stderr/exit truth; neither case attempts to open a real ROM. These are executable-boundary observations, not component tests or composite retirements.

The newly requested initial smoke lane then uses the first original sfFalse A/B/C/D seeds, in that order, before the full corpus. It uses the same owned harness process but four distinct Session/Cpu/Bus instances. Expected smoke totals are 4 executions, 4 Cpu, 4 Bus, 54 retirements, 36 functional reads and 14 writes. These are separate counters and do not replace four corpus cases or inflate the 5,470-case evidence.

The unchanged full positive corpus expects 5,470 complete routes, 5,470 Cpu, 5,470 Bus, 5,470 initializations/transitions, 73,784 retirements, 49,112 logical reads and 19,162 logical writes. It retains 2,735 SF pairs, both incoming DD values, boundary inputs, representable PSW contexts, SCB/pointing context and all four paths. Actual PROGRAM callback totals must be derived from the production topology; an old synthetic-adapter callback count is not forced onto the new mechanism.

The planned positive canonical inventory is 5,478 records: header, PROGRAM admission, PSW sweep, four complete smoke observations, 5,470 complete corpus observations and summary. None has been established as actual M2bq runtime evidence by this draft.

## 7. Negative authorities must not be conflated

The negative protocol has 33 ordered records, retained separately from the positive lane:

- Twelve PROGRAM admission mutations; only digest-label and provenance controls are metadata-only.
- Four seed/alias refusals and one incompatible-PSW admission control.
- Four refused constructors: budget 0/17, wrong entry PC and wrong LRB. These construct four Cpu values but no Bus; do not call them CPU-construction-free.
- Twelve accepted-session controls for closed host access, reseed/phase/API escape, PROGRAM probe, budget exhaustion and terminal sealing.

Expected negative totals are 16 actual Cpu value constructions, 12 Bus, 33 step calls, 28 shared executions and 28 retirements. The latter comprise completed A/D negative-control routes (11 + 16) and one budget-prefix retirement. These two completed control routes are not added to 5,470 positive executions. Refused pre-Bus DATA admission is counted as admission refusal, not a fabricated serviced Bus event. External attempts remain distinct from serviced external fetches, which must be zero.

The planned negative canonical stream has 36 records: header, two executable-boundary guard observations and 33 complete capability controls. The boundary guards add zero Cpu/Bus/retirements; capability totals remain 33 records, 16 Cpu, 12 Bus and 28 retirements. Unexpected prefixes and actual refused operations must remain durable rather than being hidden by a final-count assertion.

Thirteen genuine component-unit guard functions exercise internal authority relations that the public closed API cannot expose. They instantiate no Cpu/Bus and do not execute the M2bj fragment; the opaque `0xA5 × 51` fixture is not the admitted emitter payload. They are not 13 additional CPU execution proofs. Explicit executing-phase out-of-segment PROGRAM refusal and missing selected-fetch retirement assertions are review obligations before these drafts are frozen.

Seventeen pure comparator mutations exercise sensitivity to intermediate flags/registers, successor/decoder identity, DATA/writer order, missing same-value store, RMW attribution, PROGRAM order/association, retained context and terminal authority. They mutate the independently expected frozen D specimen, not a new CPU result used as its own oracle. Component guards, comparator sensitivity, metadata-only refusals and actual Session controls have separate counts and evidence labels.

The complete requested boundary inventory is mapped to these distinct authorities below. All are planned checks, not observations in this specification. A component fixture must not be described as a public CPU injection.

| Required relation | Planned authority / control |
| --- | --- |
| Wrong digest label / actual content | PROGRAM admission `program-wrong-digest-label` (metadata-only) / `program-content-changed` (both streams changed). |
| Wrong base or end | Admission `program-wrong-base` / `program-wrong-end`. |
| Wrong node count | Admission `program-node-count`, removing the actual last direct-J identity. |
| Wrong form or operand | Admission `program-node-form` / `program-node-operand`. |
| Wrong decoded index | Per-instruction real component guard and `decoded-index` comparator mutation. |
| Mid-instruction PC | Constructor `entry-wrong-pc`; internal-node component guard, not injected CPU PC. |
| Unknown successor | Actual successor component guard and `pc-successor` comparator mutation. |
| Wrong incoming DD | Admission `program-node-dd`, internal DD guard and `dd` mutation. |
| Forged path profile | No public caller-profile parameter exists; derived-seed/path component guards and actual B/C host-write denials remain distinct. |
| Unauthorized DATA read | `functional-read-outside-step` plus private per-instruction read guard. |
| Unauthorized DATA write | B/C host-write refusals plus private per-instruction direction/address guard. |
| Write DATA0196/0197 | Actual `functional-write-readonly-low/high` pre-Bus refusals; full positive writes also independently compared. |
| RMW without current read | Real same-instruction RMW component guard and `false-rmw-read` mutation. |
| Stale previous-step RMW credit | Same real RMW guard with a prior-span read fixture. |
| Missing same-value store | `missing-same-value-write` mutation of the frozen D specimen and complete ordered positive-effect comparison. |
| Prior PROGRAM event reassociated | Real step-span component guard; mutations of prior association, callback and order. |
| Extra fetch after exit | Actual terminal A/D PROGRAM attempts retained as unserviced, separate from zero-attempt positive paths. |
| Extra instruction beyond 16 | Actual D post-J step refusal; separate budget-one predecode exhaustion and component budget guard. |
| Multiple terminal transfers | Post-J actual step refusal plus direct-J-count component guard. |
| Non-J external control flow | Retirement component guard; no arbitrary opcode injection through the public API. |
| Missing terminal J | Last-J-node admission removal and an incomplete budget-prefix control; neither is mislabeled as injected CPU execution. |
| New step after fault | Actual sticky budget-fault follow-up and sticky host-API component guard. |
| Reseed after Functional phase | Actual reseed controls, including both terminal sessions. |
| Incompatible PSW | Admission control plus complete 65,536-word no-Cpu admission sweep. |
| Conflicting aliases | `seed-r-alias` / `seed-er-alias` admission controls. |
| External ROM/file input | Actual executable `--rom /invented/no-file.rom` refusal before file input or Cpu construction. |
| Arbitrary instruction stream | Actual unknown `execute_bytes` boundary plus changed-content/DD1 admission controls. |

Requested comparator relations CF, ZF, DD, AL/AH, PC successor, one DATA byte, writer order, omitted same-value store, false RMW credit, missing selected PROGRAM event, corrupt terminal target and changed pointing bank are all represented in the 17-mutation inventory. This table is descriptive; only separately retained actual results can establish successful coverage.

## 8. Complete canonical observations and compatibility

Every declared raw production field must be compared, including entry/current CPU state, full RAM representation, per-step snapshots and outcomes, decoded fields, PROGRAM/DATA/raw/diagnostic/refusal journals, global ordinals, same-value writer identities, access attribution, direct-J state, counters and preserved context. A reversible sparse `0xA5` codec may reduce repeated RAM bytes only if decoding reconstructs every field exactly. It is not a projection that drops inconvenient fields.

Independent architectural projection is an additional comparison, not a replacement for complete raw-report equality. Local expected-versus-actual streams and local/Ubuntu/Windows streams require full decompressed byte comparisons through EOF/CRC, with no post-mismatch exclusion list. Compressed archive hashes alone are not whole-stream equivalence.

The default lane retains all 493 original observations and protocol/identity checks. The one-step lane retains all 583 complete records. Active audit source identities necessarily differ from pinned M2bp in exactly two independently frozen header rows: `audit.rs` and `audit_bus.rs`, both in the top-level header and nested arbitrary-operation header. Those complete old/new headers remain paired canonical records. The other observational records must remain exactly equal. This is an explicit versioned source relation, not a mutable hash alias, field deletion or claim that unequal full old/new headers are byte-identical.

## 9. Planned proof command forms — not executed by this document

These examples describe the current draft interfaces after reviewed publication. Root must supply fresh attempt paths, verify all source/freeze bindings and finalize scheduling. They are not permission to execute private drafts or to run before full protected Before completion.

```powershell
python -B research/p28-word0196/validate_production_composite.py --pinned-root .tmp/m2bq-pinned-m2bp --historical-root .tmp/m2bq-legacy-m2bo --output-dir .tmp/m2bq-public-evidence/composite/<fresh-attempt> --target-dir .tmp/m2bq-runtime-target/<fresh-attempt> --freeze-only
```

After independent freeze review, the same explicit arguments with `--execute-freeze` are intended to build/run the admitted harness. The four initial smoke commands are a closed internal `{kind: "smoke", input: <frozen case>}` sequence within that workflow; no invented public smoke CLI is required.

```powershell
python -B research/p28-word0196/production_composite_compatibility.py --pinned-root .tmp/m2bq-pinned-m2bp --historical-root .tmp/m2bq-legacy-m2bo --output-dir .tmp/m2bq-public-evidence/compatibility/<fresh-attempt> --target-dir .tmp/m2bq-optin-target/<fresh-attempt> --composite-freeze .tmp/m2bq-public-evidence/composite/<fresh-attempt>/pre-runtime-freeze.json --pinned-optin-output .tmp/m2bq-pinned-m2bp/.tmp/m2bp-public-evidence/optin --freeze-only
```

The compatibility `--execute-freeze` mode must bind actual fresh pinned one-step receipts, native commands/logs, earlier independent freezes, source inventories and compiled binaries. It does not execute the new composite corpus itself. All exact runtime command outcomes, binary identities and elapsed times are pending.

## 10. Preservation, QA and final delivery obligations

The new full protected Before/After must include every pre-existing M2bp private file, evidence stream, old build/cache root and unrelated user file. Exclusions are only `.git`, new M2bq private scope and the 18 exact initially absent M2bq-owned roots. The old M2bp final protected After is prior evidence, not a substitute for the new full hash. Preserve all 18 stabilization guards, 23 historical runners, closed historical seals/reports and original foreign PNG. The three exact XML representations retain separate committed versus protected-filesystem identities; no normalization writes are allowed.

All new host build/cache/output paths must remain owned. Use fresh physical source copies for active .NET tests where repository-relative bin/obj/TestHost layout requires them. Source bytes must match active sources before compilation. Historical builds belong only to new exact historical checkouts, never old protected outputs. Heavy Rust/.NET/STA/portable work is sequential; Rust uses `--jobs 1`. Do not change global Windows, GC, pagefile or user caches and do not terminate foreign jobs.

Required actual QA includes historical research families and M2bj emission, pinned M2bp behavior, active default/one-step compatibility, new smoke/full corpus/negative controls, Rust default 321 plus actual opt-in count, Core 2947, CLI 959, Desktop 183, C11 398658, C/C# 81920, formatting, privacy, diff check and portable checks. Numbers here are acceptance targets, not this draft's results. No skips, relaxed expectations, expanded Option B, increased 30-second STA timeout or loss of original real-WPF assertions is permitted.

Native child start/end/PID, exact argv, stdout/stderr, exit/fault truth and first failure must be durable. Partial gzip/log artifacts remain owned and retained; a failed attempt is not overwritten or retried until a clear causal correction has been reviewed. Source-only review, pure tests and CPU observations remain separately labeled.

| M2bq evidence gate | Status in this draft |
| --- | --- |
| Complete protected Before / final After | Not attested here; actual receipts required |
| Independent final pre-runtime freeze | NOTRUN / unverified |
| Four smoke controls; full 5,470 routes | NOTRUN / unverified |
| Executable boundary 2; negative capability 33; component 13; comparator 17 | NOTRUN / unverified |
| Pinned/default/one-step/full QA and portable | NOTRUN / unverified |
| Exact pushed SHA; CI three jobs; full cross-host bytes | Not established |
| Final evidence seal and LAST report | Not created by this draft |

Only after all actual gates may root create the authorized substantive commit(s), normal push to the M2bq branch, and exact-final-SHA CI/canonical evidence. No PR/merge/default-branch change is part of this work. Final private evidence sealing includes failed attempts and excludes only the seal's own output and still-absent LAST report to avoid a hash cycle. `private/reports/m2bq/FINAL_REPORT_UK.md` is written last; this private draft is not that report.

## 11. Limits and fields still required for final documentation

Before public source freeze, finalize the reviewed source/manifest roles, command interface, lifecycle/partial-evidence handling and source policy. After freeze, actual boundary/smoke/full/negative/component/comparator results, topology-derived PROGRAM counts, commands/binaries, failure history, QA/portable/protected/privacy comparisons, final Git/CI/artifacts and cross-host bytes belong in separately bound immutable receipts and the private LAST report. They do not require rewriting this source specification after execution. Do not substitute expected constants or unexecuted JSON for those observations.

Even a successful bounded synthetic result must retain `OriginalRomExecutionNotObserved`, `ActualDownstreamRejoinNotEstablished`, `SFMeaningStorageNotEstablished`, `PhysicalROMPlacementNotEstablished`, `TargetProgramEquivalenceNotEstablished`, `FirmwareIntegrationNotEstablished` and `FirmwareReady=false`.

The intended eventual classification is `M2bq Full Production Synthetic Composite Execution Verified / Research-Only`, but this draft does not assert it. It authorizes neither M2br nor actual-ROM execution, placement, firmware generation, GUI work or hardware testing.
