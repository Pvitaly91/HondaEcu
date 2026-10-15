# M2bj Desktop QA acceptance — approved Option B

The user explicitly approved Option B on 2026-10-14: separate normal supported
Desktop delivery acceptance from deliberate stress/diagnostic controls. This
decision applies only to the existing M2bj delivery. It does not authorize a new
milestone, weaken any test, or waive a failure in the normal environment.

## Supported acceptance environment

Use Windows x64, a compatible .NET 8 Desktop Runtime under the existing project
requirements, and normal multicore execution with the original available process
affinity. Record the actual OS build, loaded runtime identity, CPU count and
affinity, memory pressure, concurrent workload, and fresh testhost PID.

Do not deliberately restrict the host to one logical CPU, introduce artificial CPU
stress, run concurrent heavy unrelated Rust/MSBuild builds in the controlled QA
window, overload memory, or attach a scheduling-perturbing profiler. These are
controlled measurement conditions, not unproven universal hardware minimums.
No Windows, pagefile, global GC, or power-plan changes are required or authorized.
The reference .NET/WPF 8.0.31 VM and kernel ETW investigation are not prerequisites
for this approved delivery route; their historical unavailability remains true.

## Unchanged test and failure contract

The real offscreen WPF Application/MainWindow, production resources, Basic and
Unified panels, both real RPM previews, all tabs, 100/125/150% equivalent viewports,
bindings, accessibility and clipping checks remain. All 56 original assertions
and all 64 current assertion calls remain. The STA Join budget stays **30 seconds**.
The existing partial lifecycle fix prevents the queued second visible startup
window; successful acceptance must verify window closure and dispatcher shutdown.
This does not claim that cleanup of a failed STA worker has been newly repaired.

Require three independent fresh-testhost focused layout runs, each 1/1, and two
independent fresh-testhost full Desktop suites, each 183/183 (or a documented larger
count of real tests), zero failed and zero skipped, including the layout test. Preserve
actual per-run timing, PID/environment and successful cleanup evidence. Never use
inherited runs as fresh delivery evidence.

The first normal-environment failure blocks delivery. Preserve it and stop
positive attestation; no retry-until-pass, Skip/Ignore, timeout extension, assertion
removal, changed expectations, fake controls/reports, catch-and-pass, or hidden
unfinished worker is allowed. A fresh sequential full QA, portable checks, source
policy/privacy and original-baseline protected comparison are also mandatory.

## Retained stress limitation and historical context

R5's deliberate one-logical-CPU plus 24-worker controls B and C failed at the
unchanged 30-second Join (observed 32.272 s and 33.470 s). Normal multicore A passed
at 6.798 s; single-CPU/no-load D passed at 11.106 s. All original failure artifacts
and R0–R6 reports remain unchanged. Classify them as:

- `StressDiagnosticFailedUnderDeliberateSingleCpuOvercommit`
- `ResourceDependentLatencyEstablished`
- `HistoricalFullTimeoutRootCauseNotEstablished`

These deliberate stress controls are diagnostic robustness evidence, not a
mandatory gate under this explicitly approved normal-environment policy. This is
an acceptance-policy decision, **not a technical fix for the stress failures**.
Do not claim StressTimeoutFixed, HistoricalRootCauseEstablished,
GcCausalityFullyEstablished, or WpfGuaranteedStableUnderAllLoads.

The preserved emission document's delivery-incomplete paragraph describes its
initial pre-closure state. Historical R6 decision text describes approval as it
stood then. This document governs the newly authorized acceptance route; actual
delivery still depends on fresh receipts and exact-SHA CI, not this policy alone.

## Delivery and exact-SHA CI

Preserve all 13 existing implementation files byte-for-byte, including the R3
Core optimization and its 15 regression tests. Require 13/13 complete canonical
RPM report equality against the immutable before-fix oracle, unchanged error and
cancellation semantics, and actual in-memory M2bj emission. Its 51-byte DD0/DD1
stream must retain SHA-256
`91ffb46922def91764f5d4da166ef2cfc9834ed0effcc051d3f97246fa147ab1`,
primary/decode 20/20, and all atomicity checks. Do not persist the raw stream.

After every local gate passes, make one substantive commit and normal push only
to `codex/p28-word0196-atomic-synthetic-emission-m2bj`; no PR, merge, force push,
empty rerun commit, or default-branch change. On that exact final SHA require:

- `build-and-test (ubuntu-latest)` — success
- `build-and-test (windows-latest)` — success
- `desktop-windows` — success

Record run, attempt and job identities. Preserve all prior research steps, actual
M2bj emission, full Desktop contract, formatting and portable startup diagnostics.
Any standard CI failure blocks delivery; a green rerun cannot erase an unanalyzed
failure. Compare actual Ubuntu/Windows emission metadata, source bindings, length,
primary/decode, DD equality, atomicity and recomputed hash. Green statuses alone
are not cross-OS byte-identity proof.

## No expansion of ECU or native authority

This policy grants no M2bk, target CPU/actual-ROM execution, linker, ROM placement
or replacement, firmware generation, GUI smoke, PC capture, or hardware authority.
Persistent synthetic BIN/HEX/ASM and FirmwareBIN remain zero.
`ActualTargetExecutionNotObserved` remains unchanged. Native exit isolation,
downstream rejoin, physical ROM placement, target program equivalence and firmware
integration remain NotEstablished;
`FirmwareReady=false`. Historical diagnostic failures remain disclosed even if
delivery closes under approved Option B.
