# M0.1 validation hardening

## Scope and status

M0.1 strengthens the Crome/HTS oracle evidence model before any real P28-304 parameter is considered for M1. It does not reimplement M0, integrate an emulator, discover offsets in arbitrary ROMs, implement a checksum bypass, or add a writable P28 definition.

The public repository contains no real Crome/HTS golden files; only `.gitkeep` placeholders are tracked below `private/`. Current M1 data status: **`AwaitingUserFiles`**. All implementation regression fixtures are synthetic and test HondaEcu's analyzer contracts, not a real editor or ECU.

## Problems reproduced with synthetic fixtures

The M0.1 regression scenarios isolate these failures or unsafe assumptions in the earlier evidence model:

| Scenario | Unsafe earlier conclusion | M0.1 rule |
|---|---|---|
| `Floor` and `Truncate` both encode non-negative samples identically | Multiple policy names always mean failure, or the first name may be chosen silently | Keep all names and record a proved behavior-equivalence domain; never choose the first policy implicitly |
| Integer-only or non-midpoint samples | Rounding is established for fractional requests | Keep rounding ambiguous until domain-relevant fractional and midpoint behavior is tested |
| Identical repeats or quantized requested values | Strict monotonicity rejects valid observations, or repeats inflate evidence | Accept non-strict monotonic groups, preserve every provenance, and count independent fitting values separately |
| Same requested value produces different raw bytes | Values can be averaged or deduplicated | Emit an explicit provenance-linked conflict |
| Three training points fit a three-coefficient inverse equation exactly | Zero fitting error implies a correct conversion | Report model complexity and require an independent holdout; a separate synthetic holdout exposes the overfit |
| A changing u8 sits beside a constant zero byte | A matching u16 hypothesis proves two-byte width | Retain both alternatives until independent evidence resolves width |
| An unrelated side byte is accidentally correlated with a parameter | Any candidate covering a byte explains that byte | Only a selected and independently verified definition explains bytes; correlated candidate coverage remains hypothetical |
| Both reports contain at least one common candidate | Cross-editor confirmation is established | Distinguish overlap from a unique validated definition and preserve all alternatives/conflicts |
| Two synthetic manifests differ only by `referenceTool` text | They model real Crome/HTS independence | Test fixtures remain synthetic; Core validates different normalized tools but cannot authenticate editor origin |
| One no-op save exists | Normalization is deterministic and harmless | Require independent no-op and chained re-save evidence; stable unknown transformations remain unknown |

These reproductions demonstrate algorithmic edge cases only. They do not reproduce or claim real Crome, HTS, P28-304, checksum, emulator, bench, or vehicle behavior.

## Observation model

Each observation retains:

- a stable observation identifier;
- user-declared editor provenance;
- the requested engineering value;
- the value displayed after reopening;
- the exact raw ROM bytes and file hash;
- `training` or `holdout` role;
- notes and source path.

Requested, displayed, and raw values are related but not interchangeable. Quantization can map several requests to one displayed/raw result. An exact repeat is useful for reproducibility but is not another independent equation. Contradictory repeats stay separate and block validation; they are never averaged silently.

Training observations are the only cases allowed to fit coefficients. Holdouts are declared before analysis and never refit coefficients or widen the declared tolerance. They evaluate the frozen training-compatible hypotheses and rounding-policy set, may rule out contradicted alternatives, and report a separate holdout-compatible policy subset. A holdout checks exact encoded bytes as well as engineering error.

For each fitted hypothesis, reports expose independent training-point count, free-coefficient count, training error, holdout count/error, observed domain, and extrapolation warnings. The historical `Confidence` concept is interpreted as a **fit score**, not a probability of correctness.

## Rounding by behavior and domain

M0.1 keeps every compatible rounding policy and evaluates equivalence over an explicit encoding-input domain:

- `Floor` and `Truncate` are equivalent over finite non-negative inputs;
- they diverge for negative fractional inputs;
- `Nearest` uses midpoint-away-from-zero behavior, whereas `ToEven` may differ at positive and negative half steps;
- agreement at integer samples or three chosen points cannot prove a rule over the whole domain.

A read-only candidate can serialize unresolved rounding alternatives without selecting one. Confirmation requires one unambiguous policy or a documented equivalence class proved over the candidate's complete allowed domain. Missing domain evidence remains `Ambiguous`.

## Candidate ambiguity and byte explanations

`HasCommonCandidate` answers only whether two hypothesis sets overlap. It does not imply `UniqueValidatedDefinition`. Offset, width, endian, conversion, and rounding alternatives remain in reports, including alternatives contradicted by holdout evidence. An explicit human selection records intent but is not evidence; the comparer may identify the sole algorithmically validated definition only when exactly one alternative survives every gate, with its rationale recorded.

Diff accounting has six layers:

1. actual bytes changed in the compared files;
2. bytes covered by each candidate hypothesis;
3. bytes explained by the selected, verified definition;
4. checksum storage changes with an explicit checksum evidence level;
5. measured no-op transformations for the exact editor provenance;
6. unexplained changes remaining after verified explanations.

The union of candidate offsets is never subtracted from unexplained changes. A parameter may require multiple linked storage locations, but such a definition must explicitly describe and verify the structure and update rule.

## Provenance and analysis binding

Core, not only CLI, enforces normalized editor identity, different-editor comparison, exact version/edition provenance, profile and baseline agreement, finite metadata, valid offsets/ranges, acceptable declared tolerances, and sufficient train/holdout data.

Manifest and analysis JSON use the M0.1 v2 contract. Analysis is bound to the source-manifest digest, profile digest, baseline/no-op/case hashes, analyzer version, and selected candidate/definition identifier. A stale or mismatched binding blocks validation rather than importing silently. Legacy v1 manifests can be read only with an explicit migration warning and their observations default to `training`; legacy candidate export requires reanalysis against the current source manifest/profile/files. `Confidence` remains a serialized compatibility alias for `fitScore`, and neither name means probability.

Every v2 manifest, analysis, preflight, comparison, and exported candidate fragment is a review artifact. It is not a production profile, write authorization, checksum proof, or flash-readiness certificate.

`export-candidate --candidate-id` is the preferred selector. The legacy `--parameter/--offset/--encoding` selector remains only when those fields identify exactly one alternative; ambiguity is rejected, and a v1 analysis must still be reanalyzed before export.

Provenance is user-declared. Recording `Crome` or `Honda Tuning Suite` plus a version/edition makes collection conditions auditable, but cannot cryptographically prove which executable produced a ROM.

## No-op determinism and code-base transformations

Each editor collection supports:

- two independent no-op saves from the same baseline;
- a re-save of an already saved no-op;
- exact diff/hash comparison for determinism and stabilization;
- an optional named transformation profile for a known, separately documented editor transformation.

The transformation-profile identifier is a provenance claim only. It does not authorize a diff, prove compatibility, or upgrade validation in M0.1. A deterministic unknown change remains unexplained. Native P28-304 bytes and an editor-modified runtime code/layout are not assigned one compatibility status silently.

## Aggregate and preflight status

An aggregate report distinguishes:

- at least one requested parameter has a verified definition;
- every requested parameter has a verified definition;
- unresolved parameters or conflicts remain.

`hondaecu oracle preflight` reads the manifest and local files without modifying a ROM. It checks presence/hashes, provenance/bindings, independent training and holdout counts, repeats and reopened/displayed values, no-op checks, and candidate conflicts. Its collection-readiness states—`collection-incomplete`, `candidate-analysis-available`, `holdout-validation-available`, and `cross-editor-comparison-available`—are analysis workflow states, never flash-readiness states.

## What real M1 evidence still requires

For both Crome and HTS, the user must privately collect:

- byte-identical copies of one baseline shared across editors;
- exact editor version, edition/variant, options, and plugin state;
- two independent no-op saves and one chained no-op re-save;
- at least three discovery/training values per parameter;
- independent repeated observations;
- holdouts never used to fit coefficients or widen tolerance; their independent results may rule out contradicted alternatives;
- formula-dependent boundary and rounding-discrimination cases;
- reopened displayed values and exact hashes for every file;
- later, HondaEcu outputs reopened and re-saved by each editor.

The 6500/7000/7500 rev-limit and 4000/5000/5500 VTEC series remain discovery cases. There is no universal boundary increment; choose boundaries only after freezing a candidate formula and documenting the editor's accepted values. Use [the collection checklist](M0_1_ORACLE_COLLECTION_CHECKLIST.md) and the public manifest template. Keep every populated manifest, report, and ROM under ignored `private/` paths.

Until those controlled files exist, no real parameter is cross-editor-confirmed, no checksum is verified, and no P28-304 output is flash-ready.
