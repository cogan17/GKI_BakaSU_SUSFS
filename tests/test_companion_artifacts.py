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
import component_sync_gate as sync
from unittest import mock


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


class CrossComponentSync(unittest.TestCase):
    """Simulate matched/mismatched source bundles without building a real kernel."""

    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.root = Path(t.name)
        self.kernel = self.root / "common"
        self.baka = self.root / "KernelSU"
        self.susfs = self.root / "susfs4ksu"
        self.nomount = self.kernel / "NoMount"
        for path in (self.kernel / "fs", self.kernel / "include/linux",
                     self.baka / "kernel/tools", self.nomount / "kernel/src",
                     self.nomount / "userspace/src", self.nomount / "module",
                     self.susfs):
            path.mkdir(parents=True, exist_ok=True)
        (self.kernel / "fs/susfs.c").write_text("SUSFS source")
        (self.kernel / "include/linux/susfs.h").write_text("SUSFS header")
        (self.baka / "kernel/Kbuild").write_text("include $(KSU_SRC)/tools/susfs_compat.mk")
        (self.baka / "kernel/tools/susfs_compat.mk").write_text("# compatible\n")
        (self.kernel / "fs/nomount").symlink_to(self.nomount / "kernel/src")
        (self.kernel / "fs/Makefile").write_text("obj-$(CONFIG_NOMOUNT) += nomount/\n")
        (self.kernel / "fs/Kconfig").write_text('source "fs/nomount/Kconfig"\n')
        for part in ("kernel/src/Kconfig", "userspace/src/nm.c", "module/module.prop"):
            (self.nomount / part).write_text("content")
        common_def = """#define NOMOUNT_MAGIC_SIG 0x4E4F4D4F554E54ULL
enum { NM_CMD_UNSPEC, NM_CMD_GET_VERSION, NM_CMD_ADD_RULE, };
"""
        payload = """struct nm_payload {
  u64 magic;
  u32 cmd;
  u32 target_uid;
  int status;
  u32 arg1;
  u32 data_size;
  char buffer[4068];
} __attribute__((packed));
"""
        (self.nomount / "kernel/src/nomount.h").write_text(common_def + payload)
        (self.nomount / "userspace/src/nm.h").write_text(
            common_def + payload.replace("u64 ", "unsigned long long ").replace("u32 ", "unsigned int "))
        self.config = self.root / "defconfig"
        self.config.write_text("CONFIG_KSU=y\nCONFIG_KSU_SUSFS=y\nCONFIG_NOMOUNT=y\n")
        self.meta = {
            "bakasu_commit": "a" * 40, "kernel_driver_version": 35224,
            "nomount_commit": "b" * 40, "susfs_commit": "c" * 40,
            "managers": {
                role: {"version_code": 35224, "certificate_sha256": "1" * 64}
                for role in ("normal", "spoofed")
            },
        }

    def check(self, stage="prebuild"):
        # This isolates the version/ABI gate from the real external Git repos.
        def fake_git(path, *args):
            if args == ("rev-parse", "HEAD"):
                if path == self.baka:
                    return "a" * 40
                if path == self.susfs:
                    return "c" * 40
                if path == self.nomount:
                    return "b" * 40
            return "42" if args == ("rev-list", "--count", "HEAD") else ""
        with mock.patch.object(sync, "git", side_effect=fake_git):
            return sync.check_sources(
                meta=self.meta, bakasu=self.baka, kernel=self.kernel,
                susfs=self.susfs, use_susfs=True, use_nomount=True,
                config=self.config, stage=stage)

    def test_matched_sources_are_silent(self):
        self.assertEqual(self.check(), [])
        self.assertEqual(sync.render([], "r9", "https://github.com/x/y/actions/runs/1",
                                     self.meta, "prebuild", "c" * 40, "b" * 40), "")

    def test_manager_version_mismatch_reports_only_bakasu(self):
        self.meta["managers"]["normal"]["version_code"] = 35223
        self.assertEqual({issue.part for issue in self.check()}, {"BakaSU"})

    def test_nomount_abi_break_reports_only_nomount(self):
        h = self.nomount / "userspace/src/nm.h"
        h.write_text(h.read_text().replace("NM_CMD_ADD_RULE", "NM_CMD_DELETE_RULE"))
        self.assertEqual({issue.part for issue in self.check()}, {"NoMount"})

    def test_susfs_upstream_guard_reports_bakasu_not_blame_susfs(self):
        (self.baka / "kernel/tools/susfs_compat.mk").write_text(
            "# comment\n$(info -- BakaSU: Please wait simonpunk update)\n"
            "$(error Please wait susfs update.)\n")
        issues = self.check()
        self.assertEqual({i.part for i in issues}, {"BakaSU"})
        self.assertTrue(any(i.upstream for i in issues))

    def test_changes_to_susfs_commit_block_publishing(self):
        self.meta["susfs_commit"] = "d" * 40
        # Other expected prepublish requirements (NoMount ZIP) may also fail.
        self.assertTrue(any(i.part == "SUSFS" for i in self.check("prepublish")))

    def test_compiled_config_mismatch_blocks_publication(self):
        self.config.write_text("CONFIG_KSU=y\nCONFIG_NOMOUNT=y\n")
        self.assertIn("Kernel", {i.part for i in self.check("prepublish")})

    def test_unsupported_nomount_protocol_layout_fails_closed(self):
        (self.nomount / "userspace/src/nm.h").write_text("source changed")
        issues = self.check()
        self.assertTrue(any(i.part == "NoMount" for i in issues))



if __name__ == "__main__":
    unittest.main()
