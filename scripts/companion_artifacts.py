#!/usr/bin/env python3
"""Fetch official, same-commit BakaSU APKs and record a verifiable build bundle."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import urllib.parse
import zipfile

BAKA = "Baka-SU/BakaSU"
ARTIFACTS = {"normal": "Manager-release", "spoofed": "Spoofed-Manager-release"}


def run(*args):
    return subprocess.check_output(args, text=True).strip()


def api(endpoint):
    return json.loads(run("gh", "api", endpoint))


def pages(endpoint, key):
    separator = "&" if "?" in endpoint else "?"
    for page in range(1, 11):
        items = api(f"{endpoint}{separator}per_page=100&page={page}")[key]
        yield from items
        if len(items) < 100:
            break


def sha256(path):
    with open(path, "rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def output(key, value):
    if "GITHUB_OUTPUT" in os.environ:
        with open(os.environ["GITHUB_OUTPUT"], "a") as stream:
            stream.write(f"{key}={value}\n")


def resolve_ref(repo, ref):
    sha = api(f"repos/{repo}/commits/{urllib.parse.quote(ref, safe='')}")["sha"]
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise ValueError("Invalid source commit")
    return sha


def matching_run(item, commit):
    return (item.get("head_sha") == commit
            and item.get("head_repository", {}).get("full_name") == BAKA
            and item.get("path") == ".github/workflows/build-manager.yml"
            and item.get("event") in ("push", "workflow_dispatch")
            and item.get("status") == "completed"
            and item.get("conclusion") == "success")


def select_apk(data):
    # Upstream repack artifacts contain complete, signed universal APKs, not
    # the intermediate Gradle APKs that lack the userspace daemon.
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        apks = [x for x in archive.namelist() if x.endswith(".apk")]
        universal = [x for x in apks if "universal" in Path(x).name.lower()]
        selected = universal or apks
        if len(selected) != 1:
            raise ValueError(f"Expected one universal release APK, found {selected}")
        return archive.read(selected[0])


def fetch(args):
    commit = resolve_ref(BAKA, args.ref or "main")
    selected = None
    endpoint = f"repos/{BAKA}/actions/runs?head_sha={commit}&status=success"
    for item in pages(endpoint, "workflow_runs"):
        if not matching_run(item, commit):
            continue
        artifacts = list(pages(f"repos/{BAKA}/actions/runs/{item['id']}/artifacts", "artifacts"))
        by_name = {a["name"]: a for a in artifacts if not a["expired"]}
        if all(name in by_name for name in ARTIFACTS.values()):
            selected = item, by_name
            break
    if selected is None:
        raise ValueError(f"No complete official normal/spoofed manager pair for {commit}. "
                         "Wait for BakaSU's Build Manager run to finish, or select a commit "
                         "with available release artifacts. No different-version fallback is allowed.")
    item, artifacts = selected
    destination = Path(args.directory)
    destination.mkdir(parents=True, exist_ok=True)
    metadata = {"schema": 1, "bakasu_commit": commit, "manager_run_id": item["id"],
                "manager_run_url": item["html_url"], "managers": {}, "nomount_commit": None}
    for variant, artifact_name in ARTIFACTS.items():
        artifact = artifacts[artifact_name]
        data = subprocess.check_output(["gh", "api", f"repos/{BAKA}/actions/artifacts/{artifact['id']}/zip"])
        digest = "sha256:" + hashlib.sha256(data).hexdigest()
        if not artifact.get("digest") or digest != artifact["digest"]:
            raise ValueError(f"Artifact digest mismatch or missing digest: {artifact_name}")
        path = destination / f"{variant}.apk"
        path.write_bytes(select_apk(data))
        metadata["managers"][variant] = {"artifact_id": artifact["id"],
                                         "artifact_digest": digest, "sha256": sha256(path)}
    if args.nomount:
        metadata["nomount_commit"] = resolve_ref("maxsteeel/nomount", "dev")
    (destination / "sources.json").write_text(json.dumps(metadata, indent=2) + "\n")
    output("bakasu_commit", commit)
    output("nomount_commit", metadata["nomount_commit"] or "")
    print(f"Pinned BakaSU {commit}; official manager run {item['id']}")


def android_tool(name):
    sdk = Path(os.environ.get("ANDROID_HOME") or os.environ["ANDROID_SDK_ROOT"])
    candidates = sorted(sdk.glob(f"build-tools/*/{name}"))
    if not candidates:
        raise ValueError(f"Android build tool unavailable: {name}")
    return str(candidates[-1])


def verify(args):
    directory, source = Path(args.directory), Path(args.source)
    metadata = json.loads((directory / "sources.json").read_text())
    if run("git", "-C", str(source), "rev-parse", "HEAD") != metadata["bakasu_commit"]:
        raise ValueError("Kernel BakaSU source differs from official managers")
    kbuild = (source / "kernel/Kbuild").read_text()
    gradle = (source / "manager/build.gradle.kts").read_text()
    # Fail closed if upstream changes either version formula.
    if ("expr 30000 + $(KSU_LOCAL_VERSION) + 700" not in kbuild
            or "30000 + getGitCommitCount() + 700" not in gradle):
        raise ValueError("Upstream version formula changed; update the verifier before building")
    version = 30700 + int(run("git", "-C", str(source), "rev-list", "--count", "HEAD"))
    sign_header = (source / "kernel/manager/manager_sign.h").read_text()
    expected_hash = re.search(r'#define EXPECTED_HASH_BAKASU "([0-9a-f]{64})"', sign_header).group(1)
    expected_package = re.search(r'extra\["defaultManagerPackageName"\] = "([^"]+)"', gradle).group(1)
    for variant, info in metadata["managers"].items():
        apk = directory / f"{variant}.apk"
        if sha256(apk) != info["sha256"]:
            raise ValueError("APK changed after download")
        cert = run(android_tool("apksigner"), "verify", "--print-certs", str(apk))
        hashes = re.findall(r"Signer #\d+ certificate SHA-256 digest: ([0-9a-fA-F]+)", cert)
        if [h.lower() for h in hashes] != [expected_hash]:
            raise ValueError(f"{variant} APK signature is not the official BakaSU key accepted by this kernel")
        badging = run(android_tool("aapt"), "dump", "badging", str(apk))
        match = re.search(r"package: name='([^']+)' versionCode='([0-9]+)' versionName='([^']*)'", badging)
        if not match or int(match[2]) != version:
            raise ValueError(f"{variant} APK versionCode differs from kernel {version}")
        if (variant == "normal") != (match[1] == expected_package):
            raise ValueError("Normal/spoofed package identity mismatch")
        with zipfile.ZipFile(apk) as archive:
            if "lib/arm64-v8a/libksud.so" not in archive.namelist():
                raise ValueError("APK is missing the arm64 userspace daemon")
        info.update(version_code=version, version_name=match[3], package=match[1], certificate_sha256=expected_hash)
    metadata["kernel_driver_version"] = version
    (directory / "sources.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(f"Both signed managers match kernel driver version {version}")


def finalize(args):
    directory, destination = Path(args.directory), Path(args.destination)
    metadata = json.loads((directory / "sources.json").read_text())
    if "kernel_driver_version" not in metadata:
        raise ValueError("Managers have not passed signature/version verification")
    config = Path(args.config).read_text().splitlines()
    if "CONFIG_KSU=y" not in config:
        raise ValueError("Compiled kernel does not contain built-in BakaSU")
    if "CONFIG_KSU_DISABLE_MANAGER=y" in config:
        raise ValueError("Compiled kernel disables manager support")
    if metadata["nomount_commit"] and "CONFIG_NOMOUNT=y" not in config:
        raise ValueError("Compiled kernel does not contain built-in NoMount")
    # Fail closed if verified APK bytes or version metadata changed.
    for variant in ARTIFACTS:
        info = metadata["managers"][variant]
        if sha256(directory / f"{variant}.apk") != info["sha256"]:
            raise ValueError(f"{variant} manager modified after verification")
        if info.get("version_code") != metadata["kernel_driver_version"]:
            raise ValueError(f"{variant} manager/driver version mismatch")
        if not re.fullmatch(r"[0-9a-f]{64}", info.get("certificate_sha256", "")):
            raise ValueError(f"{variant} manager certificate record missing")
    if metadata["managers"]["normal"]["certificate_sha256"] != metadata["managers"]["spoofed"]["certificate_sha256"]:
        raise ValueError("Official manager signing certificates disagree")
    destination.mkdir(parents=True, exist_ok=True)
    files = {}
    for variant in ARTIFACTS:
        name = f"{args.prefix}-BakaSU-{metadata['kernel_driver_version']}-{variant}.apk"
        (destination / name).write_bytes((directory / f"{variant}.apk").read_bytes())
        files[variant] = {"name": name, "sha256": sha256(destination / name)}
    kernel = Path(args.kernel)
    files["kernel"] = {"name": kernel.name, "sha256": sha256(kernel)}
    if metadata["nomount_commit"]:
        module = Path(args.module)
        with zipfile.ZipFile(module) as archive:
            if archive.read("NOMOUNT_SOURCE_COMMIT").decode().strip() != metadata["nomount_commit"]:
                raise ValueError("NoMount module/kernel commit mismatch")
        files["nomount"] = {"name": module.name, "sha256": sha256(module)}
    metadata.update(files=files, source_run_id=os.environ["GITHUB_RUN_ID"],
                    workflow_commit=os.environ["GITHUB_SHA"],
                    validation="Source commits, APK signatures/versions, daemon presence and compiled config checked; device testing still required.")
    (destination / f"{args.prefix}-bundle.json").write_text(json.dumps(metadata, indent=2) + "\n")
    with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as summary:
        summary.write("\n## Paket terintegrasi / Matched bundle / 配套文件\n\n")
        summary.write(f"BakaSU `{metadata['bakasu_commit']}` · driver/manager `{metadata['kernel_driver_version']}`\n\n")
        summary.write(f"[Official manager source run]({metadata['manager_run_url']})\n\n")
        for role, info in files.items():
            summary.write(f"- {role}: `{info['name']}`\n")
        summary.write("\nPilih satu APK manager. Flash kernel dan reboot sebelum memasang NoMount. "
                      "Kecocokan sumber telah diperiksa; fungsi di perangkat belum diuji.\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    p = commands.add_parser("fetch")
    p.add_argument("--ref", default="main")
    p.add_argument("--directory", required=True)
    p.add_argument("--nomount", action="store_true")
    p.set_defaults(func=fetch)
    p = commands.add_parser("verify")
    p.add_argument("--directory", required=True)
    p.add_argument("--source", required=True)
    p.set_defaults(func=verify)
    p = commands.add_parser("finalize")
    for name in ("directory", "destination", "config", "prefix", "kernel"):
        p.add_argument(f"--{name}", required=True)
    p.add_argument("--module", default="")
    p.set_defaults(func=finalize)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
