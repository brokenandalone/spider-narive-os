"""Webbie's narrow Studio routes must stay read-only or explicitly launch-only."""
import ast
from pathlib import Path
import re
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from webbie.agent.launch_intents import direct_launch_intent


def load_builtin():
    source = (Path(__file__).resolve().parents[1] / 'webbie/agent/webbie.py').read_text()
    tree = ast.parse(source)
    fn = next(node for node in tree.body
              if isinstance(node, ast.FunctionDef) and node.name == 'handle_builtin')
    global_vars = {
        're': re,
        'is_capability_question': lambda _: False,
        'direct_launch_intent': direct_launch_intent,
        'set_workspace': Mock(),
        'workspace_path': lambda *items: '/usr/local/lib/spider-os/' + '/'.join(items),
        'launch': Mock(return_value=True),
        'subprocess': SimpleNamespace(run=Mock(
            return_value=SimpleNamespace(returncode=0, stdout='Studio production: 2 reviewed WAV stem(s).\n'))),
    }
    exec(compile(ast.Module(body=[fn], type_ignores=[]), '<webbie-studio-route>', 'exec'),
         global_vars)
    return global_vars['handle_builtin'], global_vars


class StudioVoiceBridgeTests(unittest.TestCase):
    def test_studio_progress_calls_bounded_read_only_script_not_model(self):
        handler, context = load_builtin()
        result = handler('Studio progress')
        self.assertIn('2 reviewed', result)
        context['subprocess'].run.assert_called_once()
        args = context['subprocess'].run.call_args
        self.assertEqual(args.args[0], [
            'python3', '/usr/local/lib/spider-os/studio/production_board.py', '--summary'])
        self.assertEqual(args.kwargs['timeout'], 4)
        self.assertTrue(args.kwargs['capture_output'])
        context['launch'].assert_not_called()

    def test_webbie_next_step_reads_only_fixed_local_guide(self):
        handler, context = load_builtin()
        context['subprocess'].run.return_value = SimpleNamespace(
            returncode=0, stdout='Review independent WAV stems.\n')
        self.assertEqual(handler('What should I do next in Studio'),
                         'Review independent WAV stems.')
        args = context['subprocess'].run.call_args
        self.assertEqual(args.args[0], [
            'python3', '/usr/local/lib/spider-os/studio/production_board.py', '--next'])
        self.assertEqual(args.kwargs['timeout'], 4)
        context['launch'].assert_not_called()

    def test_open_studio_launches_an_explicit_fixed_app_path(self):
        handler, context = load_builtin()
        self.assertEqual(handler('Open Spider Studio'), 'Opening Spider Studio.')
        context['launch'].assert_called_once_with(
            ['python3', '/usr/local/lib/spider-os/studio/main.py'])
        context['set_workspace'].assert_called_once_with('studio')
        context['subprocess'].run.assert_not_called()

    def test_a_random_song_question_does_not_run_studio_or_export(self):
        handler, context = load_builtin()
        self.assertIsNone(handler('Tell me a story about a piano'))
        context['launch'].assert_not_called()
        context['subprocess'].run.assert_not_called()

    def test_failed_read_or_launch_is_not_falsely_reported_as_success(self):
        handler, context = load_builtin()
        context['subprocess'].run.return_value = SimpleNamespace(returncode=1, stdout='')
        self.assertIn('cannot read', handler('Studio status'))
        context['launch'].return_value = False
        self.assertIn('could not open', handler('launch studio'))


if __name__ == '__main__':
    unittest.main()
