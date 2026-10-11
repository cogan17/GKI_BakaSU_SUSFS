import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, "scripts")
import telegram_notify as m


class TelegramTargetTests(unittest.TestCase):
    def test_missing_target_defaults_to_channel(self):
        with patch.dict(os.environ, {"COGAN_TELEGRAM_CHANNEL_ID": "@CoganKernel"}, clear=True):
            self.assertEqual(m.destinations(), [("channel", {"chat_id": "@CoganKernel"})])

    def test_empty_target_defaults_to_channel(self):
        with patch.dict(os.environ, {"COGAN_TELEGRAM_TARGET": "", "COGAN_TELEGRAM_CHANNEL_ID": "@CoganKernel"}, clear=True):
            self.assertEqual(m.destinations(), [("channel", {"chat_id": "@CoganKernel"})])

    def test_whitespace_target_defaults_to_channel(self):
        with patch.dict(os.environ, {"COGAN_TELEGRAM_TARGET": "  ", "COGAN_TELEGRAM_CHANNEL_ID": "@CoganKernel"}, clear=True):
            self.assertEqual(m.destinations(), [("channel", {"chat_id": "@CoganKernel"})])

    def test_invalid_target_still_fails(self):
        with patch.dict(os.environ, {"COGAN_TELEGRAM_TARGET": "elsewhere", "COGAN_TELEGRAM_CHANNEL_ID": "@CoganKernel"}, clear=True):
            with self.assertRaises(ValueError):
                m.destinations()

    def test_disabled_does_not_send(self):
        with patch.dict(os.environ, {"GITHUB_REPOSITORY": m.OFFICIAL_REPO, "COGAN_TELEGRAM_ENABLED": "false"}, clear=True):
            with patch.object(m, "send") as sender:
                self.assertEqual(m.main("notice"), 0)
                sender.assert_not_called()


if __name__ == "__main__":
    unittest.main()
