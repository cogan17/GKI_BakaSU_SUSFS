"""Offline regression tests: malformed or mismatched ZIPs must fail closed."""
import json
from pathlib import Path
from types import SimpleNamespace
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import flash_safety_gate as g


STUB = """properties() { '
do.devicecheck=0
device.name1=
device.name2=
device.name3=
'; }
block=boot
is_slot_device=auto
. tools/ak3-core.sh
split_boot
flash_boot
"""


class FlashSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        (self.folder / "anykernel.sh").write_text(STUB)
        (self.folder / "tools").mkdir()
        (self.folder / "tools/ak3-core.sh").write_text("abort() { exit 1; }\n")
        img = bytearray(4096)
        img[0x38:0x3c] = b"ARMd"
        (self.folder / "Image").write_bytes(img)
        self.args = SimpleNamespace(android="android14", kernel="6.1", device="rothko",
                                    script=str(self.folder / "anykernel.sh"),
                                    directory=str(self.folder), zip=str(self.folder / "kernel.zip"))

    def make_zip(self):
        with zipfile.ZipFile(self.args.zip, "w") as z:
            for name in ("anykernel.sh", "Image", "tools/ak3-core.sh", g.MANIFEST):
                z.write(self.folder / name, name)

    def test_matching_device_and_kmi_bundle(self):
        g.prepare(self.args)
        self.assertIn("do.devicecheck=1", (self.folder / "anykernel.sh").read_text())
        self.assertIn("device.name1=rothko", (self.folder / "anykernel.sh").read_text())
        self.assertIn("android14-11", (self.folder / "anykernel.sh").read_text())
        g.stamp(self.args)
        self.make_zip()
        g.verify(self.args)

    def test_android_rom_version_is_not_used_as_kernel_kmi(self):
        self.assertIn("android14-11", g.expected_guard(self.args))
        self.assertNotIn("ro.build.version.release", g.expected_guard(self.args))

    def test_mismatched_codename_rejected(self):
        g.prepare(self.args)
        g.stamp(self.args)
        self.make_zip()
        wrong = SimpleNamespace(**vars(self.args))
        wrong.device = "degas"
        with self.assertRaises(ValueError):
            g.verify(wrong)

    def test_tampered_kernel_image_rejected(self):
        g.prepare(self.args)
        g.stamp(self.args)
        image = bytearray((self.folder / "Image").read_bytes())
        image[80] = 42
        (self.folder / "Image").write_bytes(image)
        self.make_zip()
        with self.assertRaises(ValueError):
            g.verify(self.args)

    def test_missing_guard_rejected(self):
        g.stamp if False else None
        with self.assertRaises(ValueError):
            g.assert_installer(STUB, self.args)

    def test_wrong_boot_partition_rejected(self):
        (self.folder / "anykernel.sh").write_text(STUB.replace("block=boot", "block=vendor_boot"))
        with self.assertRaises(ValueError):
            g.prepare(self.args)

    def test_duplicate_guard_rejected(self):
        g.prepare(self.args)
        with self.assertRaises(ValueError):
            g.prepare(self.args)

    def test_non_kernel_image_rejected(self):
        g.prepare(self.args)
        (self.folder / "Image").write_bytes(b"not an arm64 image")
        with self.assertRaises(ValueError):
            g.stamp(self.args)

    def test_corrupt_manifest_rejected(self):
        g.prepare(self.args)
        g.stamp(self.args)
        p = self.folder / g.MANIFEST
        data = json.loads(p.read_text())
        data["partition"] = "vendor_boot"
        p.write_text(json.dumps(data))
        self.make_zip()
        with self.assertRaises(ValueError):
            g.verify(self.args)

    def test_generic_kernel_still_checks_kmi_family(self):
        self.args.device = ""
        g.prepare(self.args)
        self.assertIn("android14-11", (self.folder / "anykernel.sh").read_text())
        g.stamp(self.args)
        self.make_zip()
        g.verify(self.args)


if __name__ == "__main__":
    unittest.main()
