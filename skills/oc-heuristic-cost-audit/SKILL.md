---
name: oc-heuristic-cost-audit
description: Audit a heuristic search or planner for scoring blind spots - the bugs that make a system look like it is making a bad decision when it is not modelling the right thing. Covers future-state blindness (a reward that only exists after the action that earns it), formulas applied by omission to a class they were never written for, two modules deciding the same predicate and disagreeing, and the tell-tale sign that a cost model is a "nice number" rather than a measured one. Use when a bot or agent takes an obviously wasteful path, when a scoring function has one special case and a silent default, when tuning constants has plateaued, or when a planner's behaviour contradicts an obvious improvement.
license: MIT
metadata:
  tags: ai, planning, heuristics, scoring, cost-function, shaping, search, tas, pathfinding, lookahead, reward, bug, audit, tuning
  category: ai-planning
  requires_toolsets: terminal
---

# Heuristic Cost Audit

Most "the bot did something dumb" reports are not tuning problems. They are cases
where the cost model cannot represent the thing that mattered, and tuning makes
the symptom move without ever fixing it.

**The tell:** a proposed improvement that is obviously correct, and which you can
describe precisely, has no effect. Before reaching for a weight, ask whether the
term that *would* express it exists at all.

## Symptom 1 - future-state blindness

> A reward is collected from objects that already exist, so a move whose payoff
> only materialises *later* is invisible to the cost model.

The report: *"if it knows a key is coming in a room, it doesn't try to kill the
last enemy in the centre, wasting travel."*

The obvious fix is a weight. The real problem is one line:

```python
drops = []
item = read_room_item(emu)                    # the room item
if item is not None: drops.append(item)
for i in range(1, 12):
    if blk[0x34F - 0x70 + i] == 0x60:         # a DEAD monster's drop on the floor
        drops.append(...)
...
cost = want * (abs(s2.x - ix) + abs(s2.y - iy))
if best is not None: shaping -= best
```

`0x60` is the object type a monster's slot becomes **after it dies**. A living
enemy has no such slot. So `drops` holds only what is *already* on the floor, and
the shaping term rewards ending the fight near an existing drop while being
completely blind to "end near where the next kill will put something". The enemy
in the middle of the room attracts no travel cost, because at scoring time it has
no drop and never will in that branch.

Audit questions:

- Which entities does the shaping term enumerate, and **at what point in their
  lifecycle**? Anything enumerated only in a terminal state is invisible while the
  decision is being made.
- Does the model know the *consequence* of each candidate action, or only the
  state that exists before it? A cost model over states cannot price transitions.
- Is there a cheap predictor for the future entity? Often yes - the same
  lookup that decides *whether* a kill is valuable also predicts *what* it yields.
  Then the fix is a few lines against an already-fetched RAM block.

The general shape: **if the reward is produced by the action, the cost model must
model the action's output, not the world's inventory.**

## Symptom 2 - a formula applied by omission

> One value function was written for one class of thing and silently applied to
> all the others, because they were not enumerated.

Same block, ten lines up:

```python
want = 1.2 + 1.6 * max(0.0, (s0.containers - s0.hearts)) / max(1.0, s0.containers)
if kind == 0x00:                       # bombs get a real premium
    want += 1.5 + (2.5 if s0.bombs < 4 else 0.0)
```

`want` is derived from **how hurt the player is**, and it is applied to every drop
that is not explicitly special-cased. Special cases: bombs, the clock (skipped),
heart and fairy (skipped at full health). Keys and rupees are not special-cased,
so at full health:

| drop | `want` per pixel of travel |
|---|---|
| bomb, `bombs < 4` | 5.2 |
| bomb | 2.7 |
| **key** | **1.2** |
| **rupee** | **1.2** |

Meanwhile the same file carries the evidence that keys are critical:

```python
if s2.keys < s0.keys: sc -= 6000
# "three rooms on the run stopped dead at the door the key was for"
```

A key is worth **6000** if you spend the wrong one and **1.2 per pixel** to pick
one up. That asymmetry is not a judgement call; it is a healing formula leaking
into a domain it was not written for.

Audit questions:

- For every value/weight, name the class it was derived from. Then list the classes
  that fall through to the default. **An unlisted default is a bug with a delay.**
- Is the formula's *unit* meaningful for the default class? `hearts missing /
  containers` is a fraction; multiplying it by a pixel distance to decide whether
  to fetch a key is a category error wearing a float.
- Does the module know the value better than the caller? `farm_dungeon_policy`
  knows it wants 20 rupees; that number never reaches the scorer. Look for
  information that stops at a layer boundary.

The general shape: **special cases are a taxonomy you have not written down yet.
The default branch is where the unwritten classes go.**

## Symptom 3 - two modules, one predicate, different answers

> The same decision is made in two places, and only one of them is right.

```python
# planner
want = 1.2 + 1.6 * (...);  cost = want * distance      # a key is worth 1.2/px
# collector
if t in (0x22, 0x23): return s.hearts < s.containers
if t == 0x00:         return s.bombs < max(8, self.emu.byte(0x67C))
return True                                             # rupees, five rupees, keys
```

The collector will cross a room for a key the planner barely wanted. The fight was
therefore planned for the wrong reason, and the collection is a late correction
that costs more than the plan assumed.

Audit questions:

- Grep for every place a predicate is evaluated. `grep -n "keys <" ` and friends.
  Duplicated policy is duplicated *inconsistency*.
- Which of the two is authoritative? Make it a function and have both call it.
- Does the disagreement show up as a *late* behaviour that undoes an early
  decision? That is the signature.

## Symptom 4 - the cost model is a nice number

Sort of an audit question, but worth asking directly: **where did this constant
come from?**

A weight that is a round number with no measured basis is a guess wearing a
decimal point. It will feel tunable and it will not be, because there is no
gradient to follow - you are just sampling noise. The constants worth trusting
tend to look like `150` (a kill, measured), `6000` (a wasted key, from three rooms
that stopped dead) or `0.5 * urgency * TIME_SCALE` (explicitly scaled). The ones
to distrust are the ones introduced as "probably about".

Good provenance for a constant is a citation to the experiment that produced it -
a script, a checkpoint, a frame. Bad provenance is a plausible sentence.

## Symptom 5 - the table is two-dimensional

> The lookup you think is keyed on one thing is keyed on two.

This one changes what is *possible*, not just what is weighted:

```python
ROW2 = {0x09,0x0A,0x03,0x01,0x12,0x06,0x0B,0x24,0x30}   # monsters with bombs in their drop row
row2_next = want_bombs and emu.byte(0x52A) in (0, 5, 7) and any(t[1] in ROW2 for t_ in tlist)
```

A drop is a function of **enemy type x kill-cycle column** (`$52A`), not enemy
type. The bomb row is mapped; nothing else is. So the planner can arrange for a
bomb drop by *waiting for a column* - legitimate play, no state writes, because
it refuses to act unless the next kill lands on a bomb column:

```python
if (cyc0 + 1) % 10 not in (1, 6, 8): return f"kill cycle {cyc0}: not a bomb column"
```

The same lever, unmapped, is the whole answer to "can we get a fairy?" - and
nobody could ask the question while the table was assumed to be one-dimensional.

Audit questions:

- For each lookup keyed on a type/enum, ask what *else* selects the row. Cycle
  counters, RNG state, room, difficulty, position.
- If two call sites of the same table agree on a transformation (`(c+1) % 10 in
  (1,6,8)` vs `c in (0,5,7)` are the same predicate), that is a sign the indexing
  is understood by two people independently - and also a sign it is fragile
  enough to deserve one named helper.
- Unmapped rows are not neutral. They are the reason a capability is believed
  impossible.

## Method

1. **Reproduce the specific waste**, with a frame number and a screenshot. Not the
   aggregate metric - the moment.
2. **Write the term that would express the improvement, in one line of maths.** If
   you cannot, you do not yet understand the case, and tuning will not help.
3. **Find where that term would have to be computed.** Usually it already exists
   for a sibling case; look for the block that special-cases a neighbour.
4. **Check whether the required data is already in hand.** A RAM block read for
   one purpose often contains what the new term needs, so the cost is one lookup.
5. **If the data does not exist, that is the real work** - and it is usually a
   *mapping* task, not an optimisation. Say so, and estimate the mapping.
6. **Measure before and after on the same segment.** One number, from a fixed
   checkpoint, with the input log kept.

## Anti-patterns

- Tuning weights when the term does not exist. Symptom moves, understanding does
  not.
- Adding a special case that increases the special-case count. If you are on the
  fourth `if`, the model is wrong; write the table.
- Fixing the collector to compensate for the planner. Now both are wrong in
  different directions and the bug is unobservable.
- Declaring a capability impossible while the underlying table is unmapped. That
  is a statement about your knowledge, not about the game.
- Trusting a doc for what a run did. Encoding and behaviour are different claims -
  see `oc-emulator-run-fidelity` and `oc-nes-rom-map-decode`.

## Related

- `oc-bizhawk-nes-harness` - the search loop, checkpoints, and RAM reads a cost
  audit needs
- `oc-nes-rom-map-decode` - where the tables and addresses come from, and the
  encoding traps that make a lookup silently wrong
- `oc-emulator-run-fidelity` - per-frame measurement, and retracting a shipped
  claim when an audit contradicts it
- `oc-run-journal` - recording which strategies were tried and failed, so an
  audit is not re-run from scratch
