"""MCP server for the AKA.CRISTI Skills repo (stdio transport only).

Exposes the repo's skills, design cases, install preview, validation and
status as 7 MCP tools (server name ``aka-skills``).

The ``mcp`` SDK is an *optional* dependency (``pip install '.[mcp]'``) and is
imported lazily inside :func:`serve` only. All tool implementations below are
plain functions testable without a running server or the SDK installed; the
FastMCP decorators in :func:`serve` are only the transport layer.

Dry-run guarantee: :func:`install_preview` never passes ``apply=True`` and
never calls ``input()`` — it only runs the preview path of
``tools.full_setup.run`` and reports ``"writes": false``.

Stdout is reserved for the MCP protocol; all diagnostics go to stderr.
"""
from __future__ import annotations

import argparse
import importlib.resources
import json
import os
import re
import sys
from pathlib import Path
from typing import Callable, Literal

from tools import full_setup, quick_install, skill_validator
from tools.skill_validator import MAX_SKILL_BYTES
from tools.universal_chef import HOSTS

SERVER_NAME = "aka-skills"
DESIGN_SKILL = "visual-design"
_STYLES_DIRNAME = "styles"
_CASES_DIRNAME = "cases"
_HEADING_RE = re.compile(r"^#\s+(.*\S)\s*$")
_FRONTMATTER_FIELD_RE = re.compile(r"^(name|description):\s*(.*)$")


# ---------------------------------------------------------------------------
# Repo-root resolution
# ---------------------------------------------------------------------------
# Canonical resolver lives in aka_skills.repo (written by the CLI implementer;
# it did not exist when this module was written). If it is importable we
# delegate to it; otherwise the local fallback below implements the same
# documented order (PLAN.md §5): explicit root / env AKA_SKILLS_REPO_ROOT ->
# checkout discovery -> importlib.resources bundled data. Fail closed.
# ---------------------------------------------------------------------------


def _local_resolve_repo_root(explicit: str | Path | None = None) -> Path | None:
    candidates: list[Path] = []
    if explicit is not None:
        candidates.append(Path(explicit))
    env_root = os.environ.get("AKA_SKILLS_REPO_ROOT")
    if env_root:
        candidates.append(Path(env_root))
    for candidate in candidates:
        if (candidate / "skills").is_dir():
            return candidate.resolve()
        # Explicit/env roots that lack skills/ are errors, not fall-throughs.
        print(
            f"aka-skills: repo root {candidate} has no skills/ directory",
            file=sys.stderr,
        )
        return None

    current = Path.cwd()
    for _ in range(6):
        if (current / "skills").is_dir() and (current / "pyproject.toml").is_file():
            return current.resolve()
        if current.parent == current:
            break
        current = current.parent

    try:
        bundled = importlib.resources.files("aka_skills") / "data"
        if bundled.is_dir() and (bundled / "skills").is_dir():
            return Path(str(bundled)).resolve()
    except (ImportError, ModuleNotFoundError, OSError, TypeError):
        pass
    return None


def resolve_repo_root(explicit: str | Path | None = None) -> Path | None:
    """Resolve the repo root, or ``None`` when nothing resolves (fail closed).

    Delegates to ``aka_skills.repo.resolve_repo_root`` (canonical resolver,
    PLAN.md §5) when it exists; a :class:`RepoRootError` becomes ``None`` so
    tools return error results instead of raising. Falls back to the local
    implementation of the same documented order when ``repo`` is absent.
    """
    try:
        from aka_skills.repo import RepoRootError
        from aka_skills.repo import resolve_repo_root as canonical
    except ImportError:
        return _local_resolve_repo_root(explicit)
    try:
        resolved = canonical(explicit)
    except RepoRootError as exc:
        print(f"aka-skills: {exc}", file=sys.stderr)
        return None
    return Path(resolved).resolve()


_repo_parse_frontmatter: Callable[[str], dict[str, str]] | None
try:
    from aka_skills.repo import parse_skill_frontmatter as _repo_parse_frontmatter
except ImportError:  # repo.py not present yet (parallel CLI work)
    _repo_parse_frontmatter = None

_bind_tools_to_root: Callable[[str | Path], None] | None
try:
    from aka_skills.repo import bind_tools_to_root as _bind_tools_to_root
except ImportError:
    _bind_tools_to_root = None


def _bind_root(root: Path) -> None:
    """Best-effort installed-wheel fix: point tools.* at ``root``."""
    if _bind_tools_to_root is not None:
        _bind_tools_to_root(root)


def _require_root(repo_root: str | Path | None) -> Path | dict[str, object]:
    root = resolve_repo_root(repo_root)
    if root is None:
        return {
            "status": "ERROR",
            "error": "repo root not found (set AKA_SKILLS_REPO_ROOT or --repo-root)",
        }
    return root


def _error(message: str) -> dict[str, object]:
    return {"status": "ERROR", "error": message}


def _bad_name(name: object) -> bool:
    return (
        not isinstance(name, str)
        or not name
        or ".." in name
        or "/" in name
        or "\\" in name
    )


def _parse_frontmatter(text: str) -> dict[str, str]:
    """Parse ``name:``/``description:`` frontmatter, regex-only (no YAML)."""
    if _repo_parse_frontmatter is not None:
        return _repo_parse_frontmatter(text)
    lines = text.splitlines()
    fields: dict[str, str] = {}
    if not lines or lines[0].strip() != "---":
        return fields
    try:
        closing = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    except StopIteration:
        return fields
    for line in lines[1:closing]:
        match = _FRONTMATTER_FIELD_RE.match(line)
        if match:
            fields[match.group(1)] = match.group(2).strip().strip("'\"")
    return fields


def _read_capped(path: Path) -> str | dict[str, object]:
    """Read a markdown file capped at MAX_SKILL_BYTES, or an error result."""
    try:
        if path.stat().st_size > MAX_SKILL_BYTES:
            return _error(f"file exceeds the {MAX_SKILL_BYTES}-byte read limit: {path.name}")
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        return _error(f"cannot read {path.name}: {type(exc).__name__}")


def _first_heading(text: str) -> str:
    for line in text.splitlines():
        match = _HEADING_RE.match(line)
        if match:
            return match.group(1)
    return ""


def _rel(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


# ---------------------------------------------------------------------------
# Tool implementations (plain functions; no SDK needed)
# ---------------------------------------------------------------------------


def list_skills(repo_root: str | Path | None = None) -> dict[str, object]:
    """Enumerate installable skills (native + vendored) with frontmatter.

    Delegates to ``aka_skills.repo.list_skills`` (31 installable: 6 native
    + 25 vendored; vendored interview-me is reference-only and excluded)
    and maps each entry to the MCP shape (``path`` is the SKILL.md file,
    relative to the repo root). Falls back to the legacy native-only scan
    when ``repo`` is not importable.
    """
    root = _require_root(repo_root)
    if isinstance(root, dict):
        return root
    try:
        from aka_skills.repo import list_skills as _repo_list_skills
    except ImportError:
        _repo_list_skills = None
    if _repo_list_skills is not None:
        skills: list[dict[str, str]] = []
        for item in _repo_list_skills(root):
            skill_file = Path(item["path"]) / "SKILL.md"
            skills.append(
                {
                    "name": item["name"],
                    "description": item["description"],
                    "path": _rel(root, skill_file),
                    "source": item["source"],
                }
            )
        return {"skills": skills}
    skills_dir = root / "skills"
    if not skills_dir.is_dir():
        return _error("repo root has no skills/ directory")
    for entry in sorted(skills_dir.iterdir(), key=lambda p: p.name):
        skill_file = entry / "SKILL.md"
        if not entry.is_dir() or not skill_file.is_file():
            continue
        try:
            text = skill_file.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        fields = _parse_frontmatter(text)
        skills.append(
            {
                "name": fields.get("name", entry.name),
                "description": fields.get("description", ""),
                "path": _rel(root, skill_file),
            }
        )
    return {"skills": skills}


def _resolve_skill_file(name: str, root: Path) -> Path:
    """Resolve a skill name to its SKILL.md (native first, then vendored)."""
    try:
        from aka_skills.repo import resolve_skill_dir as _resolve_dir
    except ImportError:
        _resolve_dir = None
    if _resolve_dir is not None:
        return _resolve_dir(root, name) / "SKILL.md"
    return root / "skills" / name / "SKILL.md"


def read_skill(
    name: str, repo_root: str | Path | None = None
) -> dict[str, object]:
    """Read a skill's SKILL.md (UTF-8, capped at MAX_SKILL_BYTES)."""
    if _bad_name(name):
        return _error(f"invalid skill name: {name!r}")
    root = _require_root(repo_root)
    if isinstance(root, dict):
        return root
    skill_file = _resolve_skill_file(name, root)
    if not skill_file.is_file():
        return _error(f"unknown skill: {name}")
    content = _read_capped(skill_file)
    if isinstance(content, dict):
        return content
    return {"name": name, "path": _rel(root, skill_file), "content": content}


def list_design_cases(
    kind: str | None = None, repo_root: str | Path | None = None
) -> dict[str, object]:
    """List visual-design style/case reference files (INDEX.md excluded)."""
    if kind is not None and kind not in ("style", "case"):
        return _error(f"invalid kind: {kind!r} (expected 'style' or 'case')")
    root = _require_root(repo_root)
    if isinstance(root, dict):
        return root
    refs = root / "skills" / DESIGN_SKILL / "references"
    result: dict[str, object] = {"styles": [], "cases": []}
    styles_index = refs / _STYLES_DIRNAME / "INDEX.md"
    result["styles_index"] = (
        _rel(root, styles_index) if styles_index.is_file() else None
    )

    def _list(subdir: str) -> list[dict[str, str]]:
        out: list[dict[str, str]] = []
        directory = refs / subdir
        if not directory.is_dir():
            return out
        for path in sorted(directory.glob("*.md"), key=lambda p: p.name):
            if path.name == "INDEX.md":
                continue
            try:
                title = _first_heading(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError):
                title = ""
            out.append(
                {"name": path.stem, "title": title, "path": _rel(root, path)}
            )
        return out

    if kind is None or kind == "style":
        result["styles"] = _list(_STYLES_DIRNAME)
    if kind is None or kind == "case":
        result["cases"] = _list(_CASES_DIRNAME)
    return result


def read_design_case(
    kind: str, name: str, repo_root: str | Path | None = None
) -> dict[str, object]:
    """Read one references/styles/<name>.md or references/cases/<name>.md."""
    if kind not in ("style", "case"):
        return _error(f"invalid kind: {kind!r} (expected 'style' or 'case')")
    if _bad_name(name):
        return _error(f"invalid design case name: {name!r}")
    root = _require_root(repo_root)
    if isinstance(root, dict):
        return root
    subdir = _STYLES_DIRNAME if kind == "style" else _CASES_DIRNAME
    path = root / "skills" / DESIGN_SKILL / "references" / subdir / f"{name}.md"
    if not path.is_file():
        return _error(f"unknown design case: {kind}/{name}")
    content = _read_capped(path)
    if isinstance(content, dict):
        return content
    return {
        "kind": kind,
        "name": name,
        "path": _rel(root, path),
        "content": content,
    }


def install_preview(
    host: str = "codex",
    scope: str = "project",
    project: str | None = None,
    repo_root: str | Path | None = None,
    *,
    codex_home: str | Path | None = None,
    skills_root: str | Path | None = None,
) -> dict[str, object]:
    """Dry-run install preview only. Never writes, never prompts.

    Calls ``tools.full_setup.run`` with neither ``apply`` nor ``interactive``
    (preview path) and returns its report verbatim plus ``"writes": false``.
    ``codex_home``/``skills_root`` are test-only sandbox overrides, not part
    of the MCP tool schema.
    """
    if host not in HOSTS:
        return _error(f"invalid host: {host!r}")
    if scope not in ("project", "user"):
        return _error(f"invalid scope: {scope!r} (expected 'project' or 'user')")
    root = _require_root(repo_root)
    if isinstance(root, dict):
        return root
    _bind_root(root)
    try:
        report = full_setup.run(
            host=host,
            scope=scope,
            project=project,
            codex_home=codex_home,
            skills_root=skills_root,
        )
    except Exception as exc:  # conflict / missing project / invalid target
        return {"status": "ERROR", "error": f"{type(exc).__name__}: {exc}", "writes": False}
    if not isinstance(report, dict):
        return {"status": "ERROR", "error": "unexpected install preview result", "writes": False}
    return {**report, "writes": False}


def validate_skill(
    name: str, repo_root: str | Path | None = None
) -> dict[str, object]:
    """Run the read-only skill preflight validator for one skill."""
    if _bad_name(name):
        return _error(f"invalid skill name: {name!r}")
    root = _require_root(repo_root)
    if isinstance(root, dict):
        return root
    try:
        from aka_skills.repo import resolve_skill_dir as _resolve_dir
    except ImportError:
        _resolve_dir = None
    skill_dir = (
        _resolve_dir(root, name) if _resolve_dir is not None
        else root / "skills" / name
    )
    return skill_validator.validate_skill(skill_dir)


def check_status(repo_root: str | Path | None = None) -> dict[str, object]:
    """Dependency preflight + install preview summary. Read-only."""
    root = _require_root(repo_root)
    if isinstance(root, dict):
        return root
    _bind_root(root)
    try:
        preview = quick_install.execute()
    except Exception as exc:
        preview = {"status": "ERROR", "error": f"{type(exc).__name__}: {exc}"}
    return {
        "preflight": full_setup.dependency_status(),
        "preview": preview,
        "repo_root": str(root),
    }


# ---------------------------------------------------------------------------
# MCP transport layer (FastMCP; SDK imported lazily)
# ---------------------------------------------------------------------------


def _build_server(repo_root: str | Path | None = None):
    """Build the FastMCP server. Imported here so module import needs no SDK."""
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP(SERVER_NAME)

    @mcp.tool(name="list_skills", description="List all skills in the repo (name, description, path).")
    async def list_skills_tool() -> str:
        return json.dumps(list_skills(repo_root), ensure_ascii=False)

    @mcp.tool(name="read_skill", description="Read one skill's SKILL.md. 'name' is the skill directory name, e.g. 'visual-design'.")
    async def read_skill_tool(name: str) -> str:
        return json.dumps(read_skill(name, repo_root), ensure_ascii=False)

    @mcp.tool(name="list_design_cases", description="List visual-design reference files. 'kind' filters to 'style' or 'case'; omit for both.")
    async def list_design_cases_tool(
        kind: Literal["style", "case"] | None = None,
    ) -> str:
        return json.dumps(list_design_cases(kind, repo_root), ensure_ascii=False)

    @mcp.tool(name="read_design_case", description="Read one visual-design reference file. 'kind' is 'style' or 'case'; 'name' is the file stem without '.md'.")
    async def read_design_case_tool(
        kind: Literal["style", "case"], name: str
    ) -> str:
        return json.dumps(read_design_case(kind, name, repo_root), ensure_ascii=False)

    @mcp.tool(name="install_preview", description="Dry-run install preview only; never writes to disk and never prompts. 'host' defaults to 'codex', 'scope' to 'project'.")
    async def install_preview_tool(
        host: Literal[
            "codex", "workbuddy", "claude", "gemini", "opencode", "hermes", "generic"
        ] = "codex",
        scope: Literal["project", "user"] = "project",
        project: str | None = None,
    ) -> str:
        return json.dumps(
            install_preview(host, scope, project, repo_root), ensure_ascii=False
        )

    @mcp.tool(name="validate_skill", description="Run the read-only skill preflight validator for one skill directory.")
    async def validate_skill_tool(name: str) -> str:
        return json.dumps(validate_skill(name, repo_root), ensure_ascii=False)

    @mcp.tool(name="check_status", description="Dependency preflight plus install preview summary. Read-only.")
    async def check_status_tool() -> str:
        return json.dumps(check_status(repo_root), ensure_ascii=False)

    return mcp


def serve(repo_root: str | Path | None = None) -> int:
    """Run the MCP server on stdio until the client disconnects.

    Blocks on stdio. Returns 0 on a clean shutdown, 2 when the ``mcp`` SDK
    is missing, 1 on any other server error.
    """
    try:
        mcp = _build_server(repo_root)
    except ImportError:
        print(
            "aka-skills: the MCP server needs the optional 'mcp' extra: "
            "pip install '.[mcp]'",
            file=sys.stderr,
        )
        return 2
    # Installed-wheel fix (see aka_skills.repo.bind_tools_to_root): point
    # tools.* at the resolved content root so install_preview/check_status
    # work from an installed wheel, not just a checkout.
    root = resolve_repo_root(repo_root)
    if root is not None:
        _bind_root(root)
    try:
        mcp.run(transport="stdio")
    except KeyboardInterrupt:
        return 0
    except Exception as exc:  # noqa: BLE001 - report and exit non-zero
        print(f"aka-skills: MCP server failed: {exc}", file=sys.stderr)
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    """Entry point for ``python -m aka_skills.mcp_server``."""
    parser = argparse.ArgumentParser(
        prog="aka-skills-mcp", description="AKA.CRISTI Skills MCP server (stdio)."
    )
    parser.add_argument("--repo-root", type=Path, default=None)
    args = parser.parse_args(argv)
    return serve(args.repo_root)


if __name__ == "__main__":
    raise SystemExit(main())
