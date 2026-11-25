---
name: interview-me
description: Extract what the user actually wants instead of what they think they should want, one question at a time, until about 95% confidence. Use when an ask is underspecified or vague, when the user says "interview me" or "grill me", or when requirements are unclear and must be pinned down before any implementation.
---

# Interview Me

## Overview

What a user asks for and what they actually want are usually two different things. They ask for a dashboard because a dashboard is the conventional answer, not because a dashboard solves their problem. They say "make it better" without saying better for whom, or better at what.

The cheapest moment to close that gap is before any plan, spec, or code exists. Once implementation starts, every wrong assumption becomes rework, and the user will often rationalize the wrong result into "good enough" rather than admit the brief was wrong. This Skill prevents that: it is the interview that runs before everything else, in the Studio lane, until the intent is clear enough that CHEF can route real work with confidence.

This Skill produces a confirmed brief, not a build. Implementation, planning, and verification are downstream and must not start until the brief is confirmed.

## When to Use

Apply this Skill when:

- The ask is missing at least one of: **who** benefits, **why** now, what **success** looks like, what the binding **constraint** is.
- The request is conventional rather than specific ("build me X", "make it faster", "make it look good") and the convention cannot be unpacked without guessing.
- The user explicitly invokes it: "interview me", "grill me", "are we sure?", "stress-test my thinking".
- You catch yourself silently filling in ambiguous requirements before any plan, spec, or code exists.
- Two reasonable values are in tension and the user has not said which one wins (simplicity vs. flexibility, cost vs. speed, reach vs. craft).

**When NOT to use:**

- The ask is unambiguous and self-contained ("rename this variable", "fix this typo", "export this file").
- The user has explicitly asked for speed over verification.
- Pure information requests ("how does X work?", "what does this code do?").
- Mechanical operations (renames, formats, file moves).
- You already hold ~95% confidence; re-read the stop test below before assuming you do not.

## Loading constraints

This Skill needs a live, responsive user. **Do not invoke it in non-interactive contexts** such as CI pipelines, scheduled runs, or autonomous loops. In those contexts, if the ask is underspecified, record it as a blocker for the user instead of guessing. CHEF invokes this Skill in the Studio lane; Factory work must wait for the confirmed brief.

## Process

### Step 1: Hypothesize, with a confidence number

Before asking anything, write down your current best read of what the user wants in **one sentence**, plus an honest confidence number (0–100%):

```
HYPOTHESIS: You want a way to answer "how are we doing?" in standup, and "dashboard" was the convention that came to mind.
CONFIDENCE: ~30% — missing: who it is for, what "metrics" means here, and what success looks like
```

The number forces honesty. If you wrote a high number but cannot predict how the user will react to the next three questions you would ask, the number is wrong. Start at the level you can defend. Below ~70%, always add one line saying what is still unresolved — the user cannot help close a gap they cannot see.

### Step 2: Read context before asking

Before spending the user's attention, read what already exists: the current conversation, project files, existing briefs, references the user supplied, and prior decisions. A question whose answer is already written down is a wasted question. Prefer reading over asking, and say what you already read so the user can correct a wrong inference instead of repeating a known fact.

### Step 3: Ask one question at a time, each with a recommended answer

Format:

```
Q: <one focused question>
RECOMMENDATION: <your best answer, with the reasoning behind it>
```

Wait for the user to react before asking the next question.

**Why one at a time, not a batch:**

- The user cannot react to your hypotheses if you bury them in a list.
- Batches invite skim-reading and surface answers.
- The third question often depends on the answer to the first; asking everything at once locks in the wrong framing.
- The user's energy for thinking carefully is finite; spend it one question at a time.

**Why attach a recommendation:**

- Reacting to a wrong guess is faster than generating an answer from scratch.
- It commits you to a hypothesis you can be visibly wrong about, which keeps you honest.
- It surfaces *your* assumptions, which is what the interview is meant to expose.

The risk is a polite user agreeing just to be agreeable. Mitigate by being visibly willing to be wrong, and occasionally recommend in a direction you expect the user to push back on.

### Step 4: Order the dependencies

As answers arrive, arrange the open questions so each one is asked only after the answer it depends on. Who the work is for comes before what it should do; what success looks like comes before which constraints bind; scope comes before schedule. If a later answer invalidates an earlier one, say so plainly and re-ask the affected question instead of quietly carrying the contradiction forward.

### Step 5: Listen for want vs. should-want

The most dangerous answers are the ones where the user says what a thoughtful answer *sounds like* rather than what they actually want. Watch for:

- Answers that pattern-match best-practice talk ("I want it to be scalable", "clean architecture") without specifics.
- Answers that defer to convention ("the way most apps do it", "the standard approach").
- Phrases like "I should probably…", "I think I'm supposed to…", "good practice says…".
- Buzzwords as goals — when "modern", "scalable", or "robust" is the answer instead of a specific outcome.

When you hear these, ask the question that does the most work:

> *"If you didn't have to justify this to anyone, what would you actually want?"*

### Step 6: Restate as a brief and confirm

When confidence is high, write back what you now think the user wants, in their own words where possible, using the brief template in the Output section below. The user must be able to confirm or correct it line by line. Include "Out of scope" — half of misalignment is silent disagreement about what is *not* being built.

The gate is an explicit "yes." The following are **not** yes:

- "Whatever you think is best." → The user is delegating, which means they do not have 95% confidence either. Re-ask with two concrete options framed as a choice.
- "Sounds good." → Ambiguous. Ask: "Anything you'd refine?" Silence is not confirmation.
- "Sure, let's go." → Often a polite exit, not an endorsement. Same follow-up.
- Silence followed by "okay, let's start." → The user has given up on the interview, not converged. Stop and ask what was missed.

If they correct you, fold the correction in and restate. Loop until you get an explicit yes.

### Step 7: Stop and hand off

When the user confirms the brief with an explicit "yes":

1. **Deliver the confirmed brief** (see Output below).
2. **Offer the downstream paths** — hand the brief to CHEF for routing, or to the next Skill the brief calls for.
3. **STOP YOUR TURN.** Do not invoke tools, start planning, or begin implementation in this turn. Hand control back to the user to choose the next step.

### The 95% confidence stop test

You are done when you can answer yes to this:

> *Can I predict the user's reaction to the next three questions I would ask?*

If yes, you have shared understanding: stop interviewing and produce the restate. If no, you are not done; ask the next question.

There is also a floor: if you have gone several rounds and confidence still is not visibly rising, that is information about the ask, not a reason to keep grinding. Stop and tell the user: "I've asked X questions and I still can't predict your reactions. Something foundational is missing. Want to step back?"

## Output: the confirmed brief

The deliverable of this Skill is a confirmed brief. Specs, plans, and task lists are downstream; they consume this brief.

```markdown
## Brief: <short title>

- Goal: <one line — the outcome the user actually wants>
- User: <one line — who benefits>
- Why now: <one line — what changed>
- Success: <one line — how we know it worked>
- Constraints: <binding limits — budget, time, platform, brand, quality bar>
- Out of scope: <what we are explicitly NOT doing>
- Acceptance criteria: <observable checks the finished work must pass>
- Open questions: <what is still unresolved, if anything>

Confirmed by: <explicit yes from the user>
```

If the user wants the brief to persist (a multi-session project, a handoff to another collaborator), offer to save it. Only save if they confirm.

## Common Rationalizations

| Rationalization | Rebuttal |
|---|---|
| "The ask is clear enough" | If you cannot write the user's desired outcome in one sentence right now, the ask is not clear. Run Step 1 before deciding. |
| "Asking questions wastes their time" | Time spent on 4–6 targeted questions is small. Time spent building the wrong thing is enormous, and the user bears that cost. |
| "I'll figure it out as I build" | Switching costs after implementation starts are many times what they are now. Discovery during implementation is rework. |
| "They said 'whatever you think,' so I should just decide" | "Whatever you think" is delegation, not a decision. Re-ask with two concrete options framed as a choice. |
| "I should give them several options to pick from" | Options help when the user knows what they want and is choosing between trade-offs. They do not know what they want yet. Listing options widens the search; asking narrows it. |
| "We've talked enough, I get it" | Test it: can you predict their reaction to the next three questions? If not, you do not get it yet. |

## Red Flags

- Three or more questions in a single message: that is batching, not interviewing.
- A question without your recommendation attached: that is surveying, not committing.
- Accepting "whatever you think is best" as a terminal answer.
- Producing a spec, plan, or task list before the user has explicitly confirmed the brief.
- Invoking tools or starting downstream work immediately upon confirmation instead of stopping the turn.
- Skipping the "Out of scope" line in the brief: silent disagreement about non-goals is half of misalignment.

## Verification

After applying interview-me:

- [ ] An explicit hypothesis with a confidence number was stated in the first turn.
- [ ] Every confidence number below ~70% was accompanied by a one-line reason (what is still unresolved or missing).
- [ ] Existing context was read before asking; no question was asked whose answer was already written down.
- [ ] Questions were asked one at a time, each with the agent's recommendation attached.
- [ ] Dependencies between questions were ordered; contradictions from later answers were surfaced and re-asked.
- [ ] At least one "what would you actually want if you didn't have to justify it?" probe ran when the user gave a sophistication-signaling or convention-signaling answer.
- [ ] A concrete brief (Goal / User / Why now / Success / Constraints / Out of scope / Acceptance criteria / Open questions) was written back to the user.
- [ ] The user confirmed the brief with an explicit yes (not "whatever you think", not "sounds good", not silence).
- [ ] At the stop point, the agent could predict reactions to the next three questions it would ask.
- [ ] Upon receiving explicit confirmation, the turn stopped immediately without invoking tools or starting downstream work.
- [ ] Any handoff to a downstream Skill was framed in terms of the confirmed brief, not the original underspecified ask.

## Interaction with other Skills

- **`chef-orchestrator`**: the invoker. CHEF runs this Skill in the Studio lane before routing Factory work; no implementation task is handed off until the brief is confirmed.
- **`verified-change-loop`**: downstream. Once the brief is confirmed and work exists to verify, the loop takes over.
- **`feature-journey-map`**: downstream. The confirmed brief's user and success lines feed the journey map.
- **`skill-evaluation-gate`**: this Skill itself is subject to the gate like any other candidate; field evidence decides whether it stays.

## Provenance

Original CHEF workflow for this repository. The interview mechanics (one question at a time, hypothesis with confidence, explicit-yes gate) are inspired by the approach in addyosmani/agent-skills `interview-me`; the text, structure, brief template, and CHEF routing are written fresh for this repository and are not a copy.
