# PLAN — CLI (`aka-skills`) + MCP Server for 2ndforcecrew/aka-cristi-skills

- Branch: `feat/cli-mcp-tools-20261125` (worktree `/home/hatch/workspace/aka-skills-cli-mcp`), HEAD `cc5bab7` (main)
- Approval: cristi, 2026-11-25 20:19 — "1和2做": (1) CLI first, then (2) MCP Server. Both in ONE branch, ONE Draft PR. **Never merge.**
- This file is a plan only. No implementation code was written while producing it.

## 1. Goal and scope

### Goal
Make the repo usable without a git checkout + manual `python -m tools.…` invocation, in two steps:

1. **CLI** — an installable Python package exposing the command `aka-skills` that wraps the existing installer flow.
2. **MCP Server** — a stdio MCP server (MCP Python SDK) exposing the repo's skills, design cases, install preview, validation and status as tools, so any MCP client can use this repo without shelling out.

### In scope
- `pyproject.toml` packaging (hatchling), console script `aka-skills`, subcommands `install` / `verify` / `status` / `list-skills` / `validate` (+ `--version` / `--help`).
- MCP server module with stdio transport and the 7 tools listed in §4.
- New tests for CLI and MCP; full existing suite stays green.
- README install section updated to document `pip install .` + `aka-skills`.
- Clean-venv CLI smoke test and MCP protocol smoke test (initialize → `tools/list` → `tools/call`).

### Out of scope (do NOT do)
- Publishing to PyPI (installable only; `pip install .` from a checkout/sdist).
- Any change to `.github/workflows/` (token has no workflow scope; a push touching them would be rejected). CI coverage for the new code therefore cannot be added in this PR — new MCP tests must skip gracefully when the SDK is absent (see §6).
- Credentials, permissions, OAuth, workspace/cloud flows, or any change to auth behaviour. The `--workspace` path in `full_setup` stays opt-in and consent-gated exactly as today.
- Any change to installer semantics: preview-first, explicit YES/INSTALL consent before writes, never overwrite a conflicting personal config, conflict aborts with no files written.
- No cost incurred (no paid APIs, no quota-consuming agent runs in tests).
- `install.ps1`, GUI installer (`tools/gui_installer.py`, `chef-gui.spec`), and the six release gates are untouched.
- No new runtime dependency for the CLI itself (stdlib only, apart from the build backend). The MCP SDK is an optional extra, not a hard CLI dependency.

## 2. What exists today (evidence implementers must reuse, not rewrite)

Read before implementing. All paths relative to repo root.

| Existing piece | Exact entry points to reuse | Notes |
|---|---|---|
| `tools/full_setup.py` (whole file read) | `run(*, apply, interactive, workspace, test_agents, codex_home, skills_root, input_fn, host, project, hermes_skills_root, scope)` → report dict; `dependency_status()` → `{"python","git","codex_cli","workspace_keyring","workspace_oauth_client_id"}`; `main(argv=None)` (argparse, prints JSON, exit 1 unless `core_install` in `PREVIEW_ONLY`/`CANCELLED`/`FILES_VERIFIED`); `_approve(question, input_fn)` requires the user to type exactly `YES` | Default (no `--apply`/`--interactive`) = preview only, `core_install: "PREVIEW_ONLY"`, `workspace`/`live_agents`: `"NOT_RUN"`. `apply` and `interactive` are mutually exclusive (`ValueError`). Non-`codex` hosts go through `_run_portable_host()` → `universal_chef.inspect` / `universal_chef.install`. `ROOT = Path(__file__).parents[1]`. |
| `tools/quick_install.py` | `execute(*, apply=False, codex_home=None, skills_root=None)` → `{"status": "PREVIEW"}` (no writes) or `{"status": "FILES_VERIFIED"/"FAIL", "rules", "roles", "skills", "agent_activation": "NOT_RUN"}`; `main(argv=None)` (`--apply` / `--interactive`, latter asks for literal `INSTALL`) | Installs 4 skills only: `SKILLS = ("chef-orchestrator", "verified-change-loop", "feature-journey-map", "skill-evaluation-gate")` — note: **not** `visual-design`. Pre-checks all targets first; any conflict raises `ValueError` before writing anything. `codex_home`/`skills_root` are the sandbox/test overrides. |
| `tools/skill_installer.py` | `inspect(source, target="directory", root=None)`, `install(source, target, root, apply=False)`, `verify(name, target="directory", root=None)`, `remove(...)`, `rollback(...)`, `InstallError(ValueError)`; `main()` actions `preview/install/verify/uninstall/rollback` with `--target codex|directory`, `--root`, `--apply` | `root_for(target, root)` resolves the destination. This is the per-skill install primitive `quick_install.execute` calls. |
| `tools/skill_validator.py` | `validate_skill(root: Path) -> dict` with keys `schema_version`, `skill_path`, `status` (`"FAILED"` if any error-severity finding else `"PREFLIGHT_ONLY"`), `runtime_verified: False`, `host_compatibility_verified: False`, `findings: [{code, message, severity}]`; `main(argv)` takes a `skill_dir` positional, exit 1 on `FAILED` | Read-only preflight. Checks: real dir (not symlink), `SKILL.md` present + ≤256 KiB (`MAX_SKILL_BYTES`), YAML frontmatter with `name` matching `^[a-z0-9]+(-[a-z0-9]+)*$` (≤64 chars) and `description` present, non-empty instructions, `scripts/` dir safety. Deliberately parses only `name:`/`description:` with regex — no YAML execution. |
| `tools/universal_chef.py` | `HOSTS = ("codex", "workbuddy", "claude", "gemini", "opencode", "hermes", "generic")`; `inspect(host, project=None, hermes_skills_root=None, scope="project")`, `install(host, project, apply=False, hermes_skills_root, scope)`, `verify(...)`, `uninstall(...)` | Multi-host adapter used by `full_setup` for non-Codex hosts. CLI `--host` choices must be exactly `HOSTS`. |
| `tools/chef_global_rules.py`, `tools/codex_subagents.py` | `chef_global_rules.plan("install", TEMPLATE, codex_home)` / `.apply("install"/"verify", TEMPLATE, codex_home, confirmed=True)`; `codex_subagents.ROLE_NAMES` (`research`, `coding`, `qa`, `automation`), `.plan(role, codex_home)`, `.install(role, codex_home, apply=True)`, `.verify(role, codex_home)` | Called by `quick_install.execute`; CLI must not reimplement their conflict/backup logic. `TEMPLATE = ROOT / "templates" / "AGENTS.global.md"`. |
| `skills/` layout | 5 dirs, each with `SKILL.md` + YAML frontmatter (`name:`/`description:` first lines): `chef-orchestrator/`, `verified-change-loop/`, `feature-journey-map/`, `skill-evaluation-gate/`, `visual-design/` (has `references/`). `visual-design/references/styles/` = 6 style MDs (`glassmorphism`, `flat-information-graphics`, `giant-type-posters`, `experimental-posters`, `colorful-commercial-posters`, `giant-type-web-design`) + `INDEX.md`; `visual-design/references/cases/` = `beauty-class-poster.md` (+ more cases may land from PR #61 follow-ups). | Skill discovery = enumerate `skills/*/SKILL.md`, parse `name:`/`description:` with the same regex approach as `skill_validator` (no YAML lib). |
| `agents/` | `research.toml`, `coding.toml`, `qa.toml`, `automation.toml` | Role definitions installed by `codex_subagents`. No CLI/MCP change needed. |
| Tests | `tests/test_*.py`, **stdlib `unittest` only** — `python -m unittest discover -s tests -v` (see `.github/workflows/tests.yml`; CI runs Python 3.11 on ubuntu/windows/macos + `pip install -r requirements-workspace.txt`, then `compileall tools tests`). No `pytest.ini`, no `conftest.py`, no pytest dependency. Existing tests mock `tools.full_setup.quick_install.execute` and `dependency_status` (see `tests/test_full_setup.py`). | New tests must follow the same style (`unittest`, `unittest.mock.patch`, `tempfile` sandboxes, `--codex-home`/`--skills-root` overrides). Do NOT introduce pytest. |
| `requirements-dev.txt` | `-r requirements-workspace.txt`, `ruff==0.14.14`, `mypy==1.19.1` | `requirements-workspace.txt` = `keyring==25.7.0` only (optional workspace runtime). |
| README install section | `README.md` §01: `git clone --depth 1 … && python3 -m tools.full_setup --interactive` (macOS/Linux); PowerShell equivalent on Windows. States: "安装器预览变更并要求同意，不覆盖有冲突的个人配置", Python 3.11+ prerequisite. | Keep this flow documented; add the new `pip install` flow alongside it, do not replace it. |
| Environment | Local VM Python is 3.12.3; CI pins 3.11; README requires 3.11+. **Neither `mcp` nor `fastmcp` is installed locally** (checked via `importlib.util.find_spec` — both `None`). No packaging files exist today (`pyproject.toml` / `setup.py` / `setup.cfg` / `MANIFEST.in` all absent). `.gitignore` already ignores `build/` and `dist/`. | MCP SDK version cannot be verified from this machine (no network in planning). See open question in §8. |

## 3. File list — create / modify

### 3a. CLI part

| # | File | New / Edit | Purpose |
|---|---|---|---|
| C1 | `pyproject.toml` | **New** | Packaging: hatchling backend, `requires-python = ">=3.11"`, project metadata, `console_scripts` entry `aka-skills = "aka_skills.cli:main"`, `[project.optional-dependencies] mcp = ["mcp==1.13.0"]`, hatchling `force-include` rules bundling content into the wheel (see §5), ruff/mypy config if not already covered elsewhere (check first — do not duplicate existing config). |
| C2 | `aka_skills/__init__.py` | **New** | Package marker + `__version__` (single source of truth, e.g. `"0.1.0"`; `pyproject.toml` must read it dynamically or duplicate it — pick one, document the choice). |
| C3 | `aka_skills/cli.py` | **New** | `argparse` CLI: `main(argv=None) -> int` (mirrors the `main(argv=None)` convention of `tools/*.py`). Thin wrappers only — every subcommand delegates to the functions in §2, no reimplementation of install/verify logic. JSON output via `--json` where noted. |
| C4 | `aka_skills/__main__.py` | **New** | `python -m aka_skills` entry (calls `cli.main()`), for parity with `python -m tools.full_setup`. |
| C5 | `aka_skills/repo.py` | **New** | Repo-root/content resolution shared by CLI and MCP server (see §5): env `AKA_SKILLS_REPO_ROOT` → `--repo-root` → checkout discovery → bundled `importlib.resources` data. Pure path logic, no I/O writes. |
| C6 | `README.md` | **Edit** | §01 install section: add `pip install .` + `aka-skills --help` + `aka-skills install` flow next to the existing `git clone` + `python -m tools.full_setup --interactive` flow; state explicitly that PyPI publication is NOT done and the existing flow still works. |
| C7 | `requirements-dev.txt` | **Edit** | Add the MCP extra for local testing (e.g. a comment + `-e .[mcp]` is NOT valid in a requirements file across installs — instead add `mcp==1.13.0` on its own line with a comment that it is only needed for MCP tests; keep `ruff`/`mypy` lines untouched). Do NOT add anything to `requirements-workspace.txt`. |
| C8 | `tests/test_cli.py` | **New** | CLI tests (see §6). |

### 3b. MCP part

| # | File | New / Edit | Purpose |
|---|---|---|---|
| M1 | `aka_skills/mcp_server.py` | **New** | MCP server: stdio transport, tool handlers (see §4). Imports `mcp` lazily inside `main()`/`serve()` so `aka-skills` works without the SDK installed; if absent, print a clear error naming the extra (`pip install '.[mcp]'`) and exit non-zero. All tool implementations are thin wrappers over §2 functions + read-only file reads. |
| M2 | `aka_skills/cli.py` | **Edit** (same file as C3) | Add the `serve` subcommand (§3, §4) that starts the MCP server. The server itself lives in `mcp_server.py`; `cli.py` only wires the subcommand. |
| M3 | `tests/test_mcp_server.py` | **New** | MCP tests (see §6): in-process tool-function tests (no SDK needed) + full protocol smoke test, skipped when `mcp` is not importable. |
| M4 | `pyproject.toml` | **Edit** (same file as C1) | The `mcp` optional dependency and any MCP-related packaging notes live here; no separate packaging file. |
| M5 | `README.md` | **Edit** (same file as C6) | Short MCP section: how to run (`aka-skills serve`), stdio transport, tool list, and a minimal example client config snippet (Claude Desktop / Codex `mcpServers` JSON shape — generic, no credentials). |

**Total: 9 files to create, 3 files to modify** (`pyproject.toml`, `aka_skills/cli.py`, `README.md` counted once each across both parts; `requirements-dev.txt` is a 4th modified file — total modified = 4). No other files may be created or changed. In particular: no `.github/workflows/` changes, no `install.ps1` changes, no changes under `tools/` or `skills/`.

## 4. CLI design

Command: `aka-skills`. Global flags: `--version`, `--help`, `--repo-root PATH` (override content location; default = auto-discovery per §5), `--json` (where a subcommand supports it: machine-readable JSON on stdout, same shape as the underlying `tools.*` report dicts).

| Subcommand | Flags | Behaviour (exact mapping to existing code) |
|---|---|---|
| `install` | `--interactive` / `--apply` (mutually exclusive, same rule as `full_setup.run`: both → error, exit 2 via argparse or `ValueError` → exit 1 with JSON error), `--host {codex,workbuddy,claude,gemini,opencode,hermes,generic}` (default `codex`), `--scope {project,user}` (default `project`), `--project PATH`, `--codex-home PATH`, `--skills-root PATH`, `--workspace`, `--json` | Calls `tools.full_setup.run(apply=…, interactive=…, workspace=…, codex_home=…, skills_root=…, host=…, project=…, scope=…)`. **Default with neither `--interactive` nor `--apply` = preview only, writes nothing** (`core_install: "PREVIEW_ONLY"`). `--interactive` prompts for literal `YES` via `full_setup._approve` before any write; declining → `CANCELLED`, exit 0. `--apply` writes without prompting (explicit user choice, mirrors `tools/quick_install.py --apply`). Prints the report dict as JSON (default) or a short human summary; exit code follows `full_setup.main`: 0 if `core_install` in (`PREVIEW_ONLY`, `CANCELLED`, `FILES_VERIFIED`), else 1. `--workspace` and agent-testing are NOT exposed as separate flags in v1 (workspace stays reachable only via `python -m tools.full_setup --workspace`; document this). |
| `verify` | `--codex-home PATH`, `--skills-root PATH`, `--json` | Read-only verification of the installed state: for each of the 5 `quick_install.SKILLS`, `tools.skill_installer.verify(name, "codex", codex_home)` (or `"directory"` when `--skills-root` is given — mirror `quick_install.execute`'s `target` logic); `tools.chef_global_rules.apply("verify", TEMPLATE, codex_home)`; `[tools.codex_subagents.verify(role, codex_home) for role in ROLE_NAMES]`; plus `tools.skill_validator.validate_skill(ROOT / "skills" / name)` for each skill dir. Output: `{"status": "PASS"/"FAIL", "rules": …, "roles": {…}, "skills": {…}, "validation": {…}}`. Exit 0 on PASS, 1 on FAIL. Writes nothing. |
| `status` | `--json` | Read-only status: `tools.full_setup.dependency_status()` + a preview summary from `tools.quick_install.execute()` (no `apply`) showing per-skill/per-role planned action (`INSTALL`/`UPGRADE`/`ALREADY_INSTALLED`/conflict). Exit 0 always (unless an unexpected exception → JSON error, exit 1). Writes nothing. |
| `list-skills` | `--json` | Enumerate `skills/*/SKILL.md`; for each, parse `name:`/`description:` frontmatter with the same regex approach as `skill_validator` (no YAML lib). Output list of `{"name", "description", "path"}`. Exit 0. |
| `validate <skill>` | `<skill>` = skill directory name (e.g. `visual-design`) or a path to a skill dir; `--json` | Calls `tools.skill_validator.validate_skill(root)` and prints its dict; exit 0 unless `status == "FAILED"` (exit 1). Read-only. |
| `serve` | `--repo-root PATH` | Starts the MCP server on stdio (see §4). This is the MCP entry point; it does not take install flags. Blocks until the client disconnects / stdin closes. |
| `update` | `--host {codex,workbuddy,claude,gemini,opencode,hermes,generic}`, `--scope {project,user}` (default `user` — differs from install's `project`), `--project PATH`, `--skills-root PATH` (overrides the `--host` given only; needs `--host`), `--repo-root` / `--repo PATH`, `--no-pull`, `--interactive` / `--apply` (mutually exclusive), `--json` | Calls `tools.repo_update.preview_update` (default: read-only preview, zero writes) or `tools.repo_update.apply_update` (`--apply`, or `--interactive` after a literal `YES`): git pre-checks (`rev-parse`, `status --porcelain`; dirty tree / non-main branch / non-checkout → error, exit 1, no sync), `git pull --ff-only origin main` (failure stops everything, never syncs from a stale tree), then per-target re-sync (codex via `quick_install.execute`, others via `universal_chef.install`, workbuddy adoption via `skill_installer.adopt`) and verification. Output: JSON report with `repo` / `targets` / `legacy_codebuddy_install` / `next`. Exit 0 on `UPDATED` / `NO_CHANGE` / `PREVIEW_ONLY` / `CANCELLED` / `NO_TARGETS` (unless a target is `CONFLICT`/`FAIL`), else 1; usage errors exit 2. WorkBuddy success text says "restart the WorkBuddy app", never "restart the session". |

Notes:
- `aka-skills` with no subcommand prints help and exits 2 (argparse default) — or exits 0 with help; pick argparse's default and record it in tests.
- All user-facing errors print a JSON object `{"status": "FAIL", "error_type": …}` on `--json`, matching the existing `tools/*.py` `main()` error shape; human mode prints a one-line message to stderr.
- Do not add `uninstall`/`rollback` subcommands in v1 (the primitives exist in `skill_installer.remove`/`rollback`, but exposing destructive ops needs a separate decision; note as future work).

## 5. MCP design

### Transport and SDK
- **Transport:** stdio only (no HTTP/SSE). Server reads JSON-RPC from stdin, writes to stdout. No network listener, no auth.
- **SDK:** MCP Python SDK, **pinned `mcp==1.13.0`** (see open question in §8 — version must be confirmed against PyPI at implementation time; it was not verifiable from this machine). Use the high-level `FastMCP` API (`mcp.server.fastmcp.FastMCP`) unless the implementer finds a concrete incompatibility, in which case fall back to the low-level `mcp.server.Server` + `stdio_server` and record the reason in the PR description. Server name: `aka-skills`.
- **Dependency shape:** `mcp` is an *optional* extra (`.[mcp]`), never a hard dependency of the `aka-skills` command. `mcp_server.py` must import `mcp` lazily and fail with a clear message if it is missing.
- **Entry points:** `aka-skills serve` (primary) and `python -m aka_skills.mcp_server` (direct, same behaviour).

### How the server finds the repo root / skills when installed
Content (`skills/`, `agents/`, `templates/`, `shared-training/`) stays at the repo root in the source tree; it is **not** moved into the package. Resolution order in `aka_skills/repo.py`, shared by CLI and server:
1. Explicit `--repo-root` / env `AKA_SKILLS_REPO_ROOT` (must contain a `skills/` dir, else error).
2. Checkout discovery: walk up from `Path.cwd()` (max ~6 levels) for a directory containing both `skills/` and `pyproject.toml`.
3. Bundled data: `importlib.resources.files("aka_skills") / "data"` — populated at build time by hatchling `force-include` rules in `pyproject.toml` mapping `skills → aka_skills/data/skills`, `agents → aka_skills/data/agents`, `templates → aka_skills/data/templates`, `shared-training → aka_skills/data/shared-training` (wheel *and* sdist targets). If the wheel was built without these, step 3 is absent and the server must error clearly instead of silently serving stale/empty content.
4. Fail closed: if no root resolves, every tool returns an error result (`{"status": "ERROR", "error": "repo root not found…"}`); the server must not guess a path.

Windows note: all paths via `pathlib.Path`; never hard-code `/` separators or `~/.codex` assumptions — reuse `skill_installer.root_for` for install-target paths.

### Tools (exact names, schemas, returns)

All tools return a JSON object (MCP `TextContent` containing a JSON string). Read-only unless stated. `install_preview` is the **only** install-adjacent tool and it **never writes to disk**.

| # | Tool name | Input schema (JSON Schema) | What it does | Returns |
|---|---|---|---|---|
| T1 | `list_skills` | `{}` (no properties) | Enumerate `skills/*/SKILL.md` at the resolved root; parse `name:`/`description:` frontmatter (same regex as `skill_validator`). | `{"skills": [{"name", "description", "path"}]}` — same shape as CLI `list-skills`. |
| T2 | `read_skill` | `{"name": {"type": "string", "description": "Skill directory name, e.g. 'visual-design'"}}` (required: `["name"]`) | Read `skills/<name>/SKILL.md` (UTF-8). Reject `..`, `/`, `\` in `name` (path-traversal guard; return an error result, do not raise). | `{"name", "path", "content": "<full SKILL.md text>"}`. Unknown skill → `{"status": "ERROR", "error": "unknown skill: <name>"}`. |
| T3 | `list_design_cases` | `{"kind": {"type": "string", "enum": ["style", "case"], "description": "Optional filter; omit for both"}}` (no required fields) | List `skills/visual-design/references/styles/*.md` (`kind: "style"`, excluding `INDEX.md` from the list but noting its presence) and `skills/visual-design/references/cases/*.md` (`kind: "case"`). Parse the first `# ` heading as `title` when present. | `{"styles": [{"name", "title", "path"}], "cases": [{"name", "title", "path"}]}` (filtered by `kind` when given). |
| T4 | `read_design_case` | `{"kind": {"type": "string", "enum": ["style", "case"]}, "name": {"type": "string"}}` (required: `["kind", "name"]`) | Read one file from `references/styles/<name>.md` or `references/cases/<name>.md`. Same traversal guard as T2; `.md` suffix is added by the server, never taken from input. | `{"kind", "name", "path", "content": "<full markdown>"}`; unknown → error result. |
| T5 | `install_preview` | `{"host": {"type": "string", "enum": ["codex","workbuddy","claude","gemini","opencode","hermes","generic"], "default": "codex"}, "scope": {"type": "string", "enum": ["project","user"], "default": "project"}, "project": {"type": "string", "description": "Optional target project path (required for non-Codex hosts)"}}` (no required fields) | Dry-run only: calls `tools.full_setup.run(host=…, scope=…, project=…)` with **no** `apply`/`interactive` (preview path), i.e. `quick_install.execute()` preview + `universal_chef.inspect` for non-Codex hosts. **Must never pass `apply=True` and must never call `input()`** — assert this in tests by patching and by checking no files change. | The `full_setup.run` report dict verbatim (`core_install: "PREVIEW_ONLY"`, `preview: {…}`, `workspace: "NOT_RUN"`, `live_agents: "NOT_RUN"`), plus `"writes": false`. |
| T6 | `validate_skill` | `{"name": {"type": "string", "description": "Skill directory name"}}` (required: `["name"]`) | Calls `tools.skill_validator.validate_skill(ROOT / "skills" / <name>)`. Read-only. | The validator dict verbatim (`schema_version`, `skill_path`, `status`, `runtime_verified`, `host_compatibility_verified`, `findings`). |
| T7 | `check_status` | `{}` (no properties) | `tools.full_setup.dependency_status()` + the same preview summary as CLI `status` (`quick_install.execute()` preview). Read-only. | `{"preflight": {…}, "preview": {…}, "repo_root": "<resolved path>"}`. |

### Server behaviour notes
- Tool handlers must be plain functions (or thin wrappers) so tests can call them without a running server or the SDK installed; the FastMCP decorators are only the transport layer.
- Never log secrets or user paths beyond the repo root; stdout is reserved for the MCP protocol — all diagnostics go to stderr.
- Large reads: `SKILL.md` files are small; cap `read_skill`/`read_design_case` content at the validator's 256 KiB limit and return an error result above it (reuse `MAX_SKILL_BYTES` from `skill_validator` as the cap constant).

## 6. Dependency decisions

| Decision | Choice | Rationale |
|---|---|---|
| Build backend | **hatchling** (`hatchling>=1.27,<2`) | `force-include` can map repo-root content dirs (`skills/`, `agents/`, …) into the wheel under `aka_skills/data/` without moving files or duplicating them in the source tree. setuptools would need the content physically inside the package dir or a custom build step. If the implementer hits a hatchling problem, setuptools + a `MANIFEST.in` + content copied into the package is the fallback — but that fallback requires moving/duplicating content, so it needs coordinator sign-off, not a silent swap. |
| Python | `requires-python = ">=3.11"` | Matches README ("Python 3.11+") and CI (3.11). Local VM is 3.12.3 — verify on 3.11 in CI-equivalent conditions where possible. |
| MCP SDK | **`mcp==1.13.0`**, optional extra `mcp` | Pinned exact version per task requirement. Kept optional so the CLI works without it. Must be confirmed against PyPI at implementation time (not verifiable during planning — see §8). |
| Import layout (source checkout vs pip install) | Flat layout: packages `aka_skills` (new, repo root) + `tools` (existing, repo root) both shipped in the wheel; `from tools import full_setup` keeps working unchanged in both layouts. Content resolved via `aka_skills/repo.py` (§5). **Do not** move `tools/` into `src/` — that would break `python -m tools.full_setup`, `install.ps1`, and every existing test import. | Minimal diff, zero breakage of existing entry points. |
| Test framework | stdlib `unittest` only | Matches the whole existing suite and CI (`python -m unittest discover -s tests -v`). No pytest. |
| Lint/type | `ruff==0.14.14`, `mypy==1.19.1` (already in `requirements-dev.txt`) | New modules must pass `ruff check` and `mypy` (run locally; CI already runs the suite but cannot be extended in this PR). |
| No new runtime deps for CLI | stdlib only (`argparse`, `json`, `pathlib`, `importlib.resources`) | Keeps `pip install .` fast and offline-friendly. |

## 7. Test plan

### New tests
| File | What it covers (each a real test, not a placeholder) |
|---|---|
| `tests/test_cli.py` | (a) `--help` exits 0 and lists `install`, `verify`, `status`, `list-skills`, `validate`, `serve`; (b) `--version` prints a version string; (c) `install` with no flags calls `full_setup.run` with `apply=False, interactive=False` and writes nothing — assert via a `tempfile` sandbox (`--codex-home`/`--skills-root` pointing at temp dirs) that no files appear; (d) `install --interactive` with mocked `input` returning `"NO"` returns `CANCELLED` and writes nothing; mocked `"YES"` performs the install into the sandbox and returns `FILES_VERIFIED`; (e) `install --apply --interactive` is rejected; (f) `install` against a pre-seeded conflicting config raises/aborts with no files written (reuse the conflict fixture pattern from `tests/test_quick_install.py`); (g) `verify` on a sandbox install returns PASS and on an empty target returns FAIL; (h) `status` returns preflight keys and exits 0 without writing; (i) `list-skills` returns all 5 skills with names/descriptions; (j) `validate visual-design` exits 0, `validate <nonexistent>` exits 1 / error result; (k) JSON mode (`--json`) output parses as JSON for `install`/`verify`/`status`. All file-touching tests use `tempfile.TemporaryDirectory` + `--codex-home`/`--skills-root` — never the real `~/.codex`. |
| `tests/test_mcp_server.py` | (a) Tool-function tests that do **not** need the SDK: `list_skills` returns 5 skills; `read_skill("visual-design")` contains its frontmatter name; `read_skill("../x")` and `read_skill("nope")` return error results; `list_design_cases` returns the 6 styles + cases; `read_design_case` round-trips one style and one case; `install_preview` returns `core_install == "PREVIEW_ONLY"` and `"writes": false`, and a `tempfile` sandbox proves no files were created; `validate_skill("visual-design")` returns `PREFLIGHT_ONLY` (or `FAILED` with findings — assert the shape, not a hard-coded verdict, so validator changes don't false-fail); `check_status` contains the 5 `dependency_status` keys. (b) Protocol smoke test, **skipped when `mcp` is not importable** (`unittest.skipUnless(importlib.util.find_spec("mcp"), …)` — required because CI installs only `requirements-workspace.txt` and workflows cannot be edited in this PR): spawn the server as a subprocess (`sys.executable -m aka_skills.mcp_server`), drive it with the SDK client (`mcp.client.stdio.stdio_client` + `mcp.client.session.ClientSession`): `initialize` → `list_tools` (assert all 7 tool names present) → `call_tool("list_skills", {})` succeeds and returns 5 skills → `call_tool("read_skill", {"name": "visual-design"})` succeeds. Kill the subprocess in `tearDown` (timeout-guarded). |

### Existing suite
- Full suite must stay green: `python -m unittest discover -s tests -v` (exit 0). No existing test file may be modified except if a test breaks solely because of an intended, documented behaviour change — in that case record the reason in the PR description and get coordinator approval first.
- `python -m compileall -q tools tests aka_skills`, `ruff check` (or `ruff check .` per existing config), `mypy` on new modules.

### Clean-venv CLI smoke test (manual, run by implementer, record output in PR)
```bash
python3 -m venv /tmp/aka-smoke && /tmp/aka-smoke/bin/python -m pip install .
/tmp/aka-smoke/bin/aka-skills --help            # exits 0, lists subcommands
/tmp/aka-smoke/bin/aka-skills --version         # prints version
/tmp/aka-smoke/bin/aka-skills status --json     # exits 0, valid JSON, no writes
/tmp/aka-smoke/bin/aka-skills install --json    # exits 0, core_install == "PREVIEW_ONLY", no writes
/tmp/aka-smoke/bin/aka-skills install --interactive --codex-home /tmp/aka-smoke/codex --skills-root /tmp/aka-smoke/skills
#   ^ type YES at the prompt; expect core_install == "FILES_VERIFIED"; re-run install → idempotent (second run exits 0, reports ALREADY_INSTALLED/upgrade path, no conflict error)
```
Also run the same smoke on Windows if a Windows machine is available (paths via `pathlib`; `install.ps1` is not used by the CLI).

### MCP protocol smoke test (manual, run by implementer, record transcript in PR)
```bash
/tmp/aka-smoke/bin/pip install '.[mcp]'
printf '%s' '' | /tmp/aka-smoke/bin/aka-skills serve   # exits cleanly on EOF, no traceback
# then with an MCP client (SDK example client or Claude Desktop/Codex config pointing at `aka-skills serve`):
#   initialize → tools/list (7 tools) → tools/call list_skills {} → tools/call read_skill {"name": "visual-design"}
#   → tools/call install_preview {} (assert PREVIEW_ONLY, and `find <sandbox> -newer <marker>` shows no writes)
```

## 8. Acceptance criteria (verifier checklist — each must be pass/fail checkable)

1. `pyproject.toml` exists at repo root; `pip install .` succeeds in a clean venv (Python 3.11+) with no network beyond PyPI, and no `setup.py`/`setup.cfg` is introduced.
2. `aka-skills --help` exits 0 and lists subcommands `install`, `verify`, `status`, `list-skills`, `validate`, `serve`.
3. `aka-skills --version` exits 0 and prints a version string matching `aka_skills.__version__`.
4. `aka-skills install` (no flags) exits 0, prints JSON with `core_install == "PREVIEW_ONLY"`, and creates/modifies no files (verified in a sandbox with `--codex-home`/`--skills-root` under `tempfile`).
5. `aka-skills install --interactive`, answering anything other than exactly `YES`, exits 0 with `core_install == "CANCELLED"` and writes nothing.
6. `aka-skills install --interactive` answering `YES` (sandbox targets) exits 0 with `core_install == "FILES_VERIFIED"`; a second identical run exits 0 (idempotent, no conflict error).
7. `aka-skills install` against a pre-seeded conflicting managed config aborts (non-zero or `CONFLICT`/`FAIL` status) and writes no files.
8. `aka-skills verify` exits 0 with `status == "PASS"` after a sandbox install, and exits 1 after the installed files are removed/tampered with.
9. `aka-skills status` exits 0, prints the 5 `dependency_status` keys (`python`, `git`, `codex_cli`, `workspace_keyring`, `workspace_oauth_client_id`), and writes nothing.
10. `aka-skills list-skills` exits 0 and lists all 5 skills (`chef-orchestrator`, `verified-change-loop`, `feature-journey-map`, `skill-evaluation-gate`, `visual-design`) with non-empty descriptions.
11. `aka-skills validate visual-design` exits 0; `aka-skills validate <nonexistent>` exits 1.
12. `python -m tools.full_setup --interactive` and `python -m tools.quick_install` still work unchanged (spot-check: preview output identical in shape to before this PR).
13. `aka-skills serve` starts an MCP server on stdio; a protocol-level smoke test completes `initialize` → `tools/list` (exactly the 7 tools in §4, no more, no fewer) → `tools/call list_skills {}` returning 5 skills → `tools/call read_skill {"name": "visual-design"}` returning content containing `name: visual-design`.
14. `tools/call install_preview {}` returns `core_install == "PREVIEW_ONLY"` and creates/modifies no files (sandbox check).
15. `tools/call read_skill {"name": "../secret"}` (and any `..`/`/` traversal) returns an error result, not file content, and does not raise.
16. `aka-skills serve` works with the SDK absent? No — it must fail with a clear message naming the `mcp` extra and a non-zero exit; while all other subcommands work with the SDK absent (verify by running the CLI smoke test in a venv without `.[mcp]`).
17. `python -m unittest discover -s tests -v` exits 0 (full existing suite green, including new `tests/test_cli.py` and `tests/test_mcp_server.py`).
18. `python -m compileall -q tools tests aka_skills`, `ruff check`, and `mypy` on new modules all pass.
19. No file under `.github/workflows/` is modified (check `git status` / `git diff --stat`); no PyPI publish step exists anywhere; no credentials/permissions files touched.
20. README documents both the existing `git clone` install flow and the new `pip install .` + `aka-skills` flow, plus an MCP `serve` section with the 7 tools listed.

## 9. Risks and open questions

1. **MCP SDK version (open question, blocks M1/M3 protocol test, not the CLI).** `mcp` is not installed on this machine and no network was available during planning, so `mcp==1.13.0` could not be verified against PyPI. Implementer must, before writing code: `pip index versions mcp` (or `pip install 'mcp==1.13.0' --dry-run`) in a scratch venv; if 1.13.0 is unavailable, pin the nearest available 1.x release, record the exact version in `pyproject.toml` + this plan + the PR description, and confirm `FastMCP` + `stdio_client`/`ClientSession` APIs exist in that version (API surface changed across 1.x; do not assume). If no 1.x is installable at all, stop the MCP part and report back — do not vendor the SDK or fetch it from an unverified source.
2. **Hatchling `force-include` correctness.** The wheel must actually contain `aka_skills/data/skills/…` etc. Verify with `unzip -l dist/*.whl` and by installing the wheel in a clean venv *outside* the checkout, then running `aka-skills list-skills` with cwd elsewhere — if content is missing, the server must error clearly (fail-closed per §5) and the packaging must be fixed before the PR is opened.
3. **Windows paths.** `root_for`/`codex_home` handling on Windows (`%USERPROFILE%\.codex`, backslashes) is existing behaviour — the CLI must pass paths through untouched and be smoke-tested on Windows if possible; at minimum, no new path string concatenation may be introduced (use `pathlib` everywhere).
4. **CI cannot be extended in this PR.** `.github/workflows/tests.yml` installs only `requirements-workspace.txt`, so the MCP protocol test will be skipped in CI (by design, `skipUnless(mcp)`). The protocol test must therefore be run and evidenced manually by the implementer (transcript in the PR). A follow-up PR (needs a token with workflow scope) should add `.[mcp]` to CI.
5. **Scope decision (resolved 2026-11-25, cristi authorized) — `visual-design` is now installed by `quick_install`.** The old note said the CLI `install` wraps `full_setup.run`, which installed only the 4 core skills, and that extending the set was a separate decision. That decision was made on 2026-11-25: `update` must cover all 5 skills, and to avoid install/update set drift, `"visual-design"` was added to `quick_install.SKILLS` (the single source of truth), so install and update both cover 5 skills. Verified at the time: `skills/visual-design` is 148K, 12 files, 0 images — well under `skill_installer.package()` limits (≤100 files, ≤2MB/file, ≤12MB total). WorkBuddy's user-level path was fixed in the same change (`USER_FILES["workbuddy"]` from `.codebuddy/*` to `.workbuddy/*`, verified against a real Windows machine); legacy `.codebuddy` installs are reported only — only the two state files are read (existence + recorded skill names); legacy skill content is never hashed, used, written, or deleted.
6. **Frontmatter parsing without YAML.** Both CLI and MCP reuse the regex-only `name:`/`description:` parse from `skill_validator`; multiline YAML descriptions will be flagged `DESCRIPTION_REVIEW` by the validator and may render truncated in `list-skills`. Acceptable for v1; do not add PyYAML as a dependency to fix it.
7. **`--workspace` not exposed in the CLI.** Deliberate (see §4). If a user runs `aka-skills install --workspace` expecting cloud setup, it must error as an unknown flag rather than silently ignoring it — argparse handles this, but the README must say workspace setup still goes through `python -m tools.full_setup --workspace`.
8. **Branch/PR hygiene.** One branch, one Draft PR, never merge (per approval). Do not push to `main`. If the implementer needs a token with workflow scope for anything, stop and escalate — do not work around it.
