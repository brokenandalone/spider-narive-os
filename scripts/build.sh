#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="${ROOT_DIR}/build"

required=(x86_64-elf-gcc x86_64-elf-ld x86_64-elf-objcopy grub-mkrescue xorriso)
for tool in "${required[@]}"; do
  command -v "$tool" >/dev/null 2>&1 || { echo "Missing required tool: $tool" >&2; exit 1; }
done

rm -rf "${BUILD_DIR}"
mkdir -p "${BUILD_DIR}/obj" "${BUILD_DIR}/isodir/boot/grub"

x86_64-elf-gcc -c "${ROOT_DIR}/src/bootloader/boot.S" -o "${BUILD_DIR}/obj/boot.o" -ffreestanding -m32 -O2 -Wall -Wextra
x86_64-elf-gcc -c "${ROOT_DIR}/src/kernel/kernel.c" -o "${BUILD_DIR}/obj/kernel.o" -ffreestanding -m32 -O2 -Wall -Wextra -fno-stack-protector -fno-pie
x86_64-elf-ld -m elf_i386 -T "${ROOT_DIR}/src/bootloader/linker.ld" "${BUILD_DIR}/obj/boot.o" "${BUILD_DIR}/obj/kernel.o" -o "${BUILD_DIR}/spider-narive-os.elf"
x86_64-elf-objcopy -O binary "${BUILD_DIR}/spider-narive-os.elf" "${BUILD_DIR}/spider-narive-os.bin"

cp "${BUILD_DIR}/spider-narive-os.elf" "${BUILD_DIR}/isodir/boot/kernel.elf"
cp "${ROOT_DIR}/src/bootloader/grub.cfg" "${BUILD_DIR}/isodir/boot/grub/grub.cfg"
grub-mkrescue -o "${BUILD_DIR}/spider-narive-os.iso" "${BUILD_DIR}/isodir" >/dev/null

echo "Built ${BUILD_DIR}/spider-narive-os.iso"
