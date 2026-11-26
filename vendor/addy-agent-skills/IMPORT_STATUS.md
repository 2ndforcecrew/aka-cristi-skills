# Upstream import — full vendored tree (PR #66 follow-up)

Source: https://github.com/addyosmani/agent-skills
Pinned revision: `e997ac5b9a74eab332d5e9793bb38a38c8cfdd74`
Upstream release: 0.6.18. Original MIT license retained in `LICENSE` (byte-identical).

## Import scope (final, verified by directory count)

Upstream tree: **280 entries** (279 files + 1 symlink). Imported into
`vendor/addy-agent-skills/`: **273 files + 1 symlink**; **6 files excluded**
(see below). PR #66 as opened brought in 52 entries (51 upstream files +
this file); the follow-up added 223 entries (222 files + 1 symlink) and
excluded 6. With this file, the vendor tree holds 274 files + 1 symlink.

| Category | Count |
| --- | --- |
| Skills — 26 `SKILL.md` entrypoints + 25 nested references/scripts/examples/frameworks | 51 files |
| Personas (`agents/`) | 5 files |
| Shared checklists (`references/`) | 7 files |
| Docs (`docs/`, incl. per-host setup) | 17 files |
| Evals (`evals/`: README, 26 cases, fixtures, plugin, skill-impact.md) | 124 files |
| Scripts (`scripts/` + `lib/`) | 21 files |
| Hooks (`hooks/`) | 9 files |
| Commands, 3 formats (`commands/` 10 `.toml` + `.claude/commands/` 10 `.md` + `.gemini/commands/` 10 `.toml`) | 30 files |
| `.claude/rules/skills-contributing.md` | 1 file |
| Manifests (`.claude-plugin/` 2 + `.codex-plugin/` 1 + `.agents/plugins/` 1 + root `plugin.json` 1) | 5 files |
| Root meta (`LICENSE`, `README.md`, `CONTRIBUTING.md`) | 3 files |
| Symlink (`.opencode/skills` → `../skills/`, git mode 120000) | 1 symlink |
| **Upstream total** | **273 files + 1 symlink** |

The symlink is recreated verbatim; the installer never copies or rebuilds
symlinks.

## Byte verification

- Full-tree `diff -r` upstream vs vendor: **0 content differences**
  (WP4, 2026-11-26). The only `Only in` entries are the 6 excluded files
  on the upstream side, `.git` on the upstream side, and this file on the
  vendor side.
- Per-file `cmp` on import (WP1a/WP1b): 156/156 + 66/66, 0 differences.
- The vendor evals anchor the 32 `SKILL.md` files by sha256 in
  `docs/skill-index.json` (`tools/generate_skill_index.py --check`).

## Excluded files (6)

| File | Reason (one line) |
| --- | --- |
| `AGENTS.md` | Upstream header states it is "not meant to be copied into other projects"; it configures agents working on the upstream repo itself. |
| `CLAUDE.md` | Repo-specific: "configures agents working on the addyosmani/agent-skills repository itself, not other projects. Don't copy it into another project". |
| `.gitattributes` | `* text=auto eol=lf` would change this repo's line-ending rules; `linguist-generated` marks are upstream metadata. |
| `.gitignore` | Entries point at upstream paths (`.claude/` caches, `evals/results/`); this repo has its own `.gitignore`. |
| `.github/workflows/test-plugin-install.yml` | Upstream CI workflow (Node 24 + validate-skills); never copied into this repo. |
| `.github/ISSUE_TEMPLATE/skill-gap.yml` | Generic template, but its dropdown lists the upstream 26 skills; rewriting it for this repo needs a separate decision. |

## Scan review (full tree)

skillspector 2.12.0, `--no-llm`, full vendor tree (WP4, 2026-11-26):
**235 findings** (HIGH 47, MEDIUM 186, LOW 2), score **100 CRITICAL,
DO_NOT_INSTALL**, max severity HIGH. Coverage 87.2% (239/274 fully
inspected, 35 partial, 0 uninspected) — 235 is a lower bound.

Triage (every finding concluded, 0 inconclusive) — see
`~/workspace/aka-skills-review/pr66-wp4-report.md` §2 and
`pr66-scan-full.json`:

- **180 false positives**: defensive documentation (SSRF guide teaching
  how to block `169.254.169.254`, Secrets chapter teaching not to commit
  `.env`, "Ignore previous instructions" as an **Ignore:**-list
  counter-example, `git reset --hard` in a recovery guide, `DELETE
  /api/tasks/:id` in a REST example table), test code, doc examples, and
  expected behaviour (hooks' `rm` only deletes their own cache directory;
  `doubt-driven-development`'s `codex exec --sandbox read-only` is
  gated by user authorization).
- **55 real issues, all one class**: unpinned-version `npx` calls
  (`npx lighthouse`, `npx -p chrome-devtools-mcp`, `npx skills add`,
  `npx tsc`, …) in 22 files (48 `.md` + 6 `.toml` + 1 `.js`). Low risk:
  there is no automatic execution path in this repo (the installer never
  runs `npx`; the one `.js` hit is a documentation mention). The vendor
  files must stay byte-identical, so the fix is documentation: pin the
  version when you run these commands yourself — see
  `docs/host-adaptation.md` §已知限制.

## Dedup, routing, install (Hybrid Agent System)

- **Installable: 31 skills** (6 native + 25 vendored). Vendored
  `interview-me` is **reference-only, never installed** — the native
  `interview-me` wins (the two descriptions are nearly verbatim; the
  native one carries this repo's format standard and evals routing).
  See `docs/dedup-decisions.md` for the per-pair rulings on all 32
  capabilities.
- **Routing**: CHEF routes by the table in
  `skills/chef-orchestrator/SKILL.md` §Routing. No new router persona
  (upstream AGENTS.md argues against one); `using-agent-skills` is only
  referenced as a discovery flowchart.
- **Progressive loading**: `docs/skill-index.json`, generated from
  frontmatter by `tools/generate_skill_index.py` (deterministic,
  `--check` verified). Index first; load only the 1–2 matching full
  texts; never load all 26 vendored texts at once (WP4 measured one task
  at 2 files / 737 lines vs 7,552 lines for all 26 full texts).
- **Unified installer**: `aka-skills install` / `quick_install` /
  `full_setup` / `universal_chef` install all 31 skills the same way
  (WP4 isolated drills: 31 skills on disk, 0 symlinks, installed
  `interview-me` verified native bytes, idempotent re-run). Root
  `plugin.json` is ours (`aka-cristi-skills`, v0.1.0); the upstream
  `plugin.json` (`agent-skills`) stays in vendor/ as reference.
- **Not installed, not wired**: hooks (default off — `simplify-ignore.sh`
  rewrites files in-session, `session-start.sh` injects a full SKILL.md
  into every session and warns hosts with native routing not to use it),
  upstream Node validators (reference only, not in CI, not a runtime
  dependency), `vendor/agents/` personas (see `docs/host-adaptation.md`
  for why installing them as live subagents is not an option).
- **Evals**: native evals 6/6 skills + 18/18 routing; vendor evals
  26/26 frontmatter + 26/26 routing (`evals/run_vendor_evals.py`,
  `evals/vendor-routing-cases.json`). Vendored SKILL.md files are exempt
  from this repo's literal section-title gate — only 1 of 26 carries a
  literal `## Process` (measured in WP2); their titles are never edited.
- **Tests**: 392 pass (31 skipped) on branch `pr66-followup`.

## Honest status

- This is a **Draft PR (#66), not merged, not activated**. Files are
  imported and the installer, routing and evals are verified at file
  level (WP4 isolated drills); **no live host has loaded or called the
  vendored skills** — all 7 hosts are NOT_RUN for loading/calling.
- The six release gates remain **BLOCKED**. Version stays **0.1.0**
  (no bump, no tag, no Release). Do not advertise a complete upstream
  mirror as activated, and do not bypass release gates.
