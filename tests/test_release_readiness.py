"""Read-only release audit checks, using disposable host fixtures."""
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('release_readiness_test',ROOT/'system/release_readiness.py')
mod=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=mod
spec.loader.exec_module(mod)

class ReadinessTests(unittest.TestCase):
    def test_readonly_report_preserves_private_files_and_service_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            home=root/'home'
            installed=root/'installed'
            original=home/'Documents/Author/Originals/Book.docx'
            original.parent.mkdir(parents=True)
            original.write_bytes(b'owner-private-original-docx')
            agent=installed/'webbie/agent/webbie.py'
            agent.parent.mkdir(parents=True)
            agent.write_text('MY CUSTOM VOICE = True\n')
            shell=installed/'the-web/shell/main.py'
            shell.parent.mkdir(parents=True)
            shell.write_text('MY CUSTOM UI = True\n')
            before={str(p):p.read_bytes() for p in (original,agent,shell)}
            commands=[]
            def runner(command):
                commands.append(command)
                return 'active'
            with patch.object(mod.shutil,'which',return_value=None):
                report=mod.inspect(home=home,install=installed,
                                   env={'XDG_SESSION_TYPE':'x11','DESKTOP_SESSION':'the-web'},
                                   runner=runner)
            self.assertTrue(report['display']['x11_eligible'])
            self.assertTrue(report['installed_sources']['webbie_agent']['present'])
            self.assertEqual(report['author_originals']['documents_tree_docx_count'],1)
            self.assertFalse(report['author_originals']['backup_verified'])
            self.assertTrue(report['one_drive']['oauth_not_attempted'])
            self.assertTrue(report['camera']['not_opened'])
            self.assertFalse(commands, 'No service or model commands without binaries')
            self.assertEqual(before,{str(p):p.read_bytes() for p in (original,agent,shell)})
            self.assertEqual(sorted(root.rglob('*')), sorted(root.rglob('*')))

    def test_wayland_is_a_release_blocker_not_a_desktop_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            with patch.object(mod.shutil,'which',return_value=None):
                result=mod.inspect(home=root,install=root/'not-installed',
                                   env={'XDG_SESSION_TYPE':'wayland'},runner=lambda _:None)
            self.assertFalse(result['display']['x11_eligible'])
            self.assertIn('X11 session not confirmed',result['manual_release_blockers'])
            self.assertTrue(any('backups' in value.lower() for value in result['manual_release_blockers']))

    def test_no_data_exfiltration_or_camera_capture_calls(self):
        source=(ROOT/'system/release_readiness.py').read_text()
        self.assertNotIn('VideoCapture(',source)
        self.assertNotIn('rclone config',source)
        self.assertNotIn('ollama pull',source)
        self.assertNotIn('systemctl restart',source)

if __name__=='__main__':
    unittest.main()
