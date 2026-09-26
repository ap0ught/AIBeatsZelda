---
name: oc-run-journal
description: Keep a working journal while building something hard - an agent harness, a long optimisation run, a multi-day reverse-engineering effort. Covers the entry shape that stays useful (Goal, symptom, diagnosis, fix, and the rule left behind), writing down failed strategies instead of quietly rewriting them, recording gains and losses separately, and stopping when variance rather than effort is the binding constraint. Use when starting or extending a project log, writing up a debugging session, reporting a benchmark result honestly, or deciding whether to keep optimising.
license: MIT
metadata:
  tags: journaling, writing, documentation, debugging, benchmark, honesty, reproducibility, process, engineering-log, git
  category: process
  requires_toolsets: none
---

# A working journal for long builds

Distilled from `journal/` in `~/code/games/aibeatszelda` — 46 entries, ~26,000
words, written over seven days while an agent harness was taught to play
*The Legend of Zelda* (NES) from power-on. It is one of the better engineering
logs I have read, and these are the parts that make it one.

## Why a journal and not a changelog

A changelog records what changed. A journal records **what was believed, what
disproved it, and what was concluded** — which is the part you cannot reconstruct
later. Six months on, the diff tells you the bridge now blocks on a read; only
the journal tells you it used to yield, that yielding made replays lie, and that
this was the single rule the whole project's credibility rests on.

Write it as you go. The worked example's entries are dated to the day
(2026-09-15 → 09-22) and written in past tense about work finished hours or
minutes earlier. A journal reconstructed at the end is a press release.

## Two phases, and the shift between them

**Early entries are `Phase N:` and lead with a Goal.** They are about building
capability, in dependency order, and the goal statement is what keeps them
honest:

> **Goal.** Before an AI can speedrun anything it needs hands and eyes. Hands: a
> way to press controller buttons one frame at a time. Eyes: a way to know what is
> happening in the game.

> **Goal.** Milestone 1 walked to the cave using coordinates I typed in by hand.
> That does not scale to 128 overworld screens and 9 dungeons. The bot has to read
> the map itself and find its own way.

The second one is the model: it names the limitation of the thing just achieved,
and that becomes the next entry's goal. If a phase entry cannot say what is now
insufficient, the work was not a phase.

**Later entries are dated and read like a diary**, because by then the question
has shifted from "can it do this at all" to "is this number real, and where is
the next second coming from".

## The entry shape that earns its length

Symptom → chasing → cause → fix → the rule left behind. The worked example's
"the emulator was running without me" is the archetype:

- **Symptom**, stated so it is genuinely puzzling: the scout finds a clean
  crossing, main plays exactly those inputs from exactly that state, and comes out
  with damage and mid-scroll. *"Same state, same inputs, different result. That
  should be impossible in a deterministic emulator, and the deterministic emulator
  was the one thing I had been trusting completely."*
- **Chasing**, with the reasoning order recorded, including the wrong turns
  eliminated: replay tested directly, every hash matched, **so the emulator was
  innocent**. Then it counted frames: stepped 1690 times, game at 1987.
- **Cause**, in the harness's own code, with the mechanism: the bridge yielded
  every 50 ms waiting for commands, so whenever the controller was busy the game
  ran on with nobody holding buttons.
- **Fix** — one line — and then the durable part:

> The rule this leaves behind is written into the harness: every frame of the run
> must be one the script explicitly asked for.

That last clause is the whole value. A journal entry that stops at "fixed the
bug" has expired the day it is written. One that ends in a rule is still true when
someone else reads it a year later.

## Name the failures. Do not quietly rewrite them

The single most useful habit in the example is recording strategies that did not
work, by name, in the entry where they failed:

> Gleeok beat me five different ways in Level 4. Every time, the arithmetic was
> the same: two heads…

and

> Gleeok is the first thing this bot cannot beat. Its body and neck cannot be hurt
> at the wooden sword.

Five attempts, five named approaches, one stated reason they all failed. That
entry is why a later reader knows the White Sword is load-bearing rather than
optional, and it is unobtainable from the final code — the losing strategies are
not in the diff.

Corollary: **when a number goes backwards, say so in the same entry as the number
that went forwards.** The 37:02 entry is a draw and it presents both faces:

> Gains where the search dug deeper: Level 8's key room 1,162 → 850. Losses that
> nobody chose: Level 6's Vire room 514 → 874. Twenty more seconds could come from
> another draw, or go the other way.

"Nobody chose" is doing real work. It separates a decision from an accident, which
is exactly the distinction a reader needs and which a summary metric destroys.

## Know when the variance, not the effort, is the limit

The same entry ends:

> this is where the engine's variance lives and I will not keep rolling.

That is a stopping rule written by the person doing the work, and it is worth more
than another hour of measurement. Concretely: if a wider search produced both the
best and the worst result seen at that setting, more of the same search buys a
coin flip, not an improvement. Write that down as a decision, with the number that
justifies it, and stop.

Contrast this with a project that kept going. The cost of not stopping is not just
hours; it is that every later entry inherits a number nobody trusts.

## Corroborate your own claims, and mark the ones you cannot

The journal's numbers are checkable, and checking them is what makes the rest
credible. The 37:02 entry claims "10,257 rehearsals"; the search log in the
repository contains exactly 10,257. The entry's 37:02-vs-37:52 distinction matches
what the frame count implies. The Gleeok/White-Sword dependency matches what the
route module encodes.

So: **after writing a number, go find the artefact that contains it.** Then, in
the entry or a README, say plainly which claims are corroborated by artefacts and
which are testimony. In this project the honest split was:

- *Proved:* the input log alone drives the emulator from power-on to the ending,
  with no memory editing and no savestates — byte-exact RAM fingerprint, replayed
  in a fresh emulator.
- *Not proved:* that an AI authored those inputs rather than a person with a tool.
  That rested on the search log's internal consistency, which is strong and is
  still the repo's own account of itself.

Writing the second sentence is what stops the first from being read as covering
it. A journal that overclaims is worse than none, because it lends credibility to
the parts it got wrong.

Look for the machine tell, and report it as a tell rather than a proof. Here: the
136,526-frame input log never holds two buttons on the same frame, in 105,781
button frames. Not once, no diagonals. That is a generation signature — and it is
evidence about *mechanism*, not about authorship, and should be labelled that way.

## Length is not the target

Entries in the example run from 238 to 2,027 words, and the short ones are short
because the work was short. Do not pad a routine fix to 2,000 words, and do not
truncate a nasty bug to keep an entry tidy. The discipline is that every entry
answers: what was the symptom, what did I rule out, what is the cause, what
changes because of it. If an entry has nothing to say on the last one, it was
probably a changelog line, not a journal entry.

## Mechanics that made it work

- **One file per entry, numbered, kebab-case, dated in the filename or the body.**
  `08-the-emulator-was-running-without-me.md` is findable by index, by date, and —
  this is the real payoff — by *searching for the symptom* months later. Name
  files after the problem, not the fix.
- **Commit the journal in the same commits as the work.** A journal entry
  describing a change that is not in the tree is a lie waiting to be found.
- **Write the goal at the top while you still remember why.** Retrofitting a goal
  turns the entry into a success story.
- **Keep the diagnosis separate from the remedy.** The worked example is careful
  to say the *cause* was the yield interval, not that adding a blocking read fixed
  it. Only the first is transferable.
- **Include the command.** The verification in these projects is one line of
  Python; a reader should be able to re-run the claim, not trust it.

## When a project has a human in it

The final entry of the example breaks frame: it is about a documentary script and
a producer rejecting two drafts — *"the process, not him; dive straight into
…"*. If your log is being read by someone who was not there, one entry saying who
the audience is and what they were asked for saves a reader from mistaking
process notes for the deliverable.

## Template

```markdown
# <N | Phase N>: <the problem, named>

<date, for dated entries>

**Goal.** <what becomes possible, and what is currently insufficient to get there.>

**Symptom.** <what was observed, stated so it is genuinely puzzling.>

**Chasing.** <what was tested, in order, including what was ruled out — and why
that exonerates the obvious suspect.>

**Cause.** <in the code, with the mechanism, not just the line.>

**Fix.** <what changed.>

**The rule this leaves behind.** <the durable claim, in one sentence, written so
it could be checked by someone else.>

<For measurements: gains AND losses, side by side, with "nobody chose" where
true. Then the stopping rule, if the variance now dominates.>
```

## Checklist before you commit an entry

- Could someone grep the symptom and find this?
- Does it say what was ruled out, not only what was found?
- Is the fix's *mechanism* recorded, so the remedy can change without invalidating it?
- Is there a rule or a constraint that outlives this bug?
- Are the numbers corroborated against an artefact, and is it said which ones are not?
- If a number went both ways, are both directions present?
- Is it dated, and is it in the same commit as the change it describes?
