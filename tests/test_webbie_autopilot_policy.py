"""Autopilot requires one explicit grant; risky actions and loops pause."""
from pathlib import Path
import importlib.util
import unittest

SOURCE=Path(__file__).resolve().parents[1]/'webbie/actions/autopilot_policy.py'
spec=importlib.util.spec_from_file_location('webbie_auto_policy',SOURCE)
p=importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)

class AutopilotPolicyTests(unittest.TestCase):
    def setUp(self):
        self.now=[100]
        self.session=p.AutopilotPolicy(clock=lambda:self.now[0],max_steps=3)

    def begin(self):
        return self.session.begin('Navigate the Audacity project', '0x01',approved=True)

    def decide(self, step, revision):
        return self.session.decide(step,window='0x01',granted=True,revision=revision)

    def test_start_requires_click_and_blocks_risky_task(self):
        with self.assertRaises(PermissionError):
            self.session.begin('Browse project','0x01')
        with self.assertRaises(PermissionError):
            self.session.begin('Send the recording to anyone','0x01',approved=True)
        self.begin()
        self.assertTrue(self.session.active)

    def test_navigation_autoruns_clicks_require_review(self):
        r=self.begin()
        self.assertEqual(self.decide(
            {'action':'press','key':'Tab','confidence':.99,'reason':'Next field'},r),'auto')
        self.assertTrue(self.session.record_step(window='0x01',granted=True,revision=r))
        self.assertEqual(self.decide(
            {'action':'click','x':12,'y':18,'confidence':.98,'reason':'Select track'},r),'review')
        self.assertTrue(self.session.record_step(window='0x01',granted=True,revision=r))
        self.assertFalse(self.session.record_step(window='0x01',granted=True,revision=r))
        self.assertFalse(self.session.active)

    def test_high_impact_reason_low_confidence_and_repeated_steps_pause(self):
        r=self.begin()
        self.assertEqual(self.decide(
            {'action':'click','x':1,'y':2,'confidence':.99,'reason':'Delete project'},r),'pause')
        r=self.begin()
        self.assertEqual(self.decide(
            {'action':'press','key':'Tab','confidence':.45,'reason':'navigate'},r),'pause')
        r=self.begin()
        step={'action':'press','key':'Tab','confidence':.99,'reason':'next field'}
        self.assertEqual(self.decide(step,r),'auto')
        self.assertEqual(self.decide(step,r),'auto')
        self.assertEqual(self.decide(step,r),'pause')

    def test_stop_expiry_wrong_window_or_stale_worker(self):
        r=self.begin()
        self.now[0]+=121
        self.assertFalse(self.session.ready(window='0x01',granted=True,revision=r))
        r=self.begin()
        self.assertFalse(self.session.ready(window='0x02',granted=True,revision=r))
        self.session.stop()
        self.assertFalse(self.session.ready(window='0x01',granted=True,revision=r))
        r=self.begin()
        self.assertFalse(self.session.ready(window='0x01',granted=False,revision=r))
        self.assertFalse(self.session.ready(window='0x01',granted=True,revision=r-1))

    def test_done_and_uncertainty_finish(self):
        r=self.begin()
        self.assertEqual(self.decide({'action':'done','confidence':1,'reason':'finished'},r),'done')
        self.assertFalse(self.session.active)
        r=self.begin()
        self.assertEqual(self.decide({'action':'ask_user','confidence':1,'reason':'unclear'},r),'pause')

if __name__=='__main__':
    unittest.main()
