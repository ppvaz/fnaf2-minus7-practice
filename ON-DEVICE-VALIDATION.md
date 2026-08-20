# On-device validation (bot over adb)

Started 2026-08-20 with the Moto g56 5G plugged in over USB. Goal: test the
decoded Android model's load-bearing rules against the real
`com.scottgames.fnaf2` build instead of only the event-sheet reading.
Target build confirmed on device: **v2.0.7** (versionCode 26, updated
2026-08-14) — matches the ledger's "release 7" target.

## Validation targets, ranked

1. **Consecutive-tick mask clears** (g292-294): a masked vent visitor should
   need ~5 s of *continuous* mask to be forced out (10%/s early roll), not the
   PC-style sub-second repel. This single rule refuted the whole Minus 3
   family in `tools/minus2test.mjs`; if the device disagrees, that family
   reopens.
2. Double-camera glitch absence (one `viewing` counter, atomic per touch).
3. Right-vent-light Toy Bonnie stall (g428).
4. Vent lights not draining the battery (g284).
5. Office-defense fuse by night (`time allowed` 100..45 frames) and the
   300-frame office sequence.

## Harness (tools/device/)

- `coords.sh` — touch calibration for this device (2400x1080 landscape),
  derived from labeled 100-px grid overlays on screenshots. Regenerate the
  grids per device/resolution.
- `trial-maskcamp.sh <name> <seconds> [continue|6th]
  [wind|nowind|nowind-flash]` — one
  scripted mask-camp trial. `wind` mutes the call, fills the box on CAM 11,
  drops, and masks; `nowind` makes a quick monitor flip and masks around 4 s
  into the recording for a longer window over early vent arrivals;
  `nowind-flash` adds one hall flash before the mask to reset W. Foxy while
  preserving continuous mask from that point onward.
  `screenrecord` captures the run (downscaled 1280x576 @3 Mbps).
- `run-batch.sh <n> [night] [prefix] [wind|nowind|nowind-flash]` —
  back-to-back trials plus event detection per capture.
- `screenstate.py` — classifies live screenshots as `night`, `gameover`, or
  `other`. The game-over signature was checked against all three retained
  W. Foxy captures; jumpscare/static frames remain `other`.
- `find-events.py <mp4>` — frame-diff event locator (stdlib only): prints
  timestamp ranges with sharp visual change (overlays, flips, jumpscares) so
  clears can be timed without scrubbing video.
- `camtrace.py [--expected N] <mp4>` — post-run selected-camera trace from
  the map's lime highlight. It verifies that printed ADB commands became real
  `10 -> 04 -> 07 -> 11` sweeps and can fail a trial when any expected sweep
  is absent.
- `windpct.py [--samples] <mp4>` — post-run CAM 11 pie-gauge meter. It uses
  the presence of the lime winding button to reject other feeds, then measures
  the solid white gauge interior. It does not participate in the timed loop.
- `grade-minus7.py <mp4>` — stable office/mask/camera state report plus visible
  hall-beam pulses. Its hall rule runs before the broad camera/static rule and
  rejects beam-like frames that begin inside an existing camera interval, so
  camera-light flashes do not become false Foxy resets.
- `trial-minus7.sh <name> [cycles]` — selectable-night Minus 7 interaction
  runner (`NIGHT=6th` by default; `NIGHT=continue` is the override). It gates
  the start, then executes one absolute-time device-side schedule. Independent
  safety guards cancel the exact remote driver immediately if the game loses
  focus or after three consecutive non-night screenshots. The fast screenshot
  path captures raw on-device and transfers only HUD scanlines. Neither guard
  chooses or retimes an action. The runner enables ADB touch/pointer overlays
  and grades the pulled recording by default (`DEBUG_OVERLAYS=0` and
  `GRADE_RUN=0` are the opt-outs).
- `grade-minus7.py <mp4>` — post-run classifier for Minus 7 screenrecords.
  It reports stable camera, office, and mask intervals and flags masks that
  remain latched for more than one second.

## Hard-won harness rules

- **The Fusion runtime polls touch by frame: zero-duration `input tap` is
  dropped roughly half the time.** Every touch must be a duration press —
  `input swipe x y x y 120`. This explained all the "did nothing" ghost runs.
- Concurrent `input swipe` processes are not independent fingers. Holding the
  camera light while launching camera-button swipes corrupted the input stream:
  a three-cycle trial produced two multi-second mask latches and entered the
  cameras only twice. Keep injected gestures non-overlapping.
- **Interactive driving is impossible**: inference/command latency between
  actions is a game over. Trials are single pre-scripted wall-clock
  sequences; analysis is post-hoc on the recording. A human watching the
  device is the best live observer. Trials enable `show_touches` and
  `pointer_location` by default for a visible touch dot and crosshair; run
  with `DEBUG_OVERLAYS=0` to disable both.
- **Never tap blind.** The script force-foregrounds the game and checks
  `mCurrentFocus` before any input: one unguarded run landed 150 s of taps
  in the Clock app and opened a real alarm's edit dialog (cancelled,
  nothing changed).
- A completed timed input list is not evidence that the game is still alive.
  The 12-cycle endurance attempt died around 38 s, after which its uncancelled
  inputs reached the title and selected New Game. `Continue` was reset to
  Night 1, although the star and 6th Night unlock remained. The Minus 7 runner
  now records the remote shell PID, kills its input children after three
  consecutive non-night screenshots (or one lost-focus sample), force-stops
  the game on every exit, refuses to overwrite captures, and saves a partial
  `-aborted.mp4` when possible.
- The device owner subsequently authorized 6th Night as the available quick
  testing ground. Mask-camp, batch, and Minus 7 interaction tests therefore
  default to `6th`; set `NIGHT=continue` explicitly to use the campaign cursor.
- The bottom ~40 px belong to Android gesture navigation — keep game taps at
  y <= 1020.
- The light input is view-dependent. `(350,615)` activates the camera light
  while the monitor is up, but activates the **left vent light** in the office;
  it does not flash Foxy. The office hall light is `(1200,540)` on this device,
  well inside the hallway hit region; the initially tested `(1400,330)` sat
  near its upper edge and intermittently placed the pointer without a beam.
  A five-coordinate recording (`hall-coordinate-cal`) visibly distinguished
  the green/blue vent light from the circular hall beam. Keep separate
  `TAP_CAM_LIGHT` and `TAP_HALL` coordinates. The hall actuator also needs a
  real hold: a 60 ms swipe placed the debug pointer correctly but produced no
  beam. Neither a longer hold nor a later single attempt cured every
  intermittent in-game lockout. The runner therefore makes two separated
  200 ms and 150 ms attempts across the office window. Together with three
  60 ms camera flashes per five seconds, the worst case is about 106 ms/s
  against the 119 ms/s light budget.
- A locked phone presents `NotificationShade` as the focused window even
  when the game activity is underneath it. The harness wakes the display and
  asks Android to dismiss an unsecured keyguard, but a secure keyguard must
  be unlocked by the device owner; the focus guard aborts before any tap.
- Title menu: the first press shows the `>>` cursor, the press must land on
  the item's hitbox (`Continue` at (400,730); `6th Night` at (400,880));
  hitboxes sit slightly above the painted text.
- The port swallows inputs briefly around the monitor flip; the mask press
  goes in ~0.3 s after the drop press (still inside the 50-frame night-5
  defense fuse).
- Nights start ~15 s after the press (intro + load varies): scripts must not
  time anything from the press itself; the recording's visible events are
  the clock.

## Findings so far

- **W. Foxy behaves as modeled (qualitative #2).** Three closed-loop 6th
  Night mask-camp trials died at 29/31/31 s to the W. Foxy office lunge
  (killer identified from the jumpscare frame) with the mask continuously on
  from ~11 s — the mask does not deter him, his D grows unflashed, and the
  10 s GOT-YOU cadence lands exactly in the predicted window. This also sets
  the protocol's observation ceiling: ~15-20 s of masked window per trial
  unless the hall is flashed (which breaks mask continuity).
- The closed loop works: `screenstate.py` gates every phase (wait-for-night
  before any tap fixed the too-early MUTE press; death detection ends the
  recording within ~6 s), and a 5 s wind hold fills the box to ~95% (pie
  gauge center ≈ (740, 840), radius ≈ 95 at 2400x1080 — a fill-percent
  meter is a planned upgrade).

- **Office-defense fuse behaves as modeled (qualitative).** Trial 4's mask
  landed ~3 s after the monitor drop — far past the sourced 50-frame night-5
  fuse — and the run died ~6 s after the drop, matching fuse expiry plus the
  300-frame office sequence. A timely mask (trial 5, ~0.45 s) survived the
  same phase.
- Mask-camp segments recorded cleanly (trial 5: ~26 s continuously masked,
  box-empty death at ~48 s). No vent visitor entered the masked window yet,
  so target #1 remains unmeasured — it needs more trials (6th Night has the
  higher AIs and more vent traffic).
- Follow-up no-wind trials masked at ~4 s but still produced no vent overlay
  before W. Foxy attacked (earliest lunge began around recording second 18).
  A single pre-mask hall flash moved the observed Foxy onset to ~24-28 s but
  likewise yielded no vent visitor. A long CAM 11 hold intended to force BB's
  cameras-up-only fourth hop is not viable as one blocking ADB press: office
  danger forced the run down around second 25-29 while the press was still in
  progress, so the mask command arrived after death. Do not restore that
  protocol; a later attempt needs short scripted slices or a real survival bot.
- Custom Night is not yet unlocked on this save (Night 5 + 6th Night only);
  the in-app "Unlocks" menu is paid cheats, not night selection. Character
  isolation therefore waits until 6th Night is beaten (a bot playing Minus 7
  on-device is the fun route to that).
- **Minus 7 timing calibration is post-hoc.** Plain taps removed command drift
  but dropped critical transitions. A held-light shortcut caused overlapping-
  touch failures. The first 40 ms asynchronous trial missed a later CAM 10;
  at 60 ms, a late light helper made the next absolute slot catch up only 79 ms
  later and overlap, dropping CAM 04. Direct `/dev/input/event8` injection is
  denied by SELinux despite the shell user's `input` group, and separate
  `motionevent DOWN`/`UP` helpers were slower than one swipe.
- **The default is now a synchronous 60 ms swipe.** On this Moto g56 the helper
  takes about 170 ms, so 190 ms action slots cannot overlap. CAM 10 to CAM 11
  takes 1.14 s instead of the old reliable cadence's 1.38 s. The monitor-down
  animation still gets a dedicated delay before the mask. CAM 10 also waits
  500 ms after monitor-up: shorter gaps were visibly swallowed by the flip and
  left the feed on CAM 11. Shortening either gap trades away input acceptance,
  not camera overhead.
- **The fast default passed a four-cycle 6th Night validation.** The 26.75 s
  `fast-sync60-6th-4c` recording contains all five expected
  `10 -> 04 -> 07 -> 11` sweeps (opening plus four cycles), five camera
  intervals, four momentary mask sequences, and no latched mask. An earlier
  two-cycle run also passed 3/3 sweeps and both mask sequences.
- **The first six-cycle extension exposed a pre-existing hall-coordinate bug.**
  Its first five camera sweeps and box holds were clean, but the supposed hall
  flashes were actually left-vent flashes. W. Foxy attacked at about 28.3 s,
  matching the repeated short-run failure the device owner observed. This was
  an actuator-mapping failure, not evidence against the sweep cadence; the
  runner now sends office flashes to the separately calibrated hall control.
- **The corrected six-cycle default crossed the old failure window.** The
  37.75 s `validated-default-6th-6c` run completed 7/7 selected-camera sweeps
  and all six scheduled monitor/mask cycles, with no Foxy attack or safety
  abort. Five hall beams were visible; both redundant attempts landed during
  some windows, while one whole window remained dark from the game's transient
  light lockout. The post-run gauge stayed in a 52-78% band. This is a bounded
  validation, not yet a full-night clear.
- **Winding is now rate-balanced instead of capacity-seeking.** Nights 6-7
  drain 120 box units/s when not winding and add 300/s while held, so net-zero
  over a five-second cycle is `120*5/(300+120) = 1.429 s`. The fast runner uses
  1400 ms, within one 30 Hz Fusion update of that balance point. Offline gauge
  measurements in the final six-cycle validation stayed around 52-78% and
  never reached 100%.
  By contrast, the old 1700 ms holds reached 100% partway through later holds.
- **The hardened runner passed its 6th Night safety validation.** An exact-PID
  test killed a harmless remote process and its host ADB session. Controlled
  game force-stops then established both failure paths: the raw-scanline guard
  cancels on persistent non-night state, while the independent 70-100 ms focus
  poll prevents queued input from reaching another app if the game process
  disappears outright. A normal two-cycle run completed without false abort,
  pulled its capture, graded it, and left the launcher focused after cleanup.
  That same run reconfirmed that `PRESS_MODE=tap` is observably unreliable: the
  command log was complete, but the recording contained only the opening camera
  interval and one later mask. Keep synchronous `fast-swipe` as the default.
- **Shooter25's bot establishes the in-game alternative for reactive work.** A
  Debian-patched CTFAK extraction of the official PC practice executable shows
  a direct-state Clickteam controller, not a vision bot. See
  [`SHOOTER25-PRACTICE-MOD.md`](SHOOTER25-PRACTICE-MOD.md) for the comparison
  and [`SHOOTER25-BOT-STATE-MACHINE.md`](SHOOTER25-BOT-STATE-MACHINE.md) for
  its controller, office-pan, and actuator reconstruction.

## Simulating the pilot (2026-08-20)

`tools/pilottest.mjs` replays `trial-minus7.sh`'s millisecond table in the
sourced engine with no state reads, so schedule changes can be judged without
spending a night on the phone. The shipped blind schedule dies **200/200 to
Foxy**.

> **Corrected 2026-08-20.** This section previously read "dies 200/200 to
> Balloon Boy walking in", and the table below carried the numbers that went
> with it. `e8fcf2f` removed that death: the source has none there at all.
> g96 forces `lit?` to zero every frame while BB is at 123 and g301/303 stop
> the vent lights answering, so a BB who walks in is **permanent and harmless
> by himself** — he takes the flashlight away and Foxy finishes the run. The
> commit that changed the mechanism said so in its own message and did not
> update this file. The numbers below are re-measured at `114b12f`.

Adding the one observation the phone can actually make — flash the left vent
light with the cams down and classify one screenshot (g289 draws BB at the
opening, g287 draws it empty) — plus a mask hold long enough for g294's five
consecutive masked ticks:

| Schedule | Result |
| --- | --- |
| blind, as shipped | 0/200 — every death is Foxy (105 no-blackout, 95 flashed after lock-on); min box 59%, min power 2460 |
| + vent check | 0/200 — **no BB or Foxy deaths left**; 87 Golden Freddy on a raise, 113 the seven inside; min box 0%, min power 2454 |
| + Markiplier eviction | 0/200 — **worse**: 177 Foxy, min power 2252 vs 2460; 200 evictions |

Note what the vent check actually trades. It removes every BB death *and*
every Foxy death, and pays for them with 87 Golden Freddy kills on the
monitor raise plus 113 office deaths — and it drives min box from 59% to 0%.
It is not a partial fix that needs tightening; it moves the whole failure
somewhere else.

### Device confirmation of the causal chain (2026-08-20)

One 80-cycle run on the phone, `trial-minus7.sh minus7-fullnight-20260820 80`,
Night 6. It died at **~138 s of the 420 s night** — the HUD still reads 1 AM —
after roughly 26 main cycles, well past the six-cycle cadence that had been
validated until now. The graded capture shows the corrected chain end to end:

1. BB is already standing in the office at ~137.6 s, visible through the mask
   eyeholes and then in the open office with his sign.
2. The scripted mask flick runs anyway — mask-on 137496 ms, mask-off
   137836 ms — because the schedule is open-loop and cannot know he is there.
3. Both hall flashes fire on time, 138085 ms and 138445 ms, and **do nothing**:
   BB has taken the flashlight, exactly as g96/g301/g303 describe.
4. Withered Foxy comes down the unrepelled hall and kills. Static at ~139 s.

So the phone reproduces the sim's Foxy death and the old "BB death" reading at
once, and shows why they were ever confused: BB is the cause, Foxy is the
killer, and only the second one is a death event. This also satisfies next
step 2 manually — the frame before the static did identify the killer.

### Teaching the pilot Balloon Boy (2026-08-20)

Two input gates were missing from the engine, both about *reachability* rather
than effect, and both flattering the pilot: the mask could go on with the
monitor up (a state the game has no way to reach), and while masked every
other control still answered, when g75/g84 leave a masked player nothing but
taking the mask off. `press()` now drops both, and the human control is
unaffected — `bbtest` never used either, which is the point.

With those in place the vent check's 87 Golden Freddy deaths turned out not to
be a Golden Freddy problem at all. Every one of them landed on the *first*
press of a cycle, the one the table means as "cams down". A sourced forcedown
(g141, executed on the monitor by g262) had already dropped the monitor
underneath the schedule, so that press — a bare toggle — **raised** the cams
instead, into an office where Golden Freddy was waiting, and g777 killed. The
schedule was desynced from the game and had no way to notice.

`--sync` makes the two monitor actions *intents* rather than presses: the
pilot spends one screenshot on the monitor state and presses only if the state
disagrees. It is device-legal — the look can be taken a second early and the
decision is a skip, not a timed reaction, so it does not need the reaction
budget that rules out interactive driving.

| Schedule | Result | Median depth |
| --- | --- | ---: |
| blind, as shipped | 0/200, all Foxy | 48 s |
| + vent check | 0/200; 87 Golden Freddy, 113 inside | 54 s |
| + vent check + `--sync` | 0/200, **every death now one mode**: the seven inside | 58 s |

So BB, Golden Freddy and Foxy are all handled, and the whole failure has
collapsed onto a single mechanism: during the response's 6.4 s cams-down
window the seven's entry timers run to completion and they walk in. Best
single night rose 92 s -> 98 s of 420. That is real progress and nowhere near
a win — the response buys BB at a price the seven collect.

**The device script is deliberately untouched.** `--sync` costs a screenshot
per monitor action, and whether the phone can classify office-vs-camera view
fast enough to keep the cadence is a device question this simulation cannot
answer.

**The eviction does not transfer to an open-loop pilot.** Spending the sourced
700 frames of hall light only evicts Foxy if he is actually in the hall while
it runs, and it only pays for itself if BB's forced mask window lands inside
the 500-999 frame nap. Markiplier can arrange both because he hears BB's
laughs and reads the hall; a pilot holding one vent screenshot per cycle knows
neither, so it burns the power and takes the exposure anyway.

**The "about 8 s" cost this section used to quote is withdrawn.** It was
written before `74e0148` sourced the mask counter, and it priced the
five-tick term at a flat 5.0 s. g907 increments v12 on the one-second event
boundary, so five ticks span *four* boundaries and the cost depends on where
the hold starts: 4.017 s if it becomes fully-on one frame before a boundary,
5.000 s if it lands exactly on one. That is a full second of spread the flat
figure hid, and the conclusion drawn from it — that the response overruns the
6.67 s stall so "one 5 s interval always lands uncovered" — **does not
follow and is not established.** The response's monitor-down portion is
6.4 s against a 6.67 s hold, not 8 s against it.

The pilot's `RESPONSE` table currently budgets the worst phase: mask on at
+800 ms, fully on by +1000, off at +6000, a flat 5.0 s hold that is never
aligned to the boundary. Up to ~1 s of that is recoverable by phasing, and
nobody has tried it.

What *is* measured is the table above: the vent check does clear BB and Foxy,
and still loses 200/200 — to Golden Freddy on the raise and to the seven
inside. So the response is net-fatal for reasons the timing arithmetic never
described. On PC the canonical strategy holds the flashlight straight through
the mask; g75/g84 make that impossible here. The proposed fix is a **second**
observation rather than better timing: a CAM 05 peek during the sweep would
see BB one move out (his 5th move
is the only monitor-gated one) and let the pilot prepare instead of react.

## Next steps

1. The synchronous cadence now holds for ~26 main cycles on the device (see
   above), not six — the schedule itself is not what fails. Keep grading the
   selected-camera trace and gauge; do not treat printed commands as accepted
   game input. `Continue` currently points to Night 1, while 6th Night is the
   authorized quick testing ground. Do not restore the held-light shortcut or
   asynchronous short swipes.
2. Automate what was done by hand above: grab the frame before the static to
   identify the killer. The `gameover` state (red face + bright lower-center
   text) is implemented; the killer identification is not.
3. Phase the `RESPONSE` mask hold to the one-second tick boundary and re-measure.
   The sourced clear is 4.017-5.000 s depending on phase and the table currently
   spends the worst case; this is the one cheap timing lever left, and it has
   never been tried.
4. Calibrate `windpct.py` against a deliberately empty-to-full capture if its
   approximate percentages will drive an interactive policy. Keep it out of
   the live Minus 7 loop unless the policy actually needs a branch.
5. Longer term: beat 6th Night and unlock Custom Night, then use character-
   isolated stock runs. For reactive strategies, compare live CV against a
   separately signed, direct-state instrumentation build.

## Bookkeeping

- Captures live in `captures/` (gitignored); delete failed runs immediately —
  raw screenrecords are large.
- Developer overlays (`show_touches`, `pointer_location`) are enabled by
  default whenever `trial-maskcamp.sh` starts and remain in that state after
  the trial. Use `DEBUG_OVERLAYS=0 tools/device/trial-maskcamp.sh ...` to run
  without them.
