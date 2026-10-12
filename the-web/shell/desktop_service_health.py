"""Read-only, allowlisted user-service health for The Web.

Checks never start/stop/restart/enable services, read journald, or inspect
arbitrary unit names. The desktop invokes this on a background QThread.
"""
from dataclasses import dataclass
import subprocess

USER_SERVICES = (
    ('webbie.service', 'Webbie resident assistant'),
    ('spider-ai-dj.service', 'Nova / Spider AI DJ'),
    ('webbie-proactive.service', 'Webbie proactive checks'),
    ('webbie-research.service', 'Webbie research'),
)
ALLOWED = {'active', 'inactive', 'failed', 'activating', 'deactivating',
           'reloading', 'unknown'}
LOAD_STATES = {'loaded', 'not-found', 'masked', 'error', 'bad-setting',
               'stub', 'unknown'}

@dataclass(frozen=True)
class ServiceHealth:
    unit: str
    label: str
    status: str
    detail: str


def parse_properties(source):
    """Read only static systemd state fields, discarding all other output."""
    properties = {}
    for line in str(source or '')[:4096].splitlines():
        if '=' not in line:
            continue
        key, value = line.split('=', 1)
        if key in ('LoadState', 'ActiveState', 'SubState'):
            properties[key] = value.strip().lower()[:60]
    return properties


def classify(props):
    load = props.get('LoadState', 'unknown')
    active = props.get('ActiveState', 'unknown')
    if load == 'not-found':
        return 'not-installed', 'Unit not found'
    if load == 'masked':
        return 'masked', 'Unit is masked'
    if load not in LOAD_STATES or active not in ALLOWED:
        return 'unavailable', 'State could not be verified'
    if active == 'active':
        return 'running', 'Service is active'
    if active == 'failed':
        return 'failed', 'Service reported failure'
    if active in ('activating', 'reloading'):
        return 'starting', 'Service is changing state'
    if active == 'inactive':
        return 'stopped', 'Service is not active'
    return 'unavailable', 'State could not be verified'


def probe_user_services(run=None, timeout=1.5):
    runner = run or subprocess.run
    result = []
    timeout = max(0.3, min(float(timeout), 3.0))
    for unit, label in USER_SERVICES:
        cmd = ['systemctl', '--user', '--no-pager', 'show', unit,
               '--property=LoadState', '--property=ActiveState',
               '--property=SubState']
        try:
            completed = runner(cmd, text=True, capture_output=True, timeout=timeout)
            props = parse_properties(completed.stdout)
            status, detail = classify(props)
        except (OSError, subprocess.TimeoutExpired, ValueError):
            status, detail = 'unavailable', 'User service manager unavailable'
        result.append(ServiceHealth(unit, label, status, detail))
    return result


def service_brief(rows):
    """Short, trusted status-only context for an explicitly drafted Webbie message."""
    verified = {item.unit: item for item in rows
                if item.unit in {unit for unit, _ in USER_SERVICES}}
    entries = [unit + ': ' + verified[unit].status
               for unit, _ in USER_SERVICES if unit in verified]
    return 'Spider OS user-service health: ' + '; '.join(entries)


def health_totals(rows):
    counts = {}
    for item in rows:
        if item.status in ('running', 'failed', 'starting', 'stopped',
                           'masked', 'not-installed', 'unavailable'):
            counts[item.status] = counts.get(item.status, 0) + 1
    return counts
