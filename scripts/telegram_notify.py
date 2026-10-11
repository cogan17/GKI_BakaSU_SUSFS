#!/usr/bin/env python3
"""Opt-in Telegram notifications for official Cogan GitHub Actions.

This sender never reads the legacy upstream BOT_TOKEN/CHAT_ID secrets.
Until COGAN_TELEGRAM_ENABLED=true and new destination secrets are configured,
it makes no network requests.
"""

import html
import json
import os
import re
import sys
from urllib import error, request

OFFICIAL_REPO = "cogan17/GKI_BakaSU_SUSFS"
API_TIMEOUT = 15


def escape(value: str) -> str:
    return html.escape(str(value), quote=True)


def notification_text(kind: str) -> str:
    if kind == "release":
        run_id = os.environ.get("COGAN_RELEASE_RUN_ID", "")
        if not re.fullmatch(r"[0-9]+", run_id):
            raise ValueError("COGAN_RELEASE_RUN_ID must be a numeric GitHub Actions run ID")
        release_type = os.environ.get("COGAN_RELEASE_TYPE", "Release")
        tag = f"BakaSU-run-{run_id}"
        url = f"https://github.com/{OFFICIAL_REPO}/releases/tag/{tag}"
        return (
            "<b>New official Cogan kernel release</b>\n\n"
            f"Type: <code>{escape(release_type)}</code>\n"
            f"Tag: <code>{escape(tag)}</code>\n"
            f'<a href="{escape(url)}">Download verified release bundle</a>\n\n'
            "Independent community project; verify device and kernel compatibility before flashing."
        )
    if kind == "notice":
        message_type = os.environ.get("COGAN_NOTICE_TYPE", "notice")[:120]
        content = os.environ.get("COGAN_NOTICE_CONTENT", "")
        if not content.strip():
            raise ValueError("COGAN_NOTICE_CONTENT must not be blank")
        # Telegram sendMessage allows up to 4096 characters after entity parsing.
        content = content[:3200]
        return (
            "<b>Cogan project notification</b>\n\n"
            f"Type: <code>{escape(message_type)}</code>\n\n"
            f"<pre>{escape(content)}</pre>\n\n"
            f'<a href="https://github.com/{OFFICIAL_REPO}">Official Cogan repository</a>'
        )
    raise ValueError("Unknown notification kind")


def destinations():
    channel_id = os.getenv("COGAN_TELEGRAM_CHANNEL_ID", "").strip()
    group_id = os.getenv("COGAN_TELEGRAM_GROUP_ID", "").strip()
    thread_id = os.getenv("COGAN_TELEGRAM_GROUP_THREAD_ID", "").strip()
    result = []
    for label, chat_id in (("channel", channel_id), ("group", group_id)):
        if not chat_id:
            continue
        # Require numeric chat IDs: no hardcoded or unexpected @handle destinations.
        if not re.fullmatch(r"-?[0-9]{5,20}", chat_id):
            raise ValueError(f"Invalid {label} chat ID (expected numeric Telegram ID)")
        payload = {"chat_id": chat_id}
        if label == "group" and thread_id:
            if not re.fullmatch(r"[1-9][0-9]*", thread_id):
                raise ValueError("Group message thread ID must be a positive integer")
            payload["message_thread_id"] = int(thread_id)
        result.append((label, payload))
    return result


def send(token: str, label: str, payload: dict) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=API_TIMEOUT) as response:
            result = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        # Do not include the request URL: it contains the bot token.
        raise RuntimeError(f"Telegram {label} delivery failed (HTTP {exc.code})") from None
    except (error.URLError, TimeoutError, ValueError) as exc:
        # Do not print exception details that might include a sensitive URL.
        raise RuntimeError(f"Telegram {label} request failed ({type(exc).__name__})") from None
    if not result.get("ok"):
        raise RuntimeError(f"Telegram {label} delivery was rejected by the API")
    print(f"Telegram {label} notification delivered.")


def main(kind: str) -> int:
    if os.getenv("GITHUB_REPOSITORY") != OFFICIAL_REPO:
        print("::notice::Telegram skipped: not the official Cogan repository.")
        return 0
    if os.getenv("COGAN_TELEGRAM_ENABLED", "").strip().lower() != "true":
        print("::notice::Telegram is disabled until COGAN_TELEGRAM_ENABLED=true.")
        return 0

    token = os.getenv("COGAN_TELEGRAM_BOT_TOKEN", "").strip()
    targets = destinations()
    if not token or not targets:
        print("::notice::Telegram skipped: new bot token or channel/group ID not configured.")
        return 0

    text = notification_text(kind)
    for label, target in targets:
        send(token, label, {**target, "parse_mode": "HTML", "text": text})
    return 0


if __name__ == "__main__":
    try:
        if len(sys.argv) != 2:
            raise ValueError("Usage: telegram_notify.py release|notice")
        sys.exit(main(sys.argv[1]))
    except (ValueError, RuntimeError) as exc:
        print(f"::error::{exc}", file=sys.stderr)
        sys.exit(1)
