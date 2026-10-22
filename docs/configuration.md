# Configuration Reference

This document describes the files EwE reads and writes. All of them live in `src\`, next to `presence.py`, and are created automatically on first start.

## `settings.json`

The app writes a default `settings.json` on first run. A reference copy with all keys is [`src/settings.example.json`] copy it to `src\settings.json` if you want to start from an explicit file, or just let the app create it and configure everything through **Settings** in the UI.

| Key                   | Meaning                                                                 |
| --------------------- | ----------------------------------------------------------------------- |
| `my_vndb_link`        | Your VNDB profile URL (e.g. `https://vndb.org/u123456`). Shown by the optional "My VNDB List" Discord button. |
| `show_my_vndb_list`   | Whether to add the "My VNDB List" button to the presence.                |
| `image_host`          | Cover upload host: `none`, `catbox`, `imgbb`, `postimages`, `imgbs`, or `freeimage`. |
| `freeimage_api_key`   | API key for FreeImage.                                                   |
| `imgbb_api_key`       | API key for ImgBB.                                                       |
| `postimages_api_key`  | API key for PostImages.                                                  |
| `imgbs_cookie`        | Session cookie for IMG.BS.                                               |
| `vndb_api_token`      | Your VNDB API token.              |
| `first_run_done`      | Internal flag: the startup guide has been shown.                         |
| `blur_explicit`       | Blur explicit covers in the app.                                         |
| `blur_rpc_explicit`   | Blur explicit covers in the Discord Rich Presence.                       |

`settings.json` stores your personal API keys, token, and session cookie in plain text. It is Git-ignored, never commit or share it.

## VNDB API token (optional but recommended)

1. Log in at <https://vndb.org>.
2. Open your account settings and copy your **API token**.
3. Paste it into **Settings → VNDB Settings**.

With a token, EwE can read your VNDB list status and fetch data with better rate limits. The app works without a token, but some features and heavy use of the VNDB API are limited.

## `vnlist.json`

Your game list: one entry per game with the executable to watch, presence text settings, covers, VNDB URL, cached VNDB data, and playtime. Created as `{}` on first start and managed entirely through the UI. If the file is ever corrupt, the app renames it to `vnlist.json.bak` and starts fresh.

## `Cache\images\`

Local cache of downloaded VNDB cover images, named by a hash of the source URL. Safe to delete at any time, the app re-downloads what it needs.

## `Saved\`

Covers and icons you save from the UI. Personal runtime data.

## `ewe_crash.log`

Standard error output plus Python crash dumps, appended on every start. Useful for bug reports.
