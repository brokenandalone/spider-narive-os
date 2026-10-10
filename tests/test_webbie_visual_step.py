import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import MagicMock, Mock

spec=importlib.util.spec_from_file_location(
    'webbie_visual_step', Path(__file__).resolve().parents[1]/
    'webbie/actions/visual_step.py')
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class VisualStepTests(unittest.TestCase):
    def test_confident_click_within_current_window(self):
        raw={'action':'click','x':12,'y':27,'confidence':0.94,'reason':'Click tab'}
        self.assertEqual(m.validate_step(raw,80,60)['x'],12)
        for change in ({'x':80},{'y':-1},{'x':'12'},{'extra':'command'}):
            candidate=dict(raw,**change)
            with self.assertRaises(ValueError):
                m.validate_step(candidate,80,60)

    def test_sensitive_or_low_confidence_steps_are_not_executable(self):
        with self.assertRaises(ValueError):
            m.validate_step({'action':'press','key':'Return','confidence':1,'reason':'Submit'},100,100)
        with self.assertRaises(ValueError):
            m.validate_step({'action':'type','text':'sudo rm','confidence':1,'reason':'bad'},100,100)
        low={'action':'click','x':10,'y':10,'confidence':.2,'reason':'uncertain'}
        self.assertEqual(m.validate_step(low,100,100)['action'],'ask_user')

    def test_loopback_vision_returns_proposal_not_operation(self):
        response=MagicMock()
        response.geturl.return_value=m.OLLAMA_CHAT
        response.read.return_value=json.dumps({'message': {'content':json.dumps({
            'action':'press','key':'Tab','reason':'Move to next field','confidence':.95
        })}}).encode()
        context=MagicMock()
        context.__enter__.return_value=response
        opener=Mock(return_value=context)
        result=m.propose_step(b'\xff\xd8yes\xff\xd9','Navigate the editor',640,480,opener=opener)
        self.assertEqual(result['action'],'press')
        self.assertEqual(result['key'],'Tab')
        request=opener.call_args.args[0]
        self.assertEqual(request.full_url,m.OLLAMA_CHAT)
        self.assertIn('UNTRUSTED',json.loads(request.data)['messages'][0]['content'])

if __name__=='__main__':
    unittest.main()
