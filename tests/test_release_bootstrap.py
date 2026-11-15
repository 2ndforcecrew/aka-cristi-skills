"""PowerShell security contract; Windows CI additionally parses/runs the script."""
import unittest
from pathlib import Path


class BootstrapReleaseTests(unittest.TestCase):
    def test_unverified_remote_sources_are_blocked_before_dependencies(self):
        raw = (Path(__file__).resolve().parents[1]/'install.ps1').read_text()
        self.assertIn('Remote source bootstrap is BLOCKED', raw)
        self.assertLess(raw.index('Remote source bootstrap is BLOCKED'), raw.index('$python = Get-PythonExecutable'))
        self.assertNotIn('chatgpt.com/codex/install.ps1', raw)
        self.assertNotIn('Expand-Archive', raw)
        self.assertNotIn('Invoke-WebRequest', raw)
        self.assertIn('--expected-sha256', raw)
        self.assertIn('--expected-commit', raw)


if __name__ == '__main__':
    unittest.main()
