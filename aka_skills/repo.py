"""Repo-root / content resolution shared by the CLI and the MCP server.

Resolution order (PLAN.md §5) — first match wins, fail closed:

1. Explicit ``--repo-root`` argument, then the ``AKA_SKILLS_REPO_ROOT``
   environment variable. Either must contain a ``skills/`` directory,
   otherwise it is an error (never silently fall through to a guess).
2. Checkout discovery: walk up from ``Path.cwd()`` (at most 6 levels) for a
   directory containing both ``skills/`` and ``pyproject.toml``.
3. Bundled data: ``importlib.resources`` ``aka_skills/data`` — populated at
   build time by the hatchling ``force-include`` rules in ``pyproject.toml``
   (``skills``/``agents``/``templates``/``shared-training``).
4. Nothing resolved → :class:`RepoRootError`. Callers must surface this as
   an error result, never guess a path.

Pure path logic; this module never writes to disk.
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

ENV_VAR = "AKA_SKILLS_REPO_ROOT"
_MAX_DISCOVERY_LEVELS = 6
# Vendored skills that are reference-only and never installed/listed as
# installable (native skill of the same name wins; docs/dedup-decisions.md).
VENDOR_REFERENCE_ONLY = frozenset({"interview-me"})
VENDOR_DIRNAME = "addy-agent-skills"

_NAME_RE = re.compile(r"^(name|description):\s*(.*)$")


class RepoRootError(ValueError):
    """No usable repo root could be resolved (see module docstring)."""


def _looks_like_repo_root(path: Path) -> bool:
    return path.is_dir() and (path / "skills").is_dir()


def resolve_repo_root(repo_root: str | Path | None = None) -> Path:
    """Resolve the repo root, following the order in the module docstring."""
    # 1. Explicit --repo-root, then the environment variable.
    for given in (repo_root, os.environ.get(ENV_VAR)):
        if given is None:
            continue
        path = Path(given).expanduser().resolve()
        if not _looks_like_repo_root(path):
            raise RepoRootError(
                f"repo root {path} does not contain a skills/ directory; "
                f"set --repo-root or {ENV_VAR} to a checkout (or pip-installed "
                "package) that does"
            )
        return path
    # 2. Checkout discovery: walk up from the working directory.
    current = Path.cwd()
    for _ in range(_MAX_DISCOVERY_LEVELS):
        if _looks_like_repo_root(current) and (current / "pyproject.toml").is_file():
            return current
        if current.parent == current:
            break
        current = current.parent
    # 3. Bundled data shipped inside the installed wheel/sdist.
    try:
        from importlib import resources

        data = resources.files("aka_skills") / "data"
        # In a normal (unpacked) install this is a pathlib.Path; anything
        # else (e.g. a zipimport Traversable) is stringified and then
        # rejected by the is_dir() check below instead of guessed at.
        candidate: Path | None = (
            data if isinstance(data, Path) else Path(str(data))
        )
    except (ModuleNotFoundError, TypeError, ValueError, OSError):
        candidate = None
    if candidate is not None and (candidate / "skills").is_dir():
        return candidate
    # 4. Fail closed.
    raise RepoRootError(
        "repo root not found: pass --repo-root, set "
        f"{ENV_VAR}, run from inside a checkout, or install the package "
        "from a build that bundles the repo content"
    )


def skills_dir(root: str | Path) -> Path:
    """Return the ``skills/`` directory under a resolved repo root."""
    return Path(root) / "skills"


def bind_tools_to_root(root: str | Path) -> None:
    """Rebind ``tools.*`` to the resolved repo root (installed-wheel fix).

    ``tools.full_setup`` / ``tools.quick_install`` / ``tools.universal_chef``
    compute their content root from ``__file__`` (parent of the ``tools/``
    package). In a source checkout that is the repo root, so everything
    works. In an installed wheel, however, ``tools/`` lives under
    ``site-packages/`` while the repo content is bundled under
    ``aka_skills/data/`` (hatchling ``force-include`` in ``pyproject.toml``),
    so ``quick_install.TEMPLATE`` (``<site-packages>/templates/...``) and
    ``ROOT / "skills" / ...`` do not exist and ``aka-skills status`` /
    ``install`` / ``verify`` fail with ``FileNotFoundError`` outside a
    checkout. This rebinds those module attributes to the resolved root
    (a no-op in a checkout, where they already agree). ``tools/`` itself
    is untouched (PLAN.md §3b); only module attributes are rebound, and
    nothing is rebound when the caller cannot resolve a root.
    """
    root = Path(root)
    try:
        from tools import full_setup, quick_install, universal_chef
    except ImportError:
        return
    full_setup.ROOT = root
    full_setup.WORKSPACE_REQ = root / "requirements-workspace.txt"
    quick_install.ROOT = root
    quick_install.TEMPLATE = root / "templates" / "AGENTS.global.md"
    universal_chef.ROOT = root
    # ``codex_subagents.source_for(name, root=None)`` resolves its content
    # root from ``__file__`` when ``root`` is None, and ``plan`` /
    # ``install`` / ``verify`` all pass ``root=None`` explicitly, so
    # rebinding a default cannot fix it. Wrap it once so ``root=None``
    # means the bound repo root's ``agents/`` directory; later binds only
    # update the directory the wrapper uses.
    from tools import codex_subagents

    existing: Any = codex_subagents.source_for
    wrapper: Any = getattr(existing, "_aka_skills_wrapper", None)
    if wrapper is None:
        original = existing

        def _bound_source_for(name, root=None, _original=original):
            if root is None:
                root = _bound_source_for._aka_agents_dir  # type: ignore[attr-defined]
            return _original(name, root)

        wrapper = _bound_source_for
        wrapper._aka_skills_wrapper = wrapper  # type: ignore[attr-defined]
        wrapper._aka_agents_dir = root / "agents"  # type: ignore[attr-defined]
        codex_subagents.source_for = wrapper
    else:
        wrapper._aka_agents_dir = root / "agents"  # type: ignore[attr-defined]


def parse_skill_frontmatter(text: str) -> dict[str, str]:
    """Parse ``name:``/``description:`` from a SKILL.md frontmatter block.

    Same regex-only approach as ``tools.skill_validator`` (no YAML lib);
    multiline YAML descriptions are returned as-is on their first line.
    """
    fields: dict[str, str] = {}
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return fields
    try:
        closing = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    except StopIteration:
        return fields
    for line in lines[1:closing]:
        match = _NAME_RE.match(line)
        if match:
            fields[match.group(1)] = match.group(2).strip().strip("'\"")
    return fields


def vendor_skills_dir(root: str | Path) -> Path:
    """Return the vendored skills directory under a resolved repo root."""
    return Path(root) / "vendor" / VENDOR_DIRNAME / "skills"


def list_skills(root: str | Path) -> list[dict[str, str]]:
    """Enumerate installable skills: native ``skills/*/SKILL.md`` plus
    vendored ``vendor/addy-agent-skills/skills/*/SKILL.md``.

    Returns ``[{"name", "description", "path", "source"}]`` sorted by name;
    ``source`` is ``"native"`` or ``"vendor"``. Reference-only vendored
    skills (see VENDOR_REFERENCE_ONLY) are excluded. Directories without
    a readable SKILL.md frontmatter are skipped.
    """
    found: list[dict[str, str]] = []
    for base, source in ((skills_dir(root), "native"),
                         (vendor_skills_dir(root), "vendor")):
        if not base.is_dir():
            continue
        for skill_dir in sorted(p for p in base.iterdir() if p.is_dir()):
            if source == "vendor" and skill_dir.name in VENDOR_REFERENCE_ONLY:
                continue
            entry = skill_dir / "SKILL.md"
            if not entry.is_file():
                continue
            try:
                fields = parse_skill_frontmatter(entry.read_text(encoding="utf-8"))
            except (OSError, UnicodeError):
                continue
            if not fields.get("name"):
                continue
            found.append(
                {
                    "name": fields["name"],
                    "description": fields.get("description", ""),
                    "path": str(skill_dir),
                    "source": source,
                }
            )
    found.sort(key=lambda item: item["name"])
    return found


def resolve_skill_dir(root: str | Path, value: str | Path) -> Path:
    """Resolve a ``validate`` argument to a skill directory.

    ``value`` may be a skill directory name (``visual-design``) or a path
    to a skill directory. Native names resolve under ``skills/`` first;
    vendored installable names resolve under
    ``vendor/addy-agent-skills/skills/``. Unknown names resolve to
    ``<root>/skills/<value>`` so the validator reports ``INVALID_ROOT``
    instead of the CLI guessing.
    """
    given = Path(value)
    if given.is_dir():
        return given
    by_name = skills_dir(root) / given.name
    if by_name.is_dir():
        return by_name
    vendor = vendor_skills_dir(root) / given.name
    if vendor.is_dir() and given.name not in VENDOR_REFERENCE_ONLY:
        return vendor
    return by_name
