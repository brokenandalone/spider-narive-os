"""Regression tests for read-only desktop user-service health."""
from pathlib import Path
from types import SimpleNamespace
import sys
import subprocess
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'the-web' / 'shell'))
from desktop_service_health import (
    USER_SERVICES, ServiceHealth, classify, health_totals,
    parse_properties, probe_user_services, service_brief)


class ServiceHealthTests(unittest.TestCase):
    def test_explicit_allowlist_and_read_only_command(self):
        recorded = []
        def run(cmd, **kwargs):
            recorded.append((cmd, kwargs))
            return SimpleNamespace(
                stdout='LoadState=loaded\nActiveState=active\nSubState=running\n',
                returncode=0)
        rows = probe_user_services(run=run, timeout=1.5)
        self.assertEqual(len(rows), len(USER_SERVICES))
        self.assertTrue(all(row.status == 'running' for row in rows))
        self.assertEqual([row.unit for row in rows], [a for a, _ in USER_SERVICES])
        self.assertTrue(all(call[:4] == ['systemctl', '--user', '--no-pager', 'show']
                            for call, _ in recorded))
        for command, opts in recorded:
            self.assertTrue(opts['capture_output'])
            self.assertLessEqual(opts['timeout'],3)
            self.assertFalse({'restart', 'enable', 'start', 'stop', 'journalctl'} & set(command))

    def test_parser_ignores_unrelated_sensitive_output(self):
        props = parse_properties(
            'LoadState=loaded\nEnvironment=PRIVATE_PASSWORD=secret\n'
            'ActiveState=failed\nExecMainStatus=1\nSubState=failed\n')
        self.assertEqual(props,
                         {'LoadState':'loaded','ActiveState':'failed','SubState':'failed'})
        self.assertNotIn('secret', str(props))
        self.assertEqual(classify(props), ('failed','Service reported failure'))

    def test_not_installed_masked_and_stopped(self):
        self.assertEqual(classify({'LoadState':'not-found','ActiveState':'inactive'})[0],
                         'not-installed')
        self.assertEqual(classify({'LoadState':'masked','ActiveState':'inactive'})[0],
                         'masked')
        self.assertEqual(classify({'LoadState':'loaded','ActiveState':'inactive'})[0],
                         'stopped')
        self.assertEqual(classify({'LoadState':'loaded','ActiveState':'activating'})[0],
                         'starting')
        self.assertEqual(classify({})[0], 'unavailable')

    def test_timeout_and_os_errors_are_nonfatal(self):
        calls = [0]
        def run(cmd, **opts):
            calls[0]+=1
            if calls[0] == 1:
                raise subprocess.TimeoutExpired(cmd, 1.5)
            if calls[0] == 2:
                raise OSError('no service manager')
            return SimpleNamespace(stdout='LoadState=not-found\nActiveState=inactive\n',
                                   returncode=1)
        rows = probe_user_services(run=run)
        self.assertEqual([x.status for x in rows][:3],
                         ['unavailable','unavailable','not-installed'])

    def test_service_brief_excludes_untrusted_units(self):
        good = ServiceHealth('webbie.service','Webbie','running','Service is active')
        bad = ServiceHealth('untrusted.service','private secret','failed','secret')
        text = service_brief([good,bad])
        self.assertIn('webbie.service: running', text)
        self.assertNotIn('untrusted.service',text)
        self.assertNotIn('secret',text)
        self.assertEqual(health_totals([good,bad]),{'running':1,'failed':1})


if __name__ == '__main__':
    unittest.main()
