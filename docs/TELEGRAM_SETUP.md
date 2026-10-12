# Cogan Telegram release announcements

Cogan Assistant now sends **published kernel releases only**: stable `Release` and `Pre-Release`. No build progress, workflow failure, arbitrary notices, chat commands, or test messages are sent automatically.

The announcement goes to the official Cogan channel (`@CoganKernel`), not directly to the discussion group. Telegram itself mirrors channel posts into the linked discussion group. The notification request uses `disable_notification=true` and `disable_web_page_preview=true`.

## Secret and opt-in

Repository: `cogan17/GKI_BakaSU_SUSFS`

- **Actions secret** `COGAN_TELEGRAM_BOT_TOKEN`: current BotFather token. Never paste into chat or workflow input.
- **Actions secret** `COGAN_TELEGRAM_CHANNEL_ID`: official channel `@CoganKernel`, or its numeric ID.
- **Actions variable** `COGAN_TELEGRAM_ENABLED`: `true` to enable, `false` to disable.

Group ID and target-routing variables are **not used** by release announcements. Keep credentials private. Administrator privileges in the channel should be limited to posting messages.

## When does a notification happen?

1. **Manual Release From Run**: after a successful artifact verification and publication. `Release` announces a stable release; `Pre-Release` announces a prerelease. A same-tag republish with the same type is not announced again. A promotion from prerelease to stable is announced once if done via this workflow. Re-running the same failed workflow attempt does not reannounce.
2. **Publish release on GitHub website**: `release: published` notifies once for a published stable release or prerelease. Drafts and edits do not trigger announcements. Release publication performed using the workflow's standard `GITHUB_TOKEN` normally does not produce another GitHub Actions release event, so the manual workflow handles its own notification.

Release announcements contain type, name, tag, and official GitHub release link; they do not include download assets or unverified URLs. Each invocation performs **at most one** send request and never automatically retries. It is intentionally quiet and produces no website preview. Frequency is limited by actual release publication, not a timer.

## Limitations and safety

- Telegram and GitHub can still enforce their own anti-abuse and rate-limit policies; no workflow can guarantee an account will never be restricted.
- To avoid duplicate announcements, do not manually publish the same release through both methods at the same time.
- The GitHub `release: published` trigger handles a newly published release. A later edit of a prerelease into a stable release using the GitHub website does not guarantee another publication event. Use `Manual Release From Run` to announce that transition reliably.
- A Telegram delivery failure cannot undo a published GitHub release. The notification step is non-blocking by design.
- The removed `Send Telegram Bot Notification` workflow no longer accepts arbitrary messages. Past successful test logs remain in GitHub history.
- This setup does not provide an always-on Telegram chat bot or moderation service.
