## IMPLEMENTATION PLAN — the sub-hour re-run

### The structural fact that reorders everything

Every audit finding ends with the same warning: *"re-searching this segment invalidates every downstream segment."* That warning is only expensive if changes land one at a time. They don't have to. `zelda/runner.py:122-126` replays each winner into MAIN and re-asserts `success()`, so any mid-log edit forces a re-search of the tail — but the tail is being re-searched anyway, because the route itself changes. **Land every code change first, run once from power-on.** The invalidation cost is paid exactly once, and it drops out of every individual step's risk budget. Do not start a run to "bank" an early win.

Corollary: nothing in this plan should be validated by editing the existing 372,090-frame log. It is an archive artifact from here on.

---

## FRAME BUDGET

`60.0988 frames = 1 second`. Current totals reconstructed from `logs/fullgame.txt` by walking the cumulative `(total N frames)` counter and rewinding on each `resumed checkpoint` line, so abandoned branches (the dead "L4 before L1" attempt at lines 1-32, `l4_stairs`, `whirl_back*`) are excluded: 596 surviving segments, deltas summing to 356,168 + a 15,922-frame milestone3 prologue = **372,090 exactly**.

| # | Phase | Current | Target | Δ |
|---|---|---:|---:|---:|
| 1 | Power-on → Level 3 Triforce (prologue, never re-searched) | 15,922 | 15,000 | −922 |
| 2 | L3→L1 travel + LEVEL 1 | 15,248 | 13,500 | −1,748 |
| 3 | White Sword + travel to L4 | 10,447 | 9,500 | −947 |
| 4 | LEVEL 4 (incl. `gleeok` 6,020) | 24,136 | 18,000 | −6,136 |
| 5 | L4→L2 travel | 5,116 | 4,800 | −316 |
| 6 | LEVEL 2 | 6,204 | 5,800 | −404 |
| 7 | L2→L5 travel | 3,591 | 3,400 | −191 |
| 8 | LEVEL 5 | 16,930 | 15,500 | −1,430 |
| 9 | L5→L6 travel | 11,626 | 11,000 | −626 |
| 10 | **MONEY: L6 abort 7,677 + arrows farm 38,270 + shop travel 6,923 + return 10,070 + food-farm trip 27,598 + food shop/re-entry 7,079** | **97,617** | **12,000** | **−85,617** |
| 11 | LEVEL 6, single climb + Gohma | 16,814 | 15,000 | −1,814 |
| 12 | L6→L7 travel + pond drain | 3,413 | 3,200 | −213 |
| 13 | LEVEL 7 | 21,113 | 18,500 | −2,613 |
| 14 | L7→L8 travel | 8,319 | 7,800 | −519 |
| 15 | LEVEL 8 (incl. `cave_6b` money round trip) | 30,570 | 26,000 | −4,570 |
| 16 | L8→L9 travel — **now carries Magical Sword + heart #12 + bombs** | 12,745 | 20,000 | **+7,255** |
| 17 | LEVEL 9 entrance wing (single entry) | 5,730 | 5,500 | −230 |
| 18 | *Magical Sword / heart detour out of L9* | 19,813 | 0 | −19,813 |
| 19 | *L9 wing re-walk + `s9_25` dead end* | 5,021 | 0 | −5,021 |
| 20 | *Bomb-buying round trip* | 17,498 | 0 | −17,498 |
| 21 | LEVEL 9 Silver Arrow wing (drop the `0x43` dead end) | 12,246 | 7,500 | −4,746 |
| 22 | Ganon + ending + credits | 11,971 | 11,500 | −471 |
| | **Route subtotal** | **372,090** | **223,500** | −148,590 |
| | Cross-cutting search/idle fixes (Steps 3, 8, 9, 10 — spread over every re-searched phase) | — | −8,000 | −8,000 |
| | **TOTAL** | **372,090** | **215,500** | **−156,590** |

**215,500 frames = 59 min 45 s. The limit is 216,000. That is a margin of 0.2%.**

Say this plainly to the owner: **under-60 is reachable without breaking any rule, but there is no slack.** It requires (a) both farms deleted and funded by a cave, and (b) Level 9 entered once. Either one failing on its own costs the hour:

- If the `0x0F` cave probe fails and a trimmed single farm is needed as backstop: **+25,000 → ~240,000 (66.5 min). Target missed.**
- If the caves land but Level 9 still needs two entries: **+18,000 → ~233,000 (64.6 min). Target missed.**
- If everything lands and the owner also adopts the standard timing convention (Step 0 below): **~205,000-211,000 (57-58.5 min)** — the realistic floor.

The single decision with the most leverage is not a code change at all — it is Step 0.

---

## STEP 0 — OWNER DECISIONS (ask before writing any code)

These four questions change the target by more than most of the engineering does.

1. **Where does the clock stop?** `g9_zelda` reaches the ending trigger (`$12 == 0x13`) at frame 369,088. `g9_credits` is the remaining **3,002 frames** of credits playing themselves out with no buttons held. Zelda 1 speedrun convention ends timing at the final hit / rescue. If the owner adopts it, that is ~3,000-4,000 frames and it turns a 500-frame margin into a 4,500-frame one. Recommend: keep recording the credits for the video, report the time at the rescue.
2. **Heart container #13.** `hc_2c_heart` costs ~3,012 frames in the detour. Only **12** containers are needed for the Magical Sword (`grave_sword_policy(nav, need=12)`, `fullgame.py:1450`, hard gate at :1463). The brief records an owner preference for hearts; this trades ~3,000 frames against survivability in Level 9. Recommend keeping #12 only and letting the search's heart ranking protect the rest.
3. **Bomb capacity upgrade.** Memory says buy it (100 rupees, max 16). With cave money this is affordable and it is what makes single-entry Level 9 possible. Confirm the 100 rupees is authorised spending.
4. **Boomerang.** Taken in Level 1 (`l1_44_boom`) and `select_b_item` never selects it again in the entire run. Drop the pickup, or keep it because it is on camera?

---

## PHASE A — CODE CHANGES (no emulator time; land all of these before any run)

### STEP 1 — Overlay reasoning per room (owner complaint #1) — 0 frames

The feature the owner actually asked for. It cannot be bolted onto the current data path, which is broken three ways, all verified.

**1a. Fix the timeline source.** `harness/record_run.py:72-78`, `boundaries()` globs `logs/checkpoints/{name}_*.json` — 618 files for a 610-segment run. Abandoned-branch checkpoints (`l4_stairs`, `whirl_back0-5`, `x8_2e`, `dock`, `ow4_73`, `c8_*`) inject ~30 phantom captions into the finished video, including `segment l4_stairs` displayed in the middle of Level 1, and displace 7 real ones. Replace `boundaries()` with a timeline built from the ordered `segments` array **inside the newest checkpoint**, and drop any checkpoint whose last segment is not in that list.

**1b. Key events off segment START, not END.** `runner.py:72` writes `"frames": len(self.main.inputs)` — the count *after* the segment finished. So every caption today fires one segment late. Build `{start_frame: segment}` where `start_frame` is the *previous* segment's `frames`. Proof of the lag: `logs/fullgame.txt` records `[warp_L3] 162 frames ... (total 16084)` while the event lands at 16085.

**1c. Keep `boundaries()` returning `dict[int, str]`.** `record_run.main()` uses `marks` as a dict at lines 89, 90 and 93. If it starts returning a list of tuples and `main()` is untouched, `i in marks` is False for every int and **the video renders with no captions at all**. Also rewrite the loop as `j = i + 1` (retiring the `if j == i: j = i + 1` guard at :95-96) and flush any mark at `>= len(frames)` after the loop, or `g9_credits` never fires.

**1d. Author the WHY in a new leaf module `harness/zelda/intent.py`:**
```python
INTENT: dict[str, tuple[str, str]] = {
    "l6_2d": ("LEVEL 6 - ROOM 2D", "Kill every Darknut: this room only drops its key once the "
                                   "floor is clear, and the door north to Gohma is locked."),
    "l7_feed": ("LEVEL 7 - THE HUNGRY GORIYA", "Nothing can kill him. He moves for meat and "
                                               "nothing else - that is what the 60 rupees bought."),
}
```
Do **not** add a 5th element to the segment tuples. `cross()` at `fullgame.py:1867-1869` returns a 3-tuple and ~200 `S.append((name,) + cross(...))` sites build on it; a 5th field means touching all of them plus the unpack at `fullgame.py:2815` and the call at :2818. A name-keyed side table costs nothing and cannot break the run. Much of the copy already exists as comments above each segment in `segments()` — lifting them is most of the authoring work.

**1e. Panel layout, `harness/render_overlay.py`.** The usable column is 480px at x=784 and it is full. `"THINKING"` is drawn at `(PX+16, 60)` (:127) and `"INPUT"` at y=214 (:128), so the new bands must live between. Proposed: OBJECTIVE label at y=48 with a RAM-derived map line right-aligned on the same row (`LEVEL 6 - ROOM 28    r6_28`); gold head at y=64; WHY wrapped to three 54-char lines at y=90/110/130; rule at y=168; the existing live feed from y=192. Head and why must **not** age-dim — an objective that fades while still current reads as stale. Suppress identical consecutive heads so one authored thought spans a corridor run steadily, and enforce a 90-frame minimum dwell (17 segments are shorter than 2 seconds). Three of the seventeen FRAME STREAM debug lines pay for the space.

`render_overlay.py:154`'s `events[ev_i][0] - 1 <= k` already cancels `note()`'s `+1` (`zelda/emulator.py:283`), so **no change is needed there** under the new keying.

**1f. Prologue.** The first 15,922 frames (4m25s) have no caption of any kind — those 26 segments came from milestone3 and have no checkpoint files. Four hand-written `NARRATION` entries (`start`, `enter_L3`, `cellar`, `manhandla`, `record_run.py:33-36`) are currently unreachable. In the fresh re-run they get their own checkpoints and the timeline picks them up automatically. Add a `"__prologue__"` fallback anyway so a partial run never shows a blank panel.

**Sequencing note:** build the *mechanism* now, author intent strings for segments that survive the route change, and write the new route's strings as Step 11 writes the segments. Do not author copy for `farm*`, `fd*`, `rb_*`, `x9_*`, `r9_*` — they are being deleted.

**Validation:** `python record_run.py fullgame` then `python render_overlay.py fullgame_run` on the *archived* log. Assert: zero `segment <name>` lines outside the authoritative list; an event at frame 1 and at the final frame; the `warp_L3` line at 15,923 not 16,085; and `record_run.py`'s printed fingerprint still `824eab07b73eb9d759d6d9a278c1a2d357e4af3b`. Note the artifacts are `logs/fullgame_run.*` and `video/fullgame_run.mkv`, so the render argument is `fullgame_run`, not `fullgame` as `PLAN.md:42` says.

**What a viewer will notice:** every room now states what the bot is trying to do and why, one segment early instead of one late, with no nonsense captions from routes the bot never took, and the first four and a half minutes stop being a blank panel. This is the change the owner asked for and the one that makes the odd choices legible.

---

### STEP 2 — Run-safety guards — 0 frames, but blocking

Without this the entire re-run can silently not happen, and **replay verification cannot detect it**. `python fullgame.py` with no args calls `run.latest_checkpoint(names)` (`fullgame.py:2807`) and resumes `fullgame_g9_credits` — both the JSON and the `.State` are on disk. Worse: `skip = set(run.done)` holds the **old** segment names, so every renamed or reordered segment is skipped and the old input prefix is kept. The resulting hybrid log is internally consistent, so the power-on replay still reports MATCH. This is the highest-risk item in the whole re-run.

- **Archive first, in this order.** Copy `logs/fullgame.{txt,inputs.txt,events.txt,bk2}`, `logs/fullgame_run.*`, `logs/run_until.log` and `video/fullgame_run*` to `logs/archive/<stamp>/`. There is no git, and `Run.finish()` (`runner.py:139`) overwrites those paths in place. Do **not** archive until the current video is rendered (Step 1's validation needs it).
- **Do not move `states/ckpt_fullgame_*.State`.** ~40 debugging tools hard-code those names (`probe_ganon.py:17`, `probe_patra_fight.py:12`, `probes/gleeok_*.py` × 8 at `ckpt_fullgame_l4_13`, `probe_whirl3.py:14`, …). Gate only on the checkpoint JSONs, or copy rather than move. The directory holds 1,720 states; leave it alone.
- **`fullgame.py:2795 main()`** — add `--fresh`: skip `latest_checkpoint` entirely, leaving `start = None, skip = set()`. No new code is needed to start at power-on: `run.open()` already gives a power-on emulator. Refuse to run if any `fullgame_*.json` checkpoint remains.
- **Mandatory companion fix, `fullgame.py:2800`:** `run.resume(run.latest_checkpoint(names))` does not guard `None`. Today that silently no-ops into `run.finish()` with an empty log and **overwrites `fullgame.inputs.txt`, `.events.txt` and `.bk2` with a zero-frame run**. Make `--verify` abort loudly on `None`.
- **`runner.py:67-74` `save_checkpoint`:** stamp a `list_hash` — sha1 over `[(name, tries, factory.__qualname__) for ...]`, not names alone, so a retuned policy is also caught. `resume()` (:76) and `latest_checkpoint()` (:88) reject on mismatch and **treat a missing hash as a mismatch (fail closed)**; add `--allow-legacy` for `--from` dev resumes against the 618 legacy files.
- **Pre-flight:** refuse to archive while `run_until.sh` holds `/tmp/zelda_run.lock` or an EmuHawk is alive. `PLAN.md:20-27` documents concurrent runs happening twice; a `.State` held open makes the move partially fail and the "refuse if any checkpoint remains" check then wedges the run.

**Validation:** `python fullgame.py --fresh` on a tree with checkpoints present must refuse; after archiving, it must start at frame 0.

---

### STEP 3 — Gleeok's dead-air burn (owner complaint #2, verbatim) — ~3,600 frames, low risk

The owner's Level 4 observation, confirmed exactly. `[gleeok] 6020 frames`, and all four logged attempts were 6019 / 6018 / 6012 / 6020 against `gleeok_policy(nav, budget=6000)` (`fullgame.py:133, 153`) — the signature of a budget cap, not a fight. The input log's last sword swing is at frame 60,986 and the next **3,677 frames contain no input at all**.

**Probe first (10 minutes, decides which fix).** On the pattern of `probe_patra_fight.py`: resume `ckpt_fullgame_l4_13`, replay the 6,020 recorded `gleeok` inputs, and at frames 60,969 / 61,100 / 63,000 dump `emu.ram(0x485,8)`, `emu.ram(0x34F,12)`, `emu.byte(0x34D)` and `gleeok_head_tracker(emu)(emu)`. Everything below is inference until this runs.

**Fix at the root, `zelda/boss.py`.** `gleeok_dead` (:215-224) falls through to `any(hp[i] >> 4 for i in range(1, 8))` while `GLEEOK_SLOTS = range(1, 7)` (:173), and its own docstring (:216-218) says the game leaves stale health values after death. Once `$034D` fails to latch, the predicate is stuck False forever and `plan_fight`'s `finished()` (`lookahead.py:135-138`) defers *wholly* to `done`. The hp bytes are stale precisely because the **type** bytes get cleared on death — so gate the health scan on the type byte: a slot counts as a live head only if `emu.ram(0x34F, 8)[i]` is non-zero. Apply the identical gate in `gleeok_parts` (:176-183) and `gleeok_head_tracker` (:192-204) so the tracker and the death test can never disagree.

Do **not** simply hoist the object-table check above the stale-hp return. Gleeok's neck/head segments are not typed objects (`boss.py:177-179`) and the L4 success test is blind to them too; a premature "no 0x43/0x44 object" would return clear with heads alive, and the run would break far later at `L4_done` when the Triforce never appears.

Also:
- `fullgame.py:2005-2006` — the `gleeok` success test `not read_enemies(emu)` is the weakest in the run. Bring it in line with its sisters: `emu.byte(0x34D) != 0 or not read_enemies(emu)`.
- `fullgame.py:133` — cut `budget=6000` to ~2,500 once the exit works, so a future regression costs 2,500 per attempt instead of 6,000. The same reasoning is already written at `fullgame.py:2494-2496` for `l8_gleeok`.
- `lookahead.py:135-144` — if belt-and-braces is wanted, add an opt-in `done_or_empty=False` parameter used only by `gleeok_policy`. Do **not** let targets-empty override `done` globally: `fullgame.py:1691-1692`'s bomb-drop fight needs its "wait for the kill cycle to tick" semantics.

**Validation:** re-search `gleeok` from `ckpt_fullgame_l4_13` (exists) and require < 2,500 frames. The same policy already exits correctly elsewhere — `l6_mini` 775 frames on a 40,000 budget, `l8_gleeok` 1,443 on 10,000 — so this is a room-specific predicate failure, not a planner problem.

**Caution on re-search:** `gleeok` currently ends at 3.5 hearts and the winner chosen at attempt 29 was **one frame worse** than attempt 1 (6,020 vs 6,019) purely to buy one heart. The `hearts < 4` cliff (`search.py:179-180`) will fight the shortening. Step 9 addresses the pricing.

**What a viewer will notice:** Link kills the two-headed dragon and immediately walks on, instead of standing motionless for 61 seconds. This is the exact thing the owner complained about.

---

### STEP 4 — Truncate attempts at first success — ~4,500 frames, medium risk

19,238 frames of trailing dead air across 87 segments: `random_search` never stops an attempt when the segment's own success test is already satisfied. Implement carefully:

- `zelda/search.py:28-40` — give `Recorder` an optional `probe` callback and a `self.cut` index. **Do not raise from inside `Recorder.step`**: `combat.py:396` and `secrets.py:118` catch bare `Exception` around recorded stepping, so a `SegmentDone` would be swallowed and the attempt would keep recording. Record the cut index, let the policy finish, then truncate `rec.inputs[:cut]` in `random_search` around line 167.
- Probe `success(emu, emu.state())` every 4 recorded frames once `mode in (5, 9)`, and require **K=3 consecutive** hits (~12 frames) to survive death animations and the `not read_enemies` flicker.
- **Opt in per segment, never globally.** Exclude segments whose trailing wait is load-bearing: `clear_push_stairs_policy`'s `sub >= 9` loop (`fullgame.py:1263-1267`, 19 segments), `settle_policy` (`fullgame.py:1526-1537`), `pond_policy`, `take_triforce_policy`, and the heart-container fanfares. Cutting those moves frames into the next segment at best and fails its navigator at worst.
- **Never truncate while `read_room_item(emu)` is not None.** In the `gleeok` segment the winning attempt's extra half heart arrived at frame 61,014 — 28 frames *into* the dead air.
- `runner.py:125-126` re-checks `success(main, s)` after playing the winner into MAIN. Keep it; that is the safety net. But note it *raises* rather than retries and `fullgame.py:2819-2821` has no handler, so consider replaying the untruncated winner on failure instead of aborting a multi-hour run.

**Validation:** re-search `x9_15`-class cheap segments and one expensive one; require identical-or-better rank and no `main diverged from scout`.

---

### STEP 5 — Fights the cartridge never required — ~8,500 frames (~6,000 if scoped to L7/L8/L9)

27 segments clear rooms whose exit door is open or locked and whose floor item is already on the floor. A locked door never requires a clear, and `nav.exit_screen` already consults the door table — the reasoning is written down for one room at `fullgame.py:2414-2417` and simply not applied to the rest.

**5a. Key grabs — `make_clear_grab_policy` → `make_grab_policy`** (`zelda/segments.py:20` → `:108`), all verified `item_after_clear=False` with an open or locked exit. The run already proves the pattern: `l1_33_key` 617, `l5_27_key` 397, versus **1,748** for the equivalent clear at `l4_40_key`.
- `fullgame.py:1979` `l4_40_key` — **but first just re-seed it.** `logs/fullgame.txt:119` shows **580 frames** with identical code; line 570 shows 1,748. That is ~1,100 frames for a single-segment re-search and zero code risk. Do this one first.
- `:2409 l8_5d_key` (1,314), `:2404 l8_7f_key` (1,193), `:1977 l4_51_key` (840), `:1930 l1_74_key` (682).
- **Leave `:1952 l1_45_key` alone** — it takes hearts 2.0 → 4.0 before Aquamentus and `search.py:179-181` would reject the shorter attempt anyway.
- Required fix before any swap: `zelda/segments.py:108 make_grab_policy` is missing the `nudge_into_room(emu, rec.step)` call that `make_clear_grab_policy` has at `:33-34`. Without it, doorway-start cases fail to plan.

**5b. Fight → cross.** `:2571 m9_15`, `:2624 r9_15`, `:2687 rb_15b` are all Level 9 room 0x14 — five Like Likes, fought three separate times for 3,755 frames, always leaving through a **locked** door. Use `make_lareach_policy(nav, Goal(...), then_exit="Right")` so `nav.exit_screen` handles the locked-door hold loop (`overworld.py:752-762`). Do **not** use `exit_ok`, whose 8-frame holds (`lookahead.py:299`) will not reliably drive a locked door. Copy the working pattern at `fullgame.py:2002 l4_12`. Same treatment for `:2333 l7_19`, `:2491 l8_3b`, `:2239 l6_1d`, `:2322 l7_49`, `:2229 l6_39`, `:2217 l6_1b`, `:2226 l6_b1a`, `:2227 l6_b19`. Skip `r8_6e2`, `l7_69`, `r6_38`, `l8_6e`, `l8_4d`, `r6_68` — already at or under the 339-frame crossing median, so the swap loses frames.

Two of these (`r9_15`, `rb_15b`) disappear entirely under Step 11 anyway.

**Risk:** room 0x14's Like Likes eat Link's shield and can trap him. `plan_reach` is damage-aware and was written for exactly this case, but each swap must be confirmed by the search succeeding, not by the ROM door table alone — a few rooms are entered from an unusual side.

**What a viewer will notice:** Link walks through open and locked doors instead of methodically killing rooms full of enemies that were never in his way. This is the second half of "choices a human never would make" — except here the human is right and the bot was wrong.

---

### STEP 6 — Whirlwind ride padding — ~1,500-2,500 frames, low risk

Poll granularity only; no rule or route implications.
- `fullgame.py:624-625` — replace `for _ in range(30 if n == len(faces)-1 else 7): s = rec.step((), 20)` with a 2-4 frame poll. The measured stationary tail is 166 frames. Keep `emu.wait_until(lambda q: q.mode == 5, 600)` at :632 as-is — already 1-frame granular.
- `fullgame.py:514` — `rec.step((), 150)` in `whirlwind_policy` becomes a landing wait (room changed AND `mode == 5` AND position stable). Only one caller remains (`whirl_east`, :2171). The recorded pad ends while Link is still drifting, so do not assume the full 150 is free.

**Do NOT touch `fullgame.py:575`** (`rec.step((), 30 + rng.randint(0, 20))`) or the stillness loop at :577-581. The docstring at :539-540 and `journal/26-which-way-link-faces.md` record that a note played during the post-ride glide is **lost**, and each lost note costs a full poll ceiling. Trimming 30 frames to risk 600 is the wrong trade. If anything, add a dud *detector* (no whirlwind object / Link not being carried after ~250 frames → replay the note).

Note the whirlwind family totals 19,710 frames across 16 segments, but `whirl_l6` (5,003) and `whirl_l3` (1,198) live inside blocks Step 11 deletes. Do not double-count them.

---

### STEP 7 — First-farm drop suppression — moot if Step 11 lands

`fd40` alone is 10,043 frames, the worst segment in the run, and it is the **first** farm attempt after re-entering at full health with full bombs — precisely the case `farm_dungeon_policy`'s docstring calls out at `fullgame.py:426`: *"Drops are also mostly invisible when Link is at full health and full bombs."* If any farm survives as a backstop, spend a heart or a bomb deliberately before farming, or lower the first target below 40. Several thousand frames for a one-line change. Skip entirely if Step 11's caves land.

---

### STEP 8 — Per-attempt lead-in jitter — ~3,600 frames, low risk

Nearly every policy opens with `rec.step((), rng.randint(0, 20))` (`fullgame.py:106, 143, 168, 438, 504, 550, 929, 1111, 1379, 1462`; `segments.py:32, 70, 92, 115`) — ~10 wasted frames × ~600 segments. The seed already decorrelates attempts; the jitter is belt-and-braces. Narrow to `randint(0, 8)` uniformly. Do not remove it: `journal` records attempts converging without it.

---

### STEP 9 — Heart pricing — ~1,100 frames, **highest risk in the plan**

`search.py:178` `r = x.hearts * 600 - x.frames` bought 6,964 extra frames of health across 60 segments. Do **not** simply lower 600 to 250-300 — that pulls in the `s9_43`-style survival buys that are doing real work. Make it deficit-aware:
- `containers` is available as `s.containers` on the state already read at `search.py:162`. Capture it once per search and weight the heart bonus by `(containers - hearts) / containers`, or zero the bonus above ~90% of containers. That kills the whole 15-segment, 1,071-frame top-up cluster (`r8_in`, `w8_69`, `l8_7f_key`, `m8_7c`) and leaves `s9_43`, `enter_L9` and the Level 9 approach untouched.
- **Keep the cliff at `:179-180` exactly as is.** It is load-bearing — `enter_L9`'s shortest success was 0.5 hearts of 11.
- Consider making the cliff relative (`hearts < 0.4 * containers`): with a 4-heart max in Level 1 the absolute `< 4` test fires on anything but full health, which is what selected `l1_33_key` at 4.0/4 over 3.5/4.

**Also (free, do it regardless):** the policy outcome string is carried on `Attempt` (`search.py:167`) and never shown. Add it to the success log line at `:186` and add a `rank()` penalty for `note == "timeout"`. Do **not** hard-reject timeouts at `:163` — `runner.py:118-120` raises `RuntimeError` and kills the run when a segment finds no success, and nobody currently knows how many segments win on timeout. Ship the logging first and count.

**Validation:** this cannot be applied selectively to an existing log; it only affects future searches. Before committing, re-measure the death rate. `logs/fullgame.txt` already shows 5 segments that failed all tries outright (lines 3408, 3454, 3460, 3613, 3681), so a worse start state failing a downstream search is an observed failure mode, not a theoretical one. The comment at `search.py:174-177` records that this exact tuning already went wrong once in the other direction.

**What a viewer will notice:** Link stops detouring for half-heart drops when he is nearly full, and finishes more rooms at 4-5 hearts instead of 6. Slightly more tension on screen; slightly more chance of a death costing a re-search.

---

### STEP 10 — Parallel scouts — 0 frames, ~2.5× wall clock

Not a frame saving, but the re-run is 19-30 hours of search and this halves it. `runner.py:42-46` builds one scout; run K=3 in a `ThreadPoolExecutor` (every step is a blocking TCP round-trip, so the GIL is released), each with its own `BizHawk(clean_sram=False)` and `Navigator`, constructed **serially** (the `.bridge_port` write at `emulator.py:126` and the 60s accept at `:143` are not safe to overlap). Thread a seed slice through `random_search` (`search.py:148`) and a shared stop signal through the early-stop block at `:198-203`. Apply `rank()` once over the merged Attempt list so the winner is unchanged in kind.

**One genuine correctness blocker:** `overworld.py:97-101` `TileKB.learn` calls `self.save()` unconditionally, whole-file. Guard with a module-level lock plus atomic write (tmp + `os.replace`).

**Risk:** `PLAN.md:31-35` records the scout losing its bridge five times in nine minutes with three EmuHawk instances alive. That case involved ffmpeg A/V dumping, far heavier than a headless scout, but pilot it for 30 minutes on one known segment and compare drop rate before committing. Stop at K=3 (4 instances on 8 cores), never K=8. Do not raise `tries` in the same commit.

Cheap serial win alongside: `runner.py:67-74` rewrites a ~2 MB JSON of the entire input log every single segment. Checkpoint every N segments.

---

## PHASE B — PROBES (no game time; these gate the route)

Run before writing Step 11. Each costs zero frames because `zelda/secrets.py` works off in-memory snapshots (`secrets.py:8-11`).

**B1. The 100-rupee cave at `0x0F` — the single highest-value unknown in the plan.** This is what deletes 59,126 frames of farming. The ROM's overworld secret table at file offset `0x18690` marks `0x0F` as `0x03`, the same value as the six walk-in dungeon doors (`0x0B, 0x22, 0x37, 0x3C, 0x45, 0x74`) and the verified open cave `0x2F` — i.e. an open mouth needing no tool at all. `knowledge/rupee_caves.md` lists it at 100 rupees.

**Unverified and it must be verified before the route is built on it:** `knowledge/rooms.json` holds 133 screens and **`0x0f` is not among them** — that corner of the map has never been walked. Confirm `0x0D → 0x0E → 0x0F` connects, using `find_secret.py <checkpoint> [methods] [dirs...]` from a checkpoint at `0x1C`.

**B2. Fallbacks, in order:** `0x67` (30 rupees; secret byte `0x40`, bit 6 set — the marker every verified secret shares, which `0x28` and `0x48` both lack; 236 tree + 50 pushable tiles; already on the route at `w8_67`, never swept). Then `0x1A` — also `0x03` in the table, and the run already walks straight across it (`[shop00_1a] 259 frames`), so an open entrance there costs a detour of **zero**. Then `0x3D`, where `knowledge/speed_faq_mariner.md` documents a 30-rupee Armos touch and the run crosses at `l5w02_3d` **before both farms**.

**B3. Re-sweep `0x28`, `0x48`, `0x62` with the candle and the fixed detector.** Their "not found" rows in `knowledge/rupee_caves.md` are stale twice over: push was never really tried, and the bomb sweeps predate the `opening()` baseline fix documented at `secrets.py:32-40` (*"reported 'nothing opened' after 220 bombs at Spectacle Rock, a rock this run had already blown open. Every bomb secret on the map was invisible until this check."*). Note `0x62` is a canyon whose halves do not connect — sweep from both sides.

**B4. Gleeok RAM probe** (Step 3).

**B5. Whirlwind counter probe** — `probe_whirl3.py` already traces one seed of `whirl_to_policy` frame by frame; change its `emu.load()` target and counter arguments. `tries=20` at both whirl sites may want raising, since `counter=None` spends the first note learning the counter.

**Knowledge hygiene:** `knowledge/rupee_caves.md` still presents the community map as fact after it has been wrong four times. Add the ROM table at `0x18690` as the authority, with the decoded rule (`0x03` = entrance already drawn; bit 6 set = hidden secret; bit 6 clear = nothing there) and the twelve `0x03` screens: `03, 07, 0B, 0F, 1A, 1F, 22, 2F, 37, 3C, 45, 74`.

---

## PHASE C — THE ROUTE

### STEP 11 — Delete both farms, fund from caves, one shopping leg — **~85,600 frames**

The whole ballgame. Farming ran at ~620 frames per rupee; the one cave the run opened paid 100 rupees in 1,127 frames — 55× cheaper. Both purchases are genuinely required (a ROM scan of every room-item byte in both dungeon tables confirms Monster Bait exists nowhere as a floor item, and arrows are sold only in shops). Only the **source** is wrong.

Edits, all in `harness/fullgame.py`:
- `:2162-2164` — delete the `farm{target}` loop (37,421 frames).
- `:2279-2281` — delete the `fd{t}` loop (21,705 frames).
- `:2154-2161` — `l6_out` / `l6_back` become redundant with `shop_out` at `:2169`; collapse to one dungeon exit. Level 6 is climbed **once**.
- `:2272-2283` — drop `l7_out`, `w7_52`, `whirl_l6`, `l6_farm_in`, `l6_farm_out`. Level 7 is entered **once** (the current `enter_L7` 177 → `l7_out` 128 → … → `l7_drain2` 269 → `enter_L7b` 183 double entry plus a second pond drain is ~750 frames of pure waste, and is exactly the "in and out of level 6 a lot" pattern the owner named).
- `:2288-2300` — replace the ten-screen `m7_` chain (which existed only because Link was standing at Level 6's door) with the direct `0x42 → 0x52 → 0x53 → 0x54 → 0x44 → 0x34`.
- `:2295-2298` — the fairy heal detour was added to repair farming damage (`:2291-2294`); re-measure and likely drop.
- **NEW cave segment**, after the `L2_TO_HILLS` chain at `:2043` (which lands Link on `0x1C`): `cross("Up", 0x0C)`, `cross("Right", 0x0D)`, `0x0E`, `0x0F`, then the cave.

**No new policy is needed.** `burn_cave_policy` (`fullgame.py:917`) reads `spot = secrets.opening(emu)` at `:931` and only runs the candle block `if spot is None:` — so on a screen whose staircase is already drawn it skips straight to walk-in / take / exit. Call it as `burn_cave_policy(nav, stand, face)`; the candle arguments are never used. Success test: `lambda emu, s: s.hearts > 0 and s.level == 0 and emu.byte(0x66D) >= 120`.

**One shopping leg** at `0x44` (arrows 80, bombs 20/4, **capacity upgrade 100**) and `0x34` (bait 60, under the gravestone — `grave_shop_policy`, `fullgame.py:808`, push east from `(48,125)`), which are two screens apart and which the run already walks between. Keep `shop_policy(nav, 0x658, xs=(120,))` for bombs — the `xs` restriction exists so walking into the arrows at x=152 does not spend 80 by accident.

**Risk:** `0x0F` is unwalked (B1). If it is a dud, fall back to `0x67` + `0x1A` + floor rupees and keep one trimmed farm — that yields less and saves nearer 25,000, and the hour is missed. `journal/23` warns the community cave list is wrong at least three times over.

**What a viewer will notice:** the bot stops grinding the same two Level 6 entrance rooms thirteen separate times for ten and a half minutes, and stops walking in and out of Level 6 and Level 7. It walks into a cave, an old man gives it a hundred rupees, and it goes shopping once. Ten and a half minutes of the most tedious footage in the run disappears.

---

### STEP 12 — Enter Level 9 once — **~32,000-34,000 frames**

Today Level 9 is entered three times: once, out again for the Magical Sword and two heart containers (19,813), back in (5,021 including a re-walk of the entrance wing it already cleared and the walled-off `s9_25` dead end), out again to **buy bombs** (17,498), back in. That is 42,332 frames.

The Magical Sword cannot simply be taken earlier. Two hard gates, both verified:
- `grave_sword_policy` requires **12 heart containers** (`fullgame.py:1450`, `:1463`). At Level 6's Triforce Link has **nine** (`[l6_heart] … hp=9.0/9`).
- Heart container `0x47` is a **burn** secret (`knowledge/overworld_secrets.md`) and `hc_cave_policy` selects the candle for it (`fullgame.py:1395`). The run's first candle is Level 7's Red Candle at frame 241,214. Every crossing of `0x47` in the route is before that.

So the earliest workable point is **after Level 8's Triforce**, where Link stands at `0x6D` with 11 containers. Restructure the L8→L9 leg (currently 12,745 frames including `whirl_l5` 661 and a fairy-heal detour) to carry the whole errand:

1. Warp out of L8, bomb `0x2C` for container #12 (`hc_cave_policy(nav, (176,157), "Left", "bomb")`).
2. Warp `0x22`, walk `22 → 32 → 31 → 21`, take the Magical Sword.
3. Bombs and the capacity upgrade come from Step 11's shopping leg, topped up in-dungeon.
4. Warp `0x0B`, the Death Mountain road already walked, single entry.
5. **Drop the `0x47` leg entirely** — `hc_w37` 2,523 + `hc_38` + `hc_48` + `hc_47` + `hc_47_heart` ≈ 4,388 frames for container #13, which nothing requires.

Deletions: `fullgame.py:2579-2585` (`x9_*`), `:2608-2625` (`r9_*`), `:2629-2630` (`s9_26`/`s9_25`), `:2631-2688` (the whole `rb_*` block).

**Three things that will bite:**
- **The whirlwind counter chain.** `hc_w37(counter=0x0B) → hc_w3c(counter=0x37) → ms_w22(counter=0x3C) → r9_w0b(counter=0x22) → rb_w45(counter=0x0B) → rb_w0b(counter=0x45)`. Deleting `rb_*` and `r9_*` breaks it. Whichever warp follows `ms_sword` must have its `counter=` re-pointed to where the counter actually sits, or `cost()` (`fullgame.py:610-617`) plans the wrong way round and every ride costs extra notes.
- **Bomb budget.** The one-pass route needs walls at `0x56→0x55`, `0x06→0x05`, `0x20→0x10`, `0x31→0x30`, `0x04→0x03`, plus lookahead spends. `knowledge/level9_route.md` itemises roughly 8-10, reachable only with the capacity upgrade (base cap is 8). Add an in-dungeon top-up on the `r8_3f_bombs` pattern (`fullgame.py:2484-2485`, `make_clear_grab_policy(nav, None)` with `s.bombs >= 8`) — **not** another shop trip. `m9_16_bombs` (`:2573`) already harvests room `0x16`'s pile. `g9_04_bomb` (`:2761`) earns one from a Red Wizzrobe drop and stays as insurance.
- **Keys.** The new route frees the key `s9_25` spent; the current route reaches `s9_62` with 0 keys, so verify against `l9_56_key` (`:2558-2559`, `keys >= 5`).

**Also delete the `0x43` dead end** (Step 21 of the budget): `s9_43`, `s9_43_text`, `s9_b53`, `s9_b63` ≈ 4,773 frames and one wasted bomb, for an old man saying "PATRA HAS THE MAP". `logs/fullgame.txt:3613` records 40 attempts spent on it (`no success; most common: 40x no stairs appeared @ room 43 L9`). The journal already admits the door-graph deduction that put it there was wrong.

**What a viewer will notice:** Level 9 is entered once and played through, instead of the bot walking out twice, sailing a raft across a lake to buy bombs, and re-fighting the same entrance rooms three times. It also stops buying bombs entirely — the owner's exact objection — because it now carries a capacity upgrade and picks piles up on the way.

---

## PHASE D — EXECUTE

1. All Phase A code changes landed and unit-sane.
2. All Phase B probes green (or the fallback route chosen and the budget re-derived).
3. Phase C route rewritten in `segments()`.
4. Step 1's intent strings authored for the **new** segment names.
5. `python fullgame.py --fresh` under `run_until.sh`. Estimate 6-9 h unattended with Step 10, 24-30 h without.
6. `run.finish()` must print **MATCH**. This is non-negotiable.
7. `python record_run.py fullgame` **alone** — never while a run holds `/tmp/zelda_run.lock` (`PLAN.md:29-35`). Then `python render_overlay.py fullgame_run` (~95 min at ~3,900 frames/min).

---

## MUST NOT CHANGE

- **Replay-MATCH verification from power-on.** `runner.py:135-158` → `replay.verify`, SHA1 of RAM `0..0x800`. This is the claim. Never weaken it, never skip it, never `--force` past it.
- **No memory writes.** `msave`/`mload` in `lookahead.py`, `boss.py`, `overworld.py` and `secrets.py` are scout-side branch exploration on in-memory snapshots, discarded; they are established practice and stay. Nothing in this plan writes game RAM.
- **No savestates in the played trajectory.** Checkpoints are search bookmarks only. `runner.py:3-6` is the contract.
- **No glitches, no warps Link has not earned.** Every whirlwind stop is a dungeon Link has finished.
- **The Magical Sword stays.** It is taken later, not skipped. Ganon's kill depends on it (four Magical Sword hits, then one Silver Arrow).
- **The heart floor in `rank()`** (`search.py:179-180`). Step 9 re-prices the bonus above the floor; the floor itself is load-bearing.
- **The 30-frame settle before a whirlwind note** (`fullgame.py:575`). Measured; a lost note costs a whole ride.
- **`states/ckpt_fullgame_*.State`** — ~40 probe tools hard-code those paths.
- **Boss tunings.** Gohma 4 s, Aquamentus 3.5 s, Ganon 15.6 s. Measured, not guessed, and fragile. Leave them alone.

---

## FILES TOUCHED, BY STEP

| Step | Files |
|---|---|
| 1 | `record_run.py` (`boundaries`, `main`, `NARRATION`), `render_overlay.py` (layout only), **new** `zelda/intent.py` |
| 2 | `fullgame.py` (`main`), `zelda/runner.py` (`save_checkpoint`, `resume`, `latest_checkpoint`) |
| 3 | `zelda/boss.py` (`gleeok_dead`, `gleeok_parts`, `gleeok_head_tracker`), `zelda/lookahead.py` (`plan_fight.finished`), `fullgame.py:133`, `:2005-2006` |
| 4 | `zelda/search.py` (`Recorder`, `random_search`) |
| 5 | `zelda/segments.py:108`, `fullgame.py` × ~14 segment lines |
| 6 | `fullgame.py:514`, `:624-625` |
| 8 | `fullgame.py` × 10 policies, `zelda/segments.py` × 4 |
| 9 | `zelda/search.py` (`rank`, logging) |
| 10 | `zelda/runner.py` (`open`, `close`, `segment`), `zelda/search.py`, `zelda/overworld.py:97-101` |
| 11-12 | `fullgame.py` `segments()`, `knowledge/rupee_caves.md`, `knowledge/overworld_secrets.md` |

Scratch analysis scripts (disposable): `C:\Users\scots\AppData\Local\Temp\claude\G--AI-World-Record\d5fcfe9d-4ac8-40d5-8a32-00e8e94fae89\scratchpad\{chain.py,chain2.py,phases.py,chain2.json}` — the chain reconstruction and phase arithmetic behind the budget table.

**One correction to the brief:** its MOST EXPENSIVE SEGMENTS table lists `1494 l4_stairs`, which is an abandoned-branch entry (`logs/fullgame.txt:133`), not a segment of the real run. Any routing decision derived from that table should be re-checked against the 596-segment surviving chain.