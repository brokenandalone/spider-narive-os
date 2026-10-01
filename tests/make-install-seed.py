#!/usr/bin/env python3
"""Generate a test-only NoCloud seed; never added to the distributable ISO."""
import importlib.util
import sys
from pathlib import Path
import yaml

spec = importlib.util.spec_from_file_location('catalog', Path(__file__).resolve().parents[1] / 'distro/verify-install-catalog.py')
catalog = importlib.util.module_from_spec(spec)
spec.loader.exec_module(catalog)


def make_config(source_id):
    return {'autoinstall': {
        'version': 1,
        'refresh-installer': {'update': False},
        'locale': 'en_US.UTF-8',
        'keyboard': {'layout': 'us'},
        'source': {'id': source_id, 'search_drivers': False},
        'identity': {'hostname': 'spider-ci', 'username': 'spider-test', 'realname': 'Disposable test', 'password': '!'},
        'storage': {'layout': {'name': 'direct', 'match': {'path': '/dev/vda'}}},
        'apt': {'geoip': False, 'fallback': 'offline-install'},
        'shutdown': 'poweroff',
        'late-commands': [
            'mkdir -p /run/spider-ci-seed /target/usr/local/lib/spider-ci',
            'mount -o ro /dev/disk/by-label/cidata /run/spider-ci-seed',
            'cp /run/spider-ci-seed/verify-payload.sh /run/spider-ci-seed/first-boot.sh /target/usr/local/lib/spider-ci/',
            'bash /target/usr/local/lib/spider-ci/verify-payload.sh /target',
            'cp /run/spider-ci-seed/spider-ci.service /target/etc/systemd/system/',
            'systemctl --root=/target enable spider-ci.service',
            "printf '%s\\n' 'GRUB_CMDLINE_LINUX_DEFAULT=\"console=ttyS0,115200n8\"' > /target/etc/default/grub.d/99-spider-ci.cfg",
            'curtin in-target --target=/target -- update-grub',
            'echo SPIDER_INSTALL_PASSED > /dev/ttyS0',
        ],
        'error-commands': ['echo SPIDER_INSTALL_FAILED > /dev/ttyS0', 'cat /var/log/installer/subiquity-server-debug.log > /dev/ttyS0 || true'],
    },
    # The desktop installer embeds the Subiquity daemon in its bootstrap snap.
    # Start the existing backend after cloud-init has made this config available.
    'runcmd': ["snap services | awk '/subiquity.*server/ {print $1}' | xargs -r snap start"],
    }


if __name__ == '__main__':
    casper, seed = map(Path, sys.argv[1:])
    config = make_config(catalog.verify(casper))
    (seed / 'user-data').write_text('#cloud-config\n' + yaml.safe_dump(config, sort_keys=False))
    (seed / 'meta-data').write_text('instance-id: spider-install-ci\nlocal-hostname: spider-ci\n')
