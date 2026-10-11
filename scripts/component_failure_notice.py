#!/usr/bin/env python3
"""Report known failing CI stages without claiming an unproven upstream bug.

A failed GitHub Actions step identifies WHERE a build stopped, not necessarily
WHY it failed. Detailed stderr stays in the linked run logs. No build behavior
or release checks are modified by this script.
"""
import json
import os
from pathlib import Path
import re
import subprocess

BACKTICK = chr(96)
FENCE = BACKTICK * 3

# Stage names are stable workflow step IDs, not log-text guesses.
# Support assignments are triage suggestions, never fault attribution.
STAGES = {
    "companions": ("BakaSU / NoMount source resolution", "Cogan integration",
                   "Source/artifact download or selection failed.", None),
    "verify_manager_driver": ("BakaSU Manager ↔ Kernel Driver", "Cogan integration",
                              "Manager, signature, or driver version verification failed.", None),
    "preflight_bakasu_susfs": ("BakaSU ↔ SUSFS compatibility", "Cogan integration",
                               "A compatibility preflight check failed.", None),
    "apply_susfs_patches": ("SUSFS integration", "SUSFS compatibility inquiry",
                           "The SUSFS patch application stage failed.", "SUSFS"),
    "add_susfs_configuration": ("SUSFS kernel configuration", "Cogan integration",
                                "SUSFS kernel configuration did not complete.", None),
    "add_kernelsu": ("BakaSU kernel integration", "BakaSU compatibility inquiry",
                     "The root implementation integration stage failed.", "BakaSU"),
    "apply_nomount": ("NoMount kernel integration", "NoMount compatibility inquiry",
                      "The NoMount kernel source integration stage failed.", "NoMount"),
    "set_up_zig_nomount": ("NoMount build toolchain", "Cogan integration",
                           "The Zig setup required for NoMount packaging failed.", None),
    "package_nomount_metamodule": ("NoMount metamodule packaging", "NoMount compatibility inquiry",
                                   "The NoMount userspace/module packaging stage failed.", "NoMount"),
    "verify_bundle": ("Manager ↔ Kernel ↔ NoMount bundle", "Cogan integration",
                      "Final pairing, checksum, or packaged-kernel verification failed.", None),
    "build_standard_kernel": ("Kernel compilation", "Cogan integration",
                              "Kernel compilation failed; the compiler log is needed to identify the cause.", None),
    "compiled_config": ("Kernel configuration inspection", "Cogan integration",
                        "Compiled kernel configuration could not be read.", None),
    "upload_normal_manager": ("Manager artifact publication", "Cogan integration",
                              "Uploading the normal manager failed.", None),
    "upload_spoofed_manager": ("Manager artifact publication", "Cogan integration",
                               "Uploading the spoofed manager failed.", None),
    "upload_nomount": ("NoMount artifact publication", "Cogan integration",
                       "Uploading the NoMount module failed.", None),
    "upload_bundle_manifest": ("Bundle manifest publication", "Cogan integration",
                               "Uploading the version/checksum manifest failed.", None),
    "upload_ready_to_flash_zip": ("Kernel ZIP publication", "Cogan integration",
                                  "Uploading the flashable kernel ZIP failed.", None),
}

UPSTREAM_URLS = {
    "BakaSU": "https://github.com/Baka-SU/BakaSU",
    "SUSFS": "https://gitlab.com/simonpunk/susfs4ksu",
    "NoMount": "https://github.com/maxsteeel/nomount",
}


def sanitize(value, limit=160):
    """Keep untrusted runner metadata out of Markdown controls/code fences."""
    data = re.sub(r"[\x00-\x1f\x7f]", " ", str(value))
    return data.replace(BACKTICK, "'").replace("<", "(").replace(">", ")")[:limit].strip()


def commit_for(path):
    if not path.is_dir() or not (path / ".git").exists():
        return "not available"
    result = subprocess.run(["git", "-C", str(path), "rev-parse", "HEAD"],
                            capture_output=True, text=True, check=False)
    sha = result.stdout.strip()
    return sha if result.returncode == 0 and re.fullmatch(r"[a-f0-9]{40}", sha) else "not available"


def load_metadata(path):
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def failing_steps(steps):
    """Preserve observed step order; do not guess from a symptom message."""
    if not isinstance(steps, dict):
        return []
    return [(key, STAGES.get(key, (key.replace("_", " "), "Cogan integration",
                                      "A CI step failed; check its log.", None)))
            for key, value in steps.items()
            if isinstance(value, dict) and value.get("outcome") == "failure"]


def format_notice(*, failures, repository, run_url, build, metadata, baka_sha,
                  susfs_sha, nomount_sha):
    first_id, (component, triage, reason, upstream) = failures[0]
    driver = metadata.get("kernel_driver_version", "not verified")
    baka_selected = metadata.get("bakasu_commit", "not available")
    nomount_selected = metadata.get("nomount_commit", "not available")
    driver = sanitize(driver)
    baka_selected = sanitize(baka_selected)
    nomount_selected = sanitize(nomount_selected)
    steps_list = ", ".join(sanitize(key) for key, _ in failures)
    code = lambda value: BACKTICK + sanitize(value) + BACKTICK

    intro = f"""## ❌ Build gagal — {sanitize(component)}

**Penyebab yang diketahui:** {reason}

- **Langkah gagal:** {code(first_id)}.
- **Pemeriksaan awal:** {sanitize(triage)}. Penanggung jawab masalah belum dapat ditentukan hanya dari status langkah.
- **Tindakan:** baca pesan error pada [log workflow]({run_url}); gunakan laporan Inggris di bawah bila memerlukan bantuan.
- **Artifact/Release:** build tidak berhasil. Jangan flash atau merilis berkas parsial.
- **Build:** {code(build)}; **Driver BakaSU:** {code(driver)}.
- **Langkah gagal lain:** {code(steps_list)}.

**Catatan:** Penyebab teknis terakhir hanya dapat dipastikan dari log error. Tidak ada pemeriksaan keamanan yang dilewati.

"""
    title = f"Compatibility/build inquiry: {component} ({build})"
    preamble = ("Hello maintainers," if upstream else "Hello Cogan maintainers,")
    disclaimer = (
        "This is a compatibility inquiry, not an attribution of fault to your project."
        if upstream else
        "This report is for Cogan integration triage. An upstream root cause has not been confirmed."
    )
    english = f"""Title: {sanitize(title)}

{preamble}

I maintain the {repository} GKI kernel workflow and am requesting help with a failed build.

Build configuration: {build}
Failing workflow step: {sanitize(first_id)}
Affected stage: {sanitize(component)}
Observed outcome: {reason}
Other failing steps: {sanitize(steps_list)}

Selected BakaSU commit: {baka_selected}
Actual BakaSU checkout: {sanitize(baka_sha)}
Verified driver version (if available): {driver}
Actual SUSFS checkout: {sanitize(susfs_sha)}
Selected NoMount commit: {nomount_selected}
Actual NoMount checkout: {sanitize(nomount_sha)}

Workflow logs: {run_url}

The exact stderr and first error line are in the linked logs; this report
does not infer an upstream code defect from a failed CI step.

{disclaimer}
Could you help identify the relevant compatibility requirements or next diagnostic step?
We have not bypassed any upstream safeguards.

Thank you."""

    if upstream:
        destination = f"**Pengembang terkait:** [{upstream}]({UPSTREAM_URLS[upstream]}) — hubungi untuk meminta arahan, bukan menyatakan mereka penyebabnya."
        heading = f"🇬🇧 English — Copy report for {upstream} developers"
    else:
        destination = "**Pengembang terkait:** periksa integrasi Cogan dahulu sebelum melaporkan bug ke proyek upstream."
        heading = "🇬🇧 English — Copy report for Cogan integration triage"

    return (intro + destination + "\n\n"
            "<details>\n"
            f"<summary>{heading}</summary>\n\n"
            "Salin seluruh laporan berikut (termasuk judulnya):\n\n"
            f"{FENCE}text\n{english}\n{FENCE}\n\n"
            "</details>\n\n")


def main():
    if os.environ.get("REPORT_STATUS") != "failure":
        return
    steps = json.loads(os.environ.get("REPORT_STEPS", "{}"))
    failures = failing_steps(steps)
    if not failures:
        return

    summary_path = Path(os.environ["GITHUB_STEP_SUMMARY"])
    if summary_path.is_file():
        # Upstream's confirmed unconditional BakaSU/SUSFS guard already generated
        # more precise two-upstream reports. Avoid duplicate/contradictory drafts.
        previous = summary_path.read_text(encoding="utf-8")
        if ("COGAN_VERIFIED_COMPAT_FAILURE" in previous
                or "Copy bug report — BakaSU developers" in previous):
            print("A precise compatibility failure report already exists; skipping generic duplicate.")
            return

    repository = sanitize(os.environ.get("GITHUB_REPOSITORY", "unknown/repository"))
    run = sanitize(os.environ.get("GITHUB_RUN_ID", ""))
    server = os.environ.get("GITHUB_SERVER_URL", "https://github.com").rstrip("/")
    run_url = f"{server}/{repository}/actions/runs/{run}" if run.isdecimal() else f"{server}/{repository}/actions"
    inputs = json.loads(os.environ.get("REPORT_INPUTS", "{}"))
    if not isinstance(inputs, dict):
        inputs = {}
    build = sanitize(os.environ.get("CONFIG") or
                     f"{inputs.get('android_version', '?')}-{inputs.get('kernel_version', '?')}."
                     f"{inputs.get('sub_level', '?')}-{inputs.get('os_patch_level', '?')}"
                     + ("-" + str(inputs["revision"]) if inputs.get("revision") else ""))
    workspace = Path(os.environ.get("GITHUB_WORKSPACE", "."))
    kernel_root = Path(os.environ.get("KERNEL_ROOT", workspace / "kernel"))
    runner_temp = Path(os.environ.get("RUNNER_TEMP", "/nonexistent"))
    metadata = load_metadata(runner_temp / "cogan-companions" / "sources.json")
    report = format_notice(
        failures=failures, repository=repository, run_url=run_url,
        build=build, metadata=metadata,
        baka_sha=commit_for(kernel_root / "KernelSU"),
        susfs_sha=commit_for(workspace / "susfs4ksu"),
        nomount_sha=commit_for(kernel_root / "common" / "NoMount"))
    with summary_path.open("a", encoding="utf-8") as stream:
        stream.write("\n" + report)
    print("Generated component-specific failure summary and copy-ready English report.")


if __name__ == "__main__":
    main()
