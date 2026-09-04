# M0.1 private oracle collection checklist

Use this checklist separately for Crome and Honda Tuning Suite, then review the cross-editor section. Keep the populated checklist, manifests, reports, and every ROM under ignored `private/` paths. The checked-in copy is an unpopulated procedure, not evidence.

Current public-repository M1 data status: **`AwaitingUserFiles`**.

## Safety and custody

- [ ] Baseline was obtained and is held privately by the user.
- [ ] Baseline, editor outputs, reports, installers, complete disassemblies, and reverse-engineering databases will not be committed.
- [ ] `base.bin` is preserved unchanged and read-only where practical.
- [ ] Every save uses a new path; no editor or HondaEcu command overwrites the baseline.
- [ ] All files are for PC inspection only and will not be flashed.
- [ ] No checksum bypass, rev-limit increase, emulator, bench, or vehicle operation is part of this collection.

## Shared baseline identity

- Baseline path: `[fill locally under private/oracle/]`
- Baseline SHA-256: `[fill locally]`
- File size: `[fill locally; P28-304 profile requires exactly 32768 bytes]`
- Acquisition/custody note: `[fill locally; do not paste OEM bytes]`
- Profile identifier: `[fill locally]`
- Profile digest recorded by analysis: `[generated locally]`

- [ ] Crome and HTS collections use byte-identical copies with the exact same baseline SHA-256.
- [ ] No collection mixes a native baseline with an editor-transformed parent under one compatibility scope.

## Editor provenance — complete once per collection

- Reference tool: `[Crome or Honda Tuning Suite]`
- Exact version: `[fill locally]`
- Edition/variant: `[fill locally]`
- OS/environment: `[fill locally]`
- Optional plugins/features present: `[fill locally or explicitly none]`
- Plugins/features disabled: `[true/false; true is required for inference]`
- RTP/datalogging/extra patches disabled: `[fill locally]`
- Relevant save/display options and locale: `[fill locally]`
- Optional transformation-profile identifier: `[fill only if separately documented]`
- Collector notes/date: `[fill locally]`

- [ ] Provenance values came from the actual local session, not a website assumption.
- [ ] The collector understands that provenance is user-declared and does not authenticate the producing executable.
- [ ] Any transformation-profile identifier is treated as a claim only, not permission or a compatibility upgrade.

## Repeated no-op and re-save files

Record each path and generated SHA-256; do not put real hashes in this public checklist.

| Role | Local path | SHA-256 | Fresh baseline/session? | Notes |
|---|---|---|---|---|
| baseline | `[fill locally]` | `[fill locally]` | n/a | `[fill locally]` |
| primary no-op A | `[fill locally]` | `[fill locally]` | `[yes/no]` | `[fill locally]` |
| independent no-op B | `[fill locally]` | `[fill locally]` | `[yes/no]` | `[fill locally]` |
| re-save of no-op A | `[fill locally]` | `[fill locally]` | no; parent is no-op A | `[fill locally]` |

- [ ] Both no-op A and no-op B were independently produced from byte-identical baseline copies.
- [ ] No-op A was reopened, displayed values/warnings were recorded, and it was saved to a distinct re-save path.
- [ ] Exact ranges were reviewed for `baseline → no-op A`, `baseline → no-op B`, and `no-op A → re-save`.
- [ ] Determinism and stabilization were assessed separately.
- [ ] Different hashes/ranges remain visible and were not silently ignored.
- [ ] No-op bytes were not called checksum bytes without checksum evidence.
- [ ] An unknown but stable code/layout transformation remains unexplained or has a separately reviewed transformation profile.

## Parameter observations — complete per parameter and editor

Parameter id: `[fill locally]`

| Observation id | Role | Requested value | Displayed after reopen | ROM path/hash | Raw bytes | Independent/repeat note |
|---|---|---:|---:|---|---|---|
| `[fill]` | `training` | `[fill]` | `[fill]` | `[fill locally]` | `[measured]` | `[fill]` |
| `[fill]` | `training` | `[fill]` | `[fill]` | `[fill locally]` | `[measured]` | `[fill]` |
| `[fill]` | `training` | `[fill]` | `[fill]` | `[fill locally]` | `[measured]` | `[fill]` |
| `[fill]` | `training` repeat | `[fill]` | `[fill]` | `[fill locally]` | `[measured]` | `[new file/session]` |
| `[fill]` | `holdout` | `[fill]` | `[fill]` | `[fill locally]` | `[measured]` | `[not used to fit coefficients]` |

- [ ] Every observation has a unique id and retains its own provenance.
- [ ] Each file changes only the declared parameter relative to the designated no-op-controlled parent.
- [ ] Requested and reopened/displayed values were recorded separately.
- [ ] Raw bytes and file hash were measured rather than copied from an expected formula.
- [ ] At least three independent training values exist; repeated identical points are not counted again.
- [ ] Quantized requests that map to one displayed/raw value are retained.
- [ ] Any same-request/different-raw observation is marked as a conflict and not averaged.
- [ ] Holdout roles were assigned before analysis; holdouts did not fit coefficients or widen tolerance, but did independently rule out contradicted candidates/policies.
- [ ] Holdout review checks exact encoded bytes as well as engineering error.

Initial discovery series, if the editor permits them:

- `rev_limit_rpm`: 6500, 7000, 7500 RPM;
- `vtec_crossover_rpm`: 4000, 5000, 5500 RPM.

These are training/discovery cases only. They are not holdouts, boundaries, or proof of an offset.

## Candidate freeze, holdout, and boundaries

- Candidate/definition id: `[generated locally; do not guess]`
- Training domain: `[generated/reviewed locally]`
- Free coefficients: `[generated locally]`
- Compatible rounding policies: `[generated locally]`
- Proved rounding-equivalence domain: `[fill only when established]`
- Predeclared conversion tolerance: `[fill before holdout evaluation]`

- [ ] Candidate alternatives for offset, width, endian, conversion, and rounding are retained.
- [ ] Manual candidate selection is not recorded as new evidence.
- [ ] Separate midpoint cases distinguish `Nearest` from `ToEven` where the domain reaches half steps.
- [ ] Negative fractional cases exist before extending `Floor`/`Truncate` equivalence beyond a non-negative domain.
- [ ] Boundary cases follow the frozen formula/raw domain and values the editor actually accepts.
- [ ] No universal Honda boundary step or tolerance was invented.
- [ ] Requests outside the observed training range carry an extrapolation warning.

## Preflight and analysis review

- Preflight report path: `[fill locally under private/reports/]`
- Analysis report path: `[fill locally under private/reports/]`
- Source-manifest digest: `[generated locally]`
- Analyzer version: `[generated locally]`

- [ ] `oracle preflight` reports all required files present and hashes matching.
- [ ] Manifest/profile digests and analyzer bindings are current.
- [ ] Independent training and holdout counts are sufficient for the intended stage.
- [ ] No-op determinism/stability state is explicit.
- [ ] Actual changes, hypothesis coverage, verified-definition coverage, checksum storage, no-op transformations, and unexplained changes are reviewed separately.
- [ ] The union of candidates was not used to erase unexplained bytes.
- [ ] `Confidence`/fit score is not described as probability or confirmation.
- [ ] Collection readiness is not described as flash readiness.

## Cross-editor review

- [ ] Crome and HTS normalized tool identities are different.
- [ ] Both manifests bind the identical baseline SHA-256 and compatible profile digest.
- [ ] Exact version/edition provenance is complete for each editor.
- [ ] Each editor independently passes no-op, training, repeat, and holdout gates.
- [ ] Exact holdout bytes agree for the selected definition or proved behavior-equivalent class.
- [ ] Multiple common candidates remain `Ambiguous`; `HasCommonCandidate` is not `UniqueValidatedDefinition`.
- [ ] Every actual changed byte has a verified explanation or remains visibly unexplained.
- [ ] Aggregate status distinguishes some verified parameters, all requested parameters verified, and unresolved/conflicting parameters.
- [ ] No result is described as emulator-, bench-, vehicle-, or flash-validated.

Prefer generating a manifest with `oracle create-manifest`; use [the public manifest template](templates/oracle-manifest.m0-1.json.template) as a v2 field-shape reference. Its placeholders and invalid hash/date values are intentional so it cannot masquerade as collected evidence. Copy any working material into `private/reports/`, let the CLI calculate hashes and diff ranges, and replace every required placeholder locally. Never populate or commit the public template with real ROM paths or hashes.
