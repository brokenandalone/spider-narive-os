import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location(
    'coverage_audit', Path(__file__).resolve().parents[1] / 'tools/audit_upgrade_coverage.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class AuditTargetTests(unittest.TestCase):
    def test_migration_target_does_not_weaken_default_lts_gate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / 'distro/config/base.env'
            config.parent.mkdir(parents=True)
            config.write_text('UBUNTU_RELEASE="26.10"\nUBUNTU_CODENAME="stonking"\n'
                              'UBUNTU_IMAGE_VERSION="26.10"\nUBUNTU_CHANNEL="release"\n')
            self.assertFalse(audit.audit(root)['base_config_pinned'])
            report = audit.audit(root, '26.10')
            self.assertTrue(report['base_config_pinned'])
            self.assertFalse(report['passes_source_coverage'])
            self.assertFalse(report['ready_for_host_installation'])
            config.write_text(config.read_text().replace('release', 'beta'))
            self.assertFalse(audit.audit(root, '26.10')['base_config_pinned'])
