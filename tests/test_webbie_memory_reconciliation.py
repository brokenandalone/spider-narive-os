"""Preserve installed memory behavior together with new model/workspace choices."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('reconciled_brain', ROOT / 'webbie/brain/brain.py')
brain = importlib.util.module_from_spec(spec)
spec.loader.exec_module(brain)


class MemoryReconciliationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        for key, value in {'CONVERSATION_FILE': root / 'conversation.json',
                           'LONG_TERM_MEMORY_DB': root / 'memory.db',
                           'RESEARCH_LATEST': root / 'latest.md',
                           'RESEARCH_SUMMARIES': root / 'summaries'}.items():
            patcher = patch.object(brain, key, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_remember_and_recall_work_without_model(self):
        with patch.object(brain, 'ask_ollama') as model:
            self.assertIn("I'll remember", brain.respond('remember that my project is Indigo'))
            self.assertIn('Indigo', brain.respond('what do you remember about Indigo'))
            model.assert_not_called()
        self.assertEqual(len(brain.load_conversation()), 4)

    def test_request_contains_history_relevant_memory_and_model_preference(self):
        brain.remember_turn('We were discussing Indigo', 'Tell me more.')
        brain.remember_memory('Indigo is the project name.')
        with patch.object(brain, 'preferred_model', return_value='qwen3:8b'), \
             patch.object(brain.urllib.request, 'urlopen') as request:
            request.return_value.__enter__.return_value.read.return_value = json.dumps(
                {'message': {'content': 'Indigo reply'}}).encode()
            self.assertEqual(brain.respond('Continue Indigo', context_name='Writer'), 'Indigo reply')
            payload = json.loads(request.call_args.args[0].data)
            self.assertEqual(payload['model'], 'qwen3:8b')
            self.assertFalse(payload['think'])
            self.assertEqual(payload['options']['num_predict'], 256)
            self.assertIn('Writer', payload['messages'][0]['content'])
            self.assertIn('Indigo is the project name', payload['messages'][0]['content'])
            self.assertEqual(payload['messages'][1]['content'], 'We were discussing Indigo')
        self.assertEqual(brain.load_conversation()[-1]['content'], 'Indigo reply')

    def test_history_is_bounded_private_and_recovers_from_corruption(self):
        for number in range(15):
            brain.remember_turn(str(number), 'Reply')
        self.assertEqual(len(brain.load_conversation()), 16)
        self.assertEqual(brain.CONVERSATION_FILE.stat().st_mode & 0o777, 0o600)
        brain.CONVERSATION_FILE.write_text('{bad')
        self.assertEqual(brain.load_conversation(), [])
        brain.remember_turn('Recovery', 'Works')
        self.assertEqual(len(brain.load_conversation()), 2)

    def test_preexisting_permissive_history_is_replaced_privately(self):
        # This uses a disposable file and never reads the owner's history.
        brain.CONVERSATION_FILE.parent.mkdir(parents=True, exist_ok=True)
        brain.CONVERSATION_FILE.write_text('[]', encoding='utf-8')
        brain.CONVERSATION_FILE.chmod(0o666)
        brain.remember_turn('Example', 'Private reply')
        self.assertEqual(brain.CONVERSATION_FILE.stat().st_mode & 0o777, 0o600)
        self.assertEqual(len(brain.load_conversation()), 2)

    def test_unavailable_memory_does_not_claim_saved(self):
        with patch.object(brain, 'LONG_TERM_MEMORY_DB', Path(self.temp.name) / 'missing/db'):
            self.assertIn("couldn't access", brain.respond('remember that Indigo is a project'))

    def test_research_history_is_local_without_inventing_findings(self):
        brain.RESEARCH_LATEST.write_text('**Topic:** Indigo\nDraft report')
        with patch.object(brain, 'ask_ollama') as model:
            self.assertIn('Indigo', brain.respond('latest research'))
            model.assert_not_called()

    def test_automatic_memory_excludes_credentials(self):
        self.assertFalse(brain.should_auto_remember('From now on my password is sample-only'))


if __name__ == '__main__':
    unittest.main()
