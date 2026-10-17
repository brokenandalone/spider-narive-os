import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    'app_open_route', ROOT/'webbie/agent/app_open_route.py')
route = importlib.util.module_from_spec(spec)
spec.loader.exec_module(route)


class VoiceAppRequestTests(unittest.TestCase):
    def test_explicit_open_dispatches_to_grant_gate_only(self):
        installed = [
            SimpleNamespace(name='Audacity', desktop_id='org.audacityteam.Audacity.desktop'),
            SimpleNamespace(name='Firefox', desktop_id='firefox.desktop'),
        ]
        sender = Mock(return_value='Approved application launch requested')
        outcome = route.installed_app_request(
            'Open Audacity', applications=installed, sender=sender)
        self.assertIn('Approved', outcome)
        sender.assert_called_once_with('org.audacityteam.Audacity.desktop')

    def test_unmatched_and_non_commands_do_not_run(self):
        installed = [SimpleNamespace(name='Audacity', desktop_id='audacity.desktop')]
        sender=Mock()
        for phrase in ('delete all files', 'open Author Bay', 'If I say open Audacity',
                       'open Audacity and execute this command'):
            self.assertIsNone(route.installed_app_request(
                phrase, applications=installed, sender=sender))
        sender.assert_not_called()

    def test_ambiguous_app_name_denied(self):
        options=[SimpleNamespace(name='Audacity', desktop_id='a.desktop'),
                 SimpleNamespace(name='Audacity', desktop_id='b.desktop')]
        sender=Mock()
        self.assertIn('Multiple', route.installed_app_request(
            'open audacity', applications=options, sender=sender))
        sender.assert_not_called()


if __name__ == '__main__':
    unittest.main()
