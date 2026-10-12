"""Check that Cogan workflow curation does not remove already finished work."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class CurationTests(unittest.TestCase):
    def test_custom_identity_and_all_default_features(self):
        text = (ROOT / ".github/workflows/kernel-custom.yml").read_text()
        for s in ('version: Cogan', 'ksu_branch: ""', 'clean_build: false',
                  'enable_susfs: true', 'supp_op: false', 'droidspaces: "off"',
                  'droidspaces_ntsync: false', 'build_bypass: false',
                  'default: "N"', 'default: "177"', 'default: "lts"',
                  'Default (automatic)'):
            self.assertIn(s, text)
        for feature in ('use_zram', 'use_nomount', 'use_bbg', 'use_rekernel',
                        'cve_2026_43499_patch'):
            self.assertIn('      ' + feature + ':', text)
            self.assertIn('      ' + feature + ': ' + '$' + '{{ inputs.' + feature, text)

    def test_advanced_options_are_not_discarded(self):
        text = (ROOT / ".github/workflows/main.yml").read_text()
        self.assertIn('name: Build Kernel (Advanced)', text)
        self.assertNotIn('Sun Dec 01 08:10:00 UTC 2024', text)
        self.assertIn('default: "N"', text)
        for option in ('clean_build', 'use_zram', 'use_bbg', 'use_rekernel',
                       'cve_2026_43499_patch', 'cancel_susfs', 'droidspaces',
                       'droidspaces_ntsync', 'build_bypass', 'build_target',
                       'build_kernel_version', 'kernel_version_filter',
                       'kernel_android_version', 'release_type', 'change_log'):
            self.assertIn('      ' + option + ':', text)
        self.assertIn('          - all', text)

    def test_original_cogan_integrity_gates(self):
        text = (ROOT / ".github/workflows/build.yml").read_text()
        for entry in ('component_sync_gate.py', 'flash_safety_gate.py verify',
                      'steps.companions.outputs.nomount_commit',
                      'Upload normal manager APK', 'Upload spoofed manager APK',
                      'Upload matching NoMount metamodule',
                      'Upload bundle source and checksum manifest',
                      'Upload ready-to-flash ZIP'):
            self.assertIn(entry, text)

    def test_all_language_documents_exist(self):
        for path in ('README.md', 'README.id.md', 'README.en.md',
                     'README.zh-CN.md'):
            text = (ROOT / path).read_text()
            for content in ('README.md', 'README.en.md', 'README.zh-CN.md', 'Cogan'):
                self.assertIn(content, text)


if __name__ == "__main__":
    unittest.main()
