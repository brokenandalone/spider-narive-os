"""Spider Studio and Media Center launcher source checks (no real launches)."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
src=ROOT/"webbie/agent/workspace_launchers.py"
spec=importlib.util.spec_from_file_location("workspace_launchers_test",src)
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class WorkspaceLaunchTests(unittest.TestCase):
    def test_actual_studio_launcher_preferred(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            script=root/"studio/bin/studio"
            script.parent.mkdir(parents=True)
            script.write_text("#!/bin/sh\n")
            script.chmod(0o755)
            self.assertEqual(module.workspace_command("studio",root=root),[str(script)])

    def test_studio_python_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            script=root/"studio/main.py"
            script.parent.mkdir(parents=True)
            script.write_text("print('studio')\n")
            result=module.workspace_command("studio",root=root)
            self.assertIsNotNone(result)
            self.assertEqual(result[1],str(script))
            self.assertTrue(result[0].endswith("python3"))

    def test_missing_workspace_does_not_launch(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(module.workspace_command("studio",root=tmp))
            self.assertIsNone(module.workspace_command("author",root=tmp))
            self.assertIsNone(module.workspace_command("../bin/bash",root=tmp))

    def test_media_center_takes_priority(self):
        def exists(path):
            return str(path) in {
                "/usr/local/bin/spider-media-center",
                "/usr/local/bin/spider-media-player",
            }
        result=module.workspace_command("media",exists=exists,executable=exists)
        self.assertEqual(result,["/usr/local/bin/spider-media-center"])

    def test_media_player_fallback_only_if_installed(self):
        def exists(path): return str(path)=="/usr/local/bin/spider-media-player"
        result=module.workspace_command("media",exists=exists,executable=exists)
        self.assertEqual(result,["/usr/local/bin/spider-media-player"])

    def test_nonexecutable_media_center_is_not_faked(self):
        self.assertIsNone(module.workspace_command(
            "media",exists=lambda p:True,executable=lambda p:False))

    def test_no_shell_or_user_supplied_commands(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(module.workspace_command(
                "studio; echo unsafe",root=tmp))
            self.assertIsNone(module.workspace_command(
                "",root=tmp))
            self.assertIsNone(module.workspace_command(
                None,root=tmp))

if __name__=="__main__":
    unittest.main()
