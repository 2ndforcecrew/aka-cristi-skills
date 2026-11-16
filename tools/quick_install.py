"""统一 Codex 安装入口；默认只读，--apply 才写本地文件。"""
import argparse
import json
import sys
from pathlib import Path

from tools import chef_global_rules, codex_subagents, skill_installer

SKILLS = (
    "chef-orchestrator",
    "verified-change-loop",
    "feature-journey-map",
    "skill-evaluation-gate",
)
ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates" / "AGENTS.global.md"


def execute(*, apply=False, codex_home=None, skills_root=None):
    """安装前预检全部目标；已有冲突则不写任何文件。"""
    target = "directory" if skills_root is not None else "codex"
    plans = {
        "global_rules": chef_global_rules.plan("install", TEMPLATE, codex_home),
        "agents": [codex_subagents.plan(role, codex_home) for role in codex_subagents.ROLE_NAMES],
        "skills": [
            skill_installer.inspect(ROOT / "skills" / skill, target, skills_root)
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
        skill_installer.install(ROOT / "skills" / skill, target, skills_root, apply=True)
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
    p = argparse.ArgumentParser(description="AKA.CRISTI CHEF 一键本地安装（默认预览）")
    p.add_argument("--apply", action="store_true", help="明确同意安装到当前用户")
    p.add_argument("--codex-home", type=Path, help="可选：独立 Codex 测试目录")
    p.add_argument("--skills-root", type=Path, help="可选：独立 Skills 测试目录")
    args = p.parse_args(argv)
    try:
        result = execute(apply=args.apply, codex_home=args.codex_home,
                         skills_root=args.skills_root)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0 if result["status"] != "FAIL" else 1
    except (OSError, ValueError, UnicodeError, KeyError) as exc:
        print(json.dumps({"status": "FAIL", "error_type": type(exc).__name__,
                          "message": "安装中止，请检查配置与文件冲突；不会强制覆盖。"},
                         ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(main())
