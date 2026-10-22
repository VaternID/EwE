# Third-Party Notices

EwE depends on the following third-party Python packages. Each remains under its own license, the GPL-3.0 license of EwE does not relicense them.

| Package    | License                          | Notes |
| ---------- | -------------------------------- | ----- |
| [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) | GPL-3.0 / LGPL-3.0 / commercial (dual-licensed) | The Qt bindings are dual-licensed; using them under GPL-3.0 or LGPL-3.0 is compatible with EwE's GPL-3.0 license. |
| [pywin32](https://github.com/mhammond/pywin32) | [Python Software Foundation License](https://github.com/mhammond/pywin32/blob/master/License.txt) (MIT-like) | Windows API bindings (`win32gui`, `win32process`, `win32con`). |
| [pypresence](https://github.com/Faust/PyPresence) | MIT | Discord Rich Presence (IPC) client. |
| [requests](https://github.com/psf/requests) | Apache-2.0 | HTTP client for the VNDB API and image hosts. |
| [psutil](https://github.com/gitpython-wrapper/psutil) | BSD-2-Clause | Process detection and monitoring. |
| [Pillow](https://python-pillow.org/) | [Pillow License](https://github.com/python-pillow/Pillow/blob/main/LICENSE) (MIT/HPND-based) | Image handling (covers, EXE icon extraction). |
| [matplotlib](https://matplotlib.org/) | [PSF-based matplotlib license](https://matplotlib.org/stable/users/license.html) (GPL-compatible) | Playtime graph dialog only. |

## External services

EwE talks to the following public services at runtime:

- **VNDB** (<https://vndb.org>) = visual novel database and its Kana API (`api.vndb.org`). Metadata and cover images are fetched at runtime and cached locally in `src/Cache/images/`.
- **Discord** = Rich Presence is published through the shared EwE Discord application.
- **Image hosts** (optional, user-selected): Catbox, ImgBB, PostImages, IMG.BS, FreeImage, used to upload local covers so Discord can display them.

Cover art and metadata displayed in EwE originate from VNDB and from the game files the user points EwE at. Their redistribution rights depend on the respective publishers and are not covered by EwE's license.
