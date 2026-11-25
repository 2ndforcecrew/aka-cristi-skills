"""Tests for tools.repo_update (aka-skills update).

All tests use temp git repos plus a mocked home; never touch the real
~/.codex, ~/.workbuddy or the real repo checkout. Git unavailable ->
skipTest. Style: stdlib unittest only.
"""
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[1]

from aka_skills import repo as repo_mod  # noqa: E402
from tools import quick_install, repo_update, universal_chef  # noqa: E402


def _git(*args, cwd):
    cp = subprocess.run(["git", *args], cwd=str(cwd), capture_output=True,
                        text=True, timeout=120)
    if cp.returncode != 0:
        raise AssertionError(f"git {' '.join(args)} failed: {cp.stderr}")
    return cp


def _copy_repo_content(dest):
    for name in ("skills", "templates", "agents"):
        shutil.copytree(REPO_ROOT / name, dest / name)
    shutil.copy2(REPO_ROOT / "pyproject.toml", dest / "pyproject.toml")


def _init_repo(path):
    _git("init", "-b", "main", cwd=path)
    _git("config", "user.email", "test@example.com", cwd=path)
    _git("config", "user.name", "Test", cwd=path)
    _git("add", "-A", cwd=path)
    _git("commit", "-m", "seed", cwd=path)


class RepoUpdateTests(unittest.TestCase):
    def setUp(self):
        if shutil.which("git") is None:
            self.skipTest("git unavailable")
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.addCleanup(lambda: repo_mod.bind_tools_to_root(REPO_ROOT))
        self.base = Path(self.temp.name).resolve()
        self.home = self.base / "home"
        self.home.mkdir()
        # upstream bare repo + seed clone + local clone
        self.upstream = self.base / "upstream.git"
        _git("init", "--bare", "-b", "main", str(self.upstream), cwd=self.base)
        self.seed = self.base / "seed"
        self.seed.mkdir()
        _copy_repo_content(self.seed)
        _init_repo(self.seed)
        _git("remote", "add", "origin", str(self.upstream), cwd=self.seed)
        _git("push", "-u", "origin", "main", cwd=self.seed)
        self.local = self.base / "local"
        _git("clone", str(self.upstream), str(self.local), cwd=self.base)
        _git("config", "user.email", "test@example.com", cwd=self.local)
        _git("config", "user.name", "Test", cwd=self.local)
        self.home_patch = patch("pathlib.Path.home", return_value=self.home)
        self.home_patch.start()
        self.addCleanup(self.home_patch.stop)

    def _tree(self, root):
        if not root.exists():
            return set()
        return {str(p.relative_to(root)) for p in root.rglob("*") if p.is_file()}

    def _preview(self, **kw):
        return repo_update.preview_update(repo_root=self.local, **kw)

    def _apply(self, **kw):
        return repo_update.apply_update(repo_root=self.local, **kw)

    def test_preview_zero_writes(self):
        before = self._tree(self.base)
        report = self._preview(no_pull=True)
        self.assertEqual(report["status"], "PREVIEW_ONLY")
        self.assertIn("codex:user", report["targets"])
        self.assertEqual(report["targets"]["codex:user"]["status"], "NOT_INSTALLED")
        self.assertEqual(report["repo"]["pull"], "SKIPPED_NO_PULL")
        self.assertEqual(self._tree(self.base), before)
        self.assertEqual(
            _git("status", "--porcelain", cwd=self.local).stdout, "")

    def test_apply_pull_already_up_to_date(self):
        report = self._apply()
        self.assertEqual(report["repo"]["pull"], "ALREADY_UP_TO_DATE")
        self.assertEqual(report["repo"]["before"], report["repo"]["after"])
        self.assertEqual(report["status"], "NO_CHANGE")
        self.assertEqual(repo_update.exit_for_report(report), 0)

    def test_apply_pull_updated(self):
        skill = self.seed / "skills" / "chef-orchestrator" / "SKILL.md"
        skill.write_text(skill.read_text(encoding="utf-8") + "\n<!-- upstream change -->\n",
                         encoding="utf-8")
        _git("add", "-A", cwd=self.seed)
        _git("commit", "-m", "upstream change", cwd=self.seed)
        _git("push", "origin", "main", cwd=self.seed)
        report = self._apply()
        self.assertEqual(report["repo"]["pull"], "UPDATED")
        self.assertNotEqual(report["repo"]["before"], report["repo"]["after"])
        self.assertEqual(report["status"], "NO_CHANGE")

    def test_dirty_tree_refused(self):
        skill = self.local / "skills" / "chef-orchestrator" / "SKILL.md"
        skill.write_text(skill.read_text(encoding="utf-8") + "\n<!-- local edit -->\n",
                         encoding="utf-8")
        with self.assertRaises(repo_update.UpdateError) as ctx:
            self._preview()
        self.assertIn("DIRTY_TREE", str(ctx.exception))
        # The local edit is still there; nothing synced it away.
        self.assertIn("local edit", skill.read_text(encoding="utf-8"))

    def test_non_main_branch_refused(self):
        _git("checkout", "-b", "feature", cwd=self.local)
        with self.assertRaises(repo_update.UpdateError) as ctx:
            self._preview()
        self.assertIn("NOT_ON_MAIN", str(ctx.exception))

    def test_non_git_checkout_refused_and_no_pull_allows(self):
        plain = self.base / "plain"
        plain.mkdir()
        _copy_repo_content(plain)
        with self.assertRaises(repo_update.UpdateError) as ctx:
            repo_update.preview_update(repo_root=plain)
        self.assertIn("NOT_A_GIT_CHECKOUT", str(ctx.exception))
        report = repo_update.preview_update(repo_root=plain, no_pull=True)
        self.assertEqual(report["status"], "PREVIEW_ONLY")
        self.assertEqual(report["repo"]["after"], "NO_GIT")

    def test_git_missing(self):
        with patch("tools.repo_update.git_available", return_value=False):
            with self.assertRaises(repo_update.UpdateError) as ctx:
                self._preview()
            self.assertIn("GIT_MISSING", str(ctx.exception))
            report = self._preview(no_pull=True)
        self.assertEqual(report["status"], "PREVIEW_ONLY")

    def test_no_targets_for_uninstalled_host(self):
        report = self._preview(hosts=["gemini"], no_pull=True)
        self.assertEqual(report["status"], "NO_TARGETS")
        self.assertEqual(report["targets"], {})
        self.assertEqual(repo_update.exit_for_report(report), 0)

    def test_discover_user_state_host(self):
        state_dir = self.home / ".aka-chef-install"
        state_dir.mkdir()
        (state_dir / "claude.json").write_text(
            json.dumps({"schema": 1, "files": {}, "rule": None}),
            encoding="utf-8")
        report = self._preview(no_pull=True)
        self.assertIn("claude:user", report["targets"])
        self.assertEqual(report["targets"]["claude:user"]["status"], "NOT_INSTALLED")

    def test_project_scope_discovery(self):
        project = self.base / "proj"
        state_dir = project / ".aka-chef-install"
        state_dir.mkdir(parents=True)
        (state_dir / "claude.json").write_text(
            json.dumps({"schema": 1, "files": {}, "rule": None}),
            encoding="utf-8")
        report = self._preview(no_pull=True, project=project)
        self.assertIn(f"claude:project:{project}", report["targets"])
        with self.assertRaises(repo_update.UpdateError):
            self._preview(no_pull=True, scope="project")

    def test_legacy_codebuddy_reported_and_untouched(self):
        state_dir = self.home / ".aka-chef-install"
        state_dir.mkdir()
        (state_dir / "workbuddy.json").write_text(json.dumps({
            "schema": 1,
            "files": {
                ".codebuddy/rules/aka-chef.md": "a" * 64,
                ".codebuddy/skills/chef-orchestrator/SKILL.md": "b" * 64,
            },
            "rule": None,
        }), encoding="utf-8")
        legacy_skills = self.home / ".codebuddy" / "skills"
        legacy_skills.mkdir(parents=True)
        (legacy_skills / ".aka-skill-installer").mkdir()
        (legacy_skills / ".aka-skill-installer" / "state.json").write_text(json.dumps({
            "version": 1,
            "installed": {"chef-orchestrator": {"sha256": "c" * 64, "backup": None}},
        }), encoding="utf-8")
        before = self._tree(self.home / ".codebuddy")
        report = self._preview(no_pull=True)
        legacy = report["legacy_codebuddy_install"]
        self.assertIsNotNone(legacy)
        self.assertIn("chef-orchestrator", legacy["skills"])
        self.assertEqual(len(legacy["paths"]), 2)
        # The legacy state is not install proof: no workbuddy target.
        self.assertNotIn("workbuddy:user", report["targets"])
        self.assertEqual(self._tree(self.home / ".codebuddy"), before)
        # Apply changes nothing under .codebuddy either.
        self._apply(no_pull=True)
        self.assertEqual(self._tree(self.home / ".codebuddy"), before)

    def test_workbuddy_adoption_flow(self):
        from tools import skill_installer

        wb_root = self.home / ".workbuddy" / "skills"
        for skill in quick_install.SKILLS:
            shutil.copytree(REPO_ROOT / "skills" / skill, wb_root / skill)
        before_hashes = {
            skill: skill_installer.package(wb_root / skill)["sha256"]
            for skill in quick_install.SKILLS
        }
        report = self._preview(no_pull=True)
        target = report["targets"]["workbuddy:user"]
        self.assertEqual(target["status"], "UPDATED")
        self.assertEqual(set(target["skills"].values()), {"adopted"})
        self.assertEqual(sorted(target["adopted"]), sorted(quick_install.SKILLS))
        self.assertEqual(target["restart"], "APP_RESTART_REQUIRED")
        self.assertIn("Restart the WorkBuddy app", report["next"])
        applied = self._apply(no_pull=True)
        self.assertEqual(applied["status"], "UPDATED")
        self.assertEqual(
            applied["targets"]["workbuddy:user"]["verification"], "FILES_VERIFIED")
        state = json.loads(
            (wb_root / ".aka-skill-installer" / "state.json").read_text(
                encoding="utf-8"))
        self.assertEqual(
            set(state["installed"]), set(quick_install.SKILLS))
        # Adoption rewrote state only, never the skill files.
        for skill, digest in before_hashes.items():
            self.assertEqual(
                skill_installer.package(wb_root / skill)["sha256"], digest)
        # Second run: everything already installed.
        again = self._apply(no_pull=True)
        self.assertEqual(again["status"], "NO_CHANGE")
        self.assertEqual(
            again["targets"]["workbuddy:user"]["status"], "NO_CHANGE")

    def test_workbuddy_adoption_conflict(self):
        wb_root = self.home / ".workbuddy" / "skills"
        for skill in quick_install.SKILLS:
            shutil.copytree(REPO_ROOT / "skills" / skill, wb_root / skill)
        edited = wb_root / "chef-orchestrator" / "SKILL.md"
        edited.write_text(edited.read_text(encoding="utf-8") + "\n<!-- user edit -->\n",
                          encoding="utf-8")
        report = self._preview(no_pull=True)
        target = report["targets"]["workbuddy:user"]
        self.assertEqual(target["status"], "CONFLICT")
        self.assertEqual(target["skills"]["chef-orchestrator"], "conflict_unmanaged")
        self.assertEqual(repo_update.exit_for_report(report), 1)
        applied = self._apply(no_pull=True)
        self.assertEqual(applied["targets"]["workbuddy:user"]["status"], "CONFLICT")
        self.assertIn("user edit", edited.read_text(encoding="utf-8"))
        self.assertFalse((wb_root / ".aka-skill-installer").exists())

    def test_update_4_to_5_skills(self):
        # Fixture repo at 4 skills: install workbuddy with the OLD
        # 4-skill installer (SKILLS patched for the install step only),
        # then add visual-design back, commit, and update to 5.
        old_skills = (
            "chef-orchestrator", "verified-change-loop",
            "feature-journey-map", "skill-evaluation-gate",
        )
        repo_mod.bind_tools_to_root(self.local)
        visual = self.local / "skills" / "visual-design"
        shutil.rmtree(visual)
        _git("add", "-A", cwd=self.local)
        _git("commit", "-m", "without visual-design", cwd=self.local)
        with patch.object(quick_install, "SKILLS", old_skills), \
                patch.object(universal_chef, "SKILLS", old_skills):
            result = universal_chef.install("workbuddy", apply=True, scope="user")
        self.assertEqual(result["status"], "FILES_VERIFIED")
        wb_root = self.home / ".workbuddy" / "skills"
        self.assertEqual(
            sorted(p.name for p in wb_root.iterdir()
                   if p.is_dir() and not p.name.startswith(".")),
            sorted(old_skills))
        shutil.copytree(REPO_ROOT / "skills" / "visual-design", visual)
        _git("add", "-A", cwd=self.local)
        _git("commit", "-m", "add visual-design", cwd=self.local)
        report = self._apply(no_pull=True)
        self.assertEqual(report["status"], "UPDATED")
        target = report["targets"]["workbuddy:user"]
        self.assertEqual(target["verification"], "FILES_VERIFIED")
        self.assertTrue((wb_root / "visual-design" / "SKILL.md").is_file())
        self.assertTrue((self.home / ".workbuddy" / "rules" / "aka-chef.md").is_file())
        self.assertTrue((self.home / ".workbuddy" / "agents" / "aka_research.md").is_file())

    def test_space_in_path(self):
        spaced_home = self.base / "with space" / "home"
        spaced_home.mkdir(parents=True)
        wb_root = spaced_home / ".workbuddy" / "skills"
        for skill in quick_install.SKILLS:
            shutil.copytree(REPO_ROOT / "skills" / skill, wb_root / skill)
        with patch("pathlib.Path.home", return_value=spaced_home):
            report = repo_update.apply_update(
                repo_root=self.local, no_pull=True)
        self.assertEqual(report["status"], "UPDATED")
        self.assertEqual(
            report["targets"]["workbuddy:user"]["verification"], "FILES_VERIFIED")


if __name__ == "__main__":
    unittest.main()
