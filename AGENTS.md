# Historical Research Archive Access Policy

These instructions supplement, and never weaken, the project's source, evidence,
privacy, safety and milestone restrictions.

- Keep source code, Git/worktrees, active work, contracts, oracles, validators,
  current fixtures, FINAL reports and compact receipts local. Ordinary builds
  and GitHub Actions must not require the private NAS.
- Before opening historical evidence, look locally, then search the offline
  index `private/archive/ARCHIVE_INDEX.jsonl` with
  `python -B tools/archive/hondaecu_archive.py find QUERY`.
- Use `private/archive/config.json` or `HONDAECU_ARCHIVE_CONFIG` for private
  locations. Never put SMB credentials, private index entries, server addresses
  or OEM names in public source, Git commits, logs or CI. If Windows needs
  authentication, ask the user to establish access manually.
- An `ArchivedAndVerified` entry is a past integrity observation, not proof that
  the archive is online now. Check access once when a required operation needs
  it. No polling, background sync, scheduled monitor or Wake-on-LAN.
- If mandatory evidence is offline, identify the exact files and purpose, ask
  the user to turn on the configured server and reply "Сервер увімкнено", and
  stop only that dependent step. Do independent local work when possible.
  Retry once after the user's reply and resume the saved step; do not repeat
  already completed work.
- Use `get` for one file, or `restore` for the explicitly selected dataset.
  Keep restored data in a controlled restore/verification directory, verify its
  size and SHA-256, and resolve old absolute paths through the index. Never
  overwrite an existing historical file with different bytes.
- Frozen validators/contracts/source SHA bindings and old reports must not be
  rewritten for archiving. Restore their exact dependencies before invocation.
  If an alternate checkout/path cannot satisfy an old validator, retain or
  explicitly restore the needed original path; never skip the check or claim
  PASS. Existing whole-storage preservation snapshots may require full restore
  or a separately approved archive-aware audit; they are not silently rebased.
- Preserve `PendingMigration`, `RestoreRequired`, `IntegrityMismatch` and
  online/offline states distinctly. Never reconstruct missing evidence from
  assumptions or new runtime experiments.
- Migrate only an explicit reviewed plan using COPY -> VERIFY -> dual durable
  RECEIPT/index -> LOCAL RELEASE. An interrupted transfer or hash mismatch must
  leave the local original intact. Never use destructive mirror/move sync.
- Before releasing the first batch of unique local evidence, obtain the user's
  single explicit approval for the exact plan and, if NAS backup is unknown,
  explicit acceptance that NAS could become the only copy. Without approval,
  copy/verify only. No symlinks/junctions to NAS by default.
- After a milestone, retain current source/reference data, FINAL report and
  compact receipts locally. If NAS is offline, retain large evidence locally as
  PendingMigration and ask when archival becomes necessary. Do not create a
  second whole-project/cache copy.
- Archive infrastructure work does not authorize new ECU milestones, runtime
  experiments, firmware, GUI/hardware, full regression/CI, commits or pushes.
  Keep independent archive changes separate from unfinished M2br changes.

# Codex Milestone Automatic Resume Policy

- Save a compact, atomic checkpoint after each meaningful milestone step.
- On a resumed session, read the existing checkpoint and verify the relevant
  source identities and saved receipts before taking the next unfinished step.
- Detect an existing owned runtime process and its exact command/identity;
  never start a duplicate or rerun completed, verified cases after interruption.
- Resume only when source/corpus identities and complete canonical records agree.
  Preserve partial evidence and report a concrete blocker if safe resume fails.
- Continue automatically through the authorized QA, commit, normal push, the
  same exact-SHA CI run, evidence seal and final report; do not require a new
  resume prompt merely because the previous answer was interrupted.
- Respect an explicit user pause immediately. Resume work only when the session
  is resumed; do not create background automation or widen milestone authority.
- Stop for a real technical blocker, missing authority, or completed delivery;
  never begin a later milestone, GUI, firmware or hardware without authorization.
