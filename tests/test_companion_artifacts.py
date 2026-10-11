import argparse
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import companion_artifacts as companions
import prepare_bundle_release as release


def archive(entries):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name, data in entries.items():
            z.writestr(name, data)
    return buf.getvalue()


class MatchingSources(unittest.TestCase):
    def test_pr_and_wrong_commit_are_not_official_manager_sources(self):
        run = dict(head_sha="a" * 40, head_repository={"full_name": companions.BAKA},
                   path=".github/workflows/build-manager.yml", event="push",
                   status="completed", conclusion="success")
        self.assertTrue(companions.matching_run(run, "a" * 40))
        for field, bad in [("event", "pull_request"), ("head_sha", "b" * 40),
                           ("head_repository", {"full_name": "other/fork"}),
                           ("conclusion", "failure")]:
            self.assertFalse(companions.matching_run(dict(run, **{field: bad}), "a" * 40))

    def test_selects_universal_and_rejects_ambiguous_apks(self):
        self.assertEqual(companions.select_apk(archive({"arm64.apk": b"arm", "x-universal.apk": b"all"})), b"all")
        with self.assertRaises(ValueError):
            companions.select_apk(archive({"one.apk": b"1", "two.apk": b"2"}))

    def test_refuses_kernel_without_nomount_before_publishing(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            (p / "sources.json").write_text(json.dumps({"kernel_driver_version": 35223, "nomount_commit": "b" * 40}))
            (p / "config").write_text("CONFIG_KSU=y\n# CONFIG_NOMOUNT is not set\n")
            args = argparse.Namespace(directory=d, destination=str(p / "out"), config=str(p / "config"))
            with self.assertRaisesRegex(ValueError, "built-in NoMount"):
                companions.finalize(args)


class ReleaseBundles(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source, self.out = self.root / "in", self.root / "out"
        self.source.mkdir()
        self.entries = {
            "kernel": ("Cogan-BakaSU-AnyKernel3.zip", archive({"anykernel.sh": "echo", "Image": "image"})),
            "normal": ("Cogan-normal.apk", b"signed normal fixture"),
            "spoofed": ("Cogan-spoofed.apk", b"signed spoofed fixture"),
            "nomount": ("Cogan-NoMount-bbbbbbbbbbbb.zip", archive({
                "module.prop": "id=nomount\nmetamodule=true", "customize.sh": "echo",
                "metamount.sh": "echo", "bin/nm-arm64": "ELF fixture", "NOMOUNT_SOURCE_COMMIT": "b" * 40})),
        }
        self.manifest = dict(schema=1, source_run_id="42", workflow_commit="c" * 40,
                             bakasu_commit="a" * 40, nomount_commit="b" * 40,
                             manager_run_url="https://github.com/Baka-SU/BakaSU/actions/runs/1",
                             kernel_driver_version=35223,
                             files={role: {"name": name, "sha256": hashlib.sha256(data).hexdigest()}
                                    for role, (name, data) in self.entries.items()})
        for name, data in self.entries.values():
            (self.source / name).write_bytes(data)
        self.write_manifest()

    def write_manifest(self):
        (self.source / "Cogan-bundle.json").write_text(json.dumps(self.manifest))

    def prepare(self):
        return release.prepare(self.source, self.out, "42", "c" * 40, True)

    def test_complete_bundle_preserves_original_bytes(self):
        self.assertEqual(self.prepare(), 1)
        for name, data in self.entries.values():
            self.assertEqual((self.out / name).read_bytes(), data)
        self.assertTrue((self.out / "SHA256SUMS.txt").is_file())

    def test_missing_spoofed_blocks_release(self):
        (self.source / self.entries["spoofed"][0]).unlink()
        with self.assertRaisesRegex(ValueError, "Missing bundle file"):
            self.prepare()

    def test_modified_module_blocks_release(self):
        path = self.source / self.entries["nomount"][0]
        path.write_bytes(archive({"module.prop": "modified"}))
        with self.assertRaisesRegex(ValueError, "Checksum mismatch"):
            self.prepare()

    def test_missing_manifest_cannot_downgrade_to_legacy_release(self):
        (self.source / "Cogan-bundle.json").unlink()
        with self.assertRaisesRegex(ValueError, "missing its bundle manifest"):
            self.prepare()

    def test_missing_all_companions_cannot_downgrade_new_run(self):
        for p in self.source.iterdir():
            if not p.name.endswith("AnyKernel3.zip"):
                p.unlink()
        with self.assertRaises(ValueError):
            self.prepare()

    def test_wrong_run_and_workflow_block_release(self):
        for field, value in [("source_run_id", "43"), ("workflow_commit", "d" * 40)]:
            original = self.manifest[field]
            self.manifest[field] = value
            self.write_manifest()
            with self.assertRaises(ValueError):
                self.prepare()
            self.manifest[field] = original

    def test_disabled_nomount_bundle(self):
        (self.source / self.entries["nomount"][0]).unlink()
        del self.manifest["files"]["nomount"]
        self.manifest["nomount_commit"] = None
        self.write_manifest()
        self.assertEqual(self.prepare(), 1)

    def test_legacy_wrapped_zip_is_unwrapped_once(self):
        for p in self.source.iterdir():
            p.unlink()
        name, data = self.entries["kernel"]
        (self.source / "old_kernel-build.zip").write_bytes(archive({name: data}))
        self.assertEqual(release.prepare(self.source, self.out, "7"), 1)
        self.assertEqual((self.out / name).read_bytes(), data)
        self.assertIn("Legacy", (self.out / "release-notes.md").read_text())

    def test_clean_build_does_not_require_root_companions(self):
        for p in self.source.iterdir():
            p.unlink()
        (self.source / "Cogan-Clean-AnyKernel3.zip").write_bytes(self.entries["kernel"][1])
        self.assertEqual(self.prepare(), 1)


if __name__ == "__main__":
    unittest.main()
