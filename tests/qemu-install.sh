#!/usr/bin/env bash
# Only a freshly created QCOW2 disk is exposed to the guest. Never takes a host disk.
set -Eeuo pipefail
[[ ${EUID} -eq 0 ]] || { echo 'Run with sudo' >&2; exit 1; }
spider_iso="$(realpath "${1:?Pass ISO}")"
spider_repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
spider_test="$(dirname "${spider_iso}")/install-test"
mkdir -p "${spider_test}"
spider_work="$(mktemp -d "${spider_test}/vm.XXXXXX")"
spider_guest_pid=''
cleanup_vm() (
    set +e
    [[ -n "${spider_guest_pid}" ]] && kill "${spider_guest_pid}" 2>/dev/null
    mountpoint -q "${spider_work}/iso" && umount "${spider_work}/iso"
    # Keep logs; remove only this invocation's disposable VM files.
    rm -rf "${spider_work}"
    return 0
)
trap cleanup_vm EXIT
mkdir -p "${spider_work}"/{iso,seed}
mount -o loop,ro "${spider_iso}" "${spider_work}/iso"
cp "${spider_work}/iso/casper/vmlinuz" "${spider_work}/vmlinuz"
cp "${spider_work}/iso/casper/initrd" "${spider_work}/initrd"
cp "${spider_repo}/distro/verify-installed-payload.sh" "${spider_work}/seed/verify-payload.sh"
cp "${spider_repo}/tests/check-the-web.py" "${spider_work}/seed/check-the-web.py"
cat > "${spider_work}/seed/first-boot.sh" <<'GUEST'
#!/usr/bin/env bash
set -Eeuo pipefail
exec >>/dev/ttyS0 2>&1
trap 'echo "SPIDER_DISK_BOOT_FAILED: line ${LINENO}: ${BASH_COMMAND}"; systemctl --no-block poweroff' ERR
echo 'SPIDER_CHECK: installed identity and writable root'
grep -q '^NAME="Spider OS"$' /etc/os-release
! grep -q 'boot=casper' /proc/cmdline
[[ "$(findmnt -no FSTYPE /)" != overlay ]]
touch /var/lib/spider-ci-write-test
rm /var/lib/spider-ci-write-test
bash /usr/local/lib/spider-ci/verify-payload.sh /
echo 'SPIDER_CHECK: system services'
systemctl is-active --quiet spider-os.service ollama.service
echo 'SPIDER_CHECK: The Web and all ten backgrounds'
install -d -m 700 /run/spider-ci-qt
export XDG_RUNTIME_DIR=/run/spider-ci-qt QT_QPA_PLATFORM=offscreen QT_ACCESSIBILITY=0
timeout --signal=TERM --kill-after=5 120 dbus-run-session -- \
    python3 -u /usr/local/lib/spider-ci/check-the-web.py /usr/local/lib/spider-os
echo SPIDER_DISK_BOOT_PASSED
systemctl --no-block poweroff
GUEST
cat > "${spider_work}/seed/spider-ci.service" <<'UNIT'
[Unit]
Description=Disposable installed-system verification
After=spider-os.service ollama.service
Wants=spider-os.service ollama.service
[Service]
# Do not hold multi-user.target open while Qt or D-Bus starts a session.
Type=exec
ExecStart=/bin/bash /usr/local/lib/spider-ci/first-boot.sh
RuntimeMaxSec=180
StandardOutput=journal+console
StandardError=journal+console
[Install]
WantedBy=multi-user.target
UNIT
python3 "${spider_repo}/tests/make-install-seed.py" "${spider_work}/iso/casper" "${spider_work}/seed"
umount "${spider_work}/iso"
xorriso -as mkisofs -quiet -V cidata -o "${spider_work}/seed.iso" "${spider_work}/seed"
qemu-img create -f qcow2 "${spider_work}/disk.qcow2" 64G
cp /usr/share/OVMF/OVMF_VARS_4M.fd "${spider_work}/vars.fd"
spider_accel=tcg
spider_cpu=max
if [[ -c /dev/kvm ]]; then spider_accel=kvm; spider_cpu=host; fi
spider_qemu=(qemu-system-x86_64 -machine "q35,accel=${spider_accel}" -cpu "${spider_cpu}"
    -m 4096 -smp 2 -display none -monitor none -no-reboot
    -drive if=pflash,format=raw,readonly=on,file=/usr/share/OVMF/OVMF_CODE_4M.fd
    -drive "if=pflash,format=raw,file=${spider_work}/vars.fd"
    -drive "if=virtio,format=qcow2,file=${spider_work}/disk.qcow2"
    -device virtio-net-pci,netdev=net0 -netdev user,id=net0)
run_guest() {
    local deadline="$1" log="$2"
    shift 2
    timeout --signal=TERM --kill-after=30 "${deadline}" "${spider_qemu[@]}" \
        -serial "file:${log}" "$@" >"${log}.qemu" 2>&1 &
    spider_guest_pid=$!
    local result=0
    wait "${spider_guest_pid}" || result=$?
    spider_guest_pid=''
    cat "${log}.qemu"
    tail -n 80 "${log}"
    [[ ${result} -eq 0 ]]
}
echo 'Installing ISO onto a blank virtual UEFI disk...'
run_guest 5400 "${spider_test}/install.serial.log" \
    -drive "file=${spider_iso},media=cdrom,readonly=on" \
    -drive "file=${spider_work}/seed.iso,media=cdrom,readonly=on" \
    -kernel "${spider_work}/vmlinuz" -initrd "${spider_work}/initrd" \
    -append 'boot=casper autoinstall ds=nocloud console=ttyS0,115200n8 systemd.mask=spider-ci.service'
grep -q SPIDER_INSTALL_PASSED "${spider_test}/install.serial.log"
echo 'Booting the installed disk with no ISO attached...'
run_guest 900 "${spider_test}/boot.serial.log"
grep -q SPIDER_DISK_BOOT_PASSED "${spider_test}/boot.serial.log"
echo 'QEMU installation and writable installed-system boot: PASSED'
