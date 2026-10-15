"""Kali Bay diagnostics must pass dpkg field markers to dpkg-query literally."""
from pathlib import Path
import subprocess
import unittest

ROOT=Path(__file__).resolve().parents[1]
MANAGER=ROOT/"kali-bay/bin/kali-bay"


class KaliDoctorFormatTests(unittest.TestCase):
    def test_package_query_field_markers_are_escaped_inside_inner_sh(self):
        source=MANAGER.read_text(encoding="utf-8")
        prefix=source.index("doctor() {")
        end=source.index("update_kali() {",prefix)
        doctor=source[prefix:end]
        self.assertIn("Core Kali package status:",doctor)
        self.assertIn(
            r'dpkg-query -W -f="\${Package}: \${Status}\\n"',
            doctor)
        self.assertNotIn(
            r'dpkg-query -W -f="${Package}: ${Status}',
            doctor)
        result=subprocess.run(
            ["bash","-n",str(MANAGER)],
            capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_the_exact_inner_shell_passes_unexpanded_dpkg_fields(self):
        source=MANAGER.read_text(encoding="utf-8")
        start=source.index("    podman exec --user 0 --tty=false",source.index("doctor() {"))
        end=source.index("\n    '",start)
        program=source[start:end]
        query=next(line.strip() for line in program.splitlines()
                   if line.strip().startswith("dpkg-query -W -f="))
        # Run only printf to verify exact shell escaping. Never contact
        # the user's container or run dpkg.
        formatted=query.split(" -f=",1)[1].split(" systemd ",1)[0]
        smoke=subprocess.run(
            ["sh","-c","printf '%s\\n' "+formatted],
            capture_output=True,text=True,timeout=10)
        self.assertEqual(smoke.returncode,0,smoke.stderr)
        self.assertEqual(smoke.stdout.strip(),
                         r"${Package}: ${Status}\n")


if __name__=="__main__":
    unittest.main()
