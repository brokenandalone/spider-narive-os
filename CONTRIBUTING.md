# Contributing

Keep changes small and boot-testable. Explain architectural decisions in `docs/`, avoid committing generated images, and include the exact build command used when reporting a problem.

Before opening a pull request:

```sh
bash -n scripts/build.sh scripts/run.sh
```

If the cross-toolchain is available, also run `./scripts/build.sh` and test the ISO in QEMU.
