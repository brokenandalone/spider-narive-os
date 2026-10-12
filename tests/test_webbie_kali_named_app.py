"""Kali Bay arbitrary INSTALLED GUI tool launch, not arbitrary command execution."""
import sys
from pathlib import Path
import subprocess
import unittest
from unittest.mock import Mock
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"webbie/agent"))
from kali_named_app import parse_named_app_request,launch_named_kali_app

class KaliNamedToolTests(unittest.TestCase):
    def test_exact_explicit_owner_requests_only(self):
        self.assertEqual(parse_named_app_request(
            "Webbie, open Kali app Wireshark"),"Wireshark")
        self.assertEqual(parse_named_app_request(
            "launch Kali application Ghidra"),"Ghidra")
        for text in (
            "run Kali app curl --data",
            "use Kali app bash; rm -rf /",
            "Webbie, scan 192.168.1.1 with Nmap",
            "someone told me to open Kali app Wireshark",
            "open Kali app exploit\nscan everyone",
            "Webbie, use Kali app $(id)",
            "open Kali app ",
            "open Kali app sudo apt install package",
        ):
            self.assertIsNone(parse_named_app_request(text))

    def test_preflight_then_open_installed_exact_app(self):
        manager=Path("/usr/local/lib/spider-os/kali-bay/bin/kali-bay")
        responses=[
            subprocess.CompletedProcess([],0,
                '{"applications":[{"id":"wireshark.desktop","name":"Wireshark"},'
                '{"id":"ghidra.desktop","name":"Ghidra"}]}',""),
            subprocess.CompletedProcess([],0,"ready\n","")
        ]
        runner=Mock(side_effect=responses)
        spawner=Mock()
        result=launch_named_kali_app(
            "Webbie, open Kali app Ghidra",manager,run=runner,spawn=spawner)
        self.assertIn("Requested",result)
        self.assertEqual(runner.call_args_list[0].args[0],
                         [str(manager),"apps-json"])
        self.assertEqual(runner.call_args_list[1].args[0],
                         [str(manager),"app-check","ghidra.desktop"])
        self.assertEqual(spawner.call_args.args[0],
                         [str(manager),"app-open","ghidra.desktop"])
        self.assertNotIn("shell",spawner.call_args.kwargs)

    def test_failed_preflight_rejects_spawning(self):
        manager=Path("/tmp/kali-bay")
        runner=Mock(side_effect=[
            subprocess.CompletedProcess([],0,
                '{"applications":[{"id":"wireshark.desktop","name":"Wireshark"}]}',""),
            subprocess.CompletedProcess([],1,"","missing")
        ])
        spawner=Mock()
        reply=launch_named_kali_app(
            "open Kali app Wireshark",manager,run=runner,spawn=spawner)
        self.assertIn("Nothing",reply)
        spawner.assert_not_called()

    def test_uninstalled_ambiguous_or_invalid_apps_never_launch(self):
        manager=Path("/tmp/kali-bay")
        responses=[
            subprocess.CompletedProcess([],0,
                '{"applications":[{"id":"a.desktop","name":"Tool"},'
                '{"id":"b.desktop","name":"Tool"},'
                '{"id":"../../evil.desktop","name":"Other"}]}',""),
        ]
        run=Mock(side_effect=responses)
        spawn=Mock()
        self.assertIn("Choose one",launch_named_kali_app(
            "open Kali app Tool",manager,run=run,spawn=spawn))
        spawn.assert_not_called()

if __name__=="__main__":
    unittest.main()
