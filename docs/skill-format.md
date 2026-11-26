<!--
  This document is the format standard for skills in this repository.
  It is NOT a skill and is not meant to be loaded into an agent's
  working set. It lives in docs/ so it stays out of the agent's
  working set. New skills copy this shape; evals enforce it.
-->

# Skill format standard

Every skill in this repository is one directory,
`skills/<name>/`, built around one file, `SKILL.md`, with
optional `references/`, `scripts/`, and `assets/` directories
(see Directory structure below). Every `SKILL.md`
follows the same shape so that any agent or host can load it, any
reader can find the same information in the same place, and the
deterministic evals (`evals/run_evals.py`) can check it without
guessing at synonyms.

The standard is enforced, not aspirational: the evals match the
literal section titles below. A skill that renames a section, or
hides a required section under a synonym, fails the structure
check. If the standard is wrong for a new skill, change the
standard (and the evals) in the same PR — never silently diverge.

## Directory structure

```text
skills/<name>/
├── SKILL.md       # entry: triggers, process, verification
├── references/    # knowledge the skill loads on demand
├── scripts/       # executable helpers the skill runs
└── assets/        # templates, materials, resources
```

- `SKILL.md` is required — it is the only file an agent loads
  up front. Everything else is loaded on demand (progressive
  disclosure): the skill names what it needs, when it needs it.
- `references/` holds supplementary knowledge: style catalogues,
  case files, research notes, decision records. Examples:
  `visual-design/references/` holds the design-style catalogues
  and case files; `chef-orchestrator/references/` bundles the
  shared training rules.
- `scripts/` holds executable helpers the skill runs for
  deterministic steps. A script must be named from the skill that
  runs it, and the skill must say when it runs.
- `assets/` holds templates, materials, and resources the skill
  uses or produces.
- A directory exists only when it has content. Do not create
  empty `references/`, `scripts/`, or `assets/` directories —
  git does not track them, and an empty placeholder is noise. A
  new skill starts as `SKILL.md` alone and grows directories as
  content arrives.

## Frontmatter

```yaml
---
name: <directory name>
description: <one or two sentences>. Use when <trigger language>.
---
```

- `name` must equal the skill's directory name, lowercase
  kebab-case (`^[a-z0-9][a-z0-9-]*$`).
- `description` must be non-empty and must contain a `Use when ...`
  trigger clause. The trigger language is taken from the skill's
  own `When to Use` section — it states when the skill fires, in
  the user's words, not a new scenario invented for the
  frontmatter. A description without `Use when` is flagged by the
  evals as a soft recommendation.

## Title

```markdown
# <Skill Name>
```

The H1 is the skill's plain name only — no suffix. Version
markers (`V0.1`), maturity notes (`Portable Starter`), and similar
qualifiers belong in `Overview`, not in the title.

## Section order

Sections appear in this fixed order, numbered as below.
Frontmatter (1) and the title (2) are covered in the sections
above; the body sections are 3–10. Sections 3–5 and 7–9 are
required in every skill; section 6 holds the skill's own middle
sections; section 10 is present only when the skill has one.

| # | Section | What it is |
|---|---|---|
| 1 | frontmatter | `name` + `description` with a `Use when` trigger clause (see above). |
| 2 | `# <Skill Name>` | Plain name only, no suffix (see above). |
| 3 | `## Overview` | A short overview (typically 2–4 sentences): what the skill does, for whom, and its standing (e.g. field-validation status). Written from the skill's own description and body — never new capabilities. `interview-me` is the one exception: its Overview is longer because the framing (the dashboard example and the confirmed-brief idea) needs the room. |
| 4 | `## When to Use` | When the skill fires (and, where useful, when explicitly NOT to use it). The source of the frontmatter trigger clause. |
| 5 | `## Process` | The numbered steps the skill runs, in order. Sub-steps are `###` headings under it. |
| 6 | Middle sections | The skill's own sections — inputs, preconditions, safety, templates, gates, output contracts, research libraries. Content unchanged, relative order kept, all between `Process` and `Common Rationalizations`. |
| 7 | `## Common Rationalizations` | The excuses agents actually make for skipping this skill, each with its rebuttal (see table format below). |
| 8 | `## Red Flags` | Observable signs the skill is being skipped or misapplied, as a bullet list. |
| 9 | `## Verification` | The checks that prove the skill was actually applied — checklists, evidence contracts, hard gates. Not safety constraints; those live in the middle sections. |
| 10 | `## Provenance` | Where the skill came from (original work, inspiration, attribution). Last section when present; omitted when the skill has none. |

Two naming rules:

- **No synonyms.** `Procedure`, `Workflow`, `Evidence check`,
  `Evidence contract`, `Quality gates`, `Acceptance`, `Trigger and
  boundaries` are old names. They were renamed to `Process`,
  `Verification`, and `When to Use` in the 2026-11-26 unification;
  do not reintroduce them.
- **Merges keep content.** When two old sections map to one
  standard section (e.g. `Quality gates` + `Acceptance` both became
  `Verification` in visual-design), merge the full content into the
  one section. Nothing is dropped.

## Common Rationalizations table

Fixed two-column format:

```markdown
| Rationalization | Rebuttal |
| --- | --- |
| "<the excuse, in the agent's voice>" | <why it is wrong, and what to do instead> |
```

4–6 rows. Each excuse must be one this repo's agents actually
make for this skill — not generic filler. The rebuttal names the
concrete failure the excuse causes.

## Red Flags

A bullet list of 4–6 items. Each flag is an observable behaviour
("a handoff with no task ID", "a hard-check matrix missing"), not
a vague warning.

## Verification

A checklist (`- [ ]`) or an evidence contract the reviewer can
check line by line. A skill whose verification lives only inside
its process steps — with no dedicated section — does not pass the
standard: the contract must be visible on its own.

## Enforcement

```bash
python3 -m evals.run_evals            # structure + routing, exit 0/1
python3 -m evals.run_vendor_evals     # vendor frontmatter + routing + index coverage, exit 0/1
python3 -m unittest discover -s tests # whole suite, evals included
```

`evals/run_evals.py` matches the literal titles in the table
above (`overview`, `when-to-use`, `process`, `verification` by
exact heading; `common-rationalizations` and `red-flags` by
heading substring). `Safety gates` deliberately does not count as
verification. See `evals/README.md` for the full check
description.

### Vendored skills are exempt from the structure gate

Skills under `vendor/addy-agent-skills/skills/` do **not** follow
this standard and are **not** checked by `evals/run_evals.py`:
only 1 of 26 has a literal `## Process` heading, and
`using-agent-skills` has no standard sections at all. They are
checked instead by `evals/run_vendor_evals.py` (frontmatter +
routing + generated-index coverage). Never retitle a vendored file
to make it pass the native gate — vendor files stay byte-identical
to upstream (red line R1). The decision record is
`docs/dedup-decisions.md` §4; the routing table that names all 32
capabilities is the `## Routing` section of
`skills/chef-orchestrator/SKILL.md`, and the machine-readable index
is `docs/skill-index.json` (generated by
`tools/generate_skill_index.py`, never hand-edited).

## Sources

The shape is borrowed from addyosmani/agent-skills
(`docs/skill-anatomy.md`): Overview, When to Use, Process, Common
Rationalizations, Red Flags, Verification — adapted to this repo's
skills, whose middle sections (inputs, gates, templates, research
libraries) stay where they are.
