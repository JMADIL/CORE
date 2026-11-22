"""The source layout must not change environment/database resolution with cwd."""
import json
import subprocess
import sys
import unittest
from pathlib import Path


class ConfigurationPathsTests(unittest.TestCase):
    def test_root_and_backend_commands_share_configuration_paths(self):
        root = Path(__file__).resolve().parents[2]
        command = [sys.executable, "-c", (
            "import json; from core.config import REPOSITORY_ROOT, settings; "
            "print(json.dumps([str(REPOSITORY_ROOT), settings.DATABASE_PATH]))"
        )]
        from_root = json.loads(subprocess.check_output(command, cwd=root, text=True))
        from_backend = json.loads(subprocess.check_output(command, cwd=root / "backend", text=True))
        self.assertEqual(from_root, from_backend)
        self.assertEqual(from_root[0], str(root))


if __name__ == "__main__":
    unittest.main()
