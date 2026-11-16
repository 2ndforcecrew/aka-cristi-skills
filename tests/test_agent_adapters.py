"""Read-only adapter discovery contract tests."""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.agent_adapters import ADAPTERS, discover, main


class AdapterDiscoveryTests(unittest.TestCase):
    def test_ids_are_unique_and_support_is_not_invented(self):
        self.assertEqual(len({adapter.id for adapter in ADAPTERS}), len(ADAPTERS))
        with tempfile.TemporaryDirectory() as directory:
            with patch("tools.agent_adapters.shutil.which", return_value="/mock/bin/agent"):
                result = discover(home=Path(directory), path="/mock/bin")
        self.assertEqual(len(result), len(ADAPTERS))
        self.assertTrue(all(not item["available_for_install"] for item in result))
        self.assertTrue(all(not item["runtime_verified"] for item in result))
        self.assertFalse(result[-1]["executable_detected"])

    def test_empty_environment_does_not_write_home(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            before = list(home.iterdir())
            with patch("tools.agent_adapters.shutil.which", return_value=None):
                result = discover(home=home, path="")
            self.assertEqual(before, list(home.iterdir()))
            self.assertTrue(all(not item["executable_detected"] for item in result))

    def test_cli_json(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(main(["list"]), 0)
        payload = json.loads(output.getvalue())
        self.assertEqual(payload["schema_version"], 1)
        self.assertIn("codex", [item["id"] for item in payload["adapters"]])


if __name__ == "__main__":
    unittest.main()
