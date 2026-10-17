"""One Webbie, owner-selected permanent local Heretic/Ollama brain."""
from pathlib import Path
import importlib.util
import json
import os
import stat
import sys
import tempfile
import unittest
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
BRAIN=ROOT/"webbie"/"brain"
sys.path.insert(0,str(BRAIN))
from resident_model_choice import (
    read_choice, restore_default, select_installed_model, model_readiness
)


class PersistentBrainTests(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.file=Path(self.folder.name)/"spider-os"/"webbie-brain-choice.json"
        self.available=("qwen3:8b","webbie-heretic:8b","gemma3:4b")

    def test_model_selection_requires_one_real_owner_gui_action(self):
        with self.assertRaises(PermissionError):
            select_installed_model("webbie-heretic:8b",
                                   path=self.file,available=self.available)
        self.assertIsNone(read_choice(path=self.file))
        selected=select_installed_model(
            "webbie-heretic:8b",owner_clicked=True,path=self.file,
            available=self.available)
        self.assertEqual(selected,"webbie-heretic:8b")
        self.assertEqual(read_choice(path=self.file),"webbie-heretic:8b")
        self.assertEqual(self.file.stat().st_mode & 0o777,0o600)

    def test_choice_persists_between_new_reader_instances(self):
        select_installed_model("webbie-heretic:8b",owner_clicked=True,
                               path=self.file,available=self.available)
        for _ in range(4):
            self.assertEqual(read_choice(path=self.file),"webbie-heretic:8b")
        result=model_readiness(path=self.file,available=self.available)
        self.assertTrue(result["present"])
        self.assertIn("webbie-heretic:8b",result["heretic_available"])

    def test_no_noninstalled_model_or_shell_injection(self):
        for model in ("unavailable-heretic:8b",
                      "webbie-heretic:8b; sudo reboot",
                      "../../private", "foo\nbar"):
            with self.subTest(model=model):
                with self.assertRaises(ValueError):
                    select_installed_model(model,owner_clicked=True,
                                           path=self.file,available=self.available)
        self.assertFalse(self.file.exists())

    def test_restore_original_model_is_one_owner_action(self):
        select_installed_model("webbie-heretic:8b",owner_clicked=True,
                               path=self.file,available=self.available)
        with self.assertRaises(PermissionError):
            restore_default(path=self.file)
        self.assertTrue(restore_default(path=self.file,owner_clicked=True))
        self.assertIsNone(read_choice(path=self.file))

    def test_private_config_path_refuses_symlinks(self):
        with tempfile.TemporaryDirectory() as dirname:
            target=Path(dirname)/"real.json"
            target.write_text("NOT A MODEL")
            self.file.parent.mkdir(parents=True,exist_ok=True)
            self.file.symlink_to(target)
            with self.assertRaises(PermissionError):
                select_installed_model("qwen3:8b",owner_clicked=True,
                                       path=self.file,available=self.available)
            self.assertEqual(target.read_text(),"NOT A MODEL")

    def test_live_brain_reads_owner_choice_before_original_config(self):
        src=(BRAIN/"brain.py").read_text()
        self.assertIn("from resident_model_choice import read_choice",src)
        self.assertIn("chosen = read_choice()",src)
        self.assertIn("if chosen:\n        return chosen",src)
        self.assertIn('"model": preferred_model() if model is None else model',src)

    def test_owner_selected_model_gets_cpu_time_without_changing_default(self):
        worker=(ROOT/"webbie"/"agent"/"webbie_ai_worker.py").read_text()
        outer=(ROOT/"webbie"/"agent"/"webbie_ai_isolation.py").read_text()
        self.assertIn("default_wait = 70 if read_choice() else 14",worker)
        self.assertIn("default_wait = 90 if read_choice() else 28",outer)
        self.assertIn("max_wait = min(120, max(4, max_wait))",outer)
        self.assertIn('"model": "qwen3:8b"',worker)
        self.assertIn('from resident_model_choice import read_choice',worker)

    def test_one_owner_click_can_launch_local_heretic_download_and_activation(self):
        from resident_model_choice import launch_prebuilt_heretic, PREBUILT_SCRIPT
        self.assertTrue(PREBUILT_SCRIPT.is_file())
        self.assertTrue((ROOT/"tools"/"activate_heretic_brain.py").is_file())
        launched=[]
        def runner(argv,**kwargs):
            launched.append((argv,kwargs))
        fake_console=lambda program: "/usr/bin/"+program
        with self.assertRaises(PermissionError):
            launch_prebuilt_heretic(owner_clicked=False,popen=runner,
                                   console=fake_console,disk_free_bytes=100*1024**3)
        self.assertFalse(launched)
        self.assertTrue(launch_prebuilt_heretic(
            owner_clicked=True,popen=runner,console=fake_console,
            disk_free_bytes=100*1024**3))
        self.assertEqual(len(launched),1)
        args,kw=launched[0]
        self.assertEqual(args,["konsole","--hold","-e","bash",
                               str(PREBUILT_SCRIPT),"--approved-by-owner"])
        self.assertFalse(kw.get("shell",False))
        with self.assertRaisesRegex(RuntimeError,"10 GiB"):
            launch_prebuilt_heretic(
                owner_clicked=True,popen=runner,console=fake_console,
                disk_free_bytes=2*1024**3)
        self.assertEqual(len(launched),1)

    def test_post_pull_selection_is_exactly_one_reviewed_model(self):
        import importlib.util
        helper=ROOT/"tools"/"activate_heretic_brain.py"
        spec=importlib.util.spec_from_file_location("heretic_import_test",helper)
        module=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        model=module.MODEL
        with self.assertRaisesRegex(RuntimeError,"not found"):
            module.activate_prebuilt(model_list=["qwen3:8b"],path=self.file)
        self.assertIsNone(read_choice(path=self.file))
        selection=module.activate_prebuilt(
            model_list=("qwen3:8b",model),path=self.file)
        self.assertEqual(selection,model)
        self.assertEqual(read_choice(path=self.file),model)
        self.assertEqual(module.main(["--unknown"]),2)

    def test_shell_source_only_installs_fixed_quantization(self):
        script=(ROOT/"tools"/"install_everyday_heretic.sh").read_text()
        self.assertIn("ollama pull \"$MODEL\"",script)
        self.assertIn("ollama show \"$MODEL\"",script)
        self.assertIn("10 GiB free disk",script)
        self.assertIn("flock -n 9",script)
        self.assertNotIn("sudo ",script)
        self.assertNotIn("ollama rm",script)
        src=(ROOT/"the-web"/"shell"/"webbie_cognitive_center.py").read_text()
        self.assertIn("webbieInstallEverydayHereticButton",src)
        self.assertIn("launch_prebuilt_heretic(owner_clicked=True)",src)

    def test_native_ui_has_permanent_choice_and_restore(self):
        src=(ROOT/"the-web"/"shell"/"webbie_cognitive_center.py").read_text()
        self.assertIn("class ResidentBrainDialog",src)
        self.assertIn("webbieActivatePermanentBrain",src)
        self.assertIn("webbieHereticEverydayBrainButton",src)
        self.assertIn("select_installed_model(name,owner_clicked=True)",src)
        self.assertIn("restore_default(owner_clicked=True)",src)
        self.assertNotIn("ollama pull",src)
        self.assertNotIn("ollama rm",src)


if __name__=="__main__":
    unittest.main()
