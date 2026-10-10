"""Full Kali desktop VM controller tests: use fake libvirt, never start a real VM."""
import importlib.util
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / "kali-bay/vm/kali_desktop.py"
SPEC = importlib.util.spec_from_file_location("spider_kali_vm", SOURCE)
vm = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(vm)


class KaliDesktopVMTests(unittest.TestCase):
    def which(self, name):
        return "/usr/bin/" + name

    def test_missing_domain_does_not_create_or_start(self):
        rows = subprocess.CompletedProcess([], 0, "existing-other-vm\n", "")
        with patch.object(vm, "tool", side_effect=self.which), \
                patch.object(vm, "_run", return_value=rows) as run, \
                patch.object(vm.subprocess, "Popen") as spawn:
            state = vm.inspect_vm()
            self.assertEqual(state["state"], "not-configured")
            self.assertFalse(state["configured"])
            self.assertEqual(run.call_count, 1)
            self.assertEqual(run.call_args.args[0][-3:], ["list", "--all", "--name"])
            spawn.assert_not_called()

    def test_running_domain_state_fixed_name_and_uri(self):
        rows = subprocess.CompletedProcess([], 0, "other\nspider-kali-desktop\n", "")
        state = subprocess.CompletedProcess([], 0, "running\n", "")
        with patch.object(vm, "tool", side_effect=self.which), \
                patch.object(vm, "_run", side_effect=[rows, state]) as run:
            info = vm.inspect_vm()
            self.assertEqual(info["state"], "running")
            self.assertTrue(info["configured"])
            self.assertEqual(
                run.call_args.args[0],
                ["/usr/bin/virsh", "-c", "qemu:///system",
                 "domstate", "spider-kali-desktop"]
            )

    def test_console_requires_existing_running_vm(self):
        with patch.object(vm, "inspect_vm", return_value={"state": "stopped"}), \
                patch.object(vm.subprocess, "Popen") as spawn:
            ok, _ = vm.open_console()
            self.assertFalse(ok)
            spawn.assert_not_called()

    def test_console_uses_fixed_domain_no_shell(self):
        with patch.object(vm, "inspect_vm", return_value={"state": "running"}), \
                patch.object(vm, "tool", side_effect=self.which), \
                patch.object(vm.subprocess, "Popen") as spawn:
            ok, _ = vm.open_console()
            self.assertTrue(ok)
            self.assertEqual(spawn.call_args.args[0],
                             ["/usr/bin/virt-viewer", "--connect",
                              "qemu:///system", "spider-kali-desktop"])
            self.assertNotIn("shell", spawn.call_args.kwargs)

    def test_vm_manager_only_launches_virt_manager(self):
        with patch.object(vm, "tool", side_effect=self.which), \
                patch.object(vm.subprocess, "Popen") as spawn:
            ok, _ = vm.open_manager()
            self.assertTrue(ok)
            self.assertEqual(spawn.call_args.args[0],
                             ["/usr/bin/virt-manager", "--connect", "qemu:///system"])

    def test_start_rejects_missing_domain(self):
        with patch.object(vm, "inspect_vm", return_value={"state": "not-configured"}), \
                patch.object(vm, "_run") as run:
            ok, _ = vm.start_desktop()
            self.assertFalse(ok)
            run.assert_not_called()

    def test_explicit_start_only_fixed_kali_domain(self):
        reply = subprocess.CompletedProcess([], 0, "Domain started", "")
        with patch.object(vm, "inspect_vm", return_value={"state": "stopped"}), \
                patch.object(vm, "tool", side_effect=self.which), \
                patch.object(vm, "_run", return_value=reply) as run:
            ok, _ = vm.start_desktop()
            self.assertTrue(ok)
            self.assertEqual(run.call_args.args[0],
                             ["/usr/bin/virsh", "-c", "qemu:///system",
                              "start", "spider-kali-desktop"])

    def test_source_exposes_no_delete_or_vm_creation_action(self):
        source = SOURCE.read_text()
        self.assertIn('choices=["status", "manager", "console", "start"]', source)
        self.assertNotIn('"destroy"', source)
        self.assertNotIn('"undefine"', source)
        self.assertNotIn('"net-create"', source)
        self.assertNotIn("shell=True", source)


if __name__ == "__main__":
    unittest.main()
