"""Jarvis owner-review navigation parser and mission state, no X11 dependencies."""
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"webbie/actions"))
from navigation_missions import parse_navigation_request, NavigationMission


class NavigationMissionTests(unittest.TestCase):
    def test_single_and_multi_step(self):
        for text, keys in {
            "scroll down": ["Page_Down"],
            "Webbie scroll up twice": ["Page_Up", "Page_Up"],
            "page down three times": ["Page_Down"] * 3,
            "scroll down 2 times then go back": ["Page_Down", "Page_Down", "alt+Left"],
            "next tab then go back": ["ctrl+Page_Down", "alt+Left"],
            "go forward and then reload page": ["alt+Right", "ctrl+r"],
            "Webby, switch to previous tab": ["ctrl+Page_Up"],
        }.items():
            with self.subTest(text=text):
                plan=parse_navigation_request(text)
                self.assertIsNotNone(plan)
                self.assertEqual([s.key for s in plan.steps],keys)

    def test_unsupported_requests_never_become_plan(self):
        for text in ("rm -rf /", "delete my documents", "type my password",
                     "search online for scripts", "scroll down then type hello",
                     "click the publish button", "turn off firewall",
                     "next tab then open github.com",
                     "scroll down 100 times", "page down 0 times",
                     "go back then " * 10, " ",
                     "click 20,40", "scroll down twice, go back"):
            with self.subTest(text=text):
                self.assertIsNone(parse_navigation_request(text))

    def test_no_arbitrary_parameter_commands(self):
        self.assertIsNone(parse_navigation_request("scroll down 999999999999 times"))
        self.assertIsNone(parse_navigation_request("next tab\nclick submit"))
        self.assertIsNone(parse_navigation_request("refresh page && delete"))

    def test_stage_needs_window_and_approval(self):
        plan=parse_navigation_request("scroll down twice")
        mission=NavigationMission(clock=lambda:100)
        with self.assertRaises(PermissionError):
            mission.stage(plan,window="0x01",selected_app_id="firefox.desktop")
        with self.assertRaises(ValueError):
            mission.stage(plan,window="INVALID",selected_app_id="firefox.desktop",approved=True)
        with self.assertRaises(ValueError):
            mission.stage(plan,window="0x1",selected_app_id="not desktop",approved=True)

    def test_browser_action_does_not_run_for_nonbrowser_app(self):
        plan=parse_navigation_request("next tab")
        mission=NavigationMission(clock=lambda:100)
        with self.assertRaises(PermissionError):
            mission.stage(plan,window="0x01",selected_app_id="kate.desktop",
                          browser=False,approved=True)

    def test_stop_revokes_remaining_steps(self):
        now=[100.0]
        mission=NavigationMission(clock=lambda:now[0])
        rev=mission.stage(parse_navigation_request("scroll down twice"),
                          window="0x01",selected_app_id="firefox.desktop",
                          approved=True)
        first=mission.next_step(granted=True,window="0x01",
                                app_id="firefox.desktop",revision=rev)
        self.assertEqual(first.key,"Page_Down")
        self.assertTrue(mission.complete(success=True,revision=rev))
        mission.stop()
        with self.assertRaises(PermissionError):
            mission.next_step(granted=True,window="0x01",
                              app_id="firefox.desktop",revision=rev)

    def test_window_switch_and_grant_expiry_revoke(self):
        for kwargs in (
            {"granted":False,"window":"0x1","app_id":"firefox.desktop"},
            {"granted":True,"window":"0x2","app_id":"firefox.desktop"},
            {"granted":True,"window":"0x1","app_id":"other.desktop"},
        ):
            with self.subTest(kwargs=kwargs):
                m=NavigationMission(clock=lambda:100)
                m.stage(parse_navigation_request("page up"),window="0x1",
                        selected_app_id="firefox.desktop",approved=True)
                with self.assertRaises(PermissionError):
                    m.next_step(**kwargs)
                self.assertIsNone(m.plan)

    def test_timeout_expires_plan(self):
        now=[100]
        m=NavigationMission(clock=lambda:now[0])
        rev=m.stage(parse_navigation_request("scroll up"),window="0x1",
                    selected_app_id="kate.desktop",approved=True)
        now[0]=221
        with self.assertRaises(PermissionError):
            m.next_step(granted=True,window="0x1",app_id="kate.desktop",revision=rev)

    def test_failure_cancels_everything(self):
        m=NavigationMission(clock=lambda:10)
        rev=m.stage(parse_navigation_request("scroll down twice"),window="0x11",
                    selected_app_id="kate.desktop",approved=True)
        self.assertFalse(m.complete(success=False,revision=rev))
        self.assertIsNone(m.plan)

    def test_success_completes_all_and_stops(self):
        m=NavigationMission(clock=lambda:10)
        rev=m.stage(parse_navigation_request("scroll up twice"),window="0x11",
                    selected_app_id="kate.desktop",approved=True)
        self.assertTrue(m.complete(success=True,revision=rev))
        self.assertFalse(m.complete(success=True,revision=rev))
        self.assertIsNone(m.plan)

    def test_stale_revision_never_executes(self):
        m=NavigationMission(clock=lambda:10)
        first=m.stage(parse_navigation_request("scroll up"),window="0x11",
                      selected_app_id="kate.desktop",approved=True)
        second=m.stage(parse_navigation_request("page down"),window="0x11",
                       selected_app_id="kate.desktop",approved=True)
        self.assertNotEqual(first,second)
        with self.assertRaises(PermissionError):
            m.next_step(granted=True,window="0x11",app_id="kate.desktop",revision=first)

    def test_plan_never_executes_x11_functions(self):
        m=NavigationMission(clock=lambda:10)
        m.stage(parse_navigation_request("scroll down"),window="0x11",
                selected_app_id="kate.desktop",approved=True)
        self.assertIn("Click Run next reviewed step",m.progress())


if __name__=="__main__":
    unittest.main()
