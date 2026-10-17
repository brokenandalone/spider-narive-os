"""Webbie honors local Ollama model preferences without changing installed models."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('webbie_brain_test', ROOT / 'webbie/brain/brain.py')
brain = importlib.util.module_from_spec(spec)
spec.loader.exec_module(brain)


class ModelSelectionTests(unittest.TestCase):
    def test_uses_configured_local_model(self):
        with tempfile.TemporaryDirectory() as temporary:
            config = Path(temporary) / 'default.json'
            config.write_text(json.dumps({'ollama': {'model': 'qwen3:4b'}}))
            self.assertEqual(brain.preferred_model(config), 'qwen3:4b')

    def test_fallback_for_missing_corrupt_or_unsupported_value(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'default.json'
            self.assertEqual(brain.preferred_model(path), brain.DEFAULT_MODEL)
            path.write_text('{bad data')
            self.assertEqual(brain.preferred_model(path), brain.DEFAULT_MODEL)
            for value in (None, '', 'broken model', '\nmodel', [], 3):
                path.write_text(json.dumps({'ollama': {'model': value}}))
                self.assertEqual(brain.preferred_model(path), brain.DEFAULT_MODEL)

    def test_chat_request_uses_preference_with_no_network_change(self):
        response = {'message': {'content': 'Hello Writer'}}
        with patch.object(brain, 'preferred_model', return_value='qwen3:4b'):
            with patch.object(brain.urllib.request, 'urlopen') as urlopen:
                urlopen.return_value.__enter__.return_value.read.return_value = (
                    json.dumps(response).encode('utf-8')
                )
                self.assertEqual(brain.ask_ollama('Hello', context_name='Writer'),
                                 'Hello Writer')
                request = urlopen.call_args.args[0]
                self.assertEqual(request.full_url, 'http://127.0.0.1:11434/api/chat')
                payload = json.loads(request.data)
                self.assertEqual(payload['model'], 'qwen3:4b')
                self.assertIn('Writer', payload['messages'][0]['content'])
                urlopen.assert_called_once()


if __name__ == '__main__':
    unittest.main()
