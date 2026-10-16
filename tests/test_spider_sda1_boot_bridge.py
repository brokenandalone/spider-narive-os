"""Offline regression tests for SpiderOS's nonstandard unmounted boot partition."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

FILE = Path(__file__).resolve().parents[1] / "distro/spider-sda1-boot-bridge.py"
spec = importlib.util.spec_from_file_location("spider_boot_bridge", FILE)
bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)

EXAMPLE = f"""### BEGIN /etc/grub.d/10_linux ###
menuentry 'Spider OS GNU/Linux' --class spider --class gnu-linux --class gnu --class os {{
    recordfail
    insmod part_gpt
    insmod ext2
    set root='hd0,gpt1'
    search --no-floppy --fs-uuid --set=root {bridge.SPIDER_UUID}
    linux /vmlinuz-7.0.0-38-generic root={bridge.ROOT_DEVICE} ro quiet splash preempt=full rcu_nocbs=all threadirqs $vt_handoff
    initrd /initrd.img-7.0.0-38-generic
}}
submenu 'Advanced options' {{
  menuentry 'Spider OS recovery' {{
    linux /vmlinuz-7.0.0-38-generic root={bridge.ROOT_DEVICE} ro recovery
    initrd /initrd.img-7.0.0-38-generic
  }}
}}
### END /etc/grub.d/10_linux ###
"""

class BootBridgeTests(unittest.TestCase):
    def test_extract_exact_active_kernel(self):
        current, args = bridge.original_entry(EXAMPLE)
        self.assertEqual(current, "7.0.0-38-generic")
        self.assertIn("root=/dev/mapper/kali--vg-root", args)

    def test_build_preserves_default_and_adds_manually_selected_option(self):
        candidate = bridge.make_candidate(EXAMPLE, "7.1.0-10-generic",
                                          22 * 1024 * 1024, 98 * 1024 * 1024,
                                          254 * 1024 * 1024)
        self.assertIn(EXAMPLE.split("### END /etc/grub.d/10_linux ###")[0], candidate)
        self.assertEqual(bridge.original_entry(candidate), bridge.original_entry(EXAMPLE))
        self.assertIn("menuentry 'Spider OS TEST kernel 7.1.0-10-generic", candidate)
        self.assertIn("linux /vmlinuz-7.1.0-10-generic", candidate)
        self.assertIn("initrd /initrd.img-7.1.0-10-generic", candidate)
        self.assertIn("search --no-floppy --fs-uuid --set=root " + bridge.SPIDER_UUID, candidate)
        self.assertIn("manual selection only", candidate)
        self.assertNotIn("$vt_handoff", candidate.split("# SPIDER_OS_TEST_ENTRY:")[1])
        self.assertEqual(EXAMPLE.count("menuentry 'Spider OS GNU/Linux'"),
                         candidate.count("menuentry 'Spider OS GNU/Linux'"))

    def test_refuses_candidate_that_uses_working_kernel(self):
        with self.assertRaisesRegex(ValueError, "different kernel"):
            bridge.make_candidate(EXAMPLE, "7.0.0-38-generic", 100, 100, 1000000000)

    def test_refuses_low_space_without_overwriting_known_good_kernel(self):
        with self.assertRaisesRegex(ValueError, "Insufficient"):
            bridge.make_candidate(EXAMPLE, "7.1.0-10-generic",
                                  40 * 1024 * 1024, 180 * 1024 * 1024,
                                  254 * 1024 * 1024)

    def test_refuses_mismatched_old_boot_assets(self):
        tampered = EXAMPLE.replace("initrd.img-7.0.0-38", "initrd.img-7.0.0-99")
        with self.assertRaisesRegex(ValueError, "differ"):
            bridge.original_entry(tampered)

    def test_refuses_wrong_root_or_uuid(self):
        with self.assertRaises(ValueError):
            bridge.original_entry(EXAMPLE.replace(bridge.ROOT_DEVICE, "/dev/sda3"))
        with self.assertRaises(ValueError):
            bridge.original_entry(EXAMPLE.replace(bridge.SPIDER_UUID, "other-uuid"))

    def test_rejects_path_injection_into_generated_menu(self):
        with self.assertRaises(ValueError):
            bridge.make_candidate(EXAMPLE, "new'; reboot", 100, 100, 1000000000)

    def test_audit_has_no_live_boot_mutation_actions(self):
        s = FILE.read_text()
        self.assertNotIn('subprocess.run(["grub-install"', s)
        self.assertNotIn('subprocess.run(["update-grub"', s)
        self.assertNotIn('subprocess.run(["mount"', s)
        self.assertNotIn("mount -o rw", s)
        self.assertNotIn('["debugfs", "-w"', s)
        self.assertNotIn("do-release-upgrade", s)
        self.assertIn("OFFLINE PREVIEW ONLY", s)

if __name__ == "__main__":
    unittest.main()
