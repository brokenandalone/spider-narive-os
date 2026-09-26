# Building an ISO

The build is intentionally reproducible and produces `build/spider-narive-os.iso`.

```sh
./scripts/build.sh
```

The ISO is assembled with GRUB and `xorriso`; it contains the kernel ELF and `src/bootloader/grub.cfg`. To inspect or boot it:

```sh
./scripts/run.sh
```

For a real machine, treat images as experimental until hardware testing, recovery instructions, and a signed release process exist.
