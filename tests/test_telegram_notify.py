import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, "scripts")
import telegram_notify as m


class ReleaseNotificationTests(unittest.TestCase):
    def setUp(self):
        self.valid = {
            "GITHUB_REPOSITORY": m.OFFICIAL_REPO,
            "GITHUB_REPOSITORY_ID": m.OFFICIAL_REPO_ID,
            "COGAN_TELEGRAM_ENABLED": "true",
            "COGAN_TELEGRAM_CHANNEL_ID": "@CoganKernel",
            "COGAN_TELEGRAM_BOT_TOKEN": "fake-token-for-tests",
        }

    def test_manual_prerelease(self):
        with patch.dict(os.environ, {
            "COGAN_RELEASE_RUN_ID": "381012345",
            "COGAN_RELEASE_TYPE": "Pre-Release",
        }, clear=True):
            d = m.release_details("manual")
        self.assertTrue(d["prerelease"])
        self.assertEqual(d["tag"], "BakaSU-run-381012345")
        self.assertIn("Pre-Release / Pra-rilis", m.notification_text(d))
        self.assertIn("github.com/cogan17/GKI_BakaSU_SUSFS/releases/tag/", m.notification_text(d))

    def test_manual_stable_release(self):
        with patch.dict(os.environ, {
            "COGAN_RELEASE_RUN_ID": "381012345",
            "COGAN_RELEASE_TYPE": "Release",
        }, clear=True):
            d = m.release_details("manual")
        self.assertFalse(d["prerelease"])
        self.assertIn("Stable Release / Rilis Stabil", m.notification_text(d))

    def test_reject_arbitrary_notice(self):
        with self.assertRaises(ValueError):
            m.release_details("notice")

    def test_reject_invalid_release_type(self):
        with patch.dict(os.environ, {
            "COGAN_RELEASE_RUN_ID": "1234567",
            "COGAN_RELEASE_TYPE": "Test",
        }, clear=True):
            with self.assertRaises(ValueError):
                m.release_details("manual")

    def event_details(self, prerelease, draft=False, action="published"):
        event = {
            "action": action,
            "repository": {"full_name": m.OFFICIAL_REPO, "id": int(m.OFFICIAL_REPO_ID)},
            "release": {"tag_name": "v2.0", "name": "<Cogan & Friends>", "prerelease": prerelease,
                        "draft": draft, "published_at": "2026-10-11T00:00:00Z"}
        }
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".json") as f:
            json.dump(event, f)
            f.flush()
            with patch.dict(os.environ, {
                "GITHUB_EVENT_NAME": "release", "GITHUB_EVENT_PATH": f.name,
            }, clear=True):
                return m.release_details("published")

    def test_published_stable_release(self):
        d = self.event_details(False)
        self.assertFalse(d["prerelease"])
        self.assertIn("&lt;Cogan &amp; Friends&gt;", m.notification_text(d))

    def test_published_prerelease(self):
        d = self.event_details(True)
        self.assertTrue(d["prerelease"])

    def test_draft_is_not_announced(self):
        self.assertIsNone(self.event_details(True, draft=True))

    def test_edit_is_not_announced(self):
        self.assertIsNone(self.event_details(False, action="edited"))

    def test_disabled_sends_nothing(self):
        with patch.dict(os.environ, {**self.valid, "COGAN_TELEGRAM_ENABLED": "false"}, clear=True):
            with patch.object(m, "send") as sender:
                self.assertEqual(m.main("manual"), 0)
                sender.assert_not_called()

    def test_wrong_repository_sends_nothing(self):
        with patch.dict(os.environ, {**self.valid, "GITHUB_REPOSITORY_ID": "11111"}, clear=True):
            with patch.object(m, "send") as sender:
                self.assertEqual(m.main("manual"), 0)
                sender.assert_not_called()

    def test_one_channel_message_only(self):
        env = {**self.valid, "COGAN_RELEASE_RUN_ID": "381012345", "COGAN_RELEASE_TYPE": "Release"}
        with patch.dict(os.environ, env, clear=True):
            with patch.object(m, "send") as sender:
                self.assertEqual(m.main("manual"), 0)
                sender.assert_called_once()
                self.assertEqual(sender.call_args.args[1], "@CoganKernel")

    def test_no_secret_means_no_send(self):
        env = {**self.valid, "COGAN_RELEASE_RUN_ID": "381012345", "COGAN_RELEASE_TYPE": "Release",
               "COGAN_TELEGRAM_BOT_TOKEN": ""}
        with patch.dict(os.environ, env, clear=True):
            with patch.object(m, "send") as sender:
                self.assertEqual(m.main("manual"), 0)
                sender.assert_not_called()


if __name__ == "__main__":
    unittest.main()
