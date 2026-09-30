# M2q native DATA0150 consumer and software selection

Read-only research, runner0.25.0, operation `fuelPostStoreConsumerChain`.
PcInspectionOnly / NotFlashReady; physical RPM/fuel/time/degrees unavailable.
Strict M2i remains Blocked on47 81. GUI r3 paused/NotRun; D1/D2 interactive
acceptance, hardware and full boot NotRun. No firmware BIN, writable calibration,
export, compensation, binding, receipt or token is created.

## Closed boundary and native provenance

Historical M2p `fuelPostStoreChain` still stops before223B after native2239 word
store0150. M2q uses the same reusable execution-in-state components and continues
that same CPU/RAM from223B to stop-before2259, including the actual5991 helper
only when reached by the native caller. There is no enter/reset/reload at223B,
second machine, repeated2204 suffix, host0150 write or JSON-to-RAM transfer.

223B loads existing word014C.223D compares unsigned A minus current word0150;
the carry flag records borrow and the zero flag equality.223F copies that carry
into shared012C.5, retaining bit4 and every neighboring bit.2242 takes JGE when
014C is greater than or equal to0150, retaining014C; otherwise2244 reads0150
again. Equality is the carry-clear path, not a forced replacement load.
2246 reloads A through its architectural alias to refresh DD/ZF.2248 skips the
addition and helper when the selected word is zero.

Nonzero selection adds existing word0144 at224A. Its source low byte is the
existing event snapshot and the high byte remains code-owned zero.224C/224E
saturate unsigned addition overflow toFFFF.2251 performs the actual native CAL5991,
including stack push, native helper instructions and RT to2254. The helper
computes `min(floor(input * 5 / 4), 65535)` using integer multiply and carry-linked
shifts, with a distinct overflow clamp. It intentionally clobbers er0/er1;
er2/er3, X2, DP, LRB and USP are retained and the stack is balanced on return.

2254 moves the helper or zero result into architectural X1.2255 reads the bit5
written by223F. Carry-clear comparison retains the result in A; carry-set
comparison executes2258 CLR A, leaving X1 intact. The two neutral completed
software outputs are `selectedScaledWordX1` and `retainedOrZeroA`. Their physical
role and units are unknown.

## Sources, lifetime and reachable relations

0150 is native-owned:2239 produces a fresh Written generation even when the value
equals the prior event.223D and, on the borrow path,2244 are word readers of that
same current generation. No consumer suffix writes0150. Previous event storage
therefore persists until the next native2239 writer; a failed suffix never creates
a completed consumer result or rolls back prior native writes.

014C has one authoritative M2p/M2o software snapshot before each event. Its upstream
static writer2172 is outside the scripted prefix and there is no writer between
the established prefix readers and223B. No second JSON014C field is introduced.
012C is one shared persistent byte. Bit4 belongs to the established factor contract;
bit5 is newly native-produced by223F and read2255, not an external software source.
No full-byte refresh or per-event bit5 setter is allowed.

Native M2p0150 is either0 or250..2000 (rises1..249 are masked tozero), and2210
makes it zero whenever014C is nonzero. Thus
the native reachable relation sets are: positive0150 with014C0/borrow; positive014C
with01500/no borrow; equality only when both are zero. Nonzero equality and broader
storage-domain inputs are separately labeled model-only/synthetic, not actual
chain coverage. After equality, the zero branch avoids both0144 and helper5991.

## Why the suffix stops before2259

2259 is AND IE,#02A0, followed by a PSWH interrupt-mode edit at225E. The new
software-only contract does not cross this IO/IRQ boundary. The nearest static
readers of X1/A are2261 (word0194) and2264/2266 (words0190/0192), not dynamically
executed by M2q.

Unchanged original60E5/60F8 remain zero. The later226F configuration load/2273
branch and the static227A/per-channel bypass to229F are beyond the admitted
boundary: StaticOnly/NotEvaluated, not a dynamic bypass proof. No forced PC227A,
60F8 override, alternate configuration image or claimed per-channel execution is
introduced. Public invented branch-shape regressions are not actual-ROM coverage.

## Independent model, proof and partial execution

C# independently owns ROM bytes, adaptive/limiter history, fuel caches, factor
history, previous03B4, native0150 projection and downstream012C history for each
A/B image. Rust0150, selection or helper output never become model inputs and
the model never supplies a ready result to execution.

The validator checks current2239 generation, entire223B entry boundary, exact
word operands and direction, flags, selected branches, native bit5 read/write,
caller/helper/return, ordered reads/writes, aliases, banks, stack, final X1/A and
stop-before2259. Correct final numbers cannot excuse stale0150, byte readers,
swapped operands, forged equality or return, reset entry or wrong register bank.
Mandatory forms are exact-form admitted from primary ISA evidence;47 81,45 81
and disputed SUBB are not promoted. Runner version is capability, not ISA proof.

A partial/unresolved event retains completed M2p observations and partial native
stores, reports new results null, and makes later snapshots/ticks/events terminal
NotRun. Selected traces remain limited to8; bounded mandatory proof journals
are never silently truncated. Earlier ABI entries remain scripted software tests,
not a recovered ECU scheduler.

## CLI, scenario and in-memory A/B

```text
hondaecu research p28-fuel post-store-consumer-check <original.bin>
  --profile p28-304 --confirm-profile --baseline-binding <binding.json>
  --runner <runner-0.25.0> --scenario <m2q-scenario.json>
  --output <new-private-report.json>
```

The closed version1 purpose is `post-store-consumer-native-software-test`: one
authoritative M2p initialState,1..64 dense existing M2p calls, at most32 combined
native ticks/event and8 trace indexes. No new sources are needed. DATA0150,
bit5, selection, helper result, RAM/PC, branch choices, formulas and60F8 setters
are refused. Exact binding, input snapshots/rechecks, fresh-output alias guards
and bounded subprocess timeout/cancellation reuse existing contracts. Historical
runner0.24 is accepted only for earlier tasks, not this operation.

The optional mutation remains one primary raw-u8 fuel cell (nonzero delta at most8)
or one existing adaptive bank cut/resume word within the established narrow guard.
Every B starts independently from original; no accumulated cell+word changes.
Code/config/axes/metadata/coefficients and60F8 are unchanged, and checksum
calculation is diagnostic arithmetic only. Cell experiments follow0140, corrected
03B4, native0150, actual223D selection and X1/A, with unread/truncation/threshold/
clamp/selection masks separated. Adaptive-word controls may change limiter request
and03A2 without changing these ungated downstream inputs; no effect is invented.

Actual-ROM, model-only, compatibility and invented public subprocess counts are
reported separately under `private/reports/m2q/`. Old M2p223B and M2o2204 scopes
remain unchanged. No next stage, GUI or hardware is started automatically.
