import json
import tempfile
import unittest
from pathlib import Path

from tools.skill_installer import InstallError, inspect, install, verify, remove, rollback, main


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base=Path(self.tmp.name).resolve()
        self.src=self.base/"sources"/"sample-skill"
        self.src.mkdir(parents=True)
        self.out=self.base/"installed"
        self.write_skill("Procedure one")

    def write_skill(self,text):
        (self.src/"SKILL.md").write_text(
            "---\nname: sample-skill\ndescription: Sample safe skill\n---\n\n# Sample\n"+text+"\n",
            encoding="utf-8")

    def test_preview_no_write(self):
        result=inspect(self.src,root=self.out)
        self.assertEqual(result["action"],"install")
        self.assertFalse(self.out.exists())

    def test_install_explicit_apply_and_integrity(self):
        result=install(self.src,root=self.out,apply=False)
        self.assertFalse(result["applied"])
        self.assertFalse(self.out.exists())
        result=install(self.src,root=self.out,apply=True)
        self.assertTrue(result["applied"])
        self.assertEqual(verify("sample-skill",root=self.out)["integrity"],"PASS")
        self.assertEqual(verify("sample-skill",root=self.out)["activation"],"NOT_RUN")
        self.assertEqual(inspect(self.src,root=self.out)["action"],"already_installed")

    def test_upgrade_and_rollback(self):
        install(self.src,root=self.out,apply=True)
        original=(self.out/"sample-skill"/"SKILL.md").read_text()
        self.write_skill("Procedure two")
        self.assertEqual(inspect(self.src,root=self.out)["action"],"upgrade")
        upgraded=install(self.src,root=self.out,apply=True)
        self.assertIsNotNone(upgraded["backup"])
        self.assertNotEqual(original,(self.out/"sample-skill"/"SKILL.md").read_text())
        self.assertFalse(rollback("sample-skill",root=self.out)["applied"])
        rb=rollback("sample-skill",root=self.out,apply=True)
        self.assertTrue(rb["applied"])
        self.assertEqual(original,(self.out/"sample-skill"/"SKILL.md").read_text())

    def test_uninstall_keeps_archive(self):
        install(self.src,root=self.out,apply=True)
        self.assertTrue((self.out/"sample-skill").exists())
        self.assertFalse(remove("sample-skill",root=self.out)["applied"])
        result=remove("sample-skill",root=self.out,apply=True)
        self.assertTrue(result["applied"])
        self.assertFalse((self.out/"sample-skill").exists())
        self.assertTrue(Path(result["archive"]).is_dir())

    def test_unmanaged_skill_never_overwritten(self):
        target=self.out/"sample-skill"
        target.mkdir(parents=True)
        (target/"SKILL.md").write_text("user owned",encoding="utf-8")
        self.assertEqual(inspect(self.src,root=self.out)["action"],"conflict_unmanaged")
        with self.assertRaises(InstallError):
            install(self.src,root=self.out,apply=True)
        self.assertEqual((target/"SKILL.md").read_text(),"user owned")

    def test_external_edit_blocks_removal(self):
        install(self.src,root=self.out,apply=True)
        (self.out/"sample-skill"/"SKILL.md").write_text("external edit")
        with self.assertRaises(InstallError):
            remove("sample-skill",root=self.out,apply=True)

    def test_symlinks_in_source_rejected(self):
        other=self.base/"outside.txt"
        other.write_text("private")
        try:
            (self.src/"shortcut").symlink_to(other)
        except OSError as exc:
            if getattr(exc, "winerror", None) == 1314:
                self.skipTest("Windows symlink privilege unavailable (WinError 1314)")
            raise
        with self.assertRaises(InstallError):
            inspect(self.src,root=self.out)

    def test_invalid_metadata_rejected(self):
        (self.src/"SKILL.md").write_text("---\nname: unexpected\n"
                                        "description: okay\n---\n")
        with self.assertRaises(InstallError):
            inspect(self.src,root=self.out)

    def test_no_mutation_on_cli_preview(self):
        self.assertEqual(main(["preview",str(self.src),"--target","directory",
                               "--root",str(self.out)]),0)
        self.assertFalse(self.out.exists())

    def test_reject_unavailable_adapter(self):
        with self.assertRaises(InstallError):
            inspect(self.src,"hermes",self.out)


class PublishedSkillSmokeTests(unittest.TestCase):
    def test_all_three_public_skills_install_and_verify(self):
        published = Path(__file__).resolve().parents[1] / "skills"
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve() / "installed"
            for name in ("verified-change-loop", "feature-journey-map",
                         "skill-evaluation-gate"):
                source = published / name
                plan = inspect(source, root=root)
                self.assertEqual(plan["action"], "install")
                self.assertFalse((root / name).exists())
                installed = install(source, root=root, apply=True)
                self.assertTrue(installed["applied"])
                result = verify(name, root=root)
                self.assertEqual(result["integrity"], "PASS")
                self.assertEqual(result["activation"], "NOT_RUN")
            for name in ("verified-change-loop", "feature-journey-map",
                         "skill-evaluation-gate"):
                self.assertTrue(remove(name, root=root, apply=True)["applied"])
                self.assertFalse((root / name).exists())


if __name__=="__main__":
    unittest.main()
