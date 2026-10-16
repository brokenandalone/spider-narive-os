"""Owner-only Heretic model workshop: no service or Ollama mutations."""
import importlib.util
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/"webbie"/"brain"/"heretic_lab.py"
spec = importlib.util.spec_from_file_location("spider_heretic_lab", SOURCE)
lab = importlib.util.module_from_spec(spec)
# Plain dataclass modules must be discoverable in sys.modules.
import sys
sys.modules[spec.name] = lab
spec.loader.exec_module(lab)


class HereticLabTests(unittest.TestCase):
    def test_readiness_inspects_only_and_never_installs_anything(self):
        with tempfile.TemporaryDirectory() as directory:
            venv = Path(directory)/"isolated-venv"
            executable = venv/"bin"/"heretic"
            executable.parent.mkdir(parents=True)
            executable.write_text("#!/bin/sh\nexit 0\n")
            executable.chmod(0o700)
            disk = mock.Mock(free=50*1024**3)
            with mock.patch.object(lab.shutil,"disk_usage",return_value=disk):
                status=lab.inspect_heretic(
                    venv=venv,workdir=Path(directory)/"experiments",
                    meminfo="MemTotal:       33554432 kB\n",which=lambda c:"/usr/bin/konsole")
            self.assertTrue(status.installed)
            self.assertEqual(status.total_ram_gib,32.0)
            self.assertEqual(status.free_disk_gib,50.0)
            self.assertTrue(status.console_available)
            self.assertIn("qwen3:8b",status.explanation)

    def test_unknown_model_and_shell_injection_fail(self):
        status=lab.LabStatus(True,"/home/user/lab/bin/heretic",64,100,True,"")
        for model in ("Qwen/Qwen3-0.6B; rm -rf ~",
                      "../private", "local Ollama:qwen3:8b",
                      "Qwen/Qwen3-0.6B\nreboot"):
            with self.subTest(model=model):
                with self.assertRaises(ValueError):
                    lab.plan_experiment(model,status)
                with self.assertRaises(ValueError):
                    lab.launch_experiment(model,approved=True,status=status)

    def test_tight_ram_and_disk_block_heavy_models(self):
        machine=lab.LabStatus(True,"/home/user/lab/bin/heretic",15,100,True,"")
        can_small,_=lab.plan_experiment("Qwen/Qwen3-0.6B",machine)
        can_medium,_=lab.plan_experiment("Qwen/Qwen3-1.7B",machine)
        can_large,warning=lab.plan_experiment("Qwen/Qwen3-4B-Instruct-2507",machine)
        self.assertTrue(can_small)
        self.assertFalse(can_medium)
        self.assertFalse(can_large)
        self.assertIn("physical RAM",warning)
        no_space=lab.LabStatus(True,machine.executable,64,5,True,"")
        self.assertFalse(lab.plan_experiment("Qwen/Qwen3-0.6B",no_space)[0])

    def test_launch_requires_owner_click_and_frozen_model_list(self):
        status=lab.LabStatus(True,"/home/user/lab/bin/heretic",64,120,True,"")
        with tempfile.TemporaryDirectory() as directory:
            workdir=Path(directory)/"run"
            launches=[]
            def start(args,**kwargs):
                launches.append((args,kwargs))
                return object()
            with self.assertRaises(PermissionError):
                lab.launch_experiment("Qwen/Qwen3-0.6B",
                    approved=False,status=status,workdir=workdir,popen=start)
            self.assertFalse(workdir.exists())
            result=lab.launch_experiment("Qwen/Qwen3-0.6B",
                approved=True,status=status,workdir=workdir,popen=start)
            self.assertTrue(result)
            self.assertTrue(workdir.is_dir())
            self.assertEqual(len(launches),1)
            args,kwargs=launches[0]
            self.assertEqual(args,[
                "konsole","--hold","-e",status.executable,"Qwen/Qwen3-0.6B"])
            self.assertFalse(kwargs.get("shell",False))
            self.assertEqual(kwargs["cwd"],str(workdir))
            self.assertEqual(kwargs["stdin"],lab.subprocess.DEVNULL)

    def test_symlinked_runtime_and_bad_executable_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            base=Path(folder)
            venv=base/"venv"
            target=base/"target"
            target.mkdir()
            (venv/"bin").mkdir(parents=True)
            (venv/"bin"/"heretic").symlink_to(target)
            self.assertFalse(lab._trusted_executable(venv/"bin"/"heretic",base=venv))
            out=base/"experiments"
            out.symlink_to(target,target_is_directory=True)
            status=lab.LabStatus(True,str(venv/"bin"/"heretic"),64,100,True,"")
            with self.assertRaises(PermissionError):
                lab.launch_experiment("Qwen/Qwen3-0.6B",
                                      approved=True,status=status,workdir=out,
                                      popen=mock.Mock())

    def test_prod_brain_is_never_changed_by_model_lab(self):
        code=SOURCE.read_text()
        self.assertNotIn("ollama create",code)
        self.assertNotIn("ollama rm",code)
        self.assertNotIn("apt install",code)
        self.assertNotIn("git clone",code)
        config=(ROOT/"webbie"/"config"/"default.json").read_text()
        self.assertIn('"model": "qwen3:8b"',config)
        ui=(ROOT/"the-web"/"shell"/"webbie_cognitive_center.py").read_text()
        self.assertIn("Heretic model lab",ui)
        self.assertIn("HereticExperimentDialog",ui)
        self.assertIn("launch_experiment(model, approved=True",ui)


if __name__ == "__main__":
    unittest.main()
