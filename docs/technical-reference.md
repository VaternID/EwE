# EwE Technical Reference

This document describes the architecture and runtime behavior implemented by
[`src/presence.py`](../src/presence.py). It complements the
[configuration reference](configuration.md), which focuses on the files and
settings users maintain.

## Scope and platform

EwE is a Windows desktop application written as a single Python module. Its
interface is built with PyQt6; Windows process and window inspection uses
`psutil` and pywin32; Discord Rich Presence is sent through `pypresence`; and
VNDB and image-host requests use `requests`. Matplotlib is used by the
playtime graph.

The module initializes Windows APIs and a single-instance mutex before
constructing the UI. If another instance owns the mutex, the process shows a
Windows message and exits. It also initializes COM for the UI thread and sets
Qt high-DPI and logging environment defaults before importing Qt.

The program is designed to run on Windows. Its imports and startup path call
Windows-specific APIs directly; this module is not a portable, headless
library.

## Runtime architecture

The main responsibilities live in `RPCCore` and `RPCMainWindow`:

- **`RPCCore`** owns game and application settings, process matching, activity
  construction, playtime accounting, VNDB data and image caches, and the
  Discord connection worker.
- **`RPCMainWindow`** owns the Qt application interface, tray integration,
  periodic process scans, and routing scan results back onto the UI thread.
- **Dialogs and helper widgets** implement the startup guide, playtime graph,
  image viewer, code editor and syntax highlighting, and reusable UI elements.

The main window schedules process monitoring. Scans are run on a
single-worker executor to avoid blocking the Qt event loop; a scan-in-flight
guard prevents overlapping scans. Qt signals deliver results and UI work back
to the main thread. Network and other longer-running operations use worker
threads or the shared asynchronous task helper where appropriate.

Discord operations are serialized by a dedicated daemon thread consuming a
queue. Callers request connections, enqueue activity updates, or clear the
activity rather than invoking the RPC client from the UI thread. This keeps
connect/update/clear work ordered and avoids blocking the interface during
connection attempts.

## Startup and storage locations

`RPCCore.get_base_dir()` chooses the directory containing the executable when
frozen, or the directory containing `presence.py` when run from source. Runtime
files are therefore stored beside the packaged executable or source module.

At startup, the core loads:

- `vnlist.json` into the per-game configuration dictionary. If it is missing,
  invalid, or not a JSON object, the core attempts to create a fresh empty
  configuration. A parse failure triggers an attempt to preserve the original
  file as `vnlist.json.bak`.
- `settings.json` into application-wide settings. Missing keys are filled
  from built-in defaults; an absent file is created with those defaults.

Writes to both JSON files use a temporary sibling file followed by
`os.replace`, reducing the chance of leaving a partially written file after an
interrupted save. Errors are printed to standard output and save methods
return failure where applicable.

At initialization, legacy settings `blur_explicit` and `blur_rpc_explicit`
are copied to the current keys `pixel_explicit` and
`replace_rpc_explicit` only when the current key is absent. The code also
migrates the old `game_order` list in settings into each game's `order` field,
then removes the old setting. Games are subsequently listed by numeric order,
with invalid or missing order values sorted after valid ones.

Typical runtime files and directories are described in the
[configuration reference](configuration.md). Of particular note:

- Per-game configuration, including playtime and embedded VNDB cache entries,
  lives in `vnlist.json`.
- Downloaded image files are placed in `Cache/images/`, with names derived
  from a truncated SHA-1 hash of the image URL and a recognized file extension
  (or `.jpg` fallback).
- Custom Python variable scripts are read from the configured custom-script
  directory beside the application.
- Settings may contain personal tokens, API keys, and cookies; those values
  are stored as plain text and should not be shared.

## Game configuration model

Each `vnlist.json` entry is keyed by the configured executable name and stores
the game's process-matching and presence options. `add_new_game_config()`
merges supplied values over defaults, preserves an existing VNDB cache and
order when updating an existing game, assigns a new order to a new game, then
saves the configuration.

The defaults cover these groups:

| Group | Representative fields | Purpose |
| --- | --- | --- |
| Process matching | `exe_name`, `extra_exe_names`, `exe_path`, `match_path_contains` | Identify the game process, optionally by exact executable path, alternate process names, or a path substring. |
| Discord identity and cover | `vn_name`, `activity_name`, `large_image`, `cover_url`, `large_text`, `image_source_path`, `image_host` | Set activity text and imagery and retain cover-source/upload information. |
| Presence text | `details_mode`, `details`, `state` | Select manual, custom-template, or VNDB-derived text. |
| VNDB display | `vndb_url`, `vndb_state_template`, `vndb_details_cycle_items`, `vndb_swap_details_state` | Link a visual novel and customize the VNDB-mode fields. |
| Custom display | `custom_details_template`, `custom_state_template`, cycle flags, items, and intervals | Configure template output and optional rotation. |
| Text transforms | `*_transform` dictionaries | Apply prefix/suffix, substring removal/replacement, and trimming to rendered text. |
| Cached and measured data | `vndb_cache`, library-cache data, playtime fields | Reduce repeated lookups and retain runtime information. |

The exact per-game record can evolve with the application; the defaults in
`add_new_game_config()` are the implementation reference. The
[configuration reference](configuration.md) explains the user-facing JSON
files.

## Process discovery and activity lifecycle

Process matching is performed by `get_matching_process()`:

1. It compares process names case-insensitively against the configured primary
   executable name and any `extra_exe_names`.
2. When an exact executable path is configured, the primary process must match
   its normalized absolute path.
3. Alternate executable names can be constrained to the configured game's
   directory. `match_path_contains`, when non-empty, further filters the
   executable path.
4. If several candidates remain, a process with a visible window is preferred;
   otherwise the primary executable name is preferred, then the first
   candidate.
5. A short-lived process table cache is used as a fallback when a configured
   game directory is available.

The core tracks matched process IDs per game and attempts to retain child
processes, which helps when a launcher starts the actual game in a separate
process. Window titles are obtained by enumerating visible/enabled top-level
Windows windows and selecting the first non-empty title owned by a matched or
tracked process.

The main-window scan checks configured games, updates playtime for the running
set, and chooses an activity target. It asks the core to update Discord when a
target game is running and clears the RPC when the scan determines there is no
active target. The tray status reflects whether a configured game is running.
Minimizing hides the window to the system tray; the tray menu can restore the
window, toggle presence, open help-related UI, and exit.

`update_presence()` builds the activity only after requesting the shared
Discord client connection. While the connection is pending, it returns the
connection status rather than enqueueing an update. The activity payload
contains activity type, name, details, state, large image and hover text,
session start time, and optional buttons. Buttons link to the game's VNDB page
and, when enabled and configured, the user's VNDB list.

An activity key is calculated from the payload fields. If that key has not
changed, an update is suppressed for up to 30 seconds; otherwise an update is
queued. Discord update errors close the current connection and record a
reconnect status. Clearing the RPC also resets current game timing and process
tracking state.

## Presence text modes and templates

The per-game `details_mode` selects one of three paths:

- **`manual`** sends the configured `details` and `state` strings directly.
  Empty values are represented by three spaces.
- **`custom`** renders templates and transforms for both fields. If no VNDB
  URL is configured for the game, both fields are blank placeholders.
- **`vndb`** uses the configured VNDB metadata templates. Without a VNDB URL,
  both fields are blank placeholders. If VNDB data has not yet been loaded,
  the activity uses `Reading` and `Loading VNDB data...`; once available, the
  details and state fields are rendered from the configured templates.
  `vndb_swap_details_state` reverses the final field assignment.

Templates replace tokens matching `{name}` where `name` consists of letters,
digits, and underscores. Unknown tokens are left unchanged. Built-in context
values include:

| Token | Value |
| --- | --- |
| `{vn_name}` | Configured VN name, falling back to activity name or game key. |
| `{activity_name}` | Resolved Discord activity name. |
| `{exe_name}` | Configured executable name, falling back to game key. |
| `{game_key}` | The per-game configuration key. |
| `{window_title}` | First available title for the matched/tracked process window. |
| `{large_text}` | Configured large-image hover text. |
| `{vndb_url}` | Configured VNDB URL. |
| `{vndb_rating}` | Cached VNDB rating. |
| `{vndb_developer}` | Cached developer name or names. |
| `{vndb_status}` | VNDB list status, normalized from `Playing` to `Reading`; defaults to `Reading` when empty. |
| `{vndb_length}` | Human-readable VNDB length category when recognized. |
| `{vndb_year}` | Four-digit year extracted from the cached release date when available. |
| `{vndb_released}` | Cached release date string. |
| `{elapsed_time}` | Elapsed time since the tracked activity start, formatted in hours/minutes. |
| `{date}` / `{time}` | Local date (`YYYY-MM-DD`) and time (`HH:MM`) at render time. |

Each custom Python variable script also contributes a token whose name is the
script's declared `NAME` (or its filename stem). Custom values are added only
when they do not replace an existing built-in token.

Text transforms are applied after template substitution in this order:

1. Remove each configured substring.
2. Apply each configured literal `old` to `new` replacement.
3. Add the configured prefix and suffix.
4. Trim surrounding whitespace when `trim` is true.

If the result is empty, the renderer returns three spaces so Discord receives
a blank field rather than an empty string. Rotating custom and VNDB-details
templates use per-game in-memory indices and switch intervals clamped to a
minimum of five seconds. Rotation state is reset when the game's runtime state
is cleared; it is not persisted across restarts.

## Discord RPC concurrency

The core owns one daemon worker thread and a `queue.Queue`. Queue items
represent connect, update, clear, or shutdown operations. The worker performs
the blocking `pypresence` calls serially. A lock protects connection identity,
pending connection state, and the last connection error.

The client ID is the shared ID constant in the module. A connect request for an
already-connected matching client is immediately considered ready; repeated
requests while that same client is pending report a connecting state. A stale
pending connection request is ignored if it has been superseded by a different
client ID.

`shutdown_discord()` adds a sentinel to stop the worker. Normal application
exit also clears presence and flushes pending playtime updates before
terminating UI resources.

## VNDB data access and caches

VNDB API requests are sent to `https://api.vndb.org/kana/` through a shared
`requests.Session`. `_RateLimiter` serializes requests and enforces a minimum
0.25-second interval. When a token is configured, requests include the VNDB
token authorization header. API calls use explicit timeouts and HTTP status
checking.

The core supports several VNDB operations:

- `search_vndb()` searches by title and returns identifiers, titles,
  thumbnails, developers, and formatted ratings.
- `fetch_vndb_info()` retrieves rating, release date, length, developers, and
  optionally the user's list status. It first checks the in-memory cache;
  `cache_only=True` prevents a network request when there is no cached entry.
- `get_vn_status()` queries the user's list and returns the first label when
  available. Missing IDs, empty results, and request failures yield no status.
- If the VNDB API lookup fails or returns no result, `fetch_vndb_info()` can
  fall back to parsing the VNDB web page.
- Library lookups collect VN page information and gallery entries for the
  cover browser and explicit-content classification.

VNDB metadata cache records include a fetch timestamp and are embedded in
matching game records in `vnlist.json`. Cache-age helpers compute the age from
that timestamp; the declared metadata and library cache lifetimes are 12
hours. Cache seeding at startup restores records embedded in game entries.
Library cache persistence likewise stores results in game configuration.

The application also uses bounded parallel workers for thumbnail requests and
cover-rating lookups. Image downloads have a 15-second timeout and reject
empty responses or files larger than four megabytes. They are written to a
`.part` file and atomically renamed when complete. Cached images are reused
when the hashed cache path already exists.

## Cover selection and explicit-content handling

`get_rpc_cover_url()` selects a usable image reference in this order:

1. `cover_url`, if it is a non-empty URL or existing local file.
2. `large_image`, under the same validity check.
3. The cached main VNDB cover, when one exists.

For VNDB-hosted covers, the core consults library metadata and gallery
classification to determine whether a cover is explicit. When
`replace_rpc_explicit` is enabled, a protected cover is replaced in Discord
with the module's generic VNDB cover URL. This is a replacement, not an upload
of the blurred image.

The in-app explicit-cover preference is separately represented by
`pixel_explicit`; UI components consult settings and the library's explicit
metadata when displaying images. The library's explicit-image set is built
from marked gallery items and the marked main cover, normalizing thumbnail
`/cv.t/` URLs to their full `/cv/` equivalents.

`ensure_blurred_cover()` is a separate optional workflow: for a known explicit
cover, it downloads the source, downsamples and upscales it to produce a
pixelated image, uploads that image using the configured image host, and saves
the resulting URL as `blurred_cover_url`. This requires an image host and is
performed asynchronously. It is distinct from the Discord replacement
behavior above.

Image uploads are implemented by `upload_image_file()` and support the host
selection and credentials in application settings. Catbox does not require a
key; other configured hosts may require their corresponding API key or
cookie. Host errors are surfaced to the caller and, for asynchronous UI
tasks, delivered through the error callback.

## Playtime tracking

The core maintains per-game start timestamps and playtime data in each game's
configuration. `tick_playtime()` receives the current set of running game
keys and adds one second per running game per invocation to both
`total_playtime_seconds` and the current local date's `playtime_by_date`
bucket. It also updates `last_played`. The monitor's invocation cadence
therefore determines the accounting granularity. Configuration is saved every
ten non-empty tick invocations, and `flush_playtime()` persists pending
changes; the application also flushes during shutdown.
`get_playtime_seconds()` returns a game's total, and
`get_playtime_by_date()` provides sorted, date-bucketed data for the playtime
graph.

`format_playtime()` formats arbitrary seconds as seconds, minutes plus seconds,
or hours plus minutes and seconds. The running activity start timestamp is
also sent to Discord so the client can display elapsed session time.

## Custom Python variables

Custom Python scripts are discovered from the custom-script directory beside
the application. Only `.py` files are listed. The script's optional top-level
`NAME = "variable_name"` declaration determines its template token; if absent,
the filename stem is used.

Each script runs as a separate Python subprocess using the current interpreter
and its own directory as the working directory. Execution has a ten-second
timeout. The first non-empty stdout line becomes the variable value; stderr is
logged when stdout is empty. Values are cached for five seconds, and script
execution is submitted to the shared executor rather than run inline during
template rendering.

The UI can create a starter script, rename its exposed variable, and delete a
script. Names must start with an ASCII letter and then contain only letters,
digits, or underscores. Scripts execute as the current user and are not
sandboxed; only add scripts you trust.

## UI helpers and reusable utilities

The module includes supporting utilities alongside the main core and window:

- `native_open_file_dialog()` adapts Qt-style file-filter strings to the
  Windows `GetOpenFileNameW` dialog through `ctypes`.
- `run_async_task()` runs a callable in the shared thread pool and dispatches
  success or failure to its callbacks through Qt signals.
- `arm_window_picker()` temporarily allows selecting a window and captures
  the target using the Windows window/process APIs.
- `ImageViewerDialog` loads and scales cached or downloaded images for
  inspection.
- `StartupGuideDialog` provides first-run onboarding and marks
  `first_run_done` when completed.
- `PlaytimeGraphDialog` presents playtime data using Matplotlib.
- `_TemplateHighlighter`, `_CodeEditor`, and related line-number and flow
  layout widgets support editing templates and custom scripts.
- `enable_dark_title_bar()` and `DarkTitleBarFilter` apply Windows title-bar
  styling where supported.

## Failure handling and operational notes

Network requests use timeouts and generally check HTTP status before parsing
responses. The VNDB API path can fall back to page parsing for metadata. Some
cache, process-enumeration, or optional UI operations intentionally degrade
gracefully when a process disappears, access is denied, data is absent, or an
image cannot be loaded; diagnostic messages are printed for many API, save,
and worker failures.

The module is a monolithic implementation: UI and service logic are in the
same file, and several caches and runtime trackers are in-memory state. Adding
or changing persisted settings should account for existing JSON users,
defaults, legacy-key migrations, and the save behavior described above.

For user setup, supported settings, and runtime file locations, see the
[configuration reference](configuration.md) and the project
[README](../README.md).