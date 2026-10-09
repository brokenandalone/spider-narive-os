#!/usr/bin/env python3
"""Read-only hardware inventory for local Studio generation; not a benchmark."""
import json
from pathlib import Path
import re
import shutil
import subprocess


def read_command(args):
    if not shutil.which(args[0]):
        return None
    try:
        result = subprocess.run(args, capture_output=True, text=True,
                                timeout=5, check=False)
        return result.stdout[:32768] if result.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired, UnicodeError):
        return None


def inventory(meminfo=Path('/proc/meminfo'), storage=None, runner=read_command):
    """No model downloads, device activation, serial numbers or network access."""
    try:
        memory = Path(meminfo).read_text()[:16384]
    except (OSError, UnicodeError):
        memory = ''
    ram = {}
    for key in ('MemTotal', 'MemAvailable'):
        match = re.search(r'^' + key + r':\s+(\d+)\s+kB$', memory, re.MULTILINE)
        ram[key + '_bytes'] = int(match[1]) * 1024 if match else None
    pci = runner(['lspci', '-nn']) or ''
    displays = [line.strip()[:300] for line in pci.splitlines()
                if re.search(r'\[(0300|0302|0380)\]', line)][:16]
    nvidia = runner(['nvidia-smi', '--query-gpu=name,memory.total,driver_version',
                     '--format=csv,noheader,nounits'])
    gpus = []
    for line in (nvidia or '').splitlines()[:16]:
        fields = [value.strip() for value in line.split(',')]
        if len(fields) == 3 and re.fullmatch(r'\d+', fields[1]):
            gpus.append({'name': fields[0][:120], 'vram_mib': int(fields[1]),
                         'driver': fields[2][:60]})
    try:
        free = shutil.disk_usage(storage or Path.home()).free
    except OSError:
        free = None
    return {
        'memory': ram, 'display_controllers': displays,
        'nvidia_gpus': gpus, 'free_storage_bytes': free,
        'assessment': 'Inventory only; model compatibility and speed are not yet tested.',
        'notes': [
            'No NVIDIA result does not prove that no GPU is installed.',
            'AMD/Intel acceleration and VRAM need backend-specific qualification.',
            'Measure memory use while Webbie is running before selecting a music model.',
            'No model was installed or run; no hardware purchase is recommended by this report.',
        ],
    }


if __name__ == '__main__':
    print(json.dumps(inventory(), indent=2))
