#!/usr/bin/env python3
"""Generate copy-ready, per-upstream bug reports for a confirmed BakaSU/SUSFS block.

Called only when the BakaSU upstream compatibility guard blocks compilation.
This script reports the problem; it never alters or bypasses upstream safeguards.
"""
import argparse
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import subprocess

FENCE = chr(96) * 3


def safe(value, limit=180):
    """Keep build-supplied values on one line and inside Markdown code fences."""
    text = re.sub(r"[\x00-\x1f\x7f]", " ", str(value))
    return text.replace(chr(96), "'").replace("<", "(").replace(">", ")")[:limit].strip()


def git_sha(path):
    result = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "--verify", "HEAD"],
        capture_output=True, text=True, check=False,
    )
    sha = result.stdout.strip()
    return sha if result.returncode == 0 and re.fullmatch(r"[a-f0-9]{40}", sha) else "unavailable"


@dataclass(frozen=True)
class BuildContext:
    repository: str
    run_url: str
    kernel: str
    baka_sha: str
    driver_version: str
    susfs_branch: str
    susfs_sha: str


def render_report(details):
    d = BuildContext(*(safe(getattr(details, field)) for field in BuildContext.__dataclass_fields__))
    short_sha = d.baka_sha[:8] if d.baka_sha != "unavailable" else "unknown"
    proof = "kernel/tools/susfs_compat.mk:20: *** Please wait susfs update.. Stop."

    # A GitHub Actions Summary displays a copy icon on code fences, so the
    # report's title and body can be copied together without editing.
    baka_report = f"""Title: BakaSU/SUSFS compatibility guard blocks GKI kernel build (driver {d.driver_version})

Hello BakaSU maintainers,

I maintain the {d.repository} kernel-build repository.
Our build stops at BakaSU's upstream SUSFS compatibility guard.

Kernel/build: {d.kernel}
BakaSU source commit: {d.baka_sha}
BakaSU manager/kernel driver versionCode: {d.driver_version}
SUSFS branch: {d.susfs_branch}
SUSFS source commit: {d.susfs_sha}

Observed failure:
{proof}
BakaSU: susfs has NOT update with latest KernelSU source
BakaSU: Please wait simonpunk update

The error is raised by BakaSU's own kernel/tools/susfs_compat.mk.
We did not remove, bypass, or patch out the compatibility check.

Could you confirm whether this block is intentional, which SUSFS revision
is supported, and whether a compatible BakaSU update is planned?

Full failed workflow: {d.run_url}

Thank you for your guidance."""

    susfs_report = f"""Title: SUSFS/BakaSU compatibility inquiry (BakaSU driver {d.driver_version}, {d.kernel})

Hello simonpunk,

I maintain the {d.repository} kernel-build repository.
The build is blocked by a compatibility guard in BakaSU when SUSFS is enabled.

Kernel/build: {d.kernel}
BakaSU source commit: {d.baka_sha}
BakaSU manager/kernel driver versionCode: {d.driver_version}
SUSFS branch: {d.susfs_branch}
SUSFS source commit: {d.susfs_sha}

Observed error from BakaSU:
{proof}
BakaSU: susfs has NOT update with latest KernelSU source
BakaSU: Please wait simonpunk update

I am not assuming this is a SUSFS bug; the fatal check is in BakaSU's source.
Could you clarify whether this SUSFS branch supports this BakaSU revision
and whether an updated SUSFS commit or integration change is expected?

Full failed workflow: {d.run_url}
We have not bypassed the upstream compatibility check.

Thank you for your work and guidance."""

    return f"""## Build gagal / Upstream compatibility blocked

**BakaSU/SUSFS upstream compatibility guard detected.** Kernel packaging stopped safely before compilation.

<details open>
<summary>🇮🇩 Bahasa Indonesia — Pemberitahuan pemilik repository</summary>

- **Penyebab:** BakaSU commit {FENCE[:-1]}{short_sha}{FENCE[:-1]} memblokir kompilasi bersama SUSFS.
- **Driver/Manager:** versi {FENCE[:-1]}{d.driver_version}{FENCE[:-1]}; **kernel:** {FENCE[:-1]}{d.kernel}{FENCE[:-1]}.
- **Sumber:** {FENCE[:-1]}kernel/tools/susfs_compat.mk{FENCE[:-1]} meminta pembaruan SUSFS.
- **Status:** Menunggu konfirmasi/perbaikan kompatibilitas pengembang BakaSU dan SUSFS (simonpunk). Belum terbukti pihak mana yang perlu mengubah kode.
- **Tindakan:** Jangan melewati pengaman. Salin salah satu laporan Inggris di bawah untuk pengembang terkait.
- **Artifact/Release:** Tidak tersedia dari run gagal ini.

[Log build]({d.run_url})

</details>

<details>
<summary>🇬🇧 Copy bug report — BakaSU developers</summary>

Submit at [BakaSU GitHub Issues](https://github.com/Baka-SU/BakaSU/issues). Copy this complete report:

{FENCE}text
{baka_report}
{FENCE}

</details>

<details>
<summary>🇬🇧 Copy bug report — SUSFS (simonpunk)</summary>

Submit through [simonpunk's SUSFS GitLab](https://gitlab.com/simonpunk/susfs4ksu). Copy this complete report:

{FENCE}text
{susfs_report}
{FENCE}

</details>
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bakasu-source", type=Path, required=True)
    parser.add_argument("--susfs-source", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    args = parser.parse_args()

    metadata = json.loads(args.metadata.read_text())
    baka_sha = git_sha(args.bakasu_source)
    # Previous job step has already verified the source/APK pairing.
    if baka_sha == "unavailable" or baka_sha != metadata.get("bakasu_commit"):
        raise ValueError("Cannot report an unverified BakaSU source commit")
    driver_version = metadata.get("kernel_driver_version")
    if not isinstance(driver_version, int) or driver_version < 1:
        raise ValueError("BakaSU driver version has not been verified")

    repo = os.environ.get("GITHUB_REPOSITORY", "")
    run_id = os.environ.get("GITHUB_RUN_ID", "")
    server = os.environ.get("GITHUB_SERVER_URL", "https://github.com").rstrip("/")
    if not re.fullmatch(r"[\w.-]+/[\w.-]+", repo) or not run_id.isdecimal():
        raise ValueError("Invalid GitHub repository or run context")
    kernel = os.environ.get("CONFIG", "unspecified")
    susfs_branch = os.environ.get("SUSFS_EXPECTED_BRANCH", "not specified")

    details = BuildContext(
        repository=repo, run_url=f"{server}/{repo}/actions/runs/{run_id}",
        kernel=kernel, baka_sha=baka_sha, driver_version=str(driver_version),
        susfs_branch=susfs_branch, susfs_sha=git_sha(args.susfs_source),
    )
    with args.summary.open("a", encoding="utf-8") as stream:
        stream.write(render_report(details))
    print("Generated Indonesian build notification and English BakaSU/SUSFS bug reports.")


if __name__ == "__main__":
    main()
