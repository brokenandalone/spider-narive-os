"""Commercial private beta: real package, installed desktop launcher and release blocker."""
import json
import os
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

from studio.package.build_standalone import PACKAGE,VERSION,build
from studio.package.install_for_user import install,verify
from studio.package.commercial_release_gate import assess,CHECKS
from studio.package.doctor import report


class BetaPackageTests(unittest.TestCase):
    def test_beta_archive_contains_license_disclosures_and_safe_installer(self):
        self.assertEqual(VERSION,"0.16.0-beta")
        with tempfile.TemporaryDirectory() as scratch:
            root=Path(scratch)
            artifact=build(root)
            self.assertTrue(artifact.is_file())
            self.assertIn(VERSION,artifact.name)
            unpack=root/"unpack"
            unpack.mkdir()
            with tarfile.open(artifact,"r:gz") as tar:
                members=tar.getnames()
                for wanted in ("run_spider_audio_studio.py",
                               "manifest.json","install_for_user.py",
                               "installer_gui.py","START_HERE.sh","LICENSE",
                               "BETA_README.md","THIRD_PARTY_NOTICE.md"):
                    self.assertIn(PACKAGE+"/"+wanted,members)
                tar.extractall(unpack,filter="data")
            app=unpack/PACKAGE
            data=verify(app)
            self.assertEqual(data["version"],VERSION)
            self.assertIn("studio/package/doctor.py",data["files"])
            self.assertIn("studio/package/commercial_release_gate.py",data["files"])
            self.assertIn("studio/stem_import_panel.py",data["files"])
            self.assertTrue(data["private_developer_preview"])
            self.assertIn("PyQt5", (app/"THIRD_PARTY_NOTICE.md").read_text())
            self.assertIn("extras",data)
            self.assertGreaterEqual(len(data["extras"]),6)
            self.assertTrue((app/"START_HERE.sh").is_file())
            self.assertIn("MIT", (app/"LICENSE").read_text())
            # The real installed desktop entry points to the original native app.
            home=root/"person"
            home.mkdir()
            keep=home/"original_guitar.wav"
            keep.write_bytes(b"OWNER ORIGINAL AUDIO")
            location,desktop=install(app,home=home)
            self.assertTrue(location.is_dir())
            self.assertTrue(desktop.is_file())
            self.assertIn("Exec=",desktop.read_text())
            self.assertIn(str(location/"run_spider_audio_studio.py"),
                          desktop.read_text())
            self.assertIn("Spider Audio Studio",desktop.read_text())
            self.assertEqual(keep.read_bytes(),b"OWNER ORIGINAL AUDIO")
            self.assertTrue((location/"app"/"studio"/"main.py").is_file())
            self.assertTrue((location/"LICENSE").is_file())
            self.assertTrue((location/"THIRD_PARTY_NOTICE.md").is_file())
            verified=subprocess.run(
                [sys.executable,str(location/"run_spider_audio_studio.py"),
                 "--verify-only"],text=True,capture_output=True,timeout=45)
            self.assertEqual(verified.returncode,0,verified.stderr)
            with self.assertRaises(FileExistsError):
                install(app,home=home)
            self.assertEqual(keep.read_bytes(),b"OWNER ORIGINAL AUDIO")
            self.assertFalse((home/".config"/"systemd").exists())
            self.assertFalse((home/".local"/"share"/"spider-audio-studio"/"recordings").exists())
            # Tamper blocks install, not merely a warning.
            with (app/"app"/"studio"/"main.py").open("a") as handle:
                handle.write("\n# unexpected app source edit")
            with self.assertRaises(ValueError):
                verify(app)

    def test_midcopy_failure_cleans_private_staging_and_can_retry_safely(self):
        from studio.package import install_for_user as installer
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as scratch:
            root=Path(scratch)
            archive=build(root)
            extracted=root/"unpacked"
            extracted.mkdir()
            with tarfile.open(archive,"r:gz") as tar:
                tar.extractall(extracted,filter="data")
            app=extracted/PACKAGE
            home=root/"person"
            home.mkdir()
            original=home/"original-mix.wav"
            original.write_bytes(b"PRESERVE ORIGINAL")
            original_copy=installer._copy_checked
            copied=0
            def break_during_copy(*args,**kwargs):
                nonlocal copied
                copied+=1
                if copied==5:
                    raise OSError("Simulated disk/copy failure in staging")
                return original_copy(*args,**kwargs)
            with patch.object(installer,"_copy_checked",side_effect=break_during_copy):
                with self.assertRaises(OSError):
                    installer.install(app,home=home)
            versions=home/".local"/"share"/"spider-audio-studio"/"versions"
            self.assertEqual(
                list(versions.glob(".installing-*")),[])
            self.assertFalse((versions/VERSION).exists())
            menu=home/".local"/"share"/"applications"
            self.assertFalse(list(menu.glob("com.spideros.AudioStudio.Beta-*")))
            self.assertEqual(original.read_bytes(),b"PRESERVE ORIGINAL")
            # The *same exact version* can be retried with no manual cleanup.
            installed,shortcut=installer.install(app,home=home)
            self.assertTrue(installed.is_dir())
            self.assertTrue(shortcut.is_file())
            self.assertEqual(original.read_bytes(),b"PRESERVE ORIGINAL")

    def test_modified_licensing_notice_blocks_an_installer(self):
        from studio.package.install_for_user import verify
        with tempfile.TemporaryDirectory() as scratch:
            root=Path(scratch)
            archive=build(root)
            unpack=root/"unpack"
            unpack.mkdir()
            with tarfile.open(archive,"r:gz") as tar:
                tar.extractall(unpack,filter="data")
            folder=unpack/PACKAGE
            with (folder/"THIRD_PARTY_NOTICE.md").open("a") as file:
                file.write("\nThis document was changed after packaging.")
            with self.assertRaises(ValueError):
                verify(folder)

    def test_linux_user_path_redirect_and_binary_exec_injection_rejected(self):
        from studio.package.install_for_user import _safe_under,_quote_exec
        with tempfile.TemporaryDirectory() as folder:
            home=Path(folder)
            (home/".local").symlink_to(home/"untrusted")
            with self.assertRaises(ValueError):
                _safe_under(home,home/".local"/"share"/"applications")
        with self.assertRaises(ValueError):
            _quote_exec("/home/spider/evil\";rm -rf $HOME")
        with self.assertRaises(ValueError):
            _quote_exec("/home/spider/new\nExec=bad")

    def test_doctor_is_read_only_and_never_claims_hardware_ready(self):
        info=report()
        self.assertIn("linux_desktop",info)
        self.assertIn("required_ready",info)
        self.assertIn("ffmpeg",info["recommended_executables"])
        self.assertIn("PyQt5.QtMultimedia",info["required_pyqt5_modules"])
        self.assertTrue(any("No external audio interfaces" in s
                            for s in info["notes"]))
        self.assertTrue(any("does not guarantee" in s
                            for s in info["notes"]))

class BetaSetupGuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            from PyQt5.QtWidgets import QApplication
        except ImportError:
            raise unittest.SkipTest("PyQt5 is unavailable")
        cls.application=QApplication.instance() or QApplication([])

    def test_gui_requires_explicit_acknowledgment_and_never_auto_installs(self):
        from studio.package.installer_gui import SpiderAudioSetup
        gui=SpiderAudioSetup()
        try:
            self.assertFalse(gui.install_button.isEnabled())
            self.assertIsNone(gui.installed)
            self.assertIn("Nothing has been installed",gui.result.text())
            gui.ack.setChecked(True)
            self.assertFalse(gui.install_button.isEnabled())
            with patch("studio.package.installer_gui.verify",
                       return_value={"version":VERSION}),patch(
                       "studio.package.installer_gui.subprocess.run") as check:
                check.return_value.returncode=0
                check.return_value.stdout='{"required_ready": true}'
                check.return_value.stderr=""
                gui.check_computer()
            self.assertTrue(gui.install_button.isEnabled())
            with patch("studio.package.installer_gui.install") as save:
                save.return_value=(Path("/tmp/spider-studio-app"),
                                   Path("/tmp/spider-studio.desktop"))
                gui.install_beta()
            save.assert_called_once()
            self.assertEqual(gui.installed,Path("/tmp/spider-studio-app"))
            self.assertFalse(gui.install_button.isEnabled())
        finally:
            gui.close()

class CommercialReleaseGuard(unittest.TestCase):
    def test_missing_license_and_qa_approvals_block_sale(self):
        result=assess()
        self.assertEqual(result["commercial_distribution"],"BLOCKED")
        self.assertFalse(result["automated_legal_clearance"])
        self.assertGreaterEqual(len(result["blockers"]),len(CHECKS))
        self.assertEqual(result["distribution_model"],"undecided")

    def test_even_all_evidence_documents_do_not_authorize_automated_publication(self):
        sample={
            "schema":1,"distribution_model":"proprietary_licensed",
            "checks":{key:{"state":"approved",
                           "evidence":"Human reviewed legal documentation "+key,
                           "reviewer":"Human reviewer"}
                     for key in CHECKS},
        }
        with tempfile.TemporaryDirectory() as folder:
            document=Path(folder)/"evidence.json"
            document.write_text(json.dumps(sample))
            result=assess(document)
        self.assertEqual(result["commercial_distribution"],
                         "DOCUMENTED_FOR_HUMAN_REVIEW")
        self.assertFalse(result["automated_legal_clearance"])
        self.assertIn("owner-controlled release action",result["warning"])

if __name__=="__main__":
    unittest.main()
