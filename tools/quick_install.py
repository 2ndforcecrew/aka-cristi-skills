"""Unified Codex install entry; read-only by default, --apply writes local files.

Installs 31 Skills: 6 native skills from ``skills/`` plus 25 vendored skills
from ``vendor/addy-agent-skills/skills/`` (Addy Osmani agent-skills, MIT,
vendored by PR #66). The vendored ``interview-me`` is reference-only
(native ``interview-me`` wins per docs/dedup-decisions.md) and is never
installed. Hooks (``vendor/.../hooks/*.sh``) are never installed or wired
by this installer. Upstream Node validator scripts are reference-only and
are not a runtime dependency of this installer.
"""
import argparse
import json
import sys
from pathlib import Path

from tools import chef_global_rules, codex_subagents, skill_installer

# Native skills shipped in skills/ (alphabetical).
NATIVE_SKILLS = (
    "chef-orchestrator",
    "feature-journey-map",
    "interview-me",
    "skill-evaluation-gate",
    "verified-change-loop",
    "visual-design",
)
# Vendored skills shipped in vendor/addy-agent-skills/skills/ (alphabetical).
# Must stay in sync with the installable set in docs/skill-index.json
# (see tests/test_quick_install.py::test_skills_match_skill_index).
# Vendored interview-me is intentionally absent: reference-only, the
# native interview-me wins (docs/dedup-decisions.md).
VENDOR_SKILLS = (
    "accessibility-engineering",
    "api-and-interface-design",
    "browser-testing-with-devtools",
    "ci-cd-and-automation",
    "code-review-and-quality",
    "code-simplification",
    "constraint-driven-development",
    "context-engineering",
    "debugging-and-error-recovery",
    "deprecation-and-migration",
    "documentation-and-adrs",
    "doubt-driven-development",
    "frontend-ui-engineering",
    "git-workflow-and-versioning",
    "idea-refine",
    "incremental-implementation",
    "observability-and-instrumentation",
    "performance-optimization",
    "planning-and-task-breakdown",
    "security-and-hardening",
    "shipping-and-launch",
    "source-driven-development",
    "spec-driven-development",
    "test-driven-development",
    "using-agent-skills",
)
SKILLS = NATIVE_SKILLS + VENDOR_SKILLS
VENDOR_DIRNAME = "addy-agent-skills"
ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates" / "AGENTS.global.md"


def skill_source(name):
    """Return the source directory of an installable skill by name.

    Native skills live in ``<ROOT>/skills/<name>``; vendored skills in
    ``<ROOT>/vendor/addy-agent-skills/skills/<name>``. Reads the current
    module-global ROOT at call time so repo.bind_tools_to_root rebinding
    (installed-wheel layout) is honoured. Raises ValueError for names
    that are not installable (including vendored interview-me).
    """
    if name in NATIVE_SKILLS:
        return ROOT / "skills" / name
    if name in VENDOR_SKILLS:
        return ROOT / "vendor" / VENDOR_DIRNAME / "skills" / name
    raise ValueError(f"skill is not installable: {name}")


def execute(*, apply=False, codex_home=None, skills_root=None):
    """安装前预检全部目标；已有冲突则不写任何文件。"""
    # Canonicalize caller-supplied sandbox locations before the installer's
    # symlink guard sees them: on macOS, temp dirs live under /var (a
    # symlink to /private/var), so every macOS temp path would otherwise be
    # refused as a "symlink path". The guard itself is untouched and still
    # refuses a symlinked target when called directly (see
    # tests/test_filesystem_security.py).
    if codex_home is not None:
        codex_home = Path(codex_home).resolve()
    if skills_root is not None:
        skills_root = Path(skills_root).resolve()
    target = "directory" if skills_root is not None else "codex"
    plans = {
        "global_rules": chef_global_rules.plan("install", TEMPLATE, codex_home),
        "agents": [codex_subagents.plan(role, codex_home) for role in codex_subagents.ROLE_NAMES],
        "skills": [
            skill_installer.inspect(skill_source(skill), target, skills_root)
            for skill in SKILLS
        ],
    }
    if plans["global_rules"]["state"] == "conflict_modified":
        raise ValueError("AGENTS.md 受管理区块有冲突，已停止，未修改文件")
    if any(x["action"] not in ("INSTALL", "UPGRADE", "ALREADY_INSTALLED") for x in plans["agents"]):
        raise ValueError("Codex Agent 文件冲突，已停止，未修改文件")
    if any(x["action"] not in ("install", "upgrade", "already_installed") for x in plans["skills"]):
        raise ValueError("Skill 文件冲突，已停止，未修改文件")
    if not apply:
        return {"status": "PREVIEW", "applied": False, "plan": plans}
    # 保留各现有安装器的备份与冲突拒绝逻辑，不运行真实 Agent。
    chef_global_rules.apply("install", TEMPLATE, codex_home, confirmed=True)
    for role in codex_subagents.ROLE_NAMES:
        codex_subagents.install(role, codex_home, apply=True)
    for skill in SKILLS:
        skill_installer.install(skill_source(skill), target, skills_root, apply=True)
    rules = chef_global_rules.apply("verify", TEMPLATE, codex_home)
    agents = [codex_subagents.verify(role, codex_home) for role in codex_subagents.ROLE_NAMES]
    skills = [skill_installer.verify(skill, target, skills_root) for skill in SKILLS]
    passed = (
        rules["state"] == "PASS"
        and all(a["integrity"] == "PASS" for a in agents)
        and all(s["integrity"] == "PASS" for s in skills)
    )
    return {
        "status": "FILES_VERIFIED" if passed else "FAIL",
        "applied": True,
        "rules": rules["state"],
        "roles": {a["role"]: a["integrity"] for a in agents},
        "skills": {s["name"]: s["integrity"] for s in skills},
        "agent_activation": "NOT_RUN",
    }


def main(argv=None):
    p = argparse.ArgumentParser(description="AKA.CRISTI CHEF 一键本地安装（默认预览）："
        "31 个 Skills（6 原生 + 25 vendored），不装 hooks")
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true", help="明确同意安装到当前用户")
    mode.add_argument("--interactive", action="store_true", help="先预览所有变更，再询问是否安装")
    p.add_argument("--codex-home", type=Path, help="可选：独立 Codex 测试目录")
    p.add_argument("--skills-root", type=Path, help="可选：独立 Skills 测试目录")
    args = p.parse_args(argv)
    try:
        if args.interactive:
            preview = execute(codex_home=args.codex_home, skills_root=args.skills_root)
            print(json.dumps(preview, indent=2, ensure_ascii=True))
            print("Review the full preview. Enter INSTALL to apply; other input cancels.", flush=True)
            try:
                consent = input("Confirm installation [type INSTALL]: ").strip()
            except (EOFError, KeyboardInterrupt):
                consent = ""
            if consent != "INSTALL":
                print(json.dumps({"status": "CANCELLED", "applied": False}, ensure_ascii=True))
                return 0
            result = execute(apply=True, codex_home=args.codex_home, skills_root=args.skills_root)
        else:
            result = execute(apply=args.apply, codex_home=args.codex_home,
                             skills_root=args.skills_root)
        print(json.dumps(result, indent=2, ensure_ascii=True))
        return 0 if result["status"] != "FAIL" else 1
    except (OSError, ValueError, UnicodeError, KeyError) as exc:
        print(json.dumps({"status": "FAIL", "error_type": type(exc).__name__,
                          "message": "安装中止，请检查配置与文件冲突；不会强制覆盖。"},
                         ensure_ascii=True))
        return 1


if __name__ == "__main__":
    sys.exit(main())
