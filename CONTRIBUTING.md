# Contributing to EwE

This document explains how the project is organized and how to propose changes.

## Getting started

1. Fork the repository and clone your fork.
2. Install the dependencies: `pip install -r requirements.txt`.
3. Run the app with `src\start.bat`.

## Code style and structure

- The entire application lives in a single file, `src/presence.py`. This is on purpose, keep it that way. 
- The app is a Windows-only PyQt6 application. The goal of the project is that every aspect of it is customizable and user friendly, including all UI elements. 
- The app resolves all runtime files relative to its own location (`src/`). Do not hard-code absolute paths.

## Runtime data

`src/settings.json`, `src/vnlist.json`, `src/Cache/`, `src/Saved/`, `src/Custom/`, and `src/ewe_crash.log` are created at runtime and are Git-ignored. Do not commit them (they may contain personal data and API keys).

## Pull requests

1. Create a branch for your change.
2. Commit with clear, descriptive messages.
3. Open a pull request against `main`.
4. For bugs: link the issue and include reproduction steps.
5. For features: explain the user-visible behavior and, where relevant, screenshots.

## Reporting issues

Use the [issue tracker](https://github.com/VaternID/EwE/issues). Include:

- Your Windows version and Python version.
- The output of `src/ewe_crash.log` for crashes.
- Steps to reproduce.

Please do **not** paste API keys, tokens, or cookies into issue reports.
