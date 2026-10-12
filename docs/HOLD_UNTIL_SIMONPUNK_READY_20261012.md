# HOLD — wait for relevant Simonpunk SUSFS upstream readiness

Decision: **HOLD** as requested by repository owner on 2026-10-12. No BakaSU/SUSFS/NoMount/Re-Kernel integration merge, kernel build, release or flash until the owner explicitly resumes after verifying relevant official Simonpunk SUSFS changes.

Preservation:
- Cogan main at `73fe92fa8aa40cb4a7e4ed506c5eac8b36331848`.
- Backup branch `backup/cogan-main-before-upstream-sync-20261012` retains this main tip.
- Separate audit branch `audit/upstream-nomount-rekernel-20261012` retains decision documentation.
- Upstream fork divergence verified: 82 commits ahead, 8 behind at audit time. Never click 'Discard 82 commits' or force-reset main.
- Official downstream upstream commits reviewed: NoMount `fc1250efee6e5f1d020761938039e015c25d29d3`, Re-Kernel `cb7826cead9e894991db1f6e5bc355a48fcdf583`.
- NoMount upstream integration **not** cherry-picked: Cogan already pins commit and checks source/kernel/userspace/metamodule ABI.
- Re-Kernel upstream fix is **candidate for selective port only**: detect legacy single-file and new split-file layouts, fail closed on unsupported layouts; do not overwrite Cogan workflow. No code port/merge completed.
- Read detailed audit in `docs/UPSTREAM_NOMOUNT_REKERNEL_DECISION_20261012.md`.

Resume gates: owner approval; verify official SUSFS patch and BakaSU upstream compatibility; source/API/ABI/hook ownership checks; review upstream Re-Kernel layout; tests and CI; PR review before merge. No claim of compatibility, build success, or boot stability.

This is a saved decision, not an automated stop for already-running GitHub workflows.
