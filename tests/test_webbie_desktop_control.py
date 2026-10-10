"""Source-only desktop operator tests: no X11 device or user programs are touched."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    'webbie_desktop_control', ROOT / 'webbie/actions/desktop_control.py')
dc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dc)


def sample(name, ident):
    return SimpleNamespace(name=name, desktop_id=ident, workspace='studio',
                           path=Path('/usr/share/applications') / ident)


class DesktopControlTests(unittest.TestCase):
    def setUp(self):
        self.app = sample('Audacity', 'org.audacityteam.Audacity.desktop')
        self.runner = Mock(return_value=SimpleNamespace(
            stdout='0x03200009  0  4321 host-1 Audacity - Mix 1\n'))
        self.launcher = Mock()
        self.approved = Mock(return_value=True)
        self.operator = dc.DesktopOperator(
            permission=self.approved, runner=self.runner, launcher=self.launcher,
            discover=lambda: [self.app], display=':0')

    def test_default_deny_and_no_other_display(self):
        blocked = dc.DesktopOperator(
            runner=self.runner, launcher=self.launcher,
            discover=lambda: [self.app], display=':0')
        with self.assertRaises(PermissionError):
            blocked.open_app('Audacity')
        with self.assertRaises(PermissionError):
            blocked.windows()
        with self.assertRaises(PermissionError):
            blocked.type_text('hello')
        without_x = dc.DesktopOperator(permission=lambda a, p: True, display='')
        with self.assertRaises(RuntimeError):
            without_x.applications()
        self.launcher.assert_not_called()
        self.runner.assert_not_called()

    def test_launch_uses_existing_catalog_and_executable_argv(self):
        catalog = SimpleNamespace(launch_command=lambda app: ['gio', 'launch', str(app.path)])
        with patch.object(dc, 'app_catalog', return_value=catalog):
            result = self.operator.open_app('Audacity')
        self.assertEqual(result['name'], 'Audacity')
        self.assertTrue(result['launch_requested'])
        self.launcher.assert_called_once()
        args, kwargs = self.launcher.call_args
        self.assertEqual(args[0][:2], ['gio', 'launch'])
        self.assertTrue(kwargs['start_new_session'])
        self.assertNotIn('shell', kwargs)

    def test_ambiguity_and_nonexistent_apps_never_launch(self):
        self.assertEqual(dc.select_app('audacity', [self.app]), self.app)
        other = sample('Audacity', 'audacity-alternative.desktop')
        with self.assertRaises(ValueError):
            dc.select_app('Audacity', [self.app, other])
        with self.assertRaises(ValueError):
            dc.select_app('not installed', [self.app])
        with self.assertRaises(ValueError):
            dc.select_app('; rm -rf /', [self.app])
        self.launcher.assert_not_called()

    def test_window_preview_focus_and_close_are_bound_to_existing_ids(self):
        self.assertEqual(self.operator.windows()[0]['title'], 'Audacity - Mix 1')
        self.operator.focus('0x03200009')
        self.assertEqual(self.runner.call_args.args[0], ['wmctrl', '-ia', '0x03200009'])
        self.operator.close_window('0x03200009')
        self.assertEqual(self.runner.call_args.args[0], ['wmctrl', '-ic', '0x03200009'])
        self.assertIn('window.close.confirm', [x.args[0] for x in self.approved.call_args_list])
        before = self.runner.call_count
        with self.assertRaises(ValueError):
            self.operator.focus('0x00000099')
        with self.assertRaises(ValueError):
            self.operator.focus('; rm -rf /')
        self.assertEqual(self.runner.call_count, before + 1)  # one window recheck

    def test_pointer_keyboard_and_text_do_not_execute_shell(self):
        self.operator.click(150, 240)
        commands = [call.args[0] for call in self.runner.call_args_list]
        self.assertEqual(commands, [
            ['xdotool', 'mousemove', '--sync', '150', '240'],
            ['xdotool', 'click', '1'],
        ])
        self.operator.press('ctrl+z')
        self.operator.type_text('hello $(touch /tmp/unsafe) ; &&')
        command, kwargs = self.runner.call_args
        self.assertEqual(command[-1], 'hello $(touch /tmp/unsafe) ; &&')
        self.assertNotIn('shell', kwargs)
        self.assertEqual(command[0], 'xdotool')
        for bad in ('hello\nworld', 'hello\r', '\x00bad', ''):
            with self.assertRaises(ValueError):
                self.operator.type_text(bad)
        for bad in ('Return', 'ctrl+alt+Delete', 'sudo'):
            with self.assertRaises(ValueError):
                self.operator.press(bad)
        with self.assertRaises(ValueError):
            self.operator.click(-5, 3)

    def test_stop_immediately_blocks_further_ops_but_allows_new_approval(self):
        self.operator.stop()
        with self.assertRaises(InterruptedError):
            self.operator.click(2, 4)
        with self.assertRaises(InterruptedError):
            self.operator.windows()
        self.operator.begin_new_task()
        self.operator.click(2, 4)
        self.assertEqual(self.runner.call_count, 2)

    def test_permission_denial_cannot_be_bypassed_by_valid_app_or_window(self):
        self.approved.return_value = False
        with self.assertRaises(PermissionError):
            self.operator.open_app('Audacity')
        with self.assertRaises(PermissionError):
            self.operator.focus('0x03200009')
        self.runner.assert_not_called()
        self.launcher.assert_not_called()

    def test_window_parser_discards_malformed_lines(self):
        parsed = dc.parse_windows(
            'not-a-window hi\n'
            '0x09 0 11 host First title with spaces\n'
            '0x11 0 nope host Invalid pid\n')
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]['title'], 'First title with spaces')


if __name__ == '__main__':
    unittest.main()
