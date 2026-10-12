"""Regression tests for owner-approved public HTTPS browser navigation."""
import os
import sys
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"webbie/actions"))
from owner_safe_access import OwnerSafeAccess
from owner_authorization_store import update_policy

class WebPolicyTests(unittest.TestCase):
    def test_standing_grant_is_not_time_limited(self):
        with tempfile.TemporaryDirectory() as tmp:
            target=Path(tmp)/"private"/"authorization.json"
            update_policy("authorize",owner_clicked=True,path=target)
            access=OwnerSafeAccess()
            self.assertEqual(access.restore_permanent(
                ["audacity.desktop"],path=target),1)
            for _ in range(300):
                self.assertTrue(access.authorize(
                    "web.open","url=https://www.wikipedia.org/"))
            self.assertTrue(access.status()["permanent"])
            for invalid in (
                "url=http://www.wikipedia.org/",
                "url=https://localhost/",
                "url=https://127.0.0.1/",
                "url=https://example.internal/",
                "url=not-a-url"
            ):
                self.assertFalse(access.authorize("web.open",invalid))
            self.assertFalse(access.authorize(
                "service.write","publish website"))
            access.revoke()
            self.assertFalse(access.authorize(
                "web.open","url=https://www.wikipedia.org/"))

if __name__=="__main__":
    unittest.main()
