"""Jarvis direct website and web search routing, no browser launches."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import tempfile
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
p = ROOT / "webbie/agent/browser_routes.py"
spec = importlib.util.spec_from_file_location("jarvis_browser_tests", p)
m = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = m
spec.loader.exec_module(m)


class BrowserRoutesTests(unittest.TestCase):
    def test_web_commands(self):
        examples = {
            "Webbie open youtube": "https://www.youtube.com/",
            "Hey Webby, go to github": "https://github.com/",
            "open google.com": "https://google.com/",
            "please open website snhu.edu": "https://snhu.edu/",
            "Webbie open tab for github.com": "https://github.com/",
            "navigate to https://www.wikipedia.org/wiki/Spider": "https://www.wikipedia.org/wiki/Spider",
            "show me website www.youtube.com": "https://www.youtube.com/",
        }
        for command, wanted in examples.items():
            with self.subTest(command=command):
                result = m.parse_browser_command(command)
                self.assertIsNotNone(result)
                self.assertEqual(result.url, wanted)

    def test_web_search_is_urlencoded(self):
        result = m.parse_browser_command("Webbie search the web for guitar + piano")
        self.assertEqual(result.url, "https://www.google.com/search?q=guitar+%2B+piano")
        self.assertEqual(result.kind, "search")

    def test_unrelated_desktop_actions_not_website_requests(self):
        for command in (
            "open terminal", "open Firefox", "launch studio", "play a song",
            "close all my windows", "delete everything", "what do you see",
            "what is on my screen", "Webbie open Audacity",
        ):
            with self.subTest(command=command):
                self.assertIsNone(m.parse_browser_command(command))

    def test_bad_schemes_ip_private_and_credentials_denied(self):
        samples = (
            "http://example.com", "file:///etc/passwd",
            "javascript:alert(1)", "https://user:password@example.com",
            "http://localhost:8080", "https://127.0.0.1",
            "https://192.168.1.1", "https://host.local",
            "https://intranet.internal", "https://example.com:8080",
            "https://[::1]", "https://evil.example",
            "https://example.com\\foo",
        )
        for value in samples:
            with self.subTest(value=value), self.assertRaises(ValueError):
                m.canonical_url(value)

    def test_explicit_invalid_url_is_blocked_not_executed(self):
        result = m.parse_browser_command("open http://example.com")
        self.assertEqual(result.kind, "blocked")
        self.assertEqual(result.url, "")

    def test_spaces_or_commands_cannot_be_interpreted_as_urls(self):
        for example in ("https://example.com ; rm -rf /", "some page with spaces",
                        "https://example.com\nnew instruction"):
            with self.subTest(example=example):
                self.assertIsNone(m.parse_browser_command("open " + example)
                                  if " " in example else None)

    def test_too_long_refused(self):
        self.assertIsNone(m.parse_browser_command("open " + "a" * 2000))
        with self.assertRaises(ValueError):
            m.canonical_url("www.example.com/" + "a" * 3000)

    def test_xdg_browser_category_not_lookalike_names(self):
        with tempfile.TemporaryDirectory() as folder:
            name = Path(folder) / "browser.desktop"
            name.write_text("[Desktop Entry]\nName=Fake browser\nCategories=Office;\n")
            app = SimpleNamespace(path=name)
            self.assertFalse(m.is_browser_app(app))
            name.write_text("[Desktop Entry]\nName=Firefox\nCategories=Network;WebBrowser;\n")
            self.assertTrue(m.is_browser_app(app))


if __name__ == "__main__":
    unittest.main()
