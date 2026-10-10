# M2az - original ASM662 releases and component provenance

## Result and exact scope

`M2az Original Source/License ResearchBlocked`.
First unresolved prerequisite: `DocContributionRightsNotEstablished`.
The original0.9 source distribution was actually recovered and its integrity
verified, but complete component rights and a safe build are not established.
`AssemblerBuildNotRun`; `AssemblerExecutionNotRun`;
`AssemblerEncodingNotVerified`; `TargetCodeGenerationNotReady`.

Exact parent: `c6cb67cad0d8c207c837648ca6de0ab7bd7ec310`.
[M2ay source/safety](M2AY_ASM662_SOURCE_BUILD_VERIFICATION.md),
[M2ax vendor acquisition](M2AX_MAC66K_V4_DCL_PROVENANCE.md),
[M2aw context](M2AW_NX8_200_TARGET_ABI_CONTRACT.md) and
[M2av equivalence](M2AV_WORD0196_STRUCTURED_C_EQUIVALENCE.md) are preserved.
New evidence is official release bytes/notices, not rereading old manifests.

## Actual original release acquisition

The [SourceForge ASM662 index](https://sourceforge.net/projects/pgmfi/files/asm662/)
and [original0.9 listing](https://sourceforge.net/projects/pgmfi/files/asm662/asm662%20version%200.9/)
were independently reviewed. Canonical download redirected to an official
SourceForge mirror. Received archive lengths/MD5/SHA1/SHA256 match the embedded
official file metadata. HTML responses were not called archives.
Original bytes and redirects/failures remain private and unchanged.
Current official distribution identity is verified; no detached2003 author
signature or uploader identity is invented. Duplicate official endpoints are
transport corroboration, not independent source/ISA lineages.

| Distribution | Date / bytes | Container inventory | Classification |
| --- | --- | --- | --- |
| asm662-0.9.tar.gz | 2003-07-08 /188873 |56 members,48 files,45 materialized texts incl12CVS metadata | Actual historical source release |
| asm662-win32-v1.0.zip | 2003-07-11 /215910 |7 files:2EXE,4docs,1example | Binary distribution; no full source |
| asm662-win32-v1.1.zip | 2003-07-28 /206013 |2EXE only | Binary distribution; no full source |
| asm662-win32-v1.2.zip | 2003-10-08 /221582 |7 files:2EXE,4docs,1example | Binary distribution; no full source |

Original0.9 SHA256:
`2471660d08fe827af9ed1582354804eb7c16e82775bb8b6e5190317a253e5444`.
Other exact hashes are pinned separately in the public contract and private ledger.
No ready binary is executed or materialized as a runnable disk file.

Bounded gzip CRC/ISIZE, tar header/member checksums, ZIP member CRC, magic/format,
expanded size/count, duplicates/case collisions, absolute/UNC/drive/traversal,
links/devices/special entries, nested archives and payload kinds were inspected
before text materialization. Original0.9 expands to1373242 member bytes.
Independent installed bsdtar3.8.8 streamed every file into memory and matched
48/48,7/7,2/2,7/7 hashes, without extraction hooks or executing payloads.
A separate whole-container audit checked single gzip stream, sequential tar
blocks/zero terminators and exact ZIP local/central/EOCD extents; no hidden
prefix, concatenated distribution or trailing payload was found.

## Source closure, correspondence and chronology

Original0.9 has10 declared assembler input dependencies, all present.
It does not require the later66207_regs.h/init_66207 addition.
Five intermediates are declared generator outputs, not missing original source.
Its archived CVS Root/Repository/Entries bind the initial checkout metadata;
timestamps and CVS strings alone are not independent author authentication.

32 original docs/source/build/generated components were matched to protected
M2ay heads:10 byte-identical,22 changed. A private file-level matrix binds both
hashes and code/header/function/generator/security differences; no revision mix.
Changes include explicit emit_words endian handling, PRELOAD and register setup,
and Bison-to-byacc cached parser lineage. No generated source was patched.

| Snapshot / chronology | Established static finding | Boundary |
| --- | --- | --- |
| Original0.9 July2003 | TRB agrees across table/lexer/header/parser/dasm;1393 table rows/83 mnemonic names present in cached lexer/header | Bounded token/input consistency, not full regeneration or exact ISA proof |
| July11 RCS main/parser1.3 and obtained Win32v1.0 docs | PRELOAD added; original0.9 has reserved token only, no lexer directive/parser reduction/read helper | Changelog/static evidence, not binary execution |
| February2004 cached M2ay artifacts | TRB retained | Historical cached source, not current-table regeneration |
| Table1.9 February2006 | Log records TRB-to-TBR typo correction; cached artifacts remain older | Cause of divergence established; reason for omitted regeneration unknown |

Original0.9 is an identified complete input snapshot with bounded static
consistency. **Full generated-code correspondence remains NotEvaluated** because
generators were not run. No generic `ASM662Coherent` or complete-assembler PASS.
M2ay11-input heads retain their original TBR/TRB coherence blocker.
Three Win32 packages are separate binary candidates, not source replacements.

## Component licensing, not blanket legal approval

Actual0.9 ASM.txt/DASM.txt state broad full-source BSD licensing and Andy Sloane
attribution, and acknowledge the modified Doc opcode file. No complete BSD
variant/license text or Doc-specific original permission was found in the
obtained release. Project licensing/wiki notices do not automatically license
each embedded contribution. Doc legal-person identity is not established from
an alias or an unrelated disassembler attribution.

Original y.tab.c/y.tab.h identify **GNU Bison1.75**, retain FSF GPLv2-or-later
notices and an explicit unrestricted generated-output exception. That verifies
the exact skeleton contribution's documentary exception, not user grammar,
opcode-table rights or later byacc artifacts.
Authentic pinned historical FreeBSD flex/byacc notices were also acquired;
family-level generated-output permissions were kept separate from exact modified
skeleton identity/notice propagation. Those remaining rights are not silently waived.

| Classification | Actual result |
| --- | --- |
| OriginalProjectBSDStatementVerified | true |
| Original release broad BSD statement | verified in acquired bytes |
| OriginalReleaseLicenseTextVerified / complete BSD coverage | false; exact variant/full component scope unresolved |
| ComponentLicenseVerified | Original Bison output exception verified within exact files; other obligations unresolved |
| ThirdPartyRightsVerified / Doc rights | false / NotEstablished |
| MirrorRelicensingAuthorityEstablished | false; modern Unlicense addition does not supply original authority |
| LocalBuildRightsEstablished / PublicRedistributionRightsEstablished | false / false |

This is an evidence classification, not a comprehensive legal opinion or proof
that all lawful use routes are prohibited. No third-party source/archive/document
is reused publicly. Original notices remain unchanged.

## Safety and future mitigation design - NOT implemented

No implemented PRELOAD in0.9 removes one later-source read path, not all risks.
Unchecked PC/ORG/numeric/expression arithmetic, divide/shift bounds, overlaps,
symbol warnings, REL8 truncation, diagnostic-success behavior, DD omissions,
non-atomic unchecked output and host-endian DW remain static findings.
No exploit or native behavior was observed. Negative decimal ORG/OOB and
host-conditioned numeric conversion are not conflated.

For a future invented-only profile, **A: completely disabled PRELOAD** has the
smaller surface than **B: confined PRELOAD**. A needs no arbitrary file-read
resolver and original0.9 already omits the implementation. A future hardening
must reject the directive explicitly without silently changing unrelated grammar.
B requires OS-handle confinement, path/alias/symlink/reparse/hardlink/race checks,
immutable allowlisted inputs and bounded I/O; substring traversal checks are insufficient.
This selection is an engineering inference, not an implemented security fix.

The private14-area proposal covers bounds/checked writes, overflow/division/shifts,
relative branches, overlaps, missing symbols, fatal diagnostics/nonzero exit,
atomic fresh output, DD, path confinement, endian/width and resources.
Rights, exact source correspondence, a distinct reviewed patch, trusted tools,
isolated no-network/no-private-files/no-device environment and a separate milestone
remain prerequisites. No Makefile/generator/third-party compiler/build/run in M2az.

## Machine-readable contract and QA

[Contract](../research/p28-word0196/asm662_original_release_contract.json),
[validator](../research/p28-word0196/validate_asm662_original_release.py),
[tests](../research/p28-word0196/asm662_original_release_tests.py) are own-code only.
Pinned actual acquired evidence cannot be changed by JSON claims. Unknown
rights/uploader/build logs remain unknown; no input grants execution permission.
Invented documentary gate algebra and in-memory archive safety fixtures never
become real acquisition receipts, legal approval, runtime or encoding proof.
Required refusals include listing/HTML, corrupt archives, unsafe members, false
license scope/independence/revision/coherence, proposal-as-implementation,
unlogged build, invented native history and firmware promotion.

```text
python -B research/p28-word0196/validate_asm662_original_release.py
python -B research/p28-word0196/asm662_original_release_tests.py
```

CI adds only own static/invented tests, not distribution downloads or payload
execution. M2ay/M2ax/M2aw and M2av IR/C11/C# gates remain unchanged alongside
full Rust/Core/CLI/Desktop headless, format, diff and privacy checks.
Own M2av host C11 QA is not third-party ASM662 compilation.
Final private delivery receipts bind actual counts, protected hashes and the
exact new SHA's Ubuntu/Windows/Desktop jobs; old milestone CI is not counted.

## Preservation, remaining frontier and STOP

Runner0.43.0/protocol1/38 identities;20 original research files; production
executor/decoder/admission/scenarios and all18 stabilization sources unchanged.
M2av bounded equivalence/M2aw context/M2ax acquisition blocked/M2ay research
blocked retained. No target C ABI/compiler. WDT3C/C8 unresolved; reset/CAL/fullboot
blockers/M2ah STOPbefore5722/DATA019B.2 missing owner/strictM2i unchanged.
IRQNotInjected;TimerEvolutionNotModeled;RecoveredEcuSchedulerNotEstablished;
GUI/hardwareNotRun;Actual-ROM0;ASM662execution0;target bytes/objects/FirmwareBIN0.

One next evidence-driven step, **not performed**: authenticate the original Doc
66207.op/disassembler license or explicit contributor permission covering the
modified table, before considering any separately authorized build milestone.
No contact/inquiry sent. STOP: no M2ba, source patches/build/smoke, lowering,
linker/firmware/ROM replacement/trampoline, WDT/C8/reset/fullboot, GUI/hardware.
