#!/usr/bin/env python3
"""Publish original run files only; require every member of each matched bundle."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import zipfile


def digest(data):
    return hashlib.sha256(data).hexdigest()


def collect(directory):
    files = {}

    def add(name, data):
        if name in files and files[name] != data:
            raise ValueError(f"Conflicting artifacts named {name}")
        files[name] = data

    for path in directory.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix in (".apk", ".json"):
            add(path.name, path.read_bytes())
        elif path.suffix == ".zip":
            data = path.read_bytes()
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                names = archive.namelist()
                if "anykernel.sh" in names or "module.prop" in names:
                    add(path.name, data)  # archive:false upload; preserve bytes
                else:
                    # Legacy outer artifacts and normal upload-artifact archives.
                    for name in names:
                        leaf = Path(name).name
                        if leaf.endswith(("-AnyKernel3.zip", "-bundle.json", ".apk")) or (
                                "-NoMount-" in leaf and leaf.endswith(".zip")):
                            add(leaf, archive.read(name))
    return files


def prepare(source, destination, run_id, workflow_commit=None, require_bundle=False):
    files = collect(source)
    manifests = {name: json.loads(data) for name, data in files.items() if name.endswith("-bundle.json")}
    kernels = {name for name in files if name.endswith("-AnyKernel3.zip")}
    if not kernels:
        raise ValueError("No AnyKernel3 kernel ZIP found")
    rooted_kernels = {name for name in kernels if not name.endswith("-Clean-AnyKernel3.zip")}
    if not manifests and (require_bundle and rooted_kernels or any(name.endswith(".apk") for name in files)):
        raise ValueError("Matched build is missing its bundle manifest; refusing a partial release")
    selected, covered = {}, set()
    notes = [f"# Cogan build run {run_id}", "", "Original files from this run; no newer components were fetched.", ""]
    for name, manifest in manifests.items():
        if manifest.get("schema") != 1 or str(manifest.get("source_run_id")) != str(run_id):
            raise ValueError(f"Wrong bundle schema or source run: {name}")
        if workflow_commit and manifest.get("workflow_commit") != workflow_commit:
            raise ValueError(f"Wrong workflow commit: {name}")
        members = manifest["files"]
        required = {"normal", "spoofed", "kernel"}
        if manifest.get("nomount_commit"):
            required.add("nomount")
        if set(members) != required:
            raise ValueError(f"Missing or unexpected bundle components: {name}")
        for info in members.values():
            filename = info["name"]
            if Path(filename).name != filename or filename not in files:
                raise ValueError(f"Missing bundle file: {filename}")
            if digest(files[filename]) != info["sha256"]:
                raise ValueError(f"Checksum mismatch: {filename}")
            selected[filename] = files[filename]
        covered.add(members["kernel"]["name"])
        selected[name] = files[name]
        notes += [f"## {members['kernel']['name']}", "",
                  f"- BakaSU kernel and both managers: `{manifest['bakasu_commit']}`",
                  f"- Driver / manager version code: `{manifest['kernel_driver_version']}`",
                  f"- Official manager run: {manifest['manager_run_url']}",
                  f"- NoMount driver / metamodule: `{manifest.get('nomount_commit') or 'disabled'}`", ""]
    if manifests and covered != rooted_kernels:
        raise ValueError("Some kernel artifacts have no matching bundle manifest")
    for name in kernels - rooted_kernels:
        selected[name] = files[name]
    if not manifests:
        # Explicit backwards compatibility: do not claim old runs are matched bundles.
        selected = {name: files[name] for name in kernels}
        notes += ["Legacy / kernel-only run. Matching manager and NoMount artifacts are unavailable.", ""]
    for name in kernels:
        with zipfile.ZipFile(io.BytesIO(selected[name])) as archive:
            if not {"anykernel.sh", "Image"}.issubset(archive.namelist()) or archive.testzip():
                raise ValueError(f"Invalid kernel ZIP: {name}")
    for name, data in selected.items():
        if "-NoMount-" in name and name.endswith(".zip"):
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                if not {"module.prop", "customize.sh", "metamount.sh", "bin/nm-arm64", "NOMOUNT_SOURCE_COMMIT"}.issubset(archive.namelist()) or archive.testzip():
                    raise ValueError(f"Invalid NoMount metamodule: {name}")
    destination.mkdir(parents=True, exist_ok=True)
    if any(destination.iterdir()):
        raise ValueError("Release destination must be empty")
    for name, data in selected.items():
        (destination / name).write_bytes(data)
    (destination / "SHA256SUMS.txt").write_text("".join(f"{digest(data)}  {name}\n" for name, data in sorted(selected.items())))
    notes += ["## Installation / Pemasangan", "",
              "1. Install ONE manager APK: normal OR spoofed (both are official signed BakaSU builds).",
              "2. Flash the matching AnyKernel3 kernel ZIP, then reboot.",
              "3. If provided, install the matching NoMount ZIP through BakaSU, then reboot.",
              "", "NoMount is a metamodule for the built-in driver, not another kernel ZIP.",
              "Source/signature/version checks do not replace testing on your device.", ""]
    (destination / "release-notes.md").write_text("\n".join(notes))
    return len(kernels)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--workflow-commit")
    parser.add_argument("--require-bundle", action="store_true")
    args = parser.parse_args()
    count = prepare(args.source, args.destination, args.run_id, args.workflow_commit, args.require_bundle)
    print(f"Validated {count} kernel bundle(s) for release")
