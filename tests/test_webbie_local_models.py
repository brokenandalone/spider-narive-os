"""No new model download or replacement: read configured local Ollama."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock,Mock
p=Path(__file__).resolve().parents[1]/'webbie/brain/local_models.py'
spec=importlib.util.spec_from_file_location('local_models',p)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class LocalModelTests(unittest.TestCase):
    def test_expected_yesterday_installed_local_choices(self):
        self.assertEqual(m.choose_local_model('brain',names=(
            'qwen3:1.7b','qwen3:8b'),env={}), 'qwen3:8b')
        self.assertEqual(m.choose_local_model('vision',names=(
            'gemma3:4b','qwen3-vl:2b-instruct'),env={}), 'qwen3-vl:2b-instruct')

    def test_owner_config_is_authoritative_and_not_changed(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'config.json'
            original=json.dumps({'ollama':{'model':'qwen3:4b'},
                                 'vision':{'model':'gemma3:4b'}})
            path.write_text(original)
            self.assertEqual(m.choose_local_model('brain',names=(
                'qwen3:4b','qwen3:8b'),config_path=path,env={}), 'qwen3:4b')
            self.assertEqual(m.choose_local_model('vision',names=(
                'gemma3:4b','qwen3-vl:2b-instruct'),config_path=path,env={}), 'gemma3:4b')
            self.assertEqual(path.read_text(),original)

    def test_configured_model_missing_fails_closed(self):
        with self.assertRaises(RuntimeError):
            m.choose_local_model('vision',names=('gemma3:4b',),
                                 env={'WEBBIE_VISION_MODEL':'qwen3-vl:2b-instruct'})
        with self.assertRaises(RuntimeError):
            m.choose_local_model('brain',names=(),env={})
        with self.assertRaises(ValueError):
            m.choose_local_model('brain',names=(),env={'WEBBIE_BRAIN_MODEL':'./bad $(cmd)'})

    def test_installed_models_only_read_loopback(self):
        response=MagicMock()
        response.geturl.return_value=m.TAGS_URL
        response.read.return_value=json.dumps({'models':[
            {'name':'qwen3:8b'}, {'name':'qwen3-vl:2b-instruct'},
            {'name':'no space please'}]}).encode()
        ctx=MagicMock();ctx.__enter__.return_value=response
        opener=Mock(return_value=ctx)
        self.assertEqual(m.installed_models(opener=opener),
                         ('qwen3:8b','qwen3-vl:2b-instruct'))
        opener.assert_called_once_with(m.TAGS_URL,timeout=2)

if __name__=='__main__': unittest.main()
