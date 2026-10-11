#!/usr/bin/env python3
"""Notify the linked Cogan channel for *published releases only*.

Only one Telegram send is made per invocation. No build, test, arbitrary notice,
or general message functionality is exposed by this sender.
"""

import html
import json
import os
import re
import sys
from urllib import error, parse, request

OFFICIAL_REPO = "cogan17/GKI_BakaSU_SUSFS"
OFFICIAL_REPO_ID = "1397614374"
API_TIMEOUT = 15


def escape(value: str) -> str:
    return html.escape(str(value), quote=True)


def release_details(source: str):
    if source == "manual":
        run_id = os.environ.get("COGAN_RELEASE_RUN_ID", "").strip()
        if not re.fullmatch(r"[0-9]+", run_id):
            raise ValueError("COGAN_RELEASE_RUN_ID must be numeric")
        release_type = os.environ.get("COGAN_RELEASE_TYPE", "").strip()
        if release_type not in ("Release", "Pre-Release"):
            raise ValueError("Invalid release type")
        tag = f"BakaSU-run-{run_id}"
        name = os.environ.get("COGAN_RELEASE_NAME", "").strip() or f"Cogan - build {run_id}"
        prerelease = release_type == "Pre-Release"
    elif source == "published":
        if os.environ.get("GITHUB_EVENT_NAME") != "release":
            raise ValueError("Expected GitHub release event")
        path = os.environ.get("GITHUB_EVENT_PATH", "")
        with open(path, "r", encoding="utf-8") as stream:
            event = json.load(stream)
        repo = event.get("repository") or {}
        release = event.get("release") or {}
        if (event.get("action") != "published"
                or repo.get("full_name") != OFFICIAL_REPO
                or repo.get("id") != int(OFFICIAL_REPO_ID)
                or release.get("draft") is not False
                or release.get("prerelease") not in (True, False)
                or not release.get("published_at")):
            print("::notice::Not a published official Cogan release; skipped.")
            return None
        tag = release.get("tag_name", "")
        name = release.get("name", "") or tag
        prerelease = release["prerelease"]
    else:
        raise ValueError("Only published release sources are supported")

    if not isinstance(tag, str) or not tag or len(tag) > 180:
        raise ValueError("Invalid release tag")
    if not isinstance(name, str):
        name = tag
    return {"tag": tag, "name": name[:180], "prerelease": prerelease}


def notification_text(details):
    prerelease = details["prerelease"]
    state = "Pre-Release / Pra-rilis" if prerelease else "Stable Release / Rilis Stabil"
    label = "Cogan Kernel — Pre-Release" if prerelease else "Cogan Kernel — Stable Release"
    url = f"https://github.com/{OFFICIAL_REPO}/releases/tag/{parse.quote(details['tag'], safe='')}"
    return (
        f"<b>{escape(label)}</b>\n\n"
        f"Status: <b>{escape(state)}</b>\n"
        f"Name: {escape(details['name'])}\n"
        f"Tag: <code>{escape(details['tag'])}</code>\n\n"
        f'<a href="{escape(url)}">View official GitHub release / Lihat rilis</a>\n\n'
        "Verify your device and kernel compatibility before flashing."
    )


def channel_destination():
    channel = os.getenv("COGAN_TELEGRAM_CHANNEL_ID", "").strip()
    if not channel:
        return None
    if not (
        re.fullmatch(r"@[A-Za-z][A-Za-z0-9_]{4,31}", channel)
        or re.fullmatch(r"-?[0-9]{5,20}", channel)
    ):
        raise ValueError("Channel ID must be a numeric Telegram ID or @public_username")
    return channel


def send(token, chat_id, message):
    payload = json.dumps({
        "chat_id": chat_id, "parse_mode": "HTML", "text": message,
        "disable_notification": True, "disable_web_page_preview": True,
    }, ensure_ascii=False).encode("utf-8")
    req = request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=API_TIMEOUT) as response:
            data = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        # Do not echo request URL: the URL includes the Telegram token.
        raise RuntimeError(f"Telegram delivery failed (HTTP {exc.code})") from None
    except (error.URLError, TimeoutError, ValueError) as exc:
        raise RuntimeError(f"Telegram request failed ({type(exc).__name__})") from None
    if not data.get("ok"):
        raise RuntimeError("Telegram rejected the release notification")
    print("One quiet Cogan release notification delivered to the channel.")


def main(source):
    if (os.getenv("GITHUB_REPOSITORY") != OFFICIAL_REPO
            or os.getenv("GITHUB_REPOSITORY_ID") != OFFICIAL_REPO_ID):
        print("::notice::Not the official Cogan repository; skipped.")
        return 0
    if os.getenv("COGAN_TELEGRAM_ENABLED", "").strip().lower() != "true":
        print("::notice::Release Telegram notifications disabled.")
        return 0
    details = release_details(source)
    if details is None:
        return 0
    token = os.getenv("COGAN_TELEGRAM_BOT_TOKEN", "").strip()
    channel = channel_destination()
    if not token or not channel:
        print("::notice::Telegram token or official channel ID missing; skipped.")
        return 0
    send(token, channel, notification_text(details))
    return 0


if __name__ == "__main__":
    try:
        if len(sys.argv) != 2:
            raise ValueError("Usage: telegram_notify.py manual|published")
        sys.exit(main(sys.argv[1]))
    except (ValueError, RuntimeError, OSError, json.JSONDecodeError) as exc:
        print(f"::error::{type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(1)
