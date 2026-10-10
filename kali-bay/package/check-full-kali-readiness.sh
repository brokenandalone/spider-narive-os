#!/usr/bin/env bash
# Read-only Kali full desktop virtualization readiness inventory.
# No sudo, package actions, container start, guest creation or network changes.
set -Eeuo pipefail

echo "Spider OS · Full Kali Linux desktop readiness (read-only)"
echo "-------------------------------------------------------"

if grep -Eiq '(vmx|svm)' /proc/cpuinfo 2>/dev/null; then
    echo "CPU virtualization flags: detected"
else
    echo "CPU virtualization flags: not detected (firmware settings or host need review)"
fi

if [[ -e /dev/kvm ]]; then
    echo "KVM device: present"
else
    echo "KVM device: missing (KVM driver/hardware requires review)"
fi

for program in virsh virt-manager virt-viewer qemu-system-x86_64; do
    if command -v "$program" >/dev/null 2>&1; then
        printf 'Installed: %s\n' "$program"
    else
        printf 'Not detected: %s\n' "$program"
    fi
done

if [[ -r /proc/meminfo ]]; then
    awk '/^MemTotal:/ { printf "Host RAM: approximately %.1f GiB\n", $2/1048576; exit }' /proc/meminfo
fi
if [[ -d /var/lib/libvirt/images ]]; then
    df -h /var/lib/libvirt/images | tail -n 1 | awk '{ print "VM image filesystem space: " $4 " available" }'
else
    df -h "$HOME" | tail -n 1 | awk '{ print "Home filesystem space: " $4 " available (VM storage location unconfirmed)" }'
fi

if command -v virsh >/dev/null 2>&1; then
    if command -v timeout >/dev/null 2>&1; then
        if timeout 8 virsh -c qemu:///system list --all --name >/dev/null 2>&1; then
            echo "System libvirt connection: accessible as current user"
        else
            echo "System libvirt connection: inaccessible or unavailable"
        fi
    else
        echo "libvirt connection: not probed (timeout utility missing)"
    fi
fi

echo "No VM or container was started. No host changes were made."
