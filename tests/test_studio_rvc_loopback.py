"""Offline checks for a private RVC trainer, including public-bind fail-closed gating."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from studio.rvc_loopback import build_local_ui, stage_local_ui, UnsafeRVCVersion

SCRIPT = Path(__file__).resolve().parents[1] / "studio/package/voice-engine.sh"


class LoopbackTrainingTests(unittest.TestCase):
    def setUp(self):
        self.rvc = ('def serve(app):\n'
                    '    app.launch(server_name="0.0.0.0", inbrowser=False)\n'
                    '    app.queue().launch(share=True)\n')

    def test_patch_binds_main_and_share_launch_to_loopback(self):
        content = build_local_ui(self.rvc)
        self.assertIn('server_name="127.0.0.1"', content)
        self.assertIn('.launch(share=False, server_name="127.0.0.1")', content)
        self.assertNotIn('0.0.0.0', content)
        self.assertNotIn('share=True', content)
        self.assertIn('0.0.0.0', self.rvc)

    def test_unknown_rvc_version_is_blocked_not_guessed(self):
        for source in ('', self.rvc.replace('server_name="0.0.0.0"', 'server_name="::"'),
                       self.rvc.replace('.launch(share=True)', ''),
                       self.rvc + self.rvc):
            with self.assertRaises(UnsafeRVCVersion):
                build_local_ui(source)

    def test_staged_script_is_private_without_overwriting_original(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            original = root / "webui.py"
            target = root / ".spider-webui-local.py"
            original.write_text(self.rvc)
            self.assertEqual(stage_local_ui(original, target), target)
            self.assertEqual(target.stat().st_mode & 0o777, 0o600)
            self.assertEqual(original.read_text(), self.rvc)
            self.assertEqual(stage_local_ui(original, target), target)
            target.write_text("OWNER CUSTOMIZED")
            with self.assertRaises(UnsafeRVCVersion):
                stage_local_ui(original, target)
            self.assertEqual(target.read_text(), "OWNER CUSTOMIZED")

    def test_shell_has_valid_syntax_and_help_does_not_modify_host(self):
        syntax = subprocess.run(["bash", "-n", str(SCRIPT)], capture_output=True, text=True)
        self.assertEqual(syntax.returncode, 0, syntax.stderr)
        with tempfile.TemporaryDirectory() as folder:
            output = subprocess.run(["bash", str(SCRIPT), "--help"],
                                    env={"PATH": "/usr/bin:/bin", "HOME": folder},
                                    capture_output=True, text=True, timeout=10)
            self.assertEqual(output.returncode, 0, output.stderr)
            self.assertIn("LOOPBACK", output.stdout)
            self.assertFalse(list(Path(folder).iterdir()))


if __name__ == "__main__":
    unittest.main()
