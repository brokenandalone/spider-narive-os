"""Kali command center: private notes, favorites, UI and strict category security."""
import importlib.util
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "kali-bay/runtime/workspace_store.py"
MANAGER = ROOT / "kali-bay/bin/kali-bay"
UI = ROOT / "kali-bay/ui/kali_bay.py"
SPEC = importlib.util.spec_from_file_location("kali_store_tested", MODULE)
store = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(store)


class LocalLabStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.mock_home = patch.object(Path, "home", return_value=self.home)
        self.mock_base = patch.object(
            store, "BASE",
            self.home / ".local/share/spider-os/kali-bay/projects",
        )
        self.mock_home.start()
        self.mock_base.start()
        self.addCleanup(self.mock_home.stop)
        self.addCleanup(self.mock_base.stop)

    def test_reads_do_not_create_directories(self):
        self.assertEqual(store.list_labs(), [])
        self.assertEqual(store.get_favorites(), set())
        self.assertFalse(store.BASE.exists())

    def test_create_save_reopen_and_private_permissions(self):
        lab = store.create_lab("Authorized LAN inventory")
        self.assertEqual(len(store.list_labs()), 1)
        saved = store.save_lab(
            lab["id"], "Scope: isolated sandbox\nObservation: ready",
            expected_revision=1,
        )
        self.assertEqual(saved["revision"], 2)
        self.assertIn("isolated sandbox", store.get_lab(lab["id"])["notes"])
        self.assertEqual(
            stat.S_IMODE((store.BASE / (lab["id"] + ".json")).stat().st_mode), 0o600
        )
        self.assertEqual(stat.S_IMODE(store.BASE.stat().st_mode), 0o700)

    def test_unsaved_conflict_and_bad_identifiers_rejected(self):
        lab = store.create_lab("Practice")
        with self.assertRaisesRegex(store.StorageError, "changed elsewhere"):
            store.save_lab(lab["id"], "oops", expected_revision=99)
        with self.assertRaises(store.StorageError):
            store.get_lab("../../home")
        with self.assertRaises(store.StorageError):
            store.create_lab("control\nname")
        with self.assertRaises(store.StorageError):
            store.save_lab(lab["id"], "x" * 40001, expected_revision=1)
        self.assertEqual(store.get_lab(lab["id"])["notes"], "")

    def test_favorites_are_explicit_bounded_and_validated(self):
        self.assertEqual(store.get_favorites(), set())
        values = store.set_favorite("builtin:wireshark", True)
        self.assertEqual(values, {"builtin:wireshark"})
        values = store.set_favorite("app:wireshark.desktop", True)
        self.assertEqual(len(values), 2)
        self.assertIn("app:wireshark.desktop", store.get_favorites())
        values = store.set_favorite("builtin:wireshark", False)
        self.assertNotIn("builtin:wireshark", values)
        for bad in ("app:../../evil.desktop", "builtin:sh", "app:evil;id.desktop"):
            with self.subTest(bad=bad), self.assertRaises(store.StorageError):
                store.set_favorite(bad, True)

    def test_symlinks_are_not_followed(self):
        store.BASE.parent.mkdir(parents=True)
        elsewhere = self.home / "elsewhere"
        elsewhere.mkdir()
        store.BASE.symlink_to(elsewhere, target_is_directory=True)
        with self.assertRaisesRegex(store.StorageError, "linked"):
            store.create_lab("Forbidden")
        self.assertFalse(list(elsewhere.iterdir()))

    def test_does_not_use_shell_or_network(self):
        source = MODULE.read_text()
        self.assertNotIn("subprocess", source)
        self.assertNotIn("requests.", source)
        self.assertNotIn("socket.", source)
        self.assertNotIn("os.system", source)


class KaliCategoryGuardTests(unittest.TestCase):
    def _run(self, category, title, running=True):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            stub = folder / "bin"
            stub.mkdir()
            events = folder / "events"
            podman = stub / "podman"
            podman.write_text("""#!/bin/sh
printf 'podman %s\\n' "$*" >> "$EVENTS"
case "$1 $2" in
 "container exists") exit 0;;
 "inspect --format") if [ "$RUNNING" = yes ]; then echo true; else echo false; fi; exit 0;;
esac
exit 88
""")
            podman.chmod(0o755)
            for cmd in ("distrobox", "konsole"):
                exe = stub / cmd
                exe.write_text(
                    '#!/bin/sh\nprintf "' + cmd +
                    ' %s\\n" "$*" >> "$EVENTS"\nexit 0\n'
                )
                exe.chmod(0o755)
            env = dict(
                os.environ, HOME=d, PATH=str(stub) + os.pathsep + os.environ["PATH"],
                EVENTS=str(events), RUNNING="yes" if running else "no",
            )
            result = subprocess.run(
                ["bash", str(MANAGER), "category", category, title],
                env=env, capture_output=True, text=True, timeout=10,
            )
            return result, events.read_text() if events.exists() else ""

    def test_rejects_injection_before_contacting_podman(self):
        for category, title in (
            ("kali-tools-detect'; touch /tmp/bad; #", "DETECT"),
            ("kali-tools-fake", "FAKE"),
            ("kali-tools-detect", "TITLE'; id; #"),
            ("kali-tools-detect", "$(id)"),
        ):
            with self.subTest(category=category, title=title):
                result, events = self._run(category, title)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(events, "")

    def test_requires_running_existing_container(self):
        result, events = self._run("kali-tools-detect", "DETECT", running=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("stopped", result.stderr)
        self.assertNotIn("distrobox", events)
        self.assertNotIn("konsole", events)

    def test_allowed_category_only_opens_explicit_shell(self):
        result, events = self._run("kali-tools-detect", "DETECT")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("konsole", events)
        self.assertIn("kali-tools-detect", events)
        self.assertNotIn("apt-get", events)
        self.assertNotIn("podman start", events)


class KaliCommandCenterQtTests(unittest.TestCase):
    def test_offscreen_private_lab_and_favorites(self):
        script = r"""
import importlib.util, sys, tempfile
from pathlib import Path
from unittest.mock import patch
from subprocess import CompletedProcess
from PyQt5.QtWidgets import QApplication, QMessageBox
root = Path(sys.argv[1])
spec = importlib.util.spec_from_file_location("kali_ui_cmd", root/"kali-bay/ui/kali_bay.py")
ui = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ui)
app = QApplication([])
with tempfile.TemporaryDirectory() as d:
    home = Path(d)
    base = home / ".local/share/spider-os/kali-bay/projects"
    with patch.object(Path, "home", return_value=home), \
         patch.object(ui.kali_store, "BASE", base), \
         patch.object(ui.subprocess, "run",
                      return_value=CompletedProcess([], 0, "missing", "")):
        window = ui.KaliBayWindow()
        assert window.security_tabs.tabText(3) == "LAB NOTES"
        assert window.findChild(ui.QWidget, "kaliLabWorkspace")
        assert window.desktop_list.count() == len(ui.DESKTOP_TOOL_MENU)
        window.toggle_selected_favorite()
        assert ui.kali_store.get_favorites() == {"builtin:wireshark"}
        window.favorite_only.setChecked(True)
        assert window.desktop_list.count() == 1
        window.favorite_only.setChecked(False)
        lab = ui.kali_store.create_lab("Sandbox 1")
        window.refresh_labs(select_id=lab["id"])
        assert window.active_lab["id"] == lab["id"]
        window.lab_editor.setPlainText("Authorized test environment.")
        window.save_active_lab()
        assert ui.kali_store.get_lab(lab["id"])["notes"] == "Authorized test environment."
        with patch.object(QMessageBox, "question", return_value=QMessageBox.Yes):
            window.prepare_lab_for_webbie()
        assert "Authorized test environment." in window.webbie_chat_entry.text()
        assert window.webbie_worker is None
        assert not window.webbie_chat_log.toPlainText()
        assert window.findChild(ui.QCheckBox, "kaliFavoritesOnly")
        window.close()
"""
        env = dict(os.environ, QT_QPA_PLATFORM="offscreen")
        result = subprocess.run(
            [sys.executable, "-c", script, str(ROOT)],
            cwd=ROOT, env=env, capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
