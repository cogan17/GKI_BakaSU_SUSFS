"""Re-Kernel source layout tests; all fixtures are offline (no kernel build)."""
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import rekernel_source_gate as g


class ReKernelLayoutTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        base = Path(tmp.name)
        self.source = base / "LKM-Source"
        self.source.mkdir()
        self.common = base / "common"
        (self.common / "drivers").mkdir(parents=True)
        (self.common / "include/linux").mkdir(parents=True)
        (self.common / "drivers/Kconfig").write_text('menu "Drivers"\nendmenu\n')
        (self.common / "drivers/Makefile").write_text('obj-y += base/\n')
        (self.common / "include/linux/proc_fs.h").write_text("struct proc_ops { int n; };\n")
        self.defconfig = self.common / "gki_defconfig"
        self.defconfig.write_text("CONFIG_MODULES=y\n")

    def add_files(self, names):
        for name in names:
            (self.source / name).write_text("/* placeholder */\n")

    def test_split_layout_preserves_all_objects(self):
        self.add_files(g.SPLIT_C + g.SPLIT_HEADERS)
        (self.source / "rekernel_binder.c").write_text(
            "#include <../android/binder_internal.h>\n")
        g.stage(self.source, self.common, self.defconfig, "6.1")
        dest = self.common / "drivers/rekernel"
        for name in g.SPLIT_C + g.SPLIT_HEADERS:
            self.assertTrue((dest / name).is_file())
        makefile = (dest / "Makefile").read_text()
        for name in g.SPLIT_C:
            self.assertIn(name[:-2] + ".o", makefile)
        self.assertIn("CONFIG_REKERNEL=y", self.defconfig.read_text())
        self.assertIn("CONFIG_REKERNEL_NETWORK=y", self.defconfig.read_text())
        self.assertIn("binder_internal.h", (dest / "rekernel_binder.c").read_text())
        self.assertEqual((self.common / "drivers/Kconfig").read_text().count(g.SOURCE), 1)
        self.assertEqual((self.common / "drivers/Makefile").read_text().count(g.REGISTER), 1)

    def test_legacy_layout_adapts_without_global_warning_suppression(self):
        self.add_files(g.LEGACY_FILES)
        (self.source / "rekernel.c").write_text(
            "struct file_operations p = { .read = fn };\n")
        (self.source / "rekernel.h").write_text("// #define KERNEL_6_1\n")
        g.stage(self.source, self.common, self.defconfig, "6.1")
        code = (self.common / "drivers/rekernel/rekernel.c").read_text()
        self.assertIn("struct proc_ops", code)
        self.assertIn(".proc_read =", code)
        self.assertIn("#define KERNEL_6_1",
                      (self.common / "drivers/rekernel/rekernel.h").read_text())
        self.assertNotIn("-Wno-error", (self.common / "drivers/rekernel/Makefile").read_text())

    def test_missing_split_file_rejected_without_integration(self):
        self.add_files(g.SPLIT_C[:-1] + g.SPLIT_HEADERS)
        with self.assertRaises(ValueError):
            g.stage(self.source, self.common, self.defconfig, "6.1")
        self.assertFalse((self.common / "drivers/rekernel").exists())

    def test_mixed_legacy_and_split_rejected(self):
        self.add_files(g.LEGACY_FILES + g.SPLIT_C + ("rekernel_internal.h",))
        with self.assertRaises(ValueError):
            g.layout(self.source)

    def test_duplicate_registration_rejected(self):
        self.add_files(g.LEGACY_FILES)
        (self.common / "drivers/Makefile").write_text(g.REGISTER + "\n")
        with self.assertRaises(ValueError):
            g.stage(self.source, self.common, self.defconfig, "6.1")
        self.assertFalse((self.common / "drivers/rekernel").exists())

    def test_duplicate_run_rejected(self):
        self.add_files(g.LEGACY_FILES)
        g.stage(self.source, self.common, self.defconfig, "6.1")
        with self.assertRaises(ValueError):
            g.stage(self.source, self.common, self.defconfig, "6.1")

    def test_unsupported_kernel_rejected(self):
        self.add_files(g.LEGACY_FILES)
        with self.assertRaises(ValueError):
            g.stage(self.source, self.common, self.defconfig, "6.18")

    def test_cogan_workflow_retains_nomount_and_susfs_gates(self):
        wf = (Path(__file__).resolve().parents[1] / ".github/workflows/build.yml").read_text()
        self.assertIn("component_sync_gate.py", wf)
        self.assertIn("steps.companions.outputs.nomount_commit", wf)
        self.assertIn("flash_safety_gate.py verify", wf)
        self.assertIn("ac08296174d7fb2801c0eee1084f067a34f8a0fe", wf)
        self.assertIn("rekernel_source_gate.py", wf)
        self.assertIn("Apply NoMount", wf)


if __name__ == "__main__":
    unittest.main()
