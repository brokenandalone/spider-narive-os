"""Native Spider OS release must NEVER bundle Media Center or BCN website."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "spider_os_only_scope", ROOT / "tools/release_inventory_guard.py"
)
scope = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(scope)


class NativeOsOnlyScope(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(scope.MANIFEST.read_text(encoding="utf-8"))

    def review(self, patch=None):
        data = copy.deepcopy(self.data)
        if patch:
            patch(data)
        return scope.review(data)

    def test_native_os_inventory_is_staged_not_installed(self):
        result = self.review()
        self.assertEqual(result["status"], "OS_SCOPE_RECORDED_NOT_INSTALLABLE")
        self.assertEqual(result["blockers"], [])
        self.assertEqual(set(self.data["repos"]), {"spider_os"})
        self.assertEqual(set(self.data["priority_pulls"]), {"spider_os"})
        self.assertEqual(set(self.data["acceptance"].values()), {False})

    def test_media_center_repository_is_not_an_os_upgrade(self):
        result = self.review(lambda d: d["repos"].update({
            "media_center": {"repository": "brokenandalone/Spider-Media-Center"}
        }))
        self.assertEqual(result["status"], "BLOCKED")

    def test_bcn_repository_is_not_an_os_upgrade(self):
        result = self.review(lambda d: d["repos"].update({
            "bcn_network": {"repository": "brokenandalone/bcn-network"}
        }))
        self.assertEqual(result["status"], "BLOCKED")

    def test_external_prs_are_never_os_release_requirements(self):
        result = self.review(lambda d: d["priority_pulls"].update({
            "media_center": [23, 22], "bcn_network": [14]
        }))
        self.assertEqual(result["status"], "BLOCKED")

    def test_external_project_approvals_cannot_gate_os(self):
        result = self.review(lambda d: d["acceptance"].update({
            "media_center_installed": False
        }))
        self.assertEqual(result["status"], "BLOCKED")
        result = self.review(lambda d: d["acceptance"].update({
            "bcn_website_deployed": False
        }))
        self.assertEqual(result["status"], "BLOCKED")

    def test_project_exclusion_is_explicit(self):
        result = self.review(lambda d: d.update(exclude_from_release=[]))
        self.assertEqual(result["status"], "BLOCKED")

    def test_native_nova_voice_still_included_within_os_source(self):
        self.assertEqual(self.data["repos"]["spider_os"]["special"]["nova_voice_merged_to_main_pr"], 102)
        result = self.review(lambda d: d["repos"]["spider_os"]["special"].update({
            "nova_voice_merged_to_main_pr": None
        }))
        self.assertEqual(result["status"], "BLOCKED")

    def test_cannot_accidentally_mark_unreviewed_os_install_ready(self):
        result = self.review(lambda d: d["acceptance"].update({
            "native_os_code_merge_complete": True
        }))
        self.assertEqual(result["status"], "BLOCKED")
        result = self.review(lambda d: d.update(status="INSTALL_APPROVED"))
        self.assertEqual(result["status"], "BLOCKED")


if __name__ == "__main__":
    unittest.main()
