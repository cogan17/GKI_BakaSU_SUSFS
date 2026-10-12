#!/usr/bin/env python3
"""Fail-closed AnyKernel3 installer and bundle validation; no device flashing."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import zipfile

MANIFEST = "COGAN_FLASH_GUARD.json"
BEGIN = "# BEGIN COGAN PRE-FLASH SAFETY CHECK"
END = "# END COGAN PRE-FLASH SAFETY CHECK"
KNOWN_KMI = {
    ("android14", "6.1"): "android14-11",
    ("android15", "6.6"): "android15-8",
    ("android16", "6.12"): "android16-5",
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def parameters(args):
    if not re.fullmatch(r"android(?:12|13|14|15|16|17)", args.android):
        raise ValueError("Unsupported Android GKI source branch")
    if not re.fullmatch(r"(?:5\.10|5\.15|6\.1|6\.6|6\.12|6\.18)", args.kernel):
        raise ValueError("Unsupported GKI kernel family")
    if args.device and not re.fullmatch(r"[a-z0-9_-]+", args.device):
        raise ValueError("Unsafe device codename")
    kmi = KNOWN_KMI.get((args.android, args.kernel))
    label = re.escape(kmi or args.android)
    suffix = "" if kmi else "-[0-9]+"
    expression = rf"^{re.escape(args.kernel)}\.[0-9]+-{label}{suffix}($|-)"
    return expression, kmi or f"{args.android}-<unverified KMI generation>"


def expected_guard(args):
    expression, label = parameters(args)
    # The host Android version can be newer than the Android GKI branch:
    # e.g. Android 16 with a 6.1.x-android14-11 running kernel.
    return "\n".join((
        BEGIN,
        'cogan_running_kernel="$(uname -r 2>/dev/null)"',
        f'printf "%s\\n" "$cogan_running_kernel" | grep -Eq \'{expression}\' || abort "Cogan safety: running kernel KMI mismatch (expected {label}, {args.kernel}.x). Refusing to flash."',
        'ui_print "Cogan: running kernel KMI verified before flashing."',
        END,
    ))


def assert_installer(script, args):
    expression, label = parameters(args)
    del expression, label
    if script.count(BEGIN) != 1 or script.count(END) != 1:
        raise ValueError("Installer is missing the unique pre-flash guard")
    if expected_guard(args) not in script:
        raise ValueError("Installer guard does not match this GKI build")
    if len(re.findall(r"^block=", script, re.M)) != 1 or not re.search(r"^block=boot\s*$", script, re.M):
        raise ValueError("Installer must flash only the boot partition")
    if script.find(BEGIN) < script.find(". tools/ak3-core.sh"):
        raise ValueError("Guard executes before AnyKernel3 abort helpers are loaded")
    if "split_boot" not in script or script.find(END) > script.find("split_boot"):
        raise ValueError("Guard is not ahead of the boot flashing procedure")
    if args.device:
        if not re.search(r"^do\.devicecheck=1\s*$", script, re.M):
            raise ValueError("Target device verification is disabled")
        if not re.search(rf"^device\.name1={re.escape(args.device)}\s*$", script, re.M):
            raise ValueError("Expected device codename is missing")
        extra = re.findall(r"^device\.name[2-9]=(.*)$", script, re.M)
        if any(x.strip() for x in extra):
            raise ValueError("Unexpected additional permitted devices")


def prepare(args):
    path = Path(args.script)
    script = path.read_text()
    if BEGIN in script or END in script:
        raise ValueError("Refusing duplicate or partially modified installer")
    if len(re.findall(r"^\. tools/ak3-core\.sh\s*$", script, re.M)) != 1:
        raise ValueError("Unknown AnyKernel3 installer structure")
    if len(re.findall(r"^block=", script, re.M)) != 1 or not re.search(r"^block=boot\s*$", script, re.M):
        raise ValueError("Unknown or unsafe boot partition selection")
    if args.device:
        for key, value in (("do.devicecheck", "1"), ("device.name1", args.device)):
            pattern = rf"^{re.escape(key)}=.*$"
            if len(re.findall(pattern, script, re.M)) != 1:
                raise ValueError(f"Missing/duplicate AnyKernel3 property {key}")
            script = re.sub(pattern, lambda match: f"{key}={value}", script, count=1, flags=re.M)
        script = re.sub(r"^device\.name([2-9])=.*$", r"device.name\1=", script, flags=re.M)
    script = re.sub(r"^\. tools/ak3-core\.sh\s*$",
                    lambda _: ". tools/ak3-core.sh\n\n" + expected_guard(args),
                    script, count=1, flags=re.M)
    assert_installer(script, args)
    path.write_text(script)
    print("Prepared fail-closed Cogan installer guard (no partition written)")


def record(directory, args):
    script = (directory / "anykernel.sh").read_bytes()
    assert_installer(script.decode(), args)
    image = (directory / "Image").read_bytes()
    if len(image) < 64 or image[0x38:0x3c] != b"ARMd":
        raise ValueError("Image is missing the arm64 Linux kernel header")
    return {"schema": 1, "android": args.android, "kernel": args.kernel,
            "device": args.device or "", "partition": "boot",
            "kmi": parameters(args)[1],
            "anykernel_sha256": sha(script), "image_sha256": sha(image)}


def stamp(args):
    folder = Path(args.directory)
    info = record(folder, args)
    (folder / MANIFEST).write_text(json.dumps(info, sort_keys=True, indent=2) + "\n")
    print("Stamped Cogan image and installer hashes")


def verify(args):
    with zipfile.ZipFile(args.zip) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or archive.testzip() is not None:
            raise ValueError("Corrupt or duplicate ZIP entries")
        if any(name.startswith("/") or ".." in Path(name).parts for name in names):
            raise ValueError("Unsafe ZIP member path")
        required = {"Image", "anykernel.sh", "tools/ak3-core.sh", MANIFEST}
        if not required.issubset(set(names)):
            raise ValueError("Incomplete flashable kernel ZIP")
        info = json.loads(archive.read(MANIFEST))
        if (info.get("schema") != 1 or info.get("android") != args.android
                or info.get("kernel") != args.kernel or info.get("device") != (args.device or "")
                or info.get("partition") != "boot" or info.get("kmi") != parameters(args)[1]):
            raise ValueError("ZIP target does not match this build")
        script = archive.read("anykernel.sh")
        image = archive.read("Image")
        if sha(script) != info.get("anykernel_sha256") or sha(image) != info.get("image_sha256"):
            raise ValueError("Kernel Image or installer was modified after stamping")
        assert_installer(script.decode(), args)
        if len(image) < 64 or image[0x38:0x3c] != b"ARMd":
            raise ValueError("ZIP does not contain a valid arm64 Image header")
    print("Kernel ZIP flash guard, Image header and hashes verified")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("prepare", "stamp", "verify"):
        p = sub.add_parser(name)
        p.add_argument("--android", required=True)
        p.add_argument("--kernel", required=True)
        p.add_argument("--device", default="")
        if name == "prepare":
            p.add_argument("--script", required=True)
        if name == "stamp":
            p.add_argument("--directory", required=True)
        if name == "verify":
            p.add_argument("--zip", required=True)
    args = parser.parse_args()
    try:
        {"prepare": prepare, "stamp": stamp, "verify": verify}[args.command](args)
    except (ValueError, OSError, zipfile.BadZipFile, KeyError, UnicodeDecodeError) as error:
        print(f"::error title=Cogan flash safety gate::{error}", file=sys.stderr)
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
