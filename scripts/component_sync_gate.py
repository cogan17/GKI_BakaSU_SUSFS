#!/usr/bin/env python3
"""Fail-closed Cogan source/config/bundle cross-check. Only report mismatches.

BakaSU versionCode and NoMount versionCode are independent; they must NOT be
numerically equated. Device runtime/ABI safety still requires actual testing.
"""
import argparse
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import zipfile

BACKTICK = chr(96)
FENCE = BACKTICK * 3
DESTINATIONS = {
    "BakaSU": "https://github.com/Baka-SU/BakaSU/issues",
    "SUSFS": "https://gitlab.com/simonpunk/susfs4ksu",
    "NoMount": "https://github.com/maxsteeel/nomount/issues",
}


@dataclass(frozen=True)
class Issue:
    part: str
    reason: str
    evidence: str
    upstream: bool = False


def safe(value):
    return re.sub(r"[\x00-\x1f\x7f]", " ", str(value)).replace(BACKTICK, "'").replace("<", "(").replace(">", ")")[:240]


def git(source, *args):
    try:
        return subprocess.check_output(["git", "-C", str(source), *args],
                                       text=True, stderr=subprocess.DEVNULL,
                                       timeout=15).strip()
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return ""


def sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read(path):
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def add(issues, part, reason, proof, upstream=False):
    issues.append(Issue(part, reason, proof, upstream))


def _nomount_protocol(header):
    """Extract common ABI portions (user-space u32 and kernel u32 are equivalent)."""
    text = read(header)
    magic = re.search(r"^\s*#define\s+NOMOUNT_MAGIC_SIG\s+([^\s/]+)", text, re.M)
    cmd = re.search(r"enum\s*\{\s*(NM_CMD_UNSPEC.*?)\}\s*;", text, re.S)
    payload = re.search(
        r"struct\s+nm_payload\s*\{(.*?)\}\s*__attribute__\s*\(\(packed\)\)",
        text, re.S)
    if not (magic and cmd and payload):
        return None
    cmds = [re.sub(r"\s+", "", part) for part in cmd.group(1).split(",") if part.strip()]
    layout = []
    for field in payload.group(1).split(";"):
        field = re.sub(r"/\*.*?\*/", "", field, flags=re.S).strip()
        if not field:
            continue
        field = re.sub(r"\bu64\b", "unsigned long long", field)
        field = re.sub(r"\bu32\b", "unsigned int", field)
        field = re.sub(r"\bu16\b", "unsigned short", field)
        layout.append(" ".join(field.split()))
    return magic.group(1), cmds, layout


def check_nomount_protocol(source):
    """Compare NoMount kernel & userspace magic, command IDs and packed ABI."""
    k = _nomount_protocol(source / "kernel/src/nomount.h")
    u = _nomount_protocol(source / "userspace/src/nm.h")
    if k is None or u is None:
        return Issue("NoMount", "ABI NoMount tidak dapat diverifikasi.",
                     "Missing or changed NoMount kernel/userspace protocol definitions")
    if k != u:
        return Issue("NoMount", "ABI kernel NoMount dan userspace tidak sinkron.",
                     "NOMOUNT_MAGIC_SIG, NM_CMD IDs or packed nm_payload differ")
    return None


def check_sources(*, meta, bakasu, kernel, susfs, use_susfs, use_nomount, config,
                  stage="prebuild", module=None):
    """Return objective errors. Stage prepublish inspects the compiled .config."""
    issues = []
    baka_sha = meta.get("bakasu_commit", "")
    if not re.fullmatch(r"[a-f0-9]{40}", str(baka_sha)) or git(bakasu, "rev-parse", "HEAD") != baka_sha:
        add(issues, "BakaSU", "Commit BakaSU Manager dan kernel tidak cocok.",
            "sources.json:bakasu_commit versus KernelSU git HEAD")
    driver = meta.get("kernel_driver_version")
    managers = meta.get("managers")
    if not isinstance(driver, int) or driver < 1 or not isinstance(managers, dict):
        add(issues, "BakaSU", "Versi driver atau metadata manager belum terverifikasi.",
            "sources.json:kernel_driver_version/managers")
    else:
        for role in ("normal", "spoofed"):
            info = managers.get(role)
            if not isinstance(info, dict) or info.get("version_code") != driver:
                add(issues, "BakaSU", f"Manager {role} tidak sama dengan versi driver {driver}.",
                    f"sources.json:managers.{role}.version_code")
            elif not re.fullmatch(r"[0-9a-f]{64}", str(info.get("certificate_sha256", ""))):
                add(issues, "BakaSU", f"Sertifikat manager {role} tidak terverifikasi.",
                    f"sources.json:managers.{role}.certificate_sha256")
        if all(isinstance(managers.get(x), dict) for x in ("normal", "spoofed")):
            first, second = managers["normal"], managers["spoofed"]
            if first.get("certificate_sha256") != second.get("certificate_sha256"):
                add(issues, "BakaSU", "Sertifikat kedua APK manager tidak cocok.",
                    "sources.json:managers.normal/spoofed.certificate_sha256")
    flags = set(read(config).splitlines())
    if "CONFIG_KSU=y" not in flags or "CONFIG_KSU_DISABLE_MANAGER=y" in flags:
        add(issues, "Kernel", "Konfigurasi kernel tidak mengaktifkan BakaSU Manager bawaan.",
            "CONFIG_KSU=y; CONFIG_KSU_DISABLE_MANAGER must be disabled")
    if use_susfs:
        susfs_head = git(susfs, "rev-parse", "HEAD")
        if not re.fullmatch(r"[0-9a-f]{40}", susfs_head):
            add(issues, "SUSFS", "Sumber SUSFS tidak tersedia/terverifikasi.",
                "susfs4ksu checkout")
        elif stage == "prepublish" and meta.get("susfs_commit") != susfs_head:
            add(issues, "SUSFS", "Commit SUSFS berubah antara kompilasi dan publikasi.",
                f"sources.json:susfs_commit versus susfs checkout ({susfs_head})")
        elif stage == "prebuild" and meta.get("susfs_commit") not in (None, susfs_head):
            add(issues, "SUSFS", "Sumber SUSFS tidak sama dengan commit tercatat.",
                "sources.json:susfs_commit versus susfs checkout")
        if "CONFIG_KSU_SUSFS=y" not in flags:
            add(issues, "Kernel", "SUSFS diaktifkan pada workflow tetapi tidak di konfigurasi kernel.",
                "CONFIG_KSU_SUSFS=y missing")
        if stage == "prebuild":
            for file in ("fs/susfs.c", "include/linux/susfs.h"):
                if not (kernel / file).is_file():
                    add(issues, "SUSFS", "Sumber SUSFS tidak terintegrasi di kernel.",
                        f"common/{file} absent")
            kbuild = read(bakasu / "kernel/Kbuild")
            guard = read(bakasu / "kernel/tools/susfs_compat.mk")
            if "tools/susfs_compat.mk" in kbuild:
                directives = [line.strip() for line in guard.splitlines()
                              if line.strip() and not line.lstrip().startswith("#")]
                if not guard:
                    add(issues, "BakaSU", "Pemeriksaan kompatibilitas SUSFS upstream hilang.",
                        "BakaSU kernel/Kbuild includes missing tools/susfs_compat.mk")
                elif directives and directives[-1] == "$(error Please wait susfs update.)":
                    add(issues, "BakaSU", "BakaSU upstream memblokir SUSFS secara eksplisit.",
                        "BakaSU/kernel/tools/susfs_compat.mk: Please wait susfs update.",
                        upstream=True)
            rejects = list(kernel.rglob("*.rej"))
            if rejects:
                add(issues, "Kernel", "Patch kernel memiliki bagian yang ditolak.",
                    f"{len(rejects)} .rej file(s) need inspection before compilation")
    else:
        if stage == "prepublish" and "CONFIG_KSU_SUSFS=y" in flags:
            add(issues, "Kernel", "SUSFS aktif di Image meski tidak diminta.",
                "unexpected CONFIG_KSU_SUSFS=y")
    expected_nm = meta.get("nomount_commit")
    nm = kernel / "NoMount"
    if use_nomount:
        if not re.fullmatch(r"[a-f0-9]{40}", str(expected_nm or "")):
            add(issues, "NoMount", "Commit NoMount tidak terkunci pada satu sumber.",
                "sources.json:nomount_commit")
        elif git(nm, "rev-parse", "HEAD") != expected_nm:
            add(issues, "NoMount", "Commit NoMount kernel berbeda dari sumber yang dipilih.",
                "sources.json:nomount_commit versus common/NoMount git HEAD")
        if "CONFIG_NOMOUNT=y" not in flags:
            add(issues, "Kernel", "NoMount diminta tetapi driver bawaan tidak aktif.",
                "CONFIG_NOMOUNT=y missing")
        if stage == "prebuild":
            link = kernel / "fs/nomount"
            if not link.is_symlink() or link.resolve() != (nm / "kernel/src").resolve():
                add(issues, "NoMount", "Kernel tidak menggunakan sumber NoMount yang sama.",
                    "common/fs/nomount symlink versus common/NoMount/kernel/src")
            if "obj-$(CONFIG_NOMOUNT) += nomount/" not in read(kernel / "fs/Makefile"):
                add(issues, "NoMount", "NoMount tidak terdaftar untuk kompilasi kernel.",
                    "common/fs/Makefile missing CONFIG_NOMOUNT target")
            if 'source "fs/nomount/Kconfig"' not in read(kernel / "fs/Kconfig"):
                add(issues, "NoMount", "Kconfig NoMount tidak terintegrasi.",
                    "common/fs/Kconfig missing NoMount source")
            for file in ("kernel/src/Kconfig", "userspace/src/nm.c", "module/module.prop"):
                if not (nm / file).is_file():
                    add(issues, "NoMount", "Sumber NoMount kernel/userspace/metamodule tidak lengkap.",
                        f"common/NoMount/{file} missing", upstream=True)
            if git(nm, "rev-parse", "HEAD") == expected_nm:
                mismatch = check_nomount_protocol(nm)
                if mismatch:
                    issues.append(mismatch)
        else:
            if not module or not module.is_file():
                add(issues, "NoMount", "Paket NoMount untuk kernel ini tidak tersedia.",
                    "NoMount metamodule ZIP missing")
            else:
                try:
                    with zipfile.ZipFile(module) as archive:
                        if archive.testzip() is not None:
                            raise ValueError("Corrupt ZIP")
                        names = archive.namelist()
                        required = {"NOMOUNT_SOURCE_COMMIT", "module.prop", "customize.sh",
                                    "metamount.sh", "bin/nm-arm64"}
                        if not required.issubset(names):
                            raise ValueError("Missing module files")
                        stamped = archive.read("NOMOUNT_SOURCE_COMMIT").decode().strip()
                        if stamped != expected_nm:
                            raise ValueError("NoMount source stamp differs from kernel")
                        props = dict(line.split("=", 1) for line in
                                     archive.read("module.prop").decode().splitlines()
                                     if "=" in line)
                        count = git(nm, "rev-list", "--count", "HEAD")
                        if not count.isdecimal() or props.get("versionCode") != count:
                            raise ValueError("NoMount metamodule versionCode differs from source")
                        if f"Cogan built-in {count}-{expected_nm[:8]}" not in props.get("version", ""):
                            raise ValueError("NoMount metamodule version stamp differs from source")
                except (OSError, ValueError, UnicodeError, KeyError, zipfile.BadZipFile) as exc:
                    add(issues, "NoMount", "Paket NoMount tidak cocok dengan driver dalam kernel.",
                        str(exc))
    elif expected_nm:
        add(issues, "NoMount", "Commit NoMount tercatat meskipun fitur tidak diminta.",
            "sources.json:nomount_commit unexpectedly set")
    elif stage == "prepublish" and "CONFIG_NOMOUNT=y" in flags:
        add(issues, "Kernel", "NoMount aktif di Image meskipun tidak diminta.",
            "unexpected CONFIG_NOMOUNT=y")
    return issues


# Every generated issue has a distinct English explanation. Never insert the
# Indonesian owner-facing reason into the developer's copy-ready report.
ENGLISH_REASONS = {
    "ABI NoMount tidak dapat diverifikasi.": "The NoMount kernel/userspace ABI definitions could not be verified.",
    "ABI kernel NoMount dan userspace tidak sinkron.": "The NoMount kernel and userspace ABI definitions do not match.",
    "Commit BakaSU Manager dan kernel tidak cocok.": "The BakaSU Manager source commit does not match the kernel's BakaSU commit.",
    "Versi driver atau metadata manager belum terverifikasi.": "The manager metadata or kernel driver version has not been verified.",
    "Sertifikat kedua APK manager tidak cocok.": "The two official manager APKs have different signing certificate records.",
    "Konfigurasi kernel tidak mengaktifkan BakaSU Manager bawaan.": "The kernel configuration does not enable the required built-in BakaSU manager support.",
    "Sumber SUSFS tidak tersedia/terverifikasi.": "The checked-out SUSFS source commit is unavailable or unverified.",
    "Commit SUSFS berubah antara kompilasi dan publikasi.": "The SUSFS source commit changed between compilation and artifact publication.",
    "Sumber SUSFS tidak sama dengan commit tercatat.": "The checked-out SUSFS source commit differs from the recorded commit.",
    "SUSFS diaktifkan pada workflow tetapi tidak di konfigurasi kernel.": "SUSFS was enabled in the workflow but not in the kernel configuration.",
    "Sumber SUSFS tidak terintegrasi di kernel.": "Required SUSFS source files were not integrated into the kernel.",
    "Pemeriksaan kompatibilitas SUSFS upstream hilang.": "A SUSFS compatibility guard referenced by BakaSU is missing.",
    "BakaSU upstream memblokir SUSFS secara eksplisit.": "BakaSU upstream explicitly blocks compilation with the current SUSFS integration.",
    "Patch kernel memiliki bagian yang ditolak.": "One or more kernel patches have rejected hunks.",
    "SUSFS aktif di Image meski tidak diminta.": "SUSFS is enabled in the compiled Image although it was not requested.",
    "Commit NoMount tidak terkunci pada satu sumber.": "The NoMount source commit was not pinned.",
    "Commit NoMount kernel berbeda dari sumber yang dipilih.": "The kernel's NoMount checkout differs from the selected source commit.",
    "NoMount diminta tetapi driver bawaan tidak aktif.": "NoMount was requested but its built-in kernel driver is not enabled.",
    "Kernel tidak menggunakan sumber NoMount yang sama.": "The kernel's NoMount symlink points to a different source tree.",
    "NoMount tidak terdaftar untuk kompilasi kernel.": "NoMount is missing from the kernel build Makefile.",
    "Kconfig NoMount tidak terintegrasi.": "NoMount is missing from the kernel Kconfig integration.",
    "Sumber NoMount kernel/userspace/metamodule tidak lengkap.": "Required NoMount kernel, userspace, or metamodule source files are missing.",
    "Paket NoMount untuk kernel ini tidak tersedia.": "The NoMount metamodule ZIP for this kernel is unavailable.",
    "Paket NoMount tidak cocok dengan driver dalam kernel.": "The packaged NoMount metamodule does not match the kernel driver.",
    "Commit NoMount tercatat meskipun fitur tidak diminta.": "A NoMount source commit is present even though NoMount was disabled.",
    "NoMount aktif di Image meskipun tidak diminta.": "NoMount is enabled in the compiled Image although it was not requested.",
}
DYNAMIC_ENGLISH_REASONS = (
    (re.compile(r"Manager (normal|spoofed) tidak sama dengan versi driver (\d+)\."), lambda m: f"The {m[1]} manager version does not match kernel driver version {m[2]}."),
    (re.compile(r"Sertifikat manager (normal|spoofed) tidak terverifikasi\."), lambda m: f"The {m[1]} manager signing certificate record is unverified."),
)


def english_reason(reason):
    if reason in ENGLISH_REASONS:
        return ENGLISH_REASONS[reason]
    for pattern, translate in DYNAMIC_ENGLISH_REASONS:
        matched = pattern.fullmatch(reason)
        if matched:
            return translate(matched)
    # Fail explicitly rather than placing Indonesian text in a developer report.
    raise ValueError(f"Missing English bug-report translation: {reason}")


def render(issues, build, run_url, meta, stage, susfs_sha, nomount_sha):
    if not issues:
        return ""
    groups = {}
    for issue in issues:
        groups.setdefault(issue.part, []).append(issue)
    driver = safe(meta.get("kernel_driver_version", "not verified"))
    baka_sha = safe(meta.get("bakasu_commit", "not available"))
    out = ["<!-- COGAN_VERIFIED_COMPAT_FAILURE -->",
           "## ❌ BUILD GAGAL — Komponen tidak sinkron",
           "",
           "**Tindakan:** Build dihentikan; tidak ada paket baru yang boleh dipublikasikan.",
           f"**Konfigurasi:** {BACKTICK}{safe(build)}{BACKTICK}",
           f"**Pemeriksaan:** {safe(stage)}. [Lihat log build]({run_url}).", ""]
    for part, problems in groups.items():
        out.extend([f"### {safe(part)} — tidak sinkron", ""])
        for issue in problems:
            out.append(f"- **Penyebab:** {safe(issue.reason)} **Bukti:** {BACKTICK}{safe(issue.evidence)}{BACKTICK}.")
        out.append("")
        direct = any(x.upstream for x in problems)
        target = f"[{part}]({DESTINATIONS[part]})" if direct and part in DESTINATIONS else "integrasi Cogan terlebih dahulu"
        out.append(f"**Tujuan laporan:** {target}.")
        if direct and part in DESTINATIONS:
            out.append("**Kirim:** salin laporan Inggris di bawah ke halaman pengembang tersebut.")
        else:
            out.append("**Kirim:** laporan ini untuk pemeriksaan internal Cogan; jangan kirim ke upstream sebelum penyebab terkonfirmasi.")
        out.append("")
        observations = "\n".join(f"- {safe(english_reason(x.reason))} | Evidence: {safe(x.evidence)}" for x in problems)
        en = (f"Title: Build compatibility inquiry — {safe(part)} ({safe(build)})\n\n"
              "Hello maintainers,\n\n"
              "I maintain the Cogan kernel build repository. The validation gate found "
              "the following objective mismatches:\n\n"
              f"{observations}\n\n"
              f"BakaSU source: {baka_sha}\nBakaSU manager/driver version: {driver}\n"
              f"SUSFS source: {safe(susfs_sha)}\nNoMount source: {safe(nomount_sha)}\n"
              f"Build: {safe(build)}\nWorkflow: {run_url}\n\n"
              "This is a request for compatibility guidance, not an attribution of blame.\n"
              "The workflow does not bypass any kernel compatibility checks. Thank you.")
        out.extend(["<details>", f"<summary>English — Copy report: {safe(part)}</summary>", "",
                    f"**[Open failed workflow logs]({run_url})** — clickable link for the developer.",
                    "", f"{FENCE}text", en, FENCE, "", "</details>", ""])
    return "\n".join(out) + "\n"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--stage", choices=("prebuild", "prepublish"), required=True)
    p.add_argument("--metadata", type=Path, required=True)
    p.add_argument("--bakasu", type=Path, required=True)
    p.add_argument("--kernel", type=Path, required=True)
    p.add_argument("--susfs", type=Path, required=True)
    p.add_argument("--config", type=Path, required=True)
    p.add_argument("--nomount-module", type=Path)
    p.add_argument("--use-susfs", choices=("true", "false"), required=True)
    p.add_argument("--use-nomount", choices=("true", "false"), required=True)
    args = p.parse_args()
    try:
        meta = json.loads(args.metadata.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        meta = {}
    issues = check_sources(
        meta=meta, bakasu=args.bakasu, kernel=args.kernel,
        susfs=args.susfs, use_susfs=args.use_susfs == "true",
        use_nomount=args.use_nomount == "true", config=args.config,
        stage=args.stage, module=args.nomount_module)
    if not issues:
        # Freeze the exact SUSFS source used when building; the publishing gate
        # compares this pin with the original checkout. BakaSU/NoMount already
        # have their own commit pins from the manager/artifact resolver.
        if args.stage == "prebuild" and args.use_susfs == "true":
            susfs_commit = git(args.susfs, "rev-parse", "HEAD")
            if re.fullmatch(r"[0-9a-f]{40}", susfs_commit):
                meta["susfs_commit"] = susfs_commit
                args.metadata.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
        # Successful compatibility checks are intentionally silent.
        return
    server = os.environ.get("GITHUB_SERVER_URL", "https://github.com").rstrip("/")
    repo = os.environ.get("GITHUB_REPOSITORY", "unknown/repo")
    run = os.environ.get("GITHUB_RUN_ID", "")
    link = f"{server}/{repo}/actions/runs/{run}"
    msg = render(issues, os.environ.get("CONFIG", "unknown"), link,
                 meta, args.stage, git(args.susfs, "rev-parse", "HEAD") or "not available",
                 git(args.kernel / "NoMount", "rev-parse", "HEAD") or "not available")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as file:
            file.write("\n" + msg)
    print(f"::error title=Cross-component mismatch::{len(issues)} compatibility checks failed. See Actions Summary.")
    raise SystemExit(1)


if __name__ == "__main__":
    main()
