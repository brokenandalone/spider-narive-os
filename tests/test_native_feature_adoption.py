"""Read-only adoption policy regressions for the one native Spider OS."""
import ast
import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "the-web/shell/native_feature_adoption.py"
spec = importlib.util.spec_from_file_location("native_feature_adoption", MODULE)
policy = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = policy
spec.loader.exec_module(policy)


class NativeFeatureAdoptionTests(unittest.TestCase):
    def test_existing_bay_only_and_unique_keys(self):
        self.assertEqual(len({idea.key for idea in policy.IDEAS}),
                         len(policy.IDEAS))
        for idea in policy.IDEAS:
            policy.validate(idea)
            self.assertTrue(idea.reuses_existing)
            self.assertTrue(idea.target)
            self.assertTrue(idea.source.startswith("https://"))

    def test_no_feature_is_installed_or_authorized(self):
        for row in policy.prioritized():
            self.assertEqual(row["stage"], "proposal_only")
            self.assertFalse(row["installation_authorized"])
            self.assertIn("owner_customizations_reconciled",
                          row["outstanding_gates"])
        report = policy.summary_text()
        self.assertIn("NO changes or installs", report)
        self.assertIn("Release remains under the existing protected", report)

    def test_fully_checked_feature_still_cannot_grant_install(self):
        idea = next(idea for idea in policy.IDEAS
                    if idea.key == "native-handoff")
        passed = (*policy.CORE_GATES, *idea.extra_gates)
        result = policy.evaluate(idea, passed)
        self.assertEqual(result["outstanding_gates"], [])
        self.assertEqual(result["stage"], "reviewed_for_release_preflight")
        self.assertFalse(result["installation_authorized"])

    def test_26_10_has_real_boot_and_backup_blockers(self):
        result = next(row for row in policy.prioritized()
                      if row["key"] == "ubuntu-2610")
        self.assertEqual(result["mode"], "release_upgrade")
        self.assertTrue({
            "sda1_boot_sync_tested", "independent_backup_proven",
            "restore_rehearsal", "upgrader_offer_confirmed",
        }.issubset(set(result["outstanding_gates"])))
        self.assertFalse(result["installation_authorized"])

    def test_plasma_68_cannot_skip_wayland_checks(self):
        result = next(row for row in policy.prioritized()
                      if row["key"] == "plasma-68")
        self.assertIn("wayland_screen_and_window_parity",
                      result["outstanding_gates"])
        self.assertIn("supported_distribution_packages",
                      result["outstanding_gates"])
        self.assertFalse(result["installation_authorized"])

    def test_app_catalog_reuses_existing_bays_and_sources(self):
        self.assertGreaterEqual(len(policy.APP_CHOICES), 20)
        keys = [choice.key for choice in policy.APP_CHOICES]
        self.assertEqual(len(keys), len(set(keys)))
        for row in policy.app_choices():
            self.assertEqual(row["visibility"], "not_audited")
            self.assertFalse(row["preferred_app_changed"])
            self.assertFalse(row["old_application_removed"])
            self.assertFalse(row["spider_app_completed"])
            self.assertGreaterEqual(len(row["required_checks"]), 8)
            self.assertTrue(row["source"].startswith("https://"))
        report = policy.app_transition_text()
        self.assertIn("No current apps uninstalled", report)
        self.assertIn("optional later removal", report)
        self.assertNotIn("apt install", report)

    def test_menu_discovery_cannot_claim_installed_or_replaced(self):
        from types import SimpleNamespace
        apps = [
            SimpleNamespace(desktop_id="org.mozilla.firefox.desktop",
                            name="Firefox"),
            SimpleNamespace(desktop_id="org.kde.krita.desktop",
                            name="Krita"),
        ]
        choices = {row["key"]: row for row in policy.app_choices(apps)}
        self.assertEqual(choices["web-research"]["visibility"], "visible_in_app_menu")
        self.assertEqual(choices["art-paint"]["visibility"], "visible_in_app_menu")
        self.assertEqual(choices["research-citations"]["visibility"], "not_seen_in_app_menu")
        self.assertEqual(choices["file-manager"]["visibility"], "not_seen_in_app_menu")
        self.assertFalse(choices["art-paint"]["preferred_app_changed"])
        self.assertFalse(choices["art-paint"]["old_application_removed"])
        self.assertIn("Menu visibility is not a functional test",
                      policy.app_transition_text(apps))
        with self.assertRaises(TypeError):
            policy.app_choices([SimpleNamespace(name=None, desktop_id=1)])

    def test_dev_bay_shows_apps_in_same_feature_button(self):
        shell = (ROOT / "the-web/shell/native_utility_bays.py").read_text()
        tree = ast.parse(shell)
        dev = next(node for node in tree.body
                   if isinstance(node, ast.ClassDef) and
                   node.name == "DevBayPanel")
        methods = {node.name for node in dev.body
                   if isinstance(node, ast.FunctionDef)}
        self.assertIn("show_adoption_priorities", methods)
        self.assertIn("native_app_transition_text(visible_apps)", shell)
        self.assertIn("discover_apps()", shell)
        self.assertEqual(shell.count("spiderNativeFeatureAdoptionButton"), 1)

    def test_plasma_68_is_a_target_not_claimed_as_installed(self):
        plan = next(row for row in policy.prioritized()
                    if row["key"] == "plasma-68")
        self.assertIn("target", plan["title"].lower())
        self.assertEqual(plan["stage"], "proposal_only")
        self.assertIn("Plasma 6.8 is a TARGET", policy.summary_text())
        self.assertFalse(plan["installation_authorized"])

    def test_26_10_best_features_remain_separate_from_distro_upgrade(self):
        keys = {idea.key: idea for idea in policy.IDEAS}
        for name in (
            "ubuntustudio-audio-2610",
            "ubuntustudio-app-selection-2610",
            "ubuntustudio-livecode-2610",
            "ubuntustudio-creative-suite-2610",
            "ubuntu-2610-system-audit",
        ):
            self.assertIn(name, keys)
            self.assertNotEqual(keys[name].mode, "release_upgrade")
            self.assertFalse(policy.evaluate(keys[name])["installation_authorized"])
        self.assertEqual(keys["ubuntu-2610"].mode, "release_upgrade")
        self.assertIn("independent_backup_proven",
                      policy.evaluate(keys["ubuntu-2610"])["outstanding_gates"])

    def test_cross_distro_patterns_reuse_existing_spider_code(self):
        keys = {idea.key: idea for idea in policy.IDEAS}
        for name in (
            "opensuse-update-batches", "opensuse-rollback-design",
            "fedora-atomic-release-principles", "nixos-declarative-inventory",
            "cosmic-native-tiling",
        ):
            with self.subTest(name=name):
                self.assertTrue(keys[name].reuses_existing)
                self.assertNotEqual(keys[name].mode, "release_upgrade")
                self.assertFalse(policy.evaluate(keys[name])["installation_authorized"])
        self.assertIn("ext4_btrfs_strategy_isolated",
                      policy.evaluate(keys["opensuse-rollback-design"])
                      ["outstanding_gates"])
        self.assertIn("wayland_screen_and_window_parity",
                      policy.evaluate(keys["cosmic-native-tiling"])
                      ["outstanding_gates"])

    def test_optional_audio_and_visual_features_require_non_disruption(self):
        ideas = {idea.key: idea for idea in policy.IDEAS}
        self.assertIn("broadcast_no_interruption",
                      policy.evaluate(ideas["ubuntustudio-audio-2610"])
                      ["outstanding_gates"])
        self.assertIn("project_roundtrip_verified",
                      policy.evaluate(ideas["ubuntustudio-creative-suite-2610"])
                      ["outstanding_gates"])
        self.assertIn("stop_revocation_verified",
                      policy.evaluate(ideas["xdg-portal-permissions"])
                      ["outstanding_gates"])

    def test_invalid_or_duplicate_release_policy_is_refused(self):
        source = policy.IDEAS[0]
        from dataclasses import replace
        with self.assertRaisesRegex(ValueError, "Duplicated"):
            policy.validate(replace(source, reuses_existing=False))
        with self.assertRaisesRegex(ValueError, "adoption mode"):
            policy.validate(replace(source, mode="mixed-apt-repositories"))
        with self.assertRaisesRegex(ValueError, "Unrecognized"):
            policy.evaluate(source, ["i_said_it_is_safe"])
        with self.assertRaisesRegex(ValueError, "Unknown idea"):
            policy.prioritized({"missing_feature": ()})
        with self.assertRaisesRegex(ValueError, "Repeated"):
            policy.validate(replace(source, extra_gates=("a", "a")))

    def test_ranked_deterministically_while_risk_matters(self):
        first = policy.prioritized()
        second = policy.prioritized()
        self.assertEqual(first, second)
        self.assertEqual(
            first, sorted(first, key=lambda row: (-row["score"], row["key"])))
        self.assertGreater(policy.score(policy.IDEAS[0]),
                           policy.score(next(idea for idea in policy.IDEAS
                                             if idea.key == "ubuntu-2610")))

    def test_embedded_in_existing_dev_bay_no_new_launcher(self):
        shell = (ROOT / "the-web/shell/native_utility_bays.py").read_text()
        tree = ast.parse(shell)
        dev = next(node for node in tree.body
                   if isinstance(node, ast.ClassDef) and
                   node.name == "DevBayPanel")
        methods = {node.name for node in dev.body
                   if isinstance(node, ast.FunctionDef)}
        self.assertIn("show_adoption_priorities", methods)
        self.assertIn("native_idea_summary()", shell)
        self.assertIn("spiderNativeFeatureAdoptionButton", shell)
        manifest = (ROOT / "system/release_batch.py").read_text()
        self.assertIn("'the-web/shell/native_feature_adoption.py'", manifest)
        self.assertNotIn("subprocess", MODULE.read_text())
        self.assertNotIn("os.system", MODULE.read_text())
        self.assertNotIn("apt install", MODULE.read_text())


if __name__ == "__main__":
    unittest.main()
