# Cogan Telegram notifications (safe setup)

Cogan Assistant is already an administrator of the official announcement channel (posting only) and community discussion group (delete messages / ban users). GitHub Actions **only sends notifications**; it does not implement moderation or personal chats.

**Do not share your bot token with anyone**, including in GitHub issues, screenshots, workflow inputs or chat messages.

## Recommended setup for a linked channel and discussion group

1. Open the official Cogan repository → **Settings → Secrets and variables → Actions → Secrets → New repository secret**.
2. Add `COGAN_TELEGRAM_BOT_TOKEN` with the fresh token obtained privately in BotFather (not the previously revoked token).
3. Add `COGAN_TELEGRAM_CHANNEL_ID` with the **channel's public username** `@CoganKernel` if that still matches the public invite link `t.me/CoganKernel`. Do not confuse the displayed channel title `CoganKernelCH` with its username.
4. Leave `COGAN_TELEGRAM_GROUP_ID` and `COGAN_TELEGRAM_GROUP_THREAD_ID` empty initially.
5. Go to **Settings → Secrets and variables → Actions → Variables → New repository variable**. Add `COGAN_TELEGRAM_ENABLED` = `true` **only after** confirming the channel and bot are correct.
6. Optional `COGAN_TELEGRAM_TARGET` values: `auto` (default: prefer channel), `channel`, or `group`. Linked channel posts already appear in the discussion group: **do not send to both**.

## Safe first test

Once the PR is merged and the secrets / enable variable are set, open **Actions → Send Telegram Bot Notification → Run workflow** on `main`.

- `msg_type`: `test`
- `content`: `Cogan Assistant integration test. No kernel release was created.`

Only the official Cogan repository may deliver messages. The sender exits without network calls if not explicitly enabled, without a token, or without a selected destination. Its logs do not print the token.

## Official releases

After a successful `Manual Release From Run`, the workflow announces the official Cogan release URL. No full kernel rebuild is required for the notification test.

## Group moderation is separate

BotFather command registration, admin rights, and GitHub Action notifications do **not** implement `/start`, `/help`, spam removal, or automatic ban rules. A running Telegram service, authorization policy, and tests must be developed and deployed separately before these work.
