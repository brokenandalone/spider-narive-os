#!/usr/bin/env bash
# ExecStopPost runs even on a crash or systemd's runtime deadline.
# Logging failures must never prevent the disposable guest from powering off.
set +e
spider_marker="${1:-/run/spider-ci-passed}"
if [[ "${SERVICE_RESULT:-unknown}" == success && -f "${spider_marker}" ]]; then
    echo SPIDER_DISK_BOOT_PASSED
else
    echo "SPIDER_DISK_BOOT_FAILED: service=${SERVICE_RESULT:-unknown} exit=${EXIT_CODE:-unknown}/${EXIT_STATUS:-unknown}"
    journalctl --no-pager -u spider-ci.service -n 100
fi
systemctl --no-block poweroff
