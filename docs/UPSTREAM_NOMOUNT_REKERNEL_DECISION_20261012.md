# Upstream NoMount / Re-Kernel integration decision (2026-10-12)

**Audit only; no merge, build, or flashing.** Main remains untouched. Backup: `backup/cogan-main-before-upstream-sync-20261012` at `73fe92fa8aa40cb4a7e4ed506c5eac8b36331848`.

## Source commits reviewed
- `coolzyd9107/GKI_BakaSU_SUSFS@fc1250efee6e5f1d020761938039e015c25d29d3`: optional NoMount workflow integration.
- `coolzyd9107/GKI_BakaSU_SUSFS@cb7826cead9e894991db1f6e5bc355a48fcdf583`: Re-Kernel support for split source layout.

## NoMount — DO NOT cherry-pick
Cogan `.github/workflows/build.yml` already exposes `use_nomount`, fetches the exact pinned commit from `steps.companions.outputs.nomount_commit`, verifies the resulting `NoMount` checkout, and enables `CONFIG_NOMOUNT=y`. `scripts/component_sync_gate.py` checks source commit, Kconfig, symlink, Makefile, kernel/userspace protocol, and companion ZIP. `scripts/package_nomount.sh` stamps the companion with the source commit. Upstream `fc1250e` uses a moving `dev` branch via `curl ... | bash`; replacing Cogan's pinned integration would weaken reproducibility and may create duplicate installation. **Keep Cogan implementation; do not merge upstream NoMount integration.**

## Re-Kernel — selective adaptation warranted
Cogan `.github/workflows/build.yml` currently finds `rekernel.c` and unconditionally applies `sed` transformations to it. Upstream `cb7826c` adds explicit legacy single-file and new split-file layout handling (`rekernel_main.c`, `rekernel_netlink.c`, `rekernel_binder.c`, `rekernel_signal.c`, `rekernel_netfilter.c`, and headers), and a multi-object Makefile. **Port only layout detection, required-file validation, and corresponding build rules; do not cherry-pick the whole upstream build workflow.** Retain Cogan's custom input and safety gates. Limit old single-file `sed` edits to legacy layout, and verify split-layout header and API requirements before enabling builds.

## Required gates before any merge
1. Fetch and inspect actual current `Sakion-Team/Re-Kernel` LKM source layout; confirm filenames and Kconfig/Makefile dependencies.
2. Ensure exactly one Re-Kernel driver registration and one NoMount integration per build; detect existing sources and fail closed.
3. Keep NoMount commit pinning and kernel/userspace/metamodule ABI checks intact.
4. Run workflow YAML/static tests and dedicated layout fixtures for both legacy and split Re-Kernel, including unsupported layout failure.
5. Review diff and CI in a separate PR before any merge; never use GitHub's `Discard 82 commits` option.

**No claim of compatibility or successful build is made by this decision document.**
