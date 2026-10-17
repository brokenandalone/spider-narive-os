"""Regression tests: Ubuntu Studio 26.10 ISO chroot has no live cdrom APT source."""
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "distro/disable-chroot-media-sources.py"
BUILD = ROOT / "distro/build-iso.sh"
spec = importlib.util.spec_from_file_location("spider_chroot_sources", HELPER)
sources = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sources)

class MediaSourcesTests(unittest.TestCase):
    def test_legacy_sources_disable_only_cdrom(self):
        old = (
            "deb file:/cdrom stonking main restricted\n"
            "deb [trusted=yes] file:///cdrom/ stonking universe\n"
            "deb cdrom:[Ubuntu Studio 26.10]/ stonking main\n"
            "deb https://archive.ubuntu.com/ubuntu stonking main\n"
            "# deb file:/cdrom stonking main\n"
            "deb file:/srv/internal-repository stonking main\n"
        )
        new, count = sources.clean_list(old)
        self.assertEqual(count, 3)
        self.assertEqual(new.count("# spider-build: disabled missing installer media:"), 3)
        self.assertIn("\ndeb https://archive.ubuntu.com/ubuntu stonking main\n", new)
        self.assertIn("\ndeb file:/srv/internal-repository stonking main\n", new)
        self.assertEqual(sources.clean_list(new), (new, 0))

    def test_deb822_entire_media_stanza_is_disabled(self):
        old = (
            "Types: deb\nURIs: file:/cdrom\nSuites: stonking\nComponents: main\n\n"
            "Types: deb\nURIs: https://archive.ubuntu.com/ubuntu\nSuites: stonking\nComponents: main\n"
        )
        new, count = sources.clean_sources(old)
        self.assertEqual(count, 1)
        self.assertIn("URIs: file:/cdrom\nSuites: stonking\nComponents: main\nEnabled: no\n", new)
        self.assertIn("URIs: https://archive.ubuntu.com/ubuntu\nSuites: stonking", new)
        self.assertEqual(sources.clean_sources(new), (new, 0))

    def test_deb822_mixed_stanza_preserves_online_mirror(self):
        old = (
            "Types: deb\nURIs: file:///cdrom https://archive.ubuntu.com/ubuntu\n"
            "Suites: stonking stonking-updates\nComponents: main\nEnabled: yes\n"
        )
        new, count = sources.clean_sources(old)
        self.assertEqual(count, 1)
        self.assertIn("URIs: https://archive.ubuntu.com/ubuntu\n", new)
        self.assertIn("Enabled: yes\n", new)
        self.assertNotIn("file:///cdrom", new)

    def test_deb822_multiline_and_disabled_media_stanza(self):
        old = (
            "Types: deb\nURIs: file:/cdrom\n https://security.ubuntu.com/ubuntu\n"
            "Suites: stonking-security\nComponents: main\n\n"
            "Types: deb\nURIs: file:/cdrom\nSuites: stonking\nEnabled: no\n"
        )
        new, count = sources.clean_sources(old)
        self.assertEqual(count, 1)
        self.assertIn("URIs: https://security.ubuntu.com/ubuntu", new)
        self.assertIn("URIs: file:/cdrom\nSuites: stonking\nEnabled: no\n", new)

    def test_actual_staged_rootfs_and_idempotence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            d = root / "etc/apt/sources.list.d"
            d.mkdir(parents=True)
            (root / "etc/apt/sources.list").write_text("deb file:/cdrom stonking main\n")
            (d / "ubuntu.sources").write_text("Types: deb\nURIs: file:/cdrom\nSuites: stonking\nComponents: main\n")
            (d / "net.sources").write_text("Types: deb\nURIs: https://archive.ubuntu.com/ubuntu\nSuites: stonking\n")
            self.assertEqual(sources.process_rootfs(root, apply=False), 3)
            self.assertEqual(sources.process_rootfs(root, apply=True), 0)
            self.assertEqual(sources.process_rootfs(root, apply=False), 0)
            self.assertIn("Enabled: no", (d / "ubuntu.sources").read_text())
            self.assertIn("archive.ubuntu.com", (d / "net.sources").read_text())
            self.assertEqual(sources.process_rootfs(root, apply=True), 0)

    def test_never_target_running_root(self):
        with self.assertRaisesRegex(ValueError, "Refusing"):
            sources.process_rootfs(Path("/"), apply=True)

    def test_build_calls_helper_before_apt_update(self):
        content = BUILD.read_text()
        apply = content.index('disable-chroot-media-sources.py" --rootfs "${ROOTFS}" --apply')
        check = content.index('disable-chroot-media-sources.py" --rootfs "${ROOTFS}" --check')
        update = content.index("apt-get update")
        self.assertLess(apply, check)
        self.assertLess(check, update)

    def test_builder_shell_syntax_and_helper_compiles(self):
        subprocess.run(["bash", "-n", str(BUILD)], check=True)
        compile(HELPER.read_text(), str(HELPER), "exec")

if __name__ == "__main__":
    unittest.main()
