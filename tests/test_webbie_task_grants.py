import importlib.util
from pathlib import Path
import unittest
from unittest.mock import Mock
SOURCE = Path(__file__).resolve().parents[1] / 'webbie/actions/task_grants.py'
spec = importlib.util.spec_from_file_location('task_grants', SOURCE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class TaskGrantTests(unittest.TestCase):
    def test_denied_until_explicit_active_consent(self):
        now = [100]
        g = mod.TaskGrant(clock=lambda: now[0])
        self.assertFalse(g.authorize('app.open', 'Open Audacity'))
        g.activate('Edit the song', 'audacity.desktop', seconds=120)
        self.assertTrue(g.authorize('app.open', 'Open Audacity'))
        self.assertEqual(g.status()['remaining_actions'], mod.MAX_ACTIONS - 1)
        now[0] += 121
        self.assertFalse(g.authorize('observe.windows', 'Watch'))
        self.assertFalse(g.status()['active'])

    def test_stop_revokes_all_actions_and_owner_must_reapprove(self):
        g = mod.TaskGrant()
        g.activate('Edit a document', 'writer.desktop')
        g.stop()
        self.assertFalse(g.authorize('keyboard.key', 'Key'))
        self.assertTrue(g.status()['stopped'])
        g.activate('Fresh approved task', 'writer.desktop')
        self.assertTrue(g.authorize('keyboard.key', 'Key'))

    def test_high_risk_actions_require_separate_confirmation(self):
        approve = Mock(return_value=False)
        g = mod.TaskGrant(approve_sensitive=approve)
        g.activate('Work', 'writer.desktop')
        self.assertFalse(g.authorize('window.close.confirm', 'Close'))
        approve.return_value = True
        self.assertTrue(g.authorize('window.close.confirm', 'Close'))
        approve.assert_called()
        self.assertFalse(g.authorize('shell.execute', 'run anything'))
        self.assertFalse(g.authorize('sudo', 'privilege elevation'))

    def test_count_limit_and_input_validation(self):
        g = mod.TaskGrant()
        for kwargs in ({'seconds': 0}, {'seconds': 9999}, {'seconds': 1.2}):
            with self.assertRaises(ValueError):
                g.activate('Work', 'writer.desktop', **kwargs)
        with self.assertRaises(ValueError):
            g.activate('', 'writer.desktop')
        g.activate('Work', 'writer.desktop')
        for _ in range(mod.MAX_ACTIONS):
            self.assertTrue(g.authorize('keyboard.key', 'Tab'))
        self.assertFalse(g.authorize('keyboard.key', 'Tab'))


if __name__ == '__main__':
    unittest.main()
