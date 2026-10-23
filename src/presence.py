import base64
import ctypes
import copy
import faulthandler
import hashlib
import io
import json
import os
import queue
import math
import re
import shutil
import sys
import html
import threading
import time
import traceback
import subprocess
import webbrowser
from concurrent.futures import ThreadPoolExecutor
sys.dont_write_bytecode = True
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(os.path.abspath(sys.executable))
    _RES_DIR = getattr(sys, '_MEIPASS', BASE_DIR)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    _RES_DIR = BASE_DIR
APP_ICON_PATH = os.path.join(_RES_DIR, 'EwE.ico')
APP_ID = 'ewe.rpc'
APP_VERSION = '1.0.0'
GITHUB_REPO = 'VaternID/EwE'
GITHUB_REPO_URL = f'https://github.com/{GITHUB_REPO}'
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
_INSTANCE_MUTEX = ctypes.windll.kernel32.CreateMutexW(None, False, 'Local\\EWE_SingleInstance_Mutex')
if ctypes.windll.kernel32.GetLastError() == 183:
    ctypes.windll.user32.MessageBoxW(0, 'EwE is already running.', 'EwE', 0)
    sys.exit(0)
try:
    ctypes.windll.ole32.CoInitializeEx(None, 2)
except OSError:
    pass
os.environ.setdefault('QT_ENABLE_HIGHDPI_SCALING', '0')
os.environ.setdefault('QT_AUTO_SCREEN_SCALE_FACTOR', '0')
os.environ.setdefault('QT_LOGGING_RULES', 'qt.qpa.window=false')
import psutil
import requests
import win32con
import win32gui
import win32process
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PyQt6.QtCore import QTimer, Qt, QFileInfo, QSize, QObject, QEvent, pyqtSignal, QRect, QRectF, QPointF, QPoint, QRegularExpression
from PyQt6.QtGui import QIcon, QPixmap, QFontMetrics, QPainter, QPen, QColor, QCursor, QFont, QSyntaxHighlighter, QTextCharFormat, QTextCursor, QPolygonF
try:
    from PyQt6 import sip
except ImportError:
    sip = None
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QTextEdit, QPushButton, QDialogButtonBox, QDialog, QLineEdit, QMessageBox, QRadioButton, QButtonGroup, QMenu, QCheckBox, QFrame, QScrollArea, QGridLayout, QFileIconProvider, QListWidgetItem, QSizePolicy, QSystemTrayIcon, QProgressDialog, QToolTip, QPlainTextEdit, QStackedLayout, QWidgetAction, QLayout, QSplitter, QInputDialog
from pypresence import Presence
try:
    from pypresence.types import ActivityType
except Exception:
    ActivityType = None
from ctypes import wintypes as _wintypes

class _OPENFILENAMEW(ctypes.Structure):
    _fields_ = [('lStructSize', _wintypes.DWORD), ('hwndOwner', _wintypes.HWND), ('hInstance', _wintypes.HINSTANCE), ('lpstrFilter', _wintypes.LPCWSTR), ('lpstrCustomFilter', _wintypes.LPWSTR), ('nMaxCustFilter', _wintypes.DWORD), ('nFilterIndex', _wintypes.DWORD), ('lpstrFile', _wintypes.LPWSTR), ('nMaxFile', _wintypes.DWORD), ('lpstrFileTitle', _wintypes.LPWSTR), ('nMaxFileTitle', _wintypes.DWORD), ('lpstrInitialDir', _wintypes.LPCWSTR), ('lpstrTitle', _wintypes.LPCWSTR), ('Flags', _wintypes.DWORD), ('nFileOffset', _wintypes.WORD), ('nFileExtension', _wintypes.WORD), ('lpstrDefExt', _wintypes.LPCWSTR), ('lCustData', ctypes.c_longlong), ('lpfnHook', _wintypes.LPVOID), ('lpTemplateName', _wintypes.LPCWSTR), ('pvReserved', _wintypes.LPVOID), ('dwReserved', _wintypes.DWORD), ('FlagsEx', _wintypes.DWORD)]
_OFN_EXPLORER = 131072
_OFN_PATHMUSTEXIST = 2048
_OFN_FILEMUSTEXIST = 4096

def _qt_filter_to_win32(qt_filter):
    if not qt_filter:
        return '*.*\x00\x00'
    parts = [p.strip() for p in qt_filter.split(';;') if p.strip()]
    out = []
    for part in parts:
        if '(' in part and part.endswith(')'):
            desc = part[:part.index('(')].strip() or 'All Files'
            pattern = part[part.index('(') + 1:-1].strip()
        else:
            desc, pattern = (part, '*.*')
        out.append(f'{desc}\x00{pattern}\x00')
    return ''.join(out) + '\x00'

def _default_ext_from_filter(qt_filter):
    if not qt_filter:
        return ''
    first = qt_filter.split(';;')[0].strip()
    if '(' in first and first.endswith(')'):
        pattern = first[first.index('(') + 1:-1].strip()
        if pattern.startswith('*.'):
            return pattern[2:].strip()
    return ''

def _win32_get_open_file_name(owner_hwnd, title, initial_dir, win32_filter, default_ext=''):
    max_file = 32768
    buf_file = ctypes.create_unicode_buffer(max_file)
    buf_title = ctypes.create_unicode_buffer(2048)
    of = _OPENFILENAMEW()
    of.lStructSize = ctypes.sizeof(_OPENFILENAMEW)
    of.hwndOwner = owner_hwnd
    of.hInstance = None
    of.lpstrFilter = win32_filter
    of.nFilterIndex = 1
    of.lpstrFile = ctypes.cast(buf_file, _wintypes.LPWSTR)
    of.nMaxFile = max_file
    of.lpstrFileTitle = ctypes.cast(buf_title, _wintypes.LPWSTR)
    of.nMaxFileTitle = 2048
    of.lpstrInitialDir = initial_dir or None
    of.lpstrTitle = title
    of.lpstrDefExt = default_ext or None
    of.Flags = _OFN_EXPLORER | _OFN_PATHMUSTEXIST | _OFN_FILEMUSTEXIST
    ctypes.windll.comdlg32.GetOpenFileNameW.restype = _wintypes.BOOL
    ok = ctypes.windll.comdlg32.GetOpenFileNameW(ctypes.byref(of))
    return buf_file.value if ok else ''

def native_open_file_dialog(parent, title, start_path='', file_filter=''):
    owner = int(parent.winId()) if parent is not None else None
    win32_filter = _qt_filter_to_win32(file_filter)
    default_ext = _default_ext_from_filter(file_filter)
    path = _win32_get_open_file_name(owner, title, start_path, win32_filter, default_ext)
    return (path, '')
HEADERS = {'Content-Type': 'application/json', 'User-Agent': 'EwERPC/1.0'}
BROWSER_HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36'}
_vndb_session = requests.Session()
PREVIEW_IMAGE_CACHE = {}
_vndb_session.headers.update(HEADERS)

class _RateLimiter:

    def __init__(self, min_interval=0.25):
        self._min_interval = min_interval
        self._lock = threading.Lock()
        self._last = 0.0

    def wait(self):
        with self._lock:
            now = time.monotonic()
            delay = self._last + self._min_interval - now
            if delay > 0:
                time.sleep(delay)
            self._last = time.monotonic()
_vndb_limiter = _RateLimiter()

def vndb_post(path, payload, token=None, timeout=10):
    _vndb_limiter.wait()
    headers = {'Authorization': f'token {token}'} if token else {}
    response = _vndb_session.post(f'https://api.vndb.org/kana/{path}', json=payload, headers=headers, timeout=timeout)
    response.raise_for_status()
    return response.json()

def get_vn_status(user_id, vn_id, token=None):
    user_id = str(user_id or '').strip()
    vn_id = str(vn_id or '').strip()
    if not user_id or not vn_id:
        return None
    if not user_id.startswith('u'):
        user_id = f'u{user_id}'
    if not vn_id.startswith('v'):
        vn_id = f'v{vn_id}'
    payload = {'user': user_id, 'fields': 'labels.label', 'filters': ['id', '=', vn_id]}
    try:
        data = vndb_post('ulist', payload, token=token)
    except requests.exceptions.RequestException:
        return None
    results = data.get('results') or []
    if not results:
        return None
    labels = results[0].get('labels') or []
    if not labels:
        return None
    return labels[0].get('label')
SHARED_CLIENT_ID = '1561366091559731201'
VNDB_DEFAULT_COVER_URL = 'https://lh3.googleusercontent.com/d/1Q8cniPNj66UFXSC-wxh0LyRfKUI8IAo8'
DEFAULT_VNDB_STATE_TEMPLATE = '★ {vndb_rating}/10 · {vndb_year} · {vndb_length}'
DEFAULT_VNDB_DETAILS_ITEMS = ['{vndb_status}', 'By {vndb_developer}']
CUSTOM_HELPER_DETAILS = '# Shown as the details line. {variables} are replaced live.'
CUSTOM_HELPER_STATE = '# Shown as the state line. {variables} are replaced live.'
CUSTOM_HELPER_CYCLE_ITEMS = '# One template per line. They rotate in order. {variables} are replaced live.'
CUSTOM_HELPER_PREFIX = '# Text added before the final text.'
CUSTOM_HELPER_SUFFIX = '# Text added after the final text.'
CUSTOM_HELPER_REMOVE = '# One substring per line. All of them are removed from the text.'
CUSTOM_HELPER_REPLACE = '# One rule per line: old=new.'

def format_playtime(seconds):
    try:
        seconds = max(0, int(seconds))
    except (TypeError, ValueError):
        seconds = 0
    hours, rem = divmod(seconds, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f'{hours}h {minutes:02d}m {secs:02d}s'
    if minutes:
        return f'{minutes}m {secs:02d}s'
    return f'{secs}s'

class RPCCore:

    def __init__(self):
        self.base_dir = self.get_base_dir()
        self.config_file = os.path.join(self.base_dir, 'vnlist.json')
        self.settings_file = os.path.join(self.base_dir, 'settings.json')
        self.config = self.load_config()
        self.settings = self.load_settings()
        self._migrate_order()
        self.vndb_cache = {}
        self._seed_persistent_vndb_cache()
        self.library_cache = {}
        self._seed_persistent_library_cache()
        self._playtime_dirty = False
        self._playtime_tick_count = 0
        self.vndb_state_index = {}
        self.vndb_last_switch = {}
        self.current_client_id = None
        self.last_running_exe = None
        self.start_time = None
        self.start_times = {}
        self.tracked_pids = {}
        self.missed_ticks = 0
        self._last_presence_key = None
        self._last_presence_sent = 0.0
        self.custom_python_cache = {}
        self._custom_py_lock = threading.Lock()
        self._blurred_inflight = set()
        self._proc_table_tick = -1
        self._proc_table = []
        self._explicit_url_set = None
        self._discord_lock = threading.Lock()
        self._discord_queue = queue.Queue()
        self._discord_rpc = None
        self._discord_client_id = None
        self._discord_pending_id = None
        self._discord_last_error = None
        self._discord_thread = threading.Thread(target=self._discord_worker, daemon=True, name='ewe-discord')
        self._discord_thread.start()

    @staticmethod
    def get_base_dir():
        if getattr(sys, 'frozen', False):
            return os.path.dirname(os.path.abspath(sys.executable))
        return os.path.dirname(os.path.abspath(__file__))

    @staticmethod
    def _write_json_atomic(path, data):
        tmp_path = f'{path}.tmp'
        with open(tmp_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, path)

    def _save_config(self):
        try:
            self._write_json_atomic(self.config_file, self.config)
        except Exception as e:
            print(f'Error saving config: {e}')

    def load_settings(self):
        default_settings = {'my_vndb_link': '', 'show_my_vndb_list': True, 'freeimage_api_key': '', 'image_host': 'none', 'imgbb_api_key': '', 'postimages_api_key': '', 'imgbs_cookie': '', 'vndb_api_token': '', 'first_run_done': False, 'pixel_explicit': True, 'replace_rpc_explicit': True, 'check_updates_on_startup': True}
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    loaded_settings = json.load(f)
                    default_settings.update(loaded_settings)
                    if 'blur_explicit' in loaded_settings and 'pixel_explicit' not in loaded_settings:
                        default_settings['pixel_explicit'] = loaded_settings['blur_explicit']
                    if 'blur_rpc_explicit' in loaded_settings and 'replace_rpc_explicit' not in loaded_settings:
                        default_settings['replace_rpc_explicit'] = loaded_settings['blur_rpc_explicit']
            except Exception as e:
                print(f'Error loading settings: {e}')
        else:
            try:
                with open(self.settings_file, 'w', encoding='utf-8') as f:
                    json.dump(default_settings, f, indent=2, ensure_ascii=False)
            except Exception as e:
                print(f'Error creating settings file: {e}')
        return default_settings

    def _migrate_order(self):
        old_order = self.settings.get('game_order')
        if isinstance(old_order, list) and old_order:
            keys = [k for k in old_order if k in self.config]
            for k in self.config:
                if k not in keys:
                    keys.append(k)
        else:
            keys = list(self.config.keys())
        changed = False
        for i, key in enumerate(keys, 1):
            entry = self.config[key]
            if str(entry.get('order', '')).strip() != str(i):
                entry['order'] = str(i)
                changed = True
        if isinstance(old_order, list):
            self.settings.pop('game_order', None)
            self.save_settings()
        if changed:
            self._save_config()

    def save_settings(self):
        try:
            self._write_json_atomic(self.settings_file, self.settings)
            return True
        except Exception as e:
            print(f'Error saving settings: {e}')
            return False

    def _discord_worker(self):
        while True:
            item = self._discord_queue.get()
            if item is None:
                break
            kind, value = item
            try:
                if kind == 'connect':
                    self._discord_do_connect(value)
                elif kind == 'update':
                    self._discord_do_update(value)
                elif kind == 'clear':
                    self._discord_do_clear()
            except Exception as e:
                print(f'[Discord worker] {kind} failed: {e}')

    def _close_discord_rpc(self):
        rpc, self._discord_rpc = (self._discord_rpc, None)
        if rpc is not None:
            try:
                rpc.clear()
            except Exception:
                pass
            try:
                rpc.close()
            except Exception:
                pass

    def _discord_do_connect(self, client_id):
        with self._discord_lock:
            if self._discord_rpc is not None and self._discord_client_id == client_id:
                return
            superseded = self._discord_pending_id is not None and self._discord_pending_id != client_id
        if superseded:
            return
        self._close_discord_rpc()
        try:
            rpc = Presence(client_id)
            rpc.connect()
        except Exception as e:
            with self._discord_lock:
                self._discord_pending_id = None
                self._discord_last_error = f'Discord connect failed: {e} (is Discord running?)'
            return
        with self._discord_lock:
            self._discord_rpc = rpc
            self._discord_client_id = client_id
            self._discord_pending_id = None
            self._discord_last_error = None
            self.current_client_id = client_id
        print(f'Successfully connected to Discord')

    def _discord_do_update(self, payload):
        with self._discord_lock:
            rpc = self._discord_rpc
        if rpc is None:
            return
        try:
            rpc.update(**payload)
        except Exception as e:
            self._close_discord_rpc()
            with self._discord_lock:
                self._discord_client_id = None
                self._discord_pending_id = None
                self._discord_last_error = f'Rich Presence connection lost ({e}); reconnecting...'
                self.current_client_id = None

    def _discord_do_clear(self):
        self._close_discord_rpc()
        with self._discord_lock:
            self._discord_client_id = None
            self._discord_pending_id = None
            self._discord_last_error = None
            self.current_client_id = None

    def request_discord(self, client_id):
        with self._discord_lock:
            if self._discord_rpc is not None and self._discord_client_id == client_id:
                return ('ready', None)
            error = self._discord_last_error
            self._discord_last_error = None
            if self._discord_pending_id == client_id:
                return ('connecting', error)
            self._discord_pending_id = client_id
        self._discord_queue.put(('connect', client_id))
        return ('connecting', None)

    def send_presence_update(self, payload):
        self._discord_queue.put(('update', payload))

    def shutdown_discord(self):
        try:
            self._discord_queue.put(None)
        except Exception:
            pass

    def clear_rpc(self):
        with self._discord_lock:
            had = self._discord_rpc is not None or self._discord_pending_id is not None
            self._discord_pending_id = None
        self._discord_queue.put(('clear', None))
        self.current_client_id = None
        self.last_running_exe = None
        self.start_time = None
        self.start_times = {}
        self._last_presence_key = None
        self._last_presence_sent = 0.0
        self.tracked_pids = {}
        self.missed_ticks = 0
        return 'Rich Presence cleared.' if had else 'No active RPC to clear.'

    def clear_game_state(self, game_key):
        self.start_times.pop(game_key, None)
        self.tracked_pids.pop(game_key, None)
        for key in list(self.vndb_state_index):
            if key == game_key or key.startswith(f'{game_key}:'):
                self.vndb_state_index.pop(key, None)
                self.vndb_last_switch.pop(key, None)

    def get_shared_client_id(self):
        return SHARED_CLIENT_ID

    def get_activity_type(self):
        if ActivityType is None:
            return 0
        return ActivityType.PLAYING

    def get_activity_name(self, game_key):
        settings = self.config.get(game_key, {})
        name = settings.get('vn_name') or settings.get('activity_name') or settings.get('large_text') or settings.get('details') or game_key
        name = str(name).strip()
        return name or game_key

    def format_elapsed_time(self):
        start = getattr(self, 'start_time', None)
        if not start:
            return '0m'
        seconds = max(0, int(time.time() - start))
        hours = seconds // 3600
        minutes = seconds % 3600 // 60
        if hours:
            return f'{hours}h {minutes}m'
        return f'{minutes}m'

    def get_template_context(self, game_key, snapshot=None):
        settings = self.config.get(game_key, {})
        window_title = self.get_window_title(game_key, snapshot) or ''
        vndb_rating = ''
        vndb_developer = ''
        vndb_status = ''
        vndb_length = ''
        vndb_year = ''
        vndb_released = ''
        vndb_url = settings.get('vndb_url', '')
        if vndb_url:
            vndb_data = self.fetch_vndb_info(vndb_url, cache_only=True)
            if vndb_data:
                vndb_rating = vndb_data.get('rating', '')
                vndb_developer = vndb_data.get('developer', '')
                vndb_status = vndb_data.get('user_status', '') or ''
                if vndb_status == 'Playing':
                    vndb_status = 'Reading'
                vndb_released = str(vndb_data.get('released') or '')
                if vndb_released[:4].isdigit():
                    vndb_year = vndb_released[:4]
                try:
                    vndb_length = self.VNDB_LENGTH_LABELS.get(int(vndb_data.get('length')), '')
                except (TypeError, ValueError):
                    vndb_length = ''
        if not vndb_status:
            vndb_status = 'Reading'
        now_struct = time.localtime()
        context = {'vn_name': str(settings.get('vn_name') or settings.get('activity_name') or game_key), 'activity_name': self.get_activity_name(game_key), 'exe_name': str(settings.get('exe_name') or game_key), 'game_key': str(game_key), 'window_title': window_title, 'large_text': str(settings.get('large_text') or ''), 'vndb_url': str(vndb_url), 'vndb_rating': str(vndb_rating), 'vndb_developer': str(vndb_developer), 'vndb_status': str(vndb_status), 'vndb_length': str(vndb_length), 'vndb_year': str(vndb_year), 'vndb_released': str(vndb_released), 'elapsed_time': self.format_elapsed_time(), 'date': time.strftime('%Y-%m-%d', now_struct), 'time': time.strftime('%H:%M', now_struct)}
        for key, value in self.get_custom_python_context().items():
            context.setdefault(key, value)
        return context

    def render_template(self, template, context):
        text = str(template or '')

        def replace_match(match):
            key = match.group(1).strip()
            return str(context.get(key, match.group(0)))
        return re.sub('\\{([A-Za-z0-9_]+)\\}', replace_match, text)

    def normalize_transform(self, transform):
        transform = transform or {}
        return {'prefix': str(transform.get('prefix', '')), 'suffix': str(transform.get('suffix', '')), 'remove': list(transform.get('remove', []) or []), 'replace': dict(transform.get('replace', {}) or {}), 'trim': bool(transform.get('trim', True))}

    def apply_text_transform(self, text, transform):
        text = str(text or '')
        transform = self.normalize_transform(transform)
        for sub in transform['remove']:
            if sub:
                text = text.replace(str(sub), '')
        for old, new in transform['replace'].items():
            if old:
                text = text.replace(str(old), str(new))
        text = f"{transform['prefix']}{text}{transform['suffix']}"
        if transform['trim']:
            text = text.strip()
        return text or '   '

    def render_custom_field(self, game_key, template, transform=None, snapshot=None):
        context = self.get_template_context(game_key, snapshot)
        text = self.render_template(template, context)
        return self.apply_text_transform(text, transform)

    def render_custom_cycle_field(self, game_key, enabled_key, items_key, template_key, seconds_key, transform_key, index_suffix, default_template, snapshot=None):
        settings = self.config.get(game_key, {})
        if settings.get(enabled_key, False):
            cycle_items = settings.get(items_key, []) or []
            cycle_items = [str(x) for x in cycle_items if str(x).strip()]
            if not cycle_items:
                cycle_items = [settings.get(template_key, default_template)]
            try:
                cycle_seconds = max(5, int(settings.get(seconds_key, 5)))
            except Exception:
                cycle_seconds = 5
            cycle_key = f'{game_key}:{index_suffix}'
            now = time.time()
            last = self.vndb_last_switch.get(cycle_key, 0)
            if now - last >= cycle_seconds:
                idx = self.vndb_state_index.get(cycle_key, 0)
                idx = (idx + 1) % len(cycle_items)
                self.vndb_state_index[cycle_key] = idx
                self.vndb_last_switch[cycle_key] = now
            template = cycle_items[self.vndb_state_index.get(cycle_key, 0) % len(cycle_items)]
        else:
            template = settings.get(template_key, default_template)
        return self.render_custom_field(game_key, template, settings.get(transform_key, {}), snapshot)

    def get_vndb_mode_details(self, game_key, snapshot=None):
        settings = self.config.get(game_key, {})
        items = [str(x) for x in settings.get('vndb_details_cycle_items') or [] if str(x).strip()]
        if not items:
            items = list(DEFAULT_VNDB_DETAILS_ITEMS)
        try:
            seconds = max(5, int(settings.get('vndb_details_cycle_seconds', 5)))
        except Exception:
            seconds = 5
        cycle_key = f'{game_key}:vndb_details'
        now = time.time()
        if now - self.vndb_last_switch.get(cycle_key, 0) >= seconds:
            idx = self.vndb_state_index.get(cycle_key, 0)
            idx = (idx + 1) % len(items)
            self.vndb_state_index[cycle_key] = idx
            self.vndb_last_switch[cycle_key] = now
        template = items[self.vndb_state_index.get(cycle_key, 0) % len(items)]
        return self.render_custom_field(game_key, template, settings.get('vndb_details_transform', {}), snapshot)

    def _get_full_process_table(self):
        tick = int(time.monotonic() // 1.5)
        if self._proc_table_tick != tick:
            table = []
            try:
                for process in psutil.process_iter(['pid', 'name', 'exe']):
                    table.append(process)
            except Exception:
                pass
            self._proc_table_tick = tick
            self._proc_table = table
        return self._proc_table

    def _pid_has_visible_window(self, pid):
        found = {'v': False}

        def callback(hwnd, _):
            if found['v']:
                return
            try:
                if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowThreadProcessId(hwnd)[1] == pid:
                    found['v'] = True
            except Exception:
                pass
        try:
            win32gui.EnumWindows(callback, None)
        except Exception:
            pass
        return found['v']

    def resolve_related_processes(self, exe_name, exe_path=''):
        try:
            normalized_exe_path = None
            if exe_path:
                try:
                    normalized_exe_path = os.path.normcase(os.path.abspath(exe_path))
                except Exception:
                    normalized_exe_path = os.path.normcase(exe_path)
            parent = None
            for p in psutil.process_iter(['pid', 'name', 'exe']):
                try:
                    if p.info.get('name') != exe_name:
                        continue
                    if normalized_exe_path:
                        ppath = p.info.get('exe') or ''
                        if ppath:
                            try:
                                ppath = os.path.normcase(os.path.abspath(ppath))
                            except Exception:
                                ppath = ''
                        if ppath != normalized_exe_path:
                            continue
                    parent = p
                    break
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            if parent is None:
                return []
            names = []
            for child in parent.children(recursive=True):
                try:
                    name = child.name()
                    if not name or name == exe_name or name in names:
                        continue
                    if self._pid_has_visible_window(child.pid):
                        names.append(name)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
                if len(names) >= 5:
                    break
            return names
        except Exception:
            return []

    def get_matching_process(self, game_key, snapshot=None):
        settings = self.config.get(game_key, {})
        process_name = settings.get('exe_name', game_key)
        extra_names = [str(n) for n in settings.get('extra_exe_names') or [] if str(n).strip()]
        primary_name = (process_name or '').lower()
        extra_name_set = {str(n).lower() for n in extra_names}
        exact_exe_path = (settings.get('exe_path', '') or '').strip()
        path_contains = (settings.get('match_path_contains', '') or '').strip().lower()
        normalized_exact_path = None
        if exact_exe_path:
            try:
                normalized_exact_path = os.path.normcase(os.path.abspath(exact_exe_path))
            except Exception:
                normalized_exact_path = os.path.normcase(exact_exe_path)
        if snapshot is None:
            snapshot = list(psutil.process_iter(['pid', 'name']))
        game_dir = None
        if normalized_exact_path:
            try:
                game_dir = os.path.dirname(normalized_exact_path)
            except Exception:
                game_dir = None
        candidates = []
        for process in snapshot:
            try:
                name = (process.info.get('name') or '').lower()
                is_primary = bool(primary_name) and name == primary_name
                is_extra = name in extra_name_set
                if not is_primary and not is_extra:
                    continue
                try:
                    process_path = process.exe() or ''
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    process_path = ''
                normalized_process_path = None
                if process_path:
                    try:
                        normalized_process_path = os.path.normcase(os.path.abspath(process_path))
                    except Exception:
                        normalized_process_path = os.path.normcase(process_path)
                if is_primary:
                    if normalized_exact_path:
                        if normalized_process_path == normalized_exact_path:
                            return process
                        continue
                    if process_path and not os.path.splitdrive(process_path)[0]:
                        continue
                elif game_dir:
                    try:
                        proc_dir = os.path.dirname(os.path.normcase(os.path.abspath(process_path))) if process_path else ''
                    except Exception:
                        proc_dir = ''
                    if proc_dir != game_dir:
                        continue
                if path_contains and path_contains not in (process_path or '').lower():
                    continue
                candidates.append(process)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        if not candidates and game_dir:
            try:
                allowed_names = ({primary_name} if primary_name else set()) | extra_name_set
                for process in self._get_full_process_table():
                    process_path = process.info.get('exe') or ''
                    if not process_path:
                        continue
                    if (process.info.get('name') or '').lower() not in allowed_names:
                        continue
                    normalized_process_path = os.path.normcase(os.path.abspath(process_path))
                    if os.path.dirname(normalized_process_path) == game_dir:
                        candidates.append(process)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        if not candidates:
            return None
        if len(candidates) > 1:
            for process in candidates:
                try:
                    if self._pid_has_visible_window(process.info.get('pid')):
                        return process
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
            for process in candidates:
                if (process.info.get('name') or '').lower() == (process_name or '').lower():
                    return process
        return candidates[0]

    def _note_running(self, exe):
        if exe not in self.start_times:
            self.start_times[exe] = int(time.time())
        return self.start_times[exe]

    def track_pid(self, game_key, pid):
        if pid:
            self.tracked_pids.setdefault(game_key, set()).add(pid)

    def sync_tracked_pids(self, game_key):
        pids = self.tracked_pids.get(game_key)
        if not pids:
            return set()
        known = set(pids)
        alive = set()
        for pid in list(pids):
            try:
                proc = psutil.Process(pid)
                proc.pid
                alive.add(pid)
                for child in proc.children():
                    alive.add(child.pid)
                    known.add(child.pid)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        try:
            for p in psutil.process_iter(['pid', 'ppid']):
                if p.info.get('ppid') in known and p.info['pid'] not in alive:
                    alive.add(p.info['pid'])
                    known.add(p.info['pid'])
        except Exception:
            pass
        if alive:
            self.tracked_pids[game_key] = alive
        else:
            self.tracked_pids.pop(game_key, None)
        return alive

    def sync_all_tracked_pids(self):
        games = [g for g, pids in self.tracked_pids.items() if pids]
        if not games:
            return
        known_all = set()
        for g in games:
            known_all |= self.tracked_pids[g]
        alive_map = {g: set() for g in games}
        children_of = {}
        for pid in known_all:
            try:
                proc = psutil.Process(pid)
                proc.pid
                owner_games = [g for g in games if pid in self.tracked_pids[g]]
                for g in owner_games:
                    alive_map[g].add(pid)
                try:
                    kids = [c.pid for c in proc.children()]
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    kids = []
                children_of[pid] = kids
                for g in owner_games:
                    alive_map[g] |= set(kids)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        owners_of = {}
        for g in games:
            for p in alive_map[g]:
                owners_of.setdefault(p, set()).add(g)
        try:
            for p in psutil.process_iter(['pid', 'ppid']):
                owners = owners_of.get(p.info.get('ppid'))
                if owners and p.info['pid'] not in owners_of:
                    for g in owners:
                        alive_map[g].add(p.info['pid'])
                    owners_of[p.info['pid']] = owners
        except Exception:
            pass
        for g in games:
            if alive_map[g]:
                self.tracked_pids[g] = alive_map[g]
            else:
                self.tracked_pids.pop(g, None)

    def get_tracked_process(self, game_key):
        for pid in self.sync_tracked_pids(game_key):
            try:
                proc = psutil.Process(pid)
                proc.pid
                return proc
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        return None

    def update_presence(self, exe, snapshot=None):
        settings = self.config.get(exe, {})
        if not settings:
            return f'No configuration found for {exe}'
        client_id = self.get_shared_client_id()
        discord_state, discord_error = self.request_discord(client_id)
        if discord_state != 'ready':
            return discord_error
        self.start_time = self._note_running(exe)
        self.last_running_exe = exe
        try:
            mode = settings.get('details_mode', 'manual')
            if mode == 'manual':
                details = settings.get('details', '   ') or '   '
                state = settings.get('state', '   ') or '   '
            elif mode == 'custom':
                if not (settings.get('vndb_url', '') or '').strip():
                    details = '   '
                    state = '   '
                else:
                    details = self.render_custom_cycle_field(exe, 'custom_details_cycle_enabled', 'custom_details_cycle_items', 'custom_details_template', 'custom_details_cycle_seconds', 'custom_details_transform', 'custom_details', '{vn_name}', snapshot)
                    state = self.render_custom_cycle_field(exe, 'custom_state_cycle_enabled', 'custom_state_cycle_items', 'custom_state_template', 'custom_state_cycle_seconds', 'custom_state_transform', 'custom_state', '{window_title}', snapshot)
            elif mode == 'vndb':
                if not (settings.get('vndb_url', '') or '').strip():
                    details = '   '
                    state = '   '
                else:
                    vndb_data = self.fetch_vndb_info(settings.get('vndb_url', ''), cache_only=True)
                    if not vndb_data:
                        details = 'Reading'
                        state = 'Loading VNDB data...'
                    else:
                        details = self.get_vndb_mode_details(exe, snapshot)
                        state = self.render_custom_field(exe, settings.get('vndb_state_template') or DEFAULT_VNDB_STATE_TEMPLATE, settings.get('vndb_state_transform', {}), snapshot)
                    if settings.get('vndb_swap_details_state', False):
                        details, state = (state, details)
            buttons = []
            vndb_url = settings.get('vndb_url', '')
            if vndb_url:
                buttons.append({'label': 'View on VNDB', 'url': vndb_url})
            if self.settings.get('show_my_vndb_list', True) and self.settings.get('my_vndb_link'):
                buttons.append({'label': 'My VNDB List', 'url': self.settings.get('my_vndb_link')})
            activity_name = self.get_activity_name(exe)
            large_image = self.get_rpc_cover_url(exe)
            large_text = settings.get('large_text') or settings.get('vn_name') or activity_name
            presence_key = (client_id, activity_name, details, state, large_image, large_text, tuple(((b['label'], b['url']) for b in buttons)))
            now = time.time()
            if self._last_presence_key == presence_key and now - self._last_presence_sent < 30:
                return None
            payload = dict(activity_type=self.get_activity_type(), name=activity_name, details=details, state=state, large_image=large_image, large_text=large_text, start=self.start_time, buttons=buttons if buttons else None)
            self.send_presence_update(payload)
            self._last_presence_key = presence_key
            self._last_presence_sent = now
            button_info = f'buttons: {len(buttons)}' if buttons else 'no buttons'
            return f'{exe} is running. RPC updated. (name: {activity_name} | details: {details} | state: {state} | {button_info})'
        except Exception as e:
            return f'Error updating Rich Presence: {e}'

    def get_window_title(self, game_key, snapshot=None):
        try:
            process = self.get_matching_process(game_key, snapshot)
            if process is None:
                process = self.get_tracked_process(game_key)
            if process is None:
                return ''
            return self.get_first_window_title(process.pid)
        except Exception:
            return ''

    def get_first_window_title(self, pid):
        titles = []

        def callback(hwnd, _):
            if win32gui.IsWindowVisible(hwnd) and win32gui.IsWindowEnabled(hwnd):
                _, found_pid = win32process.GetWindowThreadProcessId(hwnd)
                if found_pid == pid:
                    title = win32gui.GetWindowText(hwnd)
                    if title:
                        titles.append(title)
        win32gui.EnumWindows(callback, None)
        return titles[0] if titles else ''

    CUSTOM_PYTHON_TTL = 5.0

    def custom_script_dir(self):
        return os.path.join(self.base_dir, CUSTOM_SCRIPT_DIR_NAME)

    def _list_custom_scripts(self):
        d = self.custom_script_dir()
        try:
            out = []
            for fn in sorted(os.listdir(d)):
                if fn.lower().endswith('.py'):
                    p = os.path.join(d, fn)
                    if os.path.isfile(p):
                        out.append(p)
            return out
        except OSError:
            return []

    @staticmethod
    def _read_custom_script_name(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                text = f.read(8192)
            m = re.search(r'^\s*NAME\s*=\s*["\']([^"\']+)["\']', text, re.M)
            if m and m.group(1).strip():
                return m.group(1).strip()
        except Exception:
            pass
        return os.path.splitext(os.path.basename(path))[0]

    def custom_python_entries(self):
        return [(p, self._read_custom_script_name(p)) for p in self._list_custom_scripts()]

    def custom_scripts_signature(self):
        sig = []
        for p in self._list_custom_scripts():
            try:
                sig.append((os.path.basename(p), os.stat(p).st_mtime_ns))
            except OSError:
                sig.append((os.path.basename(p), 0))
        return tuple(sig)

    @staticmethod
    def _custom_python():
        if not getattr(sys, 'frozen', False):
            return sys.executable
        for name in ('python', 'pythonw'):
            found = shutil.which(name)
            if found:
                return found
        return None

    def _run_custom_script(self, path):
        py = self._custom_python()
        if py is None:
            print('[EwE custom py] No Python found on PATH; custom scripts need Python installed.')
            return ''
        try:
            proc = subprocess.run([py, path], capture_output=True, text=True, timeout=10, cwd=os.path.dirname(path) or None)
            out = (proc.stdout or '').strip()
            if not out and proc.stderr:
                print(f'[EwE custom py] {os.path.basename(path)}: {(proc.stderr or "").strip()[:300]}')
            if out:
                return out.splitlines()[0].strip()
            return ''
        except Exception as e:
            print(f'[EwE custom py] {os.path.basename(path)}: {e}')
            return ''

    def refresh_custom_python_variables(self, force=False):
        scripts = self._list_custom_scripts()
        now = time.monotonic()
        with self._custom_py_lock:
            for path in list(self.custom_python_cache):
                if path not in scripts:
                    self.custom_python_cache.pop(path, None)
            for path in scripts:
                entry = self.custom_python_cache.get(path)
                if entry is None:
                    entry = {'name': self._read_custom_script_name(path), 'value': '', 'at': 0.0, 'running': False}
                    self.custom_python_cache[path] = entry
                if force:
                    entry['at'] = 0.0
                if entry.get('running') or (now - entry.get('at', 0.0) < self.CUSTOM_PYTHON_TTL):
                    continue
                entry['running'] = True

                def _work(p=path):
                    try:
                        value = self._run_custom_script(p)
                    except Exception:
                        value = ''
                    with self._custom_py_lock:
                        e = self.custom_python_cache.get(p)
                        if e is None:
                            return
                        e['value'] = value
                        e['at'] = time.monotonic()
                        e['running'] = False
                _async_executor.submit(_work)
        return scripts

    def get_custom_python_context(self):
        self.refresh_custom_python_variables()
        ctx = {}
        with self._custom_py_lock:
            items = list(self.custom_python_cache.items())
        for path, entry in items:
            name = self._read_custom_script_name(path)
            ctx[name] = str(entry.get('value', '') or '')
        return ctx

    def create_custom_script(self):
        d = self.custom_script_dir()
        os.makedirs(d, exist_ok=True)
        i = 1
        while os.path.exists(os.path.join(d, f'custom_{i}.py')):
            i += 1
        name = f'custom_{i}'
        path = os.path.join(d, f'{name}.py')
        with open(path, 'w', encoding='utf-8') as f:
            f.write(CUSTOM_PYTHON_TEMPLATE.replace('__CUSTOM_VAR_NAME__', name))
        with self._custom_py_lock:
            self.custom_python_cache[path] = {'name': name, 'value': '', 'at': 0.0, 'running': False}
        self.refresh_custom_python_variables(force=True)
        return path

    def rename_custom_script(self, path, new_name):
        new_name = (new_name or '').strip()
        if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*', new_name):
            raise RuntimeError('The variable name must start with a letter and contain only letters, numbers and underscores (no spaces).')
        try:
            with open(path, 'r', encoding='utf-8') as f:
                text = f.read()
        except Exception as e:
            raise RuntimeError(f'Could not read the script:\n{e}')
        if re.search(r'^\s*NAME\s*=\s*["\']', text, re.M):
            text = re.sub(r'^(\s*NAME\s*=\s*)["\'].*?["\']', lambda m: f'{m.group(1)}"{new_name}"', text, count=1, flags=re.M)
        else:
            text = f'NAME = "{new_name}"\n' + text
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(text)
        except Exception as e:
            raise RuntimeError(f'Could not save the script:\n{e}')
        with self._custom_py_lock:
            self.custom_python_cache.pop(path, None)
        self.refresh_custom_python_variables(force=True)
        return new_name

    def delete_custom_script(self, path):
        try:
            os.remove(path)
        except Exception as e:
            raise RuntimeError(f'Could not delete the script:\n{e}')
        with self._custom_py_lock:
            self.custom_python_cache.pop(path, None)

    def get_supported_games(self):

        def sort_key(item):
            key, entry = item
            try:
                return (0, int(str(entry.get('order', '')).strip()), key)
            except Exception:
                return (1, 0, key)
        return [k for k, _ in sorted(self.config.items(), key=sort_key)]

    def load_config(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    return data
                print(f'Warning: {self.config_file} is not a JSON object; starting fresh.')
            except Exception as e:
                print(f'Error loading {self.config_file}: {e}')
                try:
                    os.replace(self.config_file, self.config_file + '.bak')
                    print(f'Backed up the corrupt config to {self.config_file}.bak')
                except Exception:
                    pass
        try:
            self._write_json_atomic(self.config_file, {})
        except Exception as e:
            print(f'Error creating config file: {e}')
        return {}

    def add_new_game_config(self, exe_name, config_data):
        defaults = {'vn_name': exe_name, 'exe_name': exe_name, 'extra_exe_names': [], 'exe_path': '', 'exe_icon_path': '', 'match_path_contains': '', 'details_mode': 'manual', 'details': '   ', 'state': '   ', 'activity_name': exe_name, 'large_image': '', 'cover_url': '', 'image_source_path': '', 'image_host': 'freeimage', 'large_text': '', 'vndb_url': '', 'vndb_swap_details_state': False, 'vndb_state_template': DEFAULT_VNDB_STATE_TEMPLATE, 'vndb_details_cycle_seconds': 5, 'vndb_details_cycle_items': list(DEFAULT_VNDB_DETAILS_ITEMS), 'vndb_details_transform': {'prefix': '', 'suffix': '', 'remove': [], 'replace': {}, 'trim': True}, 'vndb_state_transform': {'prefix': '', 'suffix': '', 'remove': [], 'replace': {}, 'trim': True}, 'custom_details_template': '{vndb_status}', 'custom_details_cycle_enabled': True, 'custom_details_cycle_seconds': 5, 'custom_details_cycle_items': list(DEFAULT_VNDB_DETAILS_ITEMS), 'custom_state_template': DEFAULT_VNDB_STATE_TEMPLATE, 'custom_state_cycle_enabled': False, 'custom_state_cycle_seconds': 5, 'custom_state_cycle_items': [DEFAULT_VNDB_STATE_TEMPLATE], 'custom_details_transform': {'prefix': '', 'suffix': '', 'remove': [], 'replace': {}, 'trim': True}, 'custom_state_transform': {'prefix': '', 'suffix': '', 'remove': [], 'replace': {}, 'trim': True}}
        final = copy.deepcopy(defaults)
        final.update(config_data)
        existing = self.config.get(exe_name)
        if existing is not None:
            cached = existing.get('vndb_cache')
            if isinstance(cached, dict) and cached:
                final['vndb_cache'] = cached
        if existing is not None and str(existing.get('order', '')).strip():
            final['order'] = existing['order']
        else:
            try:
                max_order = max((int(str(e.get('order', '')).strip()) for e in self.config.values() if str(e.get('order', '')).strip().isdigit()), default=0)
            except Exception:
                max_order = 0
            final['order'] = str(max_order + 1)
        self.config[exe_name] = final
        self._save_config()

    def update_settings(self, key, value):
        self.settings[key] = value
        self.save_settings()

    def get_setting(self, key, default=None):
        return self.settings.get(key, default)

    def search_vndb(self, query, limit=20):
        query = (query or '').strip()
        if not query:
            return []
        payload = {'filters': ['search', '=', query], 'fields': 'title,image.thumbnail,developers.name,rating', 'sort': 'searchrank', 'results': limit}
        data = vndb_post('vn', payload, token=self.settings.get('vndb_api_token'))
        results = []
        for vn in data.get('results') or []:
            vn_id = vn.get('id')
            title = vn.get('title')
            if vn_id and title:
                image = vn.get('image') or {}
                developers = vn.get('developers') or []
                dev_names = [d.get('name') for d in developers if d.get('name')]
                raw_rating = vn.get('rating')
                results.append({'id': vn_id, 'title': title, 'thumbnail': image.get('thumbnail') or '', 'developer': ', '.join(dev_names) if dev_names else 'Unknown', 'rating': f'{raw_rating / 10:.1f}' if raw_rating else 'N/A'})
        return results

    def fetch_thumbnails(self, urls):

        def fetch(url):
            if not url:
                return None
            try:
                r = _vndb_session.get(url, timeout=10)
                r.raise_for_status()
                return r.content
            except Exception:
                return None
        with ThreadPoolExecutor(max_workers=4) as pool:
            return list(pool.map(fetch, urls))

    def has_vndb_cache(self, vndb_url):
        return bool(vndb_url) and vndb_url in self.vndb_cache
    VNDB_CACHE_TTL_SECONDS = 12 * 60 * 60

    def _seed_persistent_vndb_cache(self):
        for entry in self.config.values():
            if not isinstance(entry, dict):
                continue
            url = (entry.get('vndb_url') or '').strip()
            cached = entry.get('vndb_cache')
            if url and isinstance(cached, dict) and cached:
                self.vndb_cache.setdefault(url, dict(cached))

    def _persist_vndb_cache(self, vndb_url, result):
        try:
            stamped = dict(result)
            stamped['fetched_at'] = time.strftime('%Y-%m-%dT%H:%M:%S')
            changed = False
            for entry in self.config.values():
                if not isinstance(entry, dict):
                    continue
                if (entry.get('vndb_url') or '').strip() == vndb_url:
                    entry['vndb_cache'] = stamped
                    changed = True
            if changed:
                self._save_config()
        except Exception as e:
            print(f'[VNDB cache] persist failed: {e}')

    def vndb_cache_age(self, vndb_url):
        cached = self.vndb_cache.get(vndb_url)
        if not isinstance(cached, dict):
            return None
        fetched_at = cached.get('fetched_at')
        if not fetched_at:
            return None
        try:
            return time.time() - time.mktime(time.strptime(fetched_at, '%Y-%m-%dT%H:%M:%S'))
        except Exception:
            return None
    VNDB_LENGTH_LABELS = {1: 'Very Short (<2h)', 2: 'Short (2-10h)', 3: 'Medium (10-30h)', 4: 'Long (30-50h)', 5: 'Very Long (>50h)'}

    def scrape_vndb_page(self, vndb_url):
        match = re.search('v(\\d+)', vndb_url or '')
        if not match:
            return None
        url = f'https://vndb.org/v{match.group(1)}'
        try:
            _vndb_limiter.wait()
            response = _vndb_session.get(url, headers=BROWSER_HEADERS, timeout=15)
            response.raise_for_status()
            page = response.text
        except requests.exceptions.RequestException as e:
            print(f'[VNDB scrape] error: {e}')
            return None
        try:
            rating = ''
            rating_match = re.search(r'([\d.]+)\s+average\s*\(\s*rank', page)
            if rating_match:
                rating = f'{float(rating_match.group(1)):.1f}'
            length = ''
            playtime_match = re.search(r'Play time</td><td>(.*?)</td>', page, re.S)
            if playtime_match:
                cell = re.sub(r'<[^>]+>', '', playtime_match.group(1)).strip()
                for label, value in (('Very Short', 1), ('Very Long', 5), ('Short', 2), ('Medium', 3), ('Long', 4)):
                    if cell.startswith(label):
                        length = value
                        break
            developer = ''
            developer_match = re.search(r'Developer</td><td>(.*?)</td>', page, re.S)
            if developer_match:
                names = [n.strip() for n in re.findall(r'<a[^>]*>([^<]+)</a>', developer_match.group(1))]
                developer = ', '.join(n for n in names if n)
            released = ''
            releases_match = re.search(r'<table class="releases">(.*?)</table>', page, re.S)
            if releases_match:
                for row in re.findall(r'<tr>(.*?)</tr>', releases_match.group(1), re.S):
                    date_match = re.search(r'<td class="tc1">(\d{4}-\d{2}-\d{2})</td>', row)
                    if date_match and 'icon-rttrial' not in row:
                        released = date_match.group(1)
                        break
            if not (rating or released or length or developer):
                return None
            return {'rating': rating, 'developer': developer, 'length': length, 'released': released}
        except Exception as e:
            print(f'[VNDB scrape] parse error: {e}')
            return None

    def fetch_vndb_info(self, vndb_url, cache_only=False):
        if not vndb_url:
            return None
        if vndb_url in self.vndb_cache:
            return self.vndb_cache[vndb_url]
        if cache_only:
            return None
        match = re.search('v(\\d+)', vndb_url)
        if not match:
            return None
        vn_id = f'v{match.group(1)}'
        result = None
        try:
            data = vndb_post('vn', {'filters': ['id', '=', vn_id], 'fields': 'rating,released,length,developers.name'}, token=self.settings.get('vndb_api_token'))
            if data.get('results'):
                vn = data['results'][0]
                raw_rating = vn.get('rating')
                rating = f'{raw_rating / 10:.1f}' if raw_rating else 'N/A'
                developers = vn.get('developers', [])
                dev_names = [d['name'] for d in developers]
                developer = ', '.join(dev_names) if dev_names else 'Unknown'
                user_status = None
                my_link = self.settings.get('my_vndb_link', '')
                user_match = re.search('u(\\d+)', my_link)
                if user_match:
                    user_id = f'u{user_match.group(1)}'
                    user_status = get_vn_status(user_id, vn_id, token=self.settings.get('vndb_api_token'))
                result = {'rating': rating, 'developer': developer, 'user_status': user_status, 'length': vn.get('length'), 'released': vn.get('released') or '', 'fetched_at': time.strftime('%Y-%m-%dT%H:%M:%S')}
        except Exception as e:
            print(f'[VNDB API] error: {e}')
        if result is None:
            scraped = self.scrape_vndb_page(vndb_url)
            if scraped:
                result = {'rating': scraped.get('rating', ''), 'developer': scraped.get('developer', ''), 'user_status': '', 'length': scraped.get('length', ''), 'released': scraped.get('released', ''), 'fetched_at': time.strftime('%Y-%m-%dT%H:%M:%S')}
                print(f'[VNDB] API unavailable, scraped page data for {vndb_url}')
        if result is None:
            return None
        self.vndb_cache[vndb_url] = result
        self._persist_vndb_cache(vndb_url, result)
        return result
    LIBRARY_CACHE_TTL_SECONDS = 12 * 60 * 60

    def _library_image_dir(self):
        return os.path.join(self.base_dir, 'Cache', 'images')

    def get_image_cache_path(self, url):
        digest = hashlib.sha1(url.encode('utf-8')).hexdigest()[:16]
        clean = (url or '').split('?')[0]
        ext = os.path.splitext(clean)[1].lower()
        if ext not in ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'):
            ext = '.jpg'
        return os.path.join(self._library_image_dir(), digest + ext)

    def load_cached_image(self, url):
        try:
            path = self.get_image_cache_path(url)
            if os.path.exists(path):
                return path
        except Exception:
            pass
        return None

    def download_image(self, url):
        if not url:
            return None
        try:
            path = self.get_image_cache_path(url)
            if os.path.exists(path):
                return path
            r = _vndb_session.get(url, timeout=15)
            r.raise_for_status()
            if not r.content or len(r.content) > 4000000:
                return None
            os.makedirs(os.path.dirname(path), exist_ok=True)
            tmp = path + '.part'
            with open(tmp, 'wb') as f:
                f.write(r.content)
            os.replace(tmp, path)
            return path
        except Exception:
            return None

    def _rebuild_explicit_url_set(self):
        explicit = set()
        for info in self.library_cache.values():
            if not isinstance(info, dict):
                continue
            for entry in info.get('gallery') or []:
                full = (entry.get('full') or '').replace('/cv.t/', '/cv/')
                if full and entry.get('exp'):
                    explicit.add(full)
            main = (info.get('cover_url_main') or '').replace('/cv.t/', '/cv/')
            if main and info.get('cover_explicit'):
                explicit.add(main)
        self._explicit_url_set = explicit
        return explicit

    def is_image_explicit(self, image_url):
        image_url = (image_url or '').strip()
        if not image_url:
            return False
        key = image_url.replace('/cv.t/', '/cv/')
        explicit = self._explicit_url_set
        if explicit is None:
            explicit = self._rebuild_explicit_url_set()
        return key in explicit

    def game_cover_explicit(self, exe):
        settings = self.config.get(exe) or {}
        vndb_url = (settings.get('vndb_url') or '').strip()
        if not vndb_url:
            return False
        info = self.library_cache.get(vndb_url) or {}
        return bool(info.get('cover_explicit'))

    @staticmethod
    def is_vndb_cover_url(url):
        url = (url or '').strip()
        return url.startswith(('https://i.vndb.org', 'https://t.vndb.org', 'http://i.vndb.org', 'http://t.vndb.org'))

    def is_cover_protected(self, exe, cover):
        settings = self.config.get(exe) or {}
        cover = (cover or '').strip()
        if not cover or not self.is_vndb_cover_url(cover):
            return False
        vndb_url = (settings.get('vndb_url') or '').strip()
        if vndb_url:
            info = self.library_cache.get(vndb_url)
            if isinstance(info, dict) and info.get('cover_explicit') is not None:
                return bool(info.get('cover_explicit'))
        return self.is_image_explicit(cover)

    def fetch_vn_cover_rating(self, vndb_url):
        vndb_url = (vndb_url or '').strip()
        match = re.search(r'v(\d+)', vndb_url)
        if not match:
            return None
        try:
            _vndb_limiter.wait()
            response = _vndb_session.get(f'https://vndb.org/v{match.group(1)}', headers=BROWSER_HEADERS, timeout=15)
            response.raise_for_status()
            page = response.text
        except requests.exceptions.RequestException as e:
            print(f'[VNDB cover rating] error: {e}')
            return None
        out = {'cover_explicit': None, 'cover_url_main': ''}
        m = re.search('<div class="vnimg">(.*?)(?:</div></div>|</details></div>)', page, re.S)
        if not m:
            return None
        frag = m.group(1)
        cm = re.search('<a href="(https://t\\.vndb\\.org/cv/[^"]+)"', frag)
        if not cm:
            cm = re.search('<img[^>]+src="(https://t\\.vndb\\.org/cv/[^"]+)"', frag)
        if cm:
            out['cover_url_main'] = cm.group(1)
        om = re.search('imghover--overlay">([^<]+)<', frag)
        if not om:

            om = re.search('imghover--overlay">([^<]+)<', page)
        if om:
            out['cover_explicit'] = 1 if om.group(1).lower().startswith('explicit') else 0
        existing = self.library_cache.get(vndb_url)
        if not isinstance(existing, dict):
            existing = {}
        merged = dict(existing)
        if out['cover_explicit'] is not None:
            merged['cover_explicit'] = out['cover_explicit']
        if out['cover_url_main'] and not merged.get('cover_url_main'):
            merged['cover_url_main'] = out['cover_url_main']
        if 'fetched_at' not in merged:
            merged['fetched_at'] = time.strftime('%Y-%m-%dT%H:%M:%S')
        self.library_cache[vndb_url] = merged
        self._explicit_url_set = None
        self._persist_library_cache(vndb_url, merged)
        return out

    def fetch_vn_cover_ratings(self, results):
        def fetch(vn):
            vn_id = (vn or {}).get('id') or ''
            if not vn_id:
                return None
            return self.fetch_vn_cover_rating(f'https://vndb.org/{vn_id}')
        with ThreadPoolExecutor(max_workers=4) as pool:
            return list(pool.map(fetch, results))

    @staticmethod
    def is_usable_image_ref(ref):
        ref = (ref or '').strip()
        if not ref:
            return False
        if ref.lower().startswith(('http://', 'https://')):
            return True
        try:
            return os.path.isfile(ref)
        except Exception:
            return False

    def get_rpc_cover_url(self, exe):
        settings = self.config.get(exe, {})
        cover = (settings.get('cover_url') or '').strip()
        if not self.is_usable_image_ref(cover):
            cover = (settings.get('large_image') or '').strip()
        if not self.is_usable_image_ref(cover):
            cover = ''
        if not cover:
            vndb_url = (settings.get('vndb_url') or '').strip()
            if vndb_url:
                info = self.library_cache.get(vndb_url)
                if isinstance(info, dict) and info.get('cover_url_main'):
                    cover = info['cover_url_main']
                    settings['cover_url'] = cover
        if not cover:
            return cover
        if not self.settings.get('replace_rpc_explicit', True):
            return cover
        if not self.is_cover_protected(exe, cover):
            return cover
        return VNDB_DEFAULT_COVER_URL

    def _blur_image_file(self, local_path):
        from PIL import Image, ImageOps
        with Image.open(local_path) as img:
            img = ImageOps.exif_transpose(img).convert('RGB')
            w, h = img.size
            small = img.resize((max(1, w // 20), max(1, h // 20)), Image.Resampling.BILINEAR)
            blurred = small.resize((w, h), Image.Resampling.BILINEAR)
        digest = hashlib.sha1(local_path.encode('utf-8')).hexdigest()[:16]
        out_path = os.path.join(self._library_image_dir(), f'blurred_{digest}.png')
        blurred.save(out_path, 'PNG', optimize=True)
        return out_path

    def _upload_blurred_cover(self, local_path):
        host = (self.settings.get('image_host', 'none') or 'none').strip().lower()
        if host == 'none':
            raise RuntimeError('no image host configured. Set one in Settings -> API Settings')
        url = upload_image_file(local_path, host, self.settings)
        if not url:
            raise RuntimeError(f"image host '{host}' returned no URL")
        return url

    def ensure_blurred_cover(self, exe, on_done=None, on_error=None):
        settings = self.config.get(exe, {})
        if not isinstance(settings, dict):
            return
        cover = settings.get('cover_url') or settings.get('large_image', '')
        if not cover or settings.get('blurred_cover_url'):
            return
        if not self.settings.get('replace_rpc_explicit', True):
            return
        if not (self.game_cover_explicit(exe) or self.is_image_explicit(cover)):
            return
        if exe in self._blurred_inflight:
            return
        self._blurred_inflight.add(exe)

        def task():
            local = self.download_image(cover)
            if not local:
                raise RuntimeError('could not download the cover image')
            blurred_path = self._blur_image_file(local)
            return self._upload_blurred_cover(blurred_path)

        def on_success(url):
            self._blurred_inflight.discard(exe)
            try:
                self.config[exe]['blurred_cover_url'] = url
                self._save_config()
            except Exception:
                pass
            if on_done:
                on_done(url)

        def on_failed(message):
            self._blurred_inflight.discard(exe)
            if on_error:
                on_error(message)
        run_async_task(task, on_success, on_failed)

    @staticmethod
    def _strip_html(fragment):
        fragment = re.sub('<br\\s*/?>', ' ', fragment or '')
        fragment = re.sub('<[^>]+>', '', fragment)
        return html.unescape(fragment).strip()

    def fetch_vn_page_details(self, vndb_url):
        match = re.search('v(\\d+)', vndb_url or '')
        if not match:
            return {}
        r = _vndb_session.get(f'https://vndb.org/v{match.group(1)}', timeout=15)
        r.raise_for_status()
        text = r.text
        out = {}
        m = re.search('<tr><td>Aliases</td><td>(.*?)</td></tr>', text, re.S)
        if m:
            out['aliases'] = self._strip_html(m.group(1))
        m = re.search('<tr><td>Play time</td><td>(.*?)</td></tr>', text, re.S)
        if m:
            out['playtime_vndb'] = self._strip_html(m.group(1))
        shots = []
        m = re.search('<article id="screenshots">(.*?)</article>', text, re.S)
        if m:
            frag = m.group(1)
            for full, cls, thumb in re.findall('<a href="(https://t\\.vndb\\.org/sf/[^"]+)"[^>]*class="([^"]*)"[^>]*><img[^>]+src="(https://t\\.vndb\\.org/sf\\.t/[^"]+)"', frag):
                shots.append({'thumb': thumb, 'full': full, 'exp': 1 if ('nsfw' in cls and 'scrlnk_s1' not in cls) else 0})
            if not shots:
                for src in re.findall('src="(https://t\\.vndb\\.org/sf\\.t/[^"]+)"', frag):
                    full = src.replace('/sf.t/', '/sf/')
                    shots.append({'thumb': src, 'full': full, 'exp': 0})
        out['screenshots'] = shots
        segs = []
        m = re.search('<td class="vndesc"[^>]*><h2>Description</h2>(.*?)</td>', text, re.S)
        if m:
            frag = m.group(1)
            pos = 0
            for sm in re.finditer('<span class="spoiler">(.*?)</span>', frag, re.S):
                if sm.start() > pos:
                    segs.append({'t': self._clean_desc_chunk(frag[pos:sm.start()]), 's': 0})
                segs.append({'t': self._clean_desc_chunk(sm.group(1)), 's': 1})
                pos = sm.end()
            if pos < len(frag):
                segs.append({'t': self._clean_desc_chunk(frag[pos:]), 's': 0})
            segs = [s for s in segs if s['t'].strip()]
        if segs:
            out['description_segments'] = segs
        links = []
        m = re.search('<tr><td>Links</td><td>(.*?)</td></tr>', text, re.S)
        if m:
            for u, n in re.findall('<a href="([^"]+)"[^>]*>([^<]+)</a>', m.group(1)):
                links.append({'name': n.strip(), 'url': u})
        if links:
            out['links'] = links
        out['cover_explicit'] = None
        out['cover_url_main'] = ''
        m = re.search('<div class="vnimg">(.*?)(?:</div></div>|</details></div>)', text, re.S)
        if m:
            frag = m.group(1)
            cm = re.search('<a href="(https://t\\.vndb\\.org/cv/[^"]+)"', frag)
            if not cm:
                cm = re.search('<img[^>]+src="(https://t\\.vndb\\.org/cv/[^"]+)"', frag)
            if cm:
                out['cover_url_main'] = cm.group(1)
            om = re.search('imghover--overlay">([^<]+)<', frag)
            if om:
                out['cover_explicit'] = 1 if om.group(1).lower().startswith('explicit') else 0
        return out

    @staticmethod
    def _clean_desc_chunk(chunk):
        t = re.sub('<[^>]+>', ' ', chunk)
        t = html.unescape(t)
        t = re.sub('\\s+', ' ', t)
        return t

    def fetch_vn_gallery(self, vndb_url, limit=24):
        match = re.search('v(\\d+)', vndb_url or '')
        if not match:
            return []
        r = _vndb_session.get(f'https://vndb.org/v{match.group(1)}/cv', timeout=15)
        r.raise_for_status()
        out, seen = ([], set())
        blocks = []
        for tag in ('div', 'details'):
            for bm in re.finditer(f'<{tag} class="imghover[^"]*"[^>]*>(.*?)</{tag}>', r.text, re.S):
                blocks.append((bm.start(), bm.group(1)))
        blocks.sort()
        for _pos, block in blocks:
            sm = re.search('<img[^>]+src="(https://t\\.vndb\\.org/cv[^"]+)"', block)
            if not sm:
                continue
            src = sm.group(1)
            full = src.replace('/cv.t/', '/cv/')
            if full in seen:
                continue
            seen.add(full)
            thumb = src if '/cv.t/' in src else full
            om = re.search('imghover--overlay">([^<]+)<', block)
            rating = om.group(1) if om else ''
            out.append({'thumb': thumb, 'full': full, 'exp': 1 if rating.lower().startswith('explicit') else 0})
            if len(out) >= limit:
                break
        return out

    def fetch_vn_library_info(self, vndb_url, force=False):
        vndb_url = (vndb_url or '').strip()
        if not vndb_url:
            return None
        age = self.library_cache_age(vndb_url)
        if vndb_url in self.library_cache and age is not None and (age < self.LIBRARY_CACHE_TTL_SECONDS) and (not force):
            return self.library_cache[vndb_url]
        info = self.fetch_vndb_info(vndb_url) or {}
        title = ''
        description = ''
        match = re.search('v(\\d+)', vndb_url)
        if match:
            try:
                data = vndb_post('vn', {'filters': ['id', '=', f'v{match.group(1)}'], 'fields': 'title,description'}, token=self.settings.get('vndb_api_token'))
                results = data.get('results') or []
                if results:
                    title = results[0].get('title') or ''
                    description = results[0].get('description') or ''
            except Exception:
                pass
        try:
            gallery = self.fetch_vn_gallery(vndb_url)
        except Exception:
            gallery = []
        try:
            page = self.fetch_vn_page_details(vndb_url)
        except Exception:
            page = {}
        result = {'title': title, 'description': description, 'aliases': page.get('aliases', ''), 'playtime_vndb': page.get('playtime_vndb', ''), 'rating': info.get('rating', 'N/A'), 'developer': info.get('developer', 'Unknown'), 'released': info.get('released') or '', 'length': info.get('length'), 'gallery': gallery, 'screenshots': page.get('screenshots', []), 'description_segments': page.get('description_segments', []), 'links': page.get('links', []), 'cover_explicit': page.get('cover_explicit'), 'cover_url_main': page.get('cover_url_main', ''), 'schema': 2, 'fetched_at': time.strftime('%Y-%m-%dT%H:%M:%S')}
        self.library_cache[vndb_url] = result
        self._explicit_url_set = None
        self._persist_library_cache(vndb_url, result)
        return result

    def _persist_library_cache(self, vndb_url, result):
        try:
            stamped = dict(result)
            changed = False
            for entry in self.config.values():
                if not isinstance(entry, dict):
                    continue
                if (entry.get('vndb_url') or '').strip() == vndb_url:
                    entry['library_cache'] = stamped
                    changed = True
            if changed:
                self._save_config()
        except Exception as e:
            print(f'[Library cache] persist failed: {e}')

    def _seed_persistent_library_cache(self):
        for entry in self.config.values():
            if not isinstance(entry, dict):
                continue
            url = (entry.get('vndb_url') or '').strip()
            cached = entry.get('library_cache')
            if url and isinstance(cached, dict) and cached:
                self.library_cache.setdefault(url, dict(cached))

    def library_cache_age(self, vndb_url):
        cached = self.library_cache.get(vndb_url)
        if not isinstance(cached, dict):
            return None
        fetched_at = cached.get('fetched_at')
        if not fetched_at:
            return None
        try:
            return time.time() - time.mktime(time.strptime(fetched_at, '%Y-%m-%dT%H:%M:%S'))
        except Exception:
            return None

    def get_playtime_seconds(self, game_key):
        try:
            return float((self.config.get(game_key) or {}).get('total_playtime_seconds', 0) or 0)
        except (TypeError, ValueError):
            return 0.0

    def get_playtime_by_date(self, game_key):
        try:
            data = (self.config.get(game_key) or {}).get('playtime_by_date') or {}
        except AttributeError:
            data = {}
        out = {}
        for day, secs in data.items():
            try:
                out[str(day)] = max(0, int(secs))
            except (TypeError, ValueError):
                continue
        return dict(sorted(out.items()))

    def tick_playtime(self, running_keys):
        if not running_keys:
            return
        now_iso = time.strftime('%Y-%m-%d %H:%M')
        today = time.strftime('%Y-%m-%d')
        for key in running_keys:
            entry = self.config.get(key)
            if not isinstance(entry, dict):
                continue
            entry['total_playtime_seconds'] = self.get_playtime_seconds(key) + 1
            entry['last_played'] = now_iso
            by_date = entry.get('playtime_by_date')
            if not isinstance(by_date, dict):
                by_date = {}
                entry['playtime_by_date'] = by_date
            by_date[today] = by_date.get(today, 0) + 1
        self._playtime_dirty = True
        self._playtime_tick_count += 1
        if self._playtime_tick_count >= 10:
            self._playtime_tick_count = 0
            self._playtime_dirty = False
            self._save_config()

    def flush_playtime(self):
        if self._playtime_dirty:
            self._playtime_dirty = False
            self._save_config()

def extract_freeimage_url(payload):
    if not isinstance(payload, dict):
        return None
    image = payload.get('image') if isinstance(payload.get('image'), dict) else {}
    for key in ('url', 'image_url', 'display_url', 'link'):
        url = image.get(key)
        if url:
            return str(url)
    data = payload.get('data') if isinstance(payload.get('data'), dict) else {}
    for key in ('url', 'image_url', 'display_url', 'link'):
        url = data.get(key)
        if url:
            return str(url)
    return None

def upload_image_file(file_path, host, settings):
    host = (host or 'none').strip().lower()
    if not os.path.exists(file_path):
        raise RuntimeError(f'Upload file not found:\n{file_path}')
    if host == 'catbox':
        with open(file_path, 'rb') as f:
            response = requests.post('https://catbox.moe/user/api.php', data={'reqtype': 'fileupload'}, files={'fileToUpload': f}, headers={'User-Agent': HEADERS['User-Agent']}, timeout=60)
        response.raise_for_status()
        url = response.text.strip()
        if not url.startswith('http'):
            raise RuntimeError(f"Catbox upload failed: {url[:200] or 'no response'}")
        return url
    if host == 'imgbb':
        api_key = (settings.get('imgbb_api_key', '') or '').strip()
        if not api_key:
            raise RuntimeError('ImgBB API key missing. Add it in Settings > API Settings.')
        with open(file_path, 'rb') as f:
            image_b64 = base64.b64encode(f.read()).decode()
        response = requests.post('https://api.imgbb.com/1/upload', data={'key': api_key, 'image': image_b64}, headers=BROWSER_HEADERS, timeout=60)
        try:
            payload = response.json()
        except ValueError:
            raise RuntimeError(f'ImgBB upload failed (HTTP {response.status_code}): {response.text[:150]}')
        url = (payload.get('data') or {}).get('url')
        if not url:
            error = (payload.get('error') or {}).get('message') or response.text[:150]
            raise RuntimeError(f'ImgBB upload failed: {error}')
        return url
    if host == 'postimages':
        api_key = (settings.get('postimages_api_key', '') or '').strip()
        if not api_key:
            raise RuntimeError('PostImages API key missing. Add it in Settings > API Settings.')
        with open(file_path, 'rb') as f:
            response = requests.post('https://api.postimages.org/v1/upload', files={'file': (os.path.basename(file_path), f, 'image/png')}, headers={'User-Agent': HEADERS['User-Agent'], 'Authorization': f'Bearer {api_key}'}, timeout=60)
        if not response.text.strip():
            raise RuntimeError('PostImages upload failed: empty response (check the API key).')
        try:
            payload = response.json()
        except ValueError:
            raise RuntimeError(f'PostImages upload failed (HTTP {response.status_code}): {response.text[:150]}')
        url = payload.get('url') or (payload.get('image') or {}).get('url')
        if not url:
            raise RuntimeError(f'PostImages upload failed: {payload}')
        return url
    if host == 'freeimage':
        api_key = settings.get('freeimage_api_key', '').strip() or settings.get('imgur_client_id', '').strip() or os.environ.get('FREEIMAGE_API_KEY', '').strip() or os.environ.get('IMGUR_CLIENT_ID', '').strip()
        if not api_key:
            raise RuntimeError("FreeImage.host upload requires an API key. Add 'freeimage_api_key' in Settings > API Settings.")
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            try:
                with open(file_path, 'rb') as f:
                    response = requests.post('https://freeimage.host/api/1/upload', data={'key': api_key, 'action': 'upload', 'format': 'json'}, files={'source': (os.path.basename(file_path), f, 'image/png')}, timeout=60)
                try:
                    payload = response.json()
                except ValueError:
                    raise RuntimeError(f'FreeImage.host upload returned invalid JSON:\n{response.text[:500]}')
                success = payload.get('success')
                if response.status_code != 200 and payload.get('status_code') not in (None, 200):
                    raise RuntimeError(f"FreeImage.host upload failed: {payload.get('error') or response.text[:200]}")
                if success is False or (isinstance(success, dict) and success.get('code') not in (None, 200)):
                    raise RuntimeError(f"FreeImage.host upload failed: {payload.get('error') or response.text[:200]}")
                image_url = extract_freeimage_url(payload)
                if not image_url:
                    raise RuntimeError(f'FreeImage.host upload returned no image URL:\n{payload}')
                return image_url
            except (requests.exceptions.RequestException, RuntimeError):
                if attempt >= max_attempts:
                    raise
                time.sleep(2 * attempt)
        raise RuntimeError('FreeImage.host upload failed after all attempts.')
    raise RuntimeError(f"Unknown image host: '{host}'")

class UpdateCheckNoRelease(RuntimeError):
    pass

def fetch_latest_github_release(timeout=10):
    headers = {'User-Agent': HEADERS['User-Agent'], 'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28'}
    response = requests.get(f'{GITHUB_REPO_URL}/releases/latest', headers=headers, timeout=timeout)
    if response.status_code == 404:
        raise UpdateCheckNoRelease('This project has no releases yet.')
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, dict) or not data.get('tag_name'):
        raise UpdateCheckNoRelease('This project has no releases yet.')
    return data

def _parse_version_text(text):
    text = str(text or '').strip().lstrip('vV')
    parts = []
    for chunk in text.split('.'):
        match = re.match(r'(\d+)', chunk)
        parts.append(int(match.group(1)) if match else 0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])

def _is_newer_version(release_text, current_text):
    return _parse_version_text(release_text) > _parse_version_text(current_text)

def _format_file_size(num):
    try:
        num = float(num)
    except (TypeError, ValueError):
        return ''
    for unit in ('B', 'KB', 'MB', 'GB', 'TB'):
        if num < 1024.0:
            return f'{num:.0f} {unit}' if unit == 'B' else f'{num:.1f} {unit}'
        num /= 1024.0
    return f'{num:.1f} TB'

class _ClickableLabel(QLabel):
    clicked = pyqtSignal()
    hoverChanged = pyqtSignal(bool)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def enterEvent(self, event):
        self.hoverChanged.emit(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.hoverChanged.emit(False)
        super().leaveEvent(event)

class _GameRowWidget(QWidget):
    rowClicked = pyqtSignal(str)

    def __init__(self, game_key, parent=None):
        super().__init__(parent)
        self._game_key = game_key

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.rowClicked.emit(self._game_key)
            event.accept()
            return
        super().mousePressEvent(event)

class _ChatBubble(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._text = ''
        self._font = QFont()
        self._font.setPixelSize(11)
        self._font.setBold(True)
        self._max_width = 220
        self._padding_x = 10
        self._padding_y = 7
        self._pointer_h = 6
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)

    def set_text(self, text):
        self._text = str(text or '')
        self._resize_to_text()
        self.update()

    def _wrap_lines(self):
        fm = QFontMetrics(self._font)
        max_w = max(10, self._max_width - self._padding_x * 2)
        lines = []
        for paragraph in self._text.split('\n'):
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            word = ''
            for piece in paragraph.split(' '):
                if fm.horizontalAdvance(piece) > max_w:
                    piece = fm.elidedText(piece, Qt.TextElideMode.ElideRight, max_w)
                candidate = f'{word} {piece}'.strip()
                if fm.horizontalAdvance(candidate) <= max_w:
                    word = candidate
                else:
                    if word:
                        lines.append(word)
                    word = piece
            if word:
                lines.append(word)
        max_lines = 4
        if len(lines) > max_lines:
            lines = lines[:max_lines]
            lines[-1] = fm.elidedText(lines[-1], Qt.TextElideMode.ElideRight, max_w)
        return lines

    def _resize_to_text(self):
        lines = self._wrap_lines()
        fm = QFontMetrics(self._font)
        line_h = fm.height()
        text_w = max((fm.horizontalAdvance(l) for l in lines), default=0)
        w = max(int(text_w) + self._padding_x * 2, 44)
        h = line_h * len(lines) + self._padding_y * 2 + self._pointer_h
        self.setFixedSize(w, h)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        body_rect = QRectF(1, 1, self.width() - 2, self.height() - self._pointer_h - 1)
        painter.setBrush(QColor(30, 31, 34, 235))
        painter.drawRoundedRect(body_rect, 6, 6)
        cx = self.width() / 2
        top_y = self.height() - self._pointer_h - 1
        tri = QPolygonF([QPointF(cx - 6, top_y), QPointF(cx + 6, top_y), QPointF(cx, self.height() - 1)])
        painter.drawPolygon(tri)
        painter.setFont(self._font)
        painter.setPen(QColor('#f2f3f5'))
        fm = QFontMetrics(self._font)
        line_h = fm.height()
        y = self._padding_y + line_h // 2
        for line in self._wrap_lines():
            x = (self.width() - fm.horizontalAdvance(line)) // 2
            painter.drawText(int(x), y, line)
            y += line_h
        painter.end()

class _TaskSignals(QObject):
    succeeded = pyqtSignal(object)
    failed = pyqtSignal(str)

class _ScanSignals(QObject):
    scan_done = pyqtSignal(object)
    ui_job = pyqtSignal(object)
_async_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix='vn-rpc')

_active_task_signals = set()

def run_async_task(task_func, on_success, on_error):
    signals = _TaskSignals()
    _active_task_signals.add(signals)

    def _cleanup(*_args):
        _active_task_signals.discard(signals)
        signals.deleteLater()

    signals.succeeded.connect(on_success)
    signals.failed.connect(on_error)
    signals.succeeded.connect(_cleanup)
    signals.failed.connect(_cleanup)

    def _work():
        try:
            result = task_func()
        except Exception as e:
            signals.failed.emit(str(e))
            return
        signals.succeeded.emit(result)
    _async_executor.submit(_work)
    return signals

class ImageViewerDialog(QDialog):
    def __init__(self, parent, rpc_core, url):
        super().__init__(parent)
        self._rpc_core = rpc_core
        self._url = url
        self._full_pm = None
        self._task = None
        name = os.path.basename((url or '').split('?')[0])
        self.setWindowTitle(name or 'Image')
        self._margin = 8
        self.setMinimumSize(120, 100)
        self.label = QLabel(self)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.label.setStyleSheet('background-color: #141417; color: #5c5e66;')
        layout = QVBoxLayout(self)
        layout.setContentsMargins(self._margin, self._margin, self._margin, self._margin)
        layout.addWidget(self.label)
        self._load()

    def _load(self):
        cached = self._rpc_core.load_cached_image(self._url)
        if cached:
            pm = QPixmap(cached)
            if not pm.isNull():
                self._set_image(pm)
                return
        self.label.setText('loading...')

        def on_done(path):
            if not self.isVisible():
                return
            pm = QPixmap(path) if path else QPixmap()
            if pm.isNull():
                self.label.setText('Could not load image')
            else:
                self._set_image(pm)

        def on_error(_message):
            if self.isVisible():
                self.label.setText('Could not load image')
        self._task = run_async_task(lambda: self._rpc_core.download_image(self._url), on_done, on_error)

    def _set_image(self, pm):
        self._full_pm = pm
        long_side = min(max(pm.width(), pm.height()), 400)
        if pm.width() >= pm.height():
            w = long_side
            h = max(1, round(long_side * pm.height() / pm.width()))
        else:
            h = long_side
            w = max(1, round(long_side * pm.width() / pm.height()))
        self.resize(w + 2 * self._margin, h + 2 * self._margin)
        self._fit()

    def _fit(self):
        pm = self._full_pm
        if pm is None:
            return
        target = self.label.size()
        scale = min(1.0, max(1, target.width()) / pm.width(), max(1, target.height()) / pm.height())
        mode = Qt.TransformationMode.SmoothTransformation if scale < 1.0 else Qt.TransformationMode.FastTransformation
        self.label.setPixmap(pm.scaled(int(pm.width() * scale), int(pm.height() * scale), Qt.AspectRatioMode.KeepAspectRatio, mode))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._fit()

def arm_window_picker(btn, on_capture, seconds=5):
    remaining = {'n': seconds}
    orig_min = btn.minimumSize()
    orig_max = btn.maximumSize()

    def paint(n):
        btn.setText(str(n))
        btn.setStyleSheet('QPushButton { background-color: #f85149; color: #ffffff; font-weight: bold; font-size: 14px; border-radius: 6px; padding: 6px;}')

    def restore():
        btn.setText('Click the game window')
        btn.setStyleSheet('')
        btn.setEnabled(True)
        btn.setMinimumSize(orig_min)
        btn.setMaximumSize(orig_max)
    timer = QTimer(btn)
    timer.setInterval(1000)

    def tick():
        remaining['n'] -= 1
        if remaining['n'] <= 0:
            timer.stop()
            restore()
            on_capture()
        else:
            paint(remaining['n'])
    timer.timeout.connect(tick)
    btn.setEnabled(False)
    btn.setFixedSize(btn.size())
    paint(seconds)
    timer.start()
CUSTOM_VARIABLES = ['vn_name', 'activity_name', 'window_title', 'exe_name', 'game_key', 'large_text', 'vndb_url', 'vndb_rating', 'vndb_developer', 'vndb_status', 'vndb_length', 'vndb_year', 'vndb_released', 'elapsed_time', 'date', 'time']

CUSTOM_SCRIPT_DIR_NAME = 'Custom'

CUSTOM_PYTHON_TEMPLATE = '''# ============================================================
#   EwE - Custom Python Processing
# ============================================================
#   * NAME is the variable name. Use it in the templates as
#     {name}. Letters, numbers and underscores only.
#   * Everything your script prints (print()) becomes the
#     VALUE of this variable. Only the first printed line is
#     used.
#   * Save this file - EwE picks up the changes automatically
#     (the value refreshes every few seconds).
#   * You can use any Python: os, time, json, requests, ...
# ============================================================

NAME = "__CUSTOM_VAR_NAME__"

# --- your code starts here ---------------------------------
print("Hello from EwE")
# --- your code ends here ------------------------------------
'''

class _TemplateHighlighter(QSyntaxHighlighter):

    def __init__(self, document, extra_names=()):
        super().__init__(document)
        self._known_fmt = QTextCharFormat()
        self._known_fmt.setForeground(QColor('#56d4dd'))
        self._known_fmt.setFontWeight(QFont.Weight.Bold)
        self._unknown_fmt = QTextCharFormat()
        self._unknown_fmt.setForeground(QColor('#f85149'))
        self._unknown_fmt.setFontWeight(QFont.Weight.Bold)
        self._comment_fmt = QTextCharFormat()
        self._comment_fmt.setForeground(QColor('#8b949e'))
        self._comment_fmt.setFontItalic(True)
        self._any_rule = (QRegularExpression('\\{[a-zA-Z_][a-zA-Z0-9_]*\\}'), self._unknown_fmt)
        self._comment_rule = (QRegularExpression('^\\s*#.*'), self._comment_fmt)
        self._rules = [self._any_rule]
        self.set_known_names(list(CUSTOM_VARIABLES) + list(extra_names or ()))

    def set_known_names(self, names):
        known = sorted({n for n in names if n})
        known_token = QRegularExpression('\\{(' + '|'.join((re.escape(k) for k in known)) + ')\\}')
        self._rules = [self._any_rule, (known_token, self._known_fmt), self._comment_rule]
        try:
            self.rehighlight(self.document())
        except Exception:
            pass

    def highlightBlock(self, text):
        try:
            doc = self.document()
            block = self.currentBlock()
            block_start = block.position()
            block_length = len(block.text())

            def fmt_char(pos, fmt):
                cursor = QTextCursor(doc)
                cursor.setPosition(pos - 1 if pos > 0 else 0)
                cursor.setPosition(pos, QTextCursor.MoveMode.KeepAnchor)
                cursor.setCharFormat(fmt)

            def fmt_range(s, e, fmt):
                if s == 0:
                    cursor = QTextCursor(doc)
                    cursor.setPosition(0)
                    cursor.setPosition(e, QTextCursor.MoveMode.KeepAnchor)
                    cursor.setCharFormat(fmt)
                else:
                    for pos in range(s, e + 1):
                        fmt_char(pos, fmt)

            fmt_range(block_start, block_start + block_length - 1, QTextCharFormat())
            for pattern, fmt in self._rules:
                it = pattern.globalMatch(text, 0)
                while it.hasNext():
                    m = it.next()
                    start = m.capturedStart(0)
                    length = m.capturedLength(0)
                    if start < 0 or length <= 0:
                        continue
                    fmt_range(block_start + start, block_start + start + length - 1, fmt)
        except Exception:
            pass

class _CodeLineNumbersArea(QWidget):

    def __init__(self, editor):
        super().__init__(editor)
        self._editor = editor

    def sizeHint(self):
        return QSize(self._editor.lineNumberAreaWidth(), 0)

    def paintEvent(self, event):
        self._editor.lineNumberAreaPaintEvent(event)

class _CodeEditor(QPlainTextEdit):

    def __init__(self, parent=None, known_variables=None):
        super().__init__(parent)
        self._line_area = _CodeLineNumbersArea(self)
        self.blockCountChanged.connect(self._update_line_area_width)
        self.updateRequest.connect(self._update_line_area)
        self._update_line_area_width(0)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        font = QFont('Consolas', 10)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.setFont(font)
        self.setStyleSheet('QPlainTextEdit { background-color: #0d1117; color: #dbdee1; border: 1px solid #3f4147; border-radius: 4px; selection-background-color: #264f78;}QPlainTextEdit QScrollBar:vertical { background: #0d1117; width: 10px; margin: 0;}QPlainTextEdit QScrollBar::handle:vertical { background: #3f4147; min-height: 24px; border-radius: 5px;}QPlainTextEdit QScrollBar::add-line:vertical,QPlainTextEdit QScrollBar::sub-line:vertical { height: 0; }')
        self._highlighter = _TemplateHighlighter(self.document(), extra_names=known_variables)
        self.cursorPositionChanged.connect(self._cursor_position_changed)

    def set_known_variables(self, names):
        try:
            self._highlighter.set_known_names(list(CUSTOM_VARIABLES) + list(names or ()))
        except Exception:
            pass

    def lineNumberAreaWidth(self):
        digits = max(2, len(str(max(1, self.blockCount()))))
        return 10 + self.fontMetrics().horizontalAdvance('9') * digits + 10

    def _update_line_area_width(self, _new_block_count):
        self.setViewportMargins(self.lineNumberAreaWidth(), 0, 0, 0)

    def _update_line_area(self, rect, dy):
        if dy:
            self._line_area.scroll(0, dy)
        else:
            self._line_area.update(0, rect.y(), self._line_area.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self._update_line_area_width(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self._line_area.setGeometry(QRect(cr.left(), cr.top(), self._line_area.sizeHint().width(), cr.height()))

    def lineNumberAreaPaintEvent(self, event):
        painter = QPainter(self._line_area)
        painter.fillRect(event.rect(), QColor('#010409'))
        font = QFont(self.font())
        font.setBold(False)
        painter.setFont(font)
        block = self.firstVisibleBlock()
        block_top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        block_height = int(self.blockBoundingRect(block).height())
        current_line = self.textCursor().blockNumber()
        while block.isValid():
            if block.isVisible() and block_top >= event.rect().top():
                number = str(block.blockNumber() + 1)
                if block.blockNumber() == current_line:
                    painter.setPen(QColor('#f0f6fc'))
                else:
                    painter.setPen(QColor('#5c6370'))
                painter.drawText(0, block_top, self._line_area.width() - 6, block_height, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, number)
            block = block.next()
            block_top = block_top + block_height
            if block_top < event.rect().bottom():
                continue
            break

    def _highlight_current_line(self):
        selections = []
        selection = QTextEdit.ExtraSelection()
        selection.format.setBackground(QColor('#161b22'))
        selection.cursor = self.textCursor()
        selection.cursor.clearSelection()
        selections.append(selection)
        self.setExtraSelections(selections)

    def _cursor_position_changed(self):
        if self.hasFocus():
            self._highlight_current_line()
        else:
            self.setExtraSelections([])
_STATUS_COLOR_RULES = ((('error', 'failed', 'fail', 'no configuration', 'not found'), '#f85149'), (('is running', 'rpc updated', 'started '), '#3fb950'), (('clear', 'paused', 'resumed', 'stopped'), '#e3b341'), (('fetch', 'upload', 'staged'), '#58a6ff'), (('saved', 'deleted', 'updated', 'settings'), '#bc8cff'), (('window', 'game file', 'picked'), '#ffa657'))
_STATUS_DEFAULT_COLOR = '#d4d4d4'
_STATUS_ERROR_KEYWORDS = _STATUS_COLOR_RULES[0][0]
_RPC_UPDATED_RE = re.compile('^(?P<exe>.+) is running\\. RPC updated\\. \\(name: (?P<name>.+?) \\| details: (?P<details>.+?) \\| state: (?P<state>.+?) \\| (?P<buttons>buttons: \\d+|no buttons)\\)$')

class FlowLayout(QLayout):

    def __init__(self, parent=None, spacing=6):
        super().__init__(parent)
        self._spacing = spacing
        self._items = []

    def addItem(self, item):
        self._items.append(item)

    def count(self):
        return len(self._items)

    def itemAt(self, index):
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self._items):
            item = self._items.pop(index)
            if item.widget() is not None:
                item.widget().setParent(None)
            return item
        return None

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        height = 0
        for item in self._items:
            height = max(height, item.sizeHint().height())
        return QSize(0, height)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._do_layout(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._do_layout(rect, False)

    def _do_layout(self, rect, test_only):
        x = rect.x()
        y = rect.y()
        line_height = 0
        right = rect.x() + rect.width()
        for item in self._items:
            w = item.sizeHint().width()
            if x + w > right and x > rect.x():
                x = rect.x()
                y += line_height + self._spacing
                line_height = 0
            if not test_only:
                item.widget().setGeometry(QRect(x, y, w, item.sizeHint().height()))
            x += w + self._spacing
            line_height = max(line_height, item.sizeHint().height())
        return y + line_height - rect.y()

def _status_color(message):
    lowered = message.lower()
    for keywords, color in _STATUS_COLOR_RULES:
        if any((k in lowered for k in keywords)):
            return color
    return _STATUS_DEFAULT_COLOR

class StartupGuideDialog(QDialog):

    def __init__(self, rpc_core, parent_window=None, on_changed=None):
        super().__init__(parent_window)
        self.rpc_core = rpc_core
        self.on_changed = on_changed
        self.completed = False
        self._check_generation = 0
        self._discord_page_shown = False
        self.setModal(True)
        self.setWindowTitle('Startup Guide')
        self.setFixedSize(680, 640)
        self.setWindowIcon(QIcon(APP_ICON_PATH))
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 12, 16, 12)
        outer.setSpacing(10)
        header = QHBoxLayout()
        header_icon = QLabel()
        header_icon.setPixmap(QIcon(APP_ICON_PATH).pixmap(36, 36))
        header_title = QLabel('Welcome to EwE')
        header_title.setStyleSheet('font-size: 16px; font-weight: bold;')
        header.addWidget(header_icon)
        header.addWidget(header_title)
        header.addStretch(1)
        outer.addLayout(header)
        self.stack = QStackedLayout()
        self.stack.setSpacing(0)
        self._build_welcome_page()
        self._build_discord_page()
        self._build_vndb_page()
        self._build_image_host_page()
        self._build_done_page()
        outer.addLayout(self.stack, 1)
        nav = QHBoxLayout()
        self.back_btn = QPushButton('Back')
        self.next_btn = QPushButton('Next')
        nav.addStretch(1)
        nav.addWidget(self.back_btn)
        nav.addWidget(self.next_btn)
        outer.addLayout(nav)
        self.back_btn.clicked.connect(self._go_back)
        self.next_btn.clicked.connect(self._go_next)
        self.stack.currentChanged.connect(self._update_nav)
        self._update_nav(0)

    def _add_page(self, page):
        self.stack.addWidget(page)
        return page

    def _build_welcome_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(8, 8, 8, 8)
        intro = QLabel('EwE is a program that shows a Discord Rich Presence for visual novels you played.\n\nHow it works: \nIt watches running processes in realtime and when you add a Visual Novel processes, it publishes the title, cover art, details and state to your Discord profile.\n')
        intro.setWordWrap(True)
        layout.addWidget(intro)
        layout.addWidget(QLabel("<b>What you'll need:</b>"))
        needs = QLabel('•  Internet Connection\n•  The Discord desktop app, running\n•  Your VNDB.org profile link (optional)\n•  Image host service for customizeable upload (optional)\n•  The visual novels you play')
        needs.setWordWrap(True)
        layout.addWidget(needs)
        note = QLabel('You can skip the optional steps and finish them later on Settings.')
        note.setWordWrap(True)
        note.setStyleSheet('color: #8b949e;')
        layout.addWidget(note)
        layout.addStretch(1)
        self._add_page(page)

    def _build_discord_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.addWidget(QLabel('<b>Discord</b>'))
        desc = QLabel("EwE need Discord desktop app for it to connect to their server.")
        desc.setWordWrap(True)
        layout.addWidget(desc)
        status_row = QHBoxLayout()
        self.discord_status_dot = QLabel('●')
        self.discord_status_dot.setStyleSheet('color: #8b949e;')
        self.discord_status_label = QLabel('Not checked yet.')
        self.discord_status_label.setWordWrap(True)
        status_row.addWidget(self.discord_status_dot)
        status_row.addWidget(self.discord_status_label, 1)
        layout.addLayout(status_row)
        self.discord_check_btn = QPushButton('Check Discord now')
        self.discord_check_btn.setFixedWidth(180)
        layout.addWidget(self.discord_check_btn, 0, Qt.AlignmentFlag.AlignLeft)
        help_text = QLabel("If Discord is running but the presence doesn't connect:\nDiscord Settings -> Activity Privacy -> enable 'Share your detected activities with others.'\n")
        help_text.setWordWrap(True)
        help_text.setStyleSheet('color: #8b949e;')
        layout.addWidget(help_text)
        blur_note = QLabel('<b>Explicit</b> cover art are not shown on your Discord profile by default and will be replaced with VNDB eye icon.\nDiscord can ban accounts that show Explicit images in their profile. You can turn this off later in Settings <b>AT YOUR OWN RISK.</b>')
        blur_note.setWordWrap(True)
        blur_note.setStyleSheet('color: #8b949e;')
        layout.addWidget(blur_note)
        layout.addStretch(1)
        self.discord_check_btn.clicked.connect(self.check_discord)
        self._add_page(page)

    def _build_vndb_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.addWidget(QLabel('<b>VNDB.org profile (optional)</b>'))
        desc = QLabel("Add your VNDB profile link to show richer game details in your Discord Rich Presence.")
        desc.setWordWrap(True)
        layout.addWidget(desc)
        layout.addWidget(QLabel('Your VNDB profile link:'))
        self.vndb_profile_input = QLineEdit(self.rpc_core.get_setting('my_vndb_link', ''))
        self.vndb_profile_input.setPlaceholderText('https://vndb.org/uXXXXXX')
        layout.addWidget(self.vndb_profile_input)
        self.vndb_profile_hint = QLabel('')
        self.vndb_profile_hint.setWordWrap(True)
        self.vndb_profile_hint.setStyleSheet('color: #f85149;')
        layout.addWidget(self.vndb_profile_hint)
        layout.addWidget(QLabel('VNDB API token (optional, raises the rate limit):'))
        self.vndb_token_input = QLineEdit(self.rpc_core.get_setting('vndb_api_token', ''))
        self.vndb_token_input.setPlaceholderText('  ')
        layout.addWidget(self.vndb_token_input)
        list_note = QLabel()
        list_note.setWordWrap(True)
        list_note.setStyleSheet('color: #8b949e;')
        layout.addWidget(list_note)
        layout.addStretch(1)
        self.vndb_profile_input.textChanged.connect(self._validate_vndb_profile)
        self._validate_vndb_profile()
        self._add_page(page)

    def _build_image_host_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.addWidget(QLabel('<b>Image Host Services (optional)</b>'))
        desc = QLabel("With 'None', cover art is taken directly from VNDB. No API keys needed. But you cannot upload your own local images and some EwE features may be limited.")
        desc.setWordWrap(True)
        layout.addWidget(desc)
        host_options = [('none', 'None'), ('catbox', 'Catbox (Recommended)'), ('imgbb', 'ImgBB'), ('postimages', 'PostImages'), ('imgbs', 'IMG.BS (session cookie)'), ('freeimage', 'FreeImage')]
        saved_host = (self.rpc_core.get_setting('image_host', 'none') or 'none').strip().lower()
        field_specs = {'imgbb': ('ImgBB API key:', 'imgbb_api_key', 'imgbb.com -> login -> account -> API key'), 'postimages': ('PostImages API key:', 'postimages_api_key', 'postimages.org -> login -> API tab'), 'imgbs': ('IMG.BS session cookie:', 'imgbs_cookie', 'imgbs.com -> log in -> copy the session cookie'), 'freeimage': ('FreeImage API key:', 'freeimage_api_key', 'Get one at freeimage.host/api/')}
        self._host_inputs = {}
        self._host_buttons = {}
        for host_id, label in host_options:
            btn = QRadioButton(label)
            btn.setChecked(host_id == saved_host)
            self._host_buttons[host_id] = btn
            layout.addWidget(btn)
        if saved_host not in self._host_buttons:
            self._host_buttons['none'].setChecked(True)
        layout.addSpacing(8)
        for host_id, (label_text, setting_key, placeholder) in field_specs.items():
            lbl = QLabel(label_text)
            inp = QLineEdit(self.rpc_core.get_setting(setting_key, ''))
            inp.setPlaceholderText(placeholder)
            self._host_inputs[host_id] = (lbl, inp)
            layout.addWidget(lbl)
            layout.addWidget(inp)
        no_key_note = QLabel('Catbox needs no API key, recommended for most users, choose another services if this one \nnot working.    \n')
        no_key_note.setStyleSheet('color: gray; font-style: italic;')
        layout.addWidget(no_key_note)
        no_host_note = QLabel("Choosing 'None' will limit some EwE customization features. \n \n")
        no_host_note.setStyleSheet('color: gray; font-style: italic;')
        layout.addWidget(no_host_note)

        def update_visibility(_checked=None):
            selected = next((h for h, b in self._host_buttons.items() if b.isChecked()), 'catbox')
            for host_id, (field_lbl, inp) in self._host_inputs.items():
                visible = host_id == selected
                field_lbl.setVisible(visible)
                inp.setVisible(visible)
            no_key_note.setVisible(selected == 'catbox')
            no_host_note.setVisible(selected == 'none')
        for btn in self._host_buttons.values():
            btn.toggled.connect(update_visibility)
        update_visibility()
        layout.addStretch(1)
        self._add_page(page)

    def _build_done_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.addWidget(QLabel("<b>You're all set!</b>"))
        tips = QLabel("Tips:\n•  EwE automatically hides in the system tray when minimized.\n•  Right click any game on the list for more options.\n•  Settings -> VNDB Settings / API Settings to change the profile settings and image host.\n•  This guide can be reopened anytime from Settings -> Startup Guide.")
        tips.setWordWrap(True)
        layout.addWidget(tips)
        dev_note = QLabel('<b>EwE is a work in progress and may have lots of bugs and limitations. Feel free to give any feedback or suggestions to my Discord or GitHub, or open an issue if you find a bug. </b>')
        dev_note.setWordWrap(True)
        layout.addWidget(dev_note)
        layout.addStretch(1)
        self._add_page(page)

    def _update_nav(self, index):
        self.back_btn.setEnabled(index > 0)
        last = index == self.stack.count() - 1
        self.next_btn.setText('Finish' if last else 'Next')
        if index == 1 and (not self._discord_page_shown):
            self._discord_page_shown = True
            self.check_discord()
        if last:
            self._fill_summary()

    def _go_back(self):
        idx = self.stack.currentIndex()
        if idx > 0:
            self.stack.setCurrentIndex(idx - 1)

    def _go_next(self):
        idx = self.stack.currentIndex()
        if idx == self.stack.count() - 1:
            self._finish()
            return
        if idx == 2 and (not self._validate_vndb_profile()):
            return
        self.stack.setCurrentIndex(idx + 1)

    def _finish(self):
        profile = self.vndb_profile_input.text().strip()
        if profile and (not re.fullmatch('https?://vndb\\.org/u\\d+', profile, re.IGNORECASE)):
            self.stack.setCurrentIndex(2)
            return
        self._save_collected()
        self.rpc_core.update_settings('first_run_done', True)
        self.completed = True
        self.accept()

    def reject(self):
        self._save_collected()
        super().reject()

    def _validate_vndb_profile(self):
        profile = self.vndb_profile_input.text().strip()
        if not profile:
            self.vndb_profile_hint.setText('')
            return True
        if re.fullmatch('https?://vndb\\.org/u\\d+', profile, re.IGNORECASE):
            self.vndb_profile_hint.setText('')
            return True
        self.vndb_profile_hint.setText('Use a profile link like https://vndb.org/u123456')
        return False

    def _selected_host(self):
        return next((h for h, b in self._host_buttons.items() if b.isChecked()), 'none')

    def _collect_settings(self):
        key_by_host = {'imgbb': 'imgbb_api_key', 'postimages': 'postimages_api_key', 'imgbs': 'imgbs_cookie', 'freeimage': 'freeimage_api_key'}
        settings = {'my_vndb_link': self.vndb_profile_input.text().strip(), 'vndb_api_token': self.vndb_token_input.text().strip(), 'show_my_vndb_list': True, 'image_host': self._selected_host()}
        for host_id, (_field_lbl, inp) in self._host_inputs.items():
            settings[key_by_host[host_id]] = inp.text().strip()
        return settings

    def _save_collected(self):
        for key, value in self._collect_settings().items():
            self.rpc_core.update_settings(key, value)

    @staticmethod
    def _discord_process_running():
        try:
            for p in psutil.process_iter(['name']):
                if (p.info.get('name') or '').lower() == 'discord.exe':
                    return True
        except Exception:
            pass
        return False

    def check_discord(self):
        self._check_generation += 1
        gen = self._check_generation
        self.discord_check_btn.setEnabled(False)
        self._set_discord_status('#8b949e', 'Checking Discord...')

        def work():
            if not self._discord_process_running():
                return 'not_running'
            self.rpc_core.request_discord(SHARED_CLIENT_ID)
            deadline = time.time() + 10
            while time.time() < deadline:
                if self.rpc_core.current_client_id == SHARED_CLIENT_ID:
                    return 'connected'
                time.sleep(0.25)
            return 'no_rpc'

        def on_done(result):
            if gen != self._check_generation or not self._dialog_alive():
                return
            self.discord_check_btn.setEnabled(True)
            if result == 'connected':
                self._set_discord_status('#3fb950', "Discord is running and Rich Presence connected.")
            elif result == 'no_rpc':
                self._set_discord_status('#e3b341', "Discord is running, but Rich Presence didn't connect. Check Discord Settings -> Activity Privacy, then try again.")
            else:
                self._set_discord_status('#f85149', 'Discord is not running. Start the official Discord desktop app. You can continue and check again later.')

        def on_error(message):
            if gen != self._check_generation or not self._dialog_alive():
                return
            self.discord_check_btn.setEnabled(True)
            self._set_discord_status('#f85149', f'Check failed: {message}')
        run_async_task(work, on_done, on_error)

    def _set_discord_status(self, color, text):
        self.discord_status_dot.setStyleSheet(f'color: {color};')
        self.discord_status_label.setText(text)

    def _dialog_alive(self):
        if sip is None:
            return True
        try:
            return not sip.isdeleted(self)
        except Exception:
            return True

    def _fill_summary(self):
        profile = self.vndb_profile_input.text().strip()
        host = self._selected_host()
        games = len(self.rpc_core.get_supported_games())

class PlaytimeGraphDialog(QDialog):

    def __init__(self, parent, game_name, by_date):
        super().__init__(parent)
        self._game_name = game_name
        self._by_date = by_date or {}
        self.setWindowTitle(f'Playtime Graph')
        self.resize(760, 500)
        self.setMinimumSize(520, 380)
        self.setStyleSheet('QDialog { background-color: #1e1f22; }')
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 14)
        root.setSpacing(10)
        title = QLabel(f'Your Playtime Graph of {game_name}')
        title.setStyleSheet('color: #e6e6e6; font-size: 15px; font-weight: bold;')
        root.addWidget(title)
        summary = QLabel(self._summary_text())
        summary.setStyleSheet('color: #9aa0a6; font-size: 12px;')
        summary.setWordWrap(True)
        root.addWidget(summary)
        self._canvas = FigureCanvasQTAgg(self._make_figure())
        self._canvas.setStyleSheet('background-color: #1e1f22;')
        root.addWidget(self._canvas, 1)
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        close_btn = QPushButton('Close')
        close_btn.setFixedHeight(30)
        close_btn.setStyleSheet('QPushButton { background-color: #2a2c31; color: #d4d4d4; border: 1px solid #3f4147; border-radius: 4px; padding: 0 14px; }QPushButton:hover { background-color: #34363c; }')
        close_btn.clicked.connect(self.close)
        btn_row.addWidget(close_btn)
        root.addLayout(btn_row)

    def _summary_text(self):
        data = self._by_date
        total = sum(data.values())
        active_days = len(data)
        if not active_days:
            return 'No playtime recorded yet.'
        days = list(data.keys())
        last_day = days[-1]
        last_secs = data[last_day]
        avg = int(total / active_days)
        peak_day = max(data, key=data.get)
        return f'Total: {format_playtime(total)}   ·   Active days: {active_days}   ·   Average/day: {format_playtime(avg)}   ·   Peak: {format_playtime(data[peak_day])} on {peak_day}   ·   Last: {last_day} ({format_playtime(last_secs)})'

    def _make_figure(self):
        fig = Figure(figsize=(8, 4.6), dpi=100)
        fig.patch.set_facecolor('#1e1f22')
        ax = fig.add_subplot(111)
        ax.set_facecolor('#18191c')
        days = list(self._by_date.keys())
        hours = [self._by_date[d] / 3600.0 for d in days]
        if days:
            xs = list(range(len(days)))
            ax.plot(xs, hours, marker='o', markersize=4, linewidth=2, color='#8ab4f8', zorder=3)
            ax.fill_between(xs, hours, color='#8ab4f8', alpha=0.15, zorder=2)
            ax.set_xlim(0, max(len(days) - 1, 0.5))
            ax.set_xticks(xs)
            step = max(1, len(days) // 8)
            ax.set_xticklabels([days[i] for i in range(0, len(days), step)], rotation=45, ha='right', fontsize=8, color='#9aa0a6')
            crowded = len(days) > 14
            for x, d, h in zip(xs, days, hours):
                label = format_playtime(self._by_date[d])
                if crowded:
                    ax.annotate(label, (x, h), textcoords='offset points', xytext=(0, 7), xyangle=90, ha='center', va='bottom', fontsize=6, color='#9aa0a6', zorder=4)
                else:
                    ax.annotate(label, (x, h), textcoords='offset points', xytext=(0, 8), ha='center', va='bottom', fontsize=7, color='#c8cdd4', zorder=4)
            ax.set_ylabel('hours', color='#9aa0a6', fontsize=9)
            ax.set_ylim(bottom=0, top=max(hours) * 1.35 + 0.05)
        else:
            ax.text(0.5, 0.5, 'No playtime recorded yet', ha='center', va='center', color='#9aa0a6', fontsize=12, transform=ax.transAxes)
            ax.set_xticks([])
            ax.set_yticks([])
        ax.tick_params(colors='#9aa0a6', labelsize=8)
        for spine in ax.spines.values():
            spine.set_color('#3f4147')
        ax.grid(True, color='#2c2e33', linewidth=0.6)
        ax.set_title('Hours played per day', color='#e6e6e6', fontsize=11, pad=10)
        fig.tight_layout()
        return fig


class RPCMainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle('EwE')
        self.setWindowIcon(QIcon(APP_ICON_PATH))
        self.setGeometry(100, 100, 1000, 800)
        self.setFixedSize(800, 600)
        self.active_dialogs = []
        self._vndb_prefetching = set()
        self._vndb_last_attempt = {}
        self._vndb_cycle_index = 0
        self._last_logged_message = None
        self._last_running_keys = set()
        self.rpc_core = RPCCore()
        self._detail_key = None
        self._detail_cover_url = None
        self._detail_cover_pm = None
        self._revealed_explicit = set()
        self._blur_cover_warned = set()
        self.create_widgets()
        self.create_layout()
        self.create_menu_bar()
        self.create_connections()
        self._is_shutting_down = False
        self.presence_enabled = True
        self.create_tray_icon()
        self.game_list.itemClicked.connect(self.on_game_selected)
        self.game_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.game_list.customContextMenuRequested.connect(self.on_game_right_click)
        self._scan_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='ewe-scan')
        self._scan_inflight = False
        self._scan_signals = _ScanSignals()
        self._scan_signals.scan_done.connect(self.check_processes)
        self._scan_signals.ui_job.connect(self._run_ui_job)
        self.monitor_timer = QTimer(self)
        self.monitor_timer.timeout.connect(self._on_monitor_tick)
        self.monitor_timer.start(1000)
        if not self.rpc_core.get_setting('first_run_done', False):
            QTimer.singleShot(400, self.open_startup_guide)
        QTimer.singleShot(5000, self._startup_update_check)

    def create_widgets(self):
        self.game_list = QListWidget()
        self.game_list.setIconSize(QSize(512, 512))
        self.game_list.setMaximumWidth(300)
        self.game_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.game_list.setStyleSheet('QScrollBar:vertical { background: #1e1f22; width: 8px; margin: 0; }QScrollBar::handle:vertical { background: #A8A1C9; border-radius: 4px; min-height: 30px; }QScrollBar::handle:vertical:hover, QScrollBar::handle:vertical:pressed { background: #A8A1C9; }QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { width: 0; height: 0; }QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }')
        self._game_row_labels = {}
        self._game_row_status = {}
        self._game_row_state = {}
        self._game_row_widgets = {}
        self._game_row_items = {}
        self.game_list.itemSelectionChanged.connect(self._update_game_row_colors)
        self.refresh_game_list()
        self.status_display = QTextEdit()
        self.status_display.setReadOnly(True)
        self.status_display.setStyleSheet('QTextEdit { background-color: #0c0c0c; color: #d4d4d4; border: 1px solid #3f4147; border-radius: 0px; font-family: Consolas; font-size: 12px; selection-background-color: #264f78;}')
        self.status_display.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.status_display.customContextMenuRequested.connect(self._on_status_right_click)
        self.add_game_btn = QPushButton('Add Game')

    def create_menu_bar(self):
        menubar = self.menuBar()
        menubar.setStyleSheet('QMenuBar { border-bottom: 1px solid #3f4147; }')
        settings_menu = menubar.addMenu('Settings')
        settings_menu.addAction('VNDB Settings', self.open_vndb_settings)
        settings_menu.addAction('API Settings', self.open_api_settings)
        settings_menu.addAction('Check for Updates', self.open_update_checker)
        settings_menu.addAction('Startup Guide', self.open_startup_guide)

    def create_layout(self):
        main_widget = QWidget()
        main_layout = QHBoxLayout(main_widget)
        left_panel = QVBoxLayout()
        left_panel.addWidget(QLabel('Visual Novels List:'))
        left_panel.addWidget(self.game_list)
        button_layout = QHBoxLayout()
        self.add_game_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.add_game_btn.setMaximumWidth(300)
        button_layout.addWidget(self.add_game_btn)
        left_panel.addLayout(button_layout)
        right_panel = QVBoxLayout()
        right_panel.addWidget(QLabel('Status:'))
        self.right_splitter = QSplitter(Qt.Orientation.Vertical)
        self.right_splitter.setChildrenCollapsible(False)
        self.right_splitter.setCollapsible(1, True)
        self.right_splitter.setStyleSheet('QSplitter::handle { background-color: #3f4147; }QSplitter::handle:horizontal { height: 4px; }QSplitter::handle:horizontal:hover { background-color: #5c606a; }')
        self.status_display.setMinimumHeight(50)
        self.vn_detail_card = self.create_detail_panel()
        self.vn_detail_card.setMinimumHeight(150)
        self.right_splitter.addWidget(self.status_display)
        self.right_splitter.addWidget(self.vn_detail_card)
        self.right_splitter.setStretchFactor(0, 1)
        self.right_splitter.setStretchFactor(1, 1)
        self.right_splitter.setSizes([300, 300])
        right_panel.addWidget(self.right_splitter, 1)
        main_layout.addLayout(left_panel, 3)
        main_layout.addLayout(right_panel, 5)
        self.setCentralWidget(main_widget)
        self.setMinimumSize(880, 700)
        self._sync_detail_panel_visibility()

    def create_connections(self):
        self.add_game_btn.clicked.connect(self.open_vndb_search_dialog)

    def create_detail_panel(self):
        card = QWidget()
        card.setObjectName('vnDetailCard')
        card.setStyleSheet('QWidget#vnDetailCard {  background-color: #232529;  border: 1px solid #3f4147;  border-radius: 6px;}')
        outer = QVBoxLayout(card)
        outer.setContentsMargins(8, 8, 8, 8)
        outer.setSpacing(6)
        top = QHBoxLayout()
        top.setSpacing(10)
        self.detail_cover = QLabel()
        self.detail_cover.setFixedSize(72, 100)
        self.detail_cover.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.detail_cover.setCursor(Qt.CursorShape.PointingHandCursor)
        self.detail_cover.setStyleSheet('background-color: #1e1f22; border: 1px solid #3f4147; border-radius: 4px; color: #5c5e66;')
        self.detail_cover.setText('no cover')
        self.detail_cover.mousePressEvent = self._on_detail_cover_click
        top.addWidget(self.detail_cover, 0, Qt.AlignmentFlag.AlignTop)
        info = QVBoxLayout()
        info.setSpacing(4)
        head = QHBoxLayout()
        head.setSpacing(6)
        self.detail_title = QLabel('Select a visual novel')
        self.detail_title.setWordWrap(True)
        self.detail_title.setStyleSheet('font-size: 13px; font-weight: bold;')
        head.addWidget(self.detail_title, 1)
        self.detail_refresh_btn = QPushButton('↻')
        self.detail_open_btn = QPushButton('↗')
        for btn in (self.detail_refresh_btn, self.detail_open_btn):
            btn.setFixedSize(24, 24)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet('font-size: 14px; padding: 0px; background-color: #2b2d31; color: #dbdee1; border: 1px solid #3f4147; border-radius: 4px;')
        self.detail_refresh_btn.setToolTip('Refresh data from VNDB')
        self.detail_open_btn.setToolTip('Open VNDB page')
        self.detail_open_btn.setEnabled(False)
        head.addWidget(self.detail_refresh_btn)
        head.addWidget(self.detail_open_btn)
        info.addLayout(head)
        self.detail_rows = {}
        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(1)
        for i, name in enumerate(['Titles', 'Aliases', 'Play time', 'Developer', 'Links', 'Release date']):
            lbl = QLabel(name)
            lbl.setStyleSheet('color: #8b8d98; font-size: 11px;')
            val = QLabel('N/A')
            val.setWordWrap(True)
            val.setStyleSheet('font-size: 11px;')
            val.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
            self.detail_rows[name] = val
            grid.addWidget(lbl, i, 0)
            grid.addWidget(val, i, 1)
        grid.setColumnStretch(1, 1)
        info.addLayout(grid)
        info.addStretch(1)
        top.addLayout(info, 1)
        outer.addLayout(top)
        self.detail_scroll = QScrollArea()
        self.detail_scroll.setObjectName('vnDetailScroll')
        self.detail_scroll.setWidgetResizable(True)
        self.detail_scroll.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Ignored)
        self.detail_scroll.setStyleSheet('QScrollArea { border: none; background: transparent; }QScrollBar:vertical { width: 6px; margin: 0; background: transparent; }QScrollBar::handle:vertical { background: #4a4d55;  border-radius: 3px; min-height: 24px; }QScrollBar::handle:vertical:hover { background: #5c606a; }QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }')
        self.detail_scroll_content = QWidget()
        self.detail_scroll_content.setStyleSheet('background: transparent;')
        scroll_layout = QVBoxLayout(self.detail_scroll_content)
        scroll_layout.setContentsMargins(2, 2, 8, 2)
        scroll_layout.setSpacing(8)
        self.detail_summary = QLabel('')
        self.detail_summary.setWordWrap(True)
        self.detail_summary.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        self.detail_summary.setStyleSheet('color: #b8bcc4; font-size: 11px;')
        self.detail_summary.linkActivated.connect(self._on_summary_link)
        self._desc_segments = []
        self._revealed_spoilers = set()
        scroll_layout.addWidget(self.detail_summary)
        self.detail_gallery_status = QLabel('')
        self.detail_gallery_status.setStyleSheet('color: #5c5e66; font-size: 10px;')
        scroll_layout.addWidget(self.detail_gallery_status)
        self.detail_gallery_strip = QScrollArea()
        self.detail_gallery_strip.setWidgetResizable(True)
        self.detail_gallery_strip.setFixedHeight(64)
        self.detail_gallery_strip.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.detail_gallery_strip.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.detail_gallery_strip.setStyleSheet('QScrollArea { border: none; background: transparent; }QScrollBar:horizontal { height: 6px; margin: 0;  background: transparent; }QScrollBar::handle:horizontal { background: #4a4d55;  border-radius: 3px; min-width: 24px; }QScrollBar::handle:horizontal:hover { background: #5c606a; }QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }')
        self.detail_gallery_inner = QWidget()
        self.detail_gallery_inner.setStyleSheet('background: transparent;')
        self.detail_gallery_layout = QHBoxLayout(self.detail_gallery_inner)
        self.detail_gallery_layout.setContentsMargins(2, 4, 2, 4)
        self.detail_gallery_layout.setSpacing(6)
        self.detail_gallery_layout.addStretch(1)
        self.detail_gallery_strip.setWidget(self.detail_gallery_inner)
        scroll_layout.addWidget(self.detail_gallery_strip)
        self.detail_screenshots_status = QLabel('')
        self.detail_screenshots_status.setStyleSheet('color: #5c5e66; font-size: 10px;')
        scroll_layout.addWidget(self.detail_screenshots_status)
        self.detail_screenshots_strip = QScrollArea()
        self.detail_screenshots_strip.setWidgetResizable(True)
        self.detail_screenshots_strip.setFixedHeight(64)
        self.detail_screenshots_strip.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.detail_screenshots_strip.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.detail_screenshots_strip.setStyleSheet('QScrollArea { border: none; background: transparent; }QScrollBar:horizontal { height: 6px; margin: 0;  background: transparent; }QScrollBar::handle:horizontal { background: #4a4d55;  border-radius: 3px; min-width: 24px; }QScrollBar::handle:horizontal:hover { background: #5c606a; }QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }')
        self.detail_screenshots_inner = QWidget()
        self.detail_screenshots_inner.setStyleSheet('background: transparent;')
        self.detail_screenshots_layout = QHBoxLayout(self.detail_screenshots_inner)
        self.detail_screenshots_layout.setContentsMargins(2, 4, 2, 4)
        self.detail_screenshots_layout.setSpacing(6)
        self.detail_screenshots_layout.addStretch(1)
        self.detail_screenshots_strip.setWidget(self.detail_screenshots_inner)
        scroll_layout.addWidget(self.detail_screenshots_strip)
        self.detail_scroll.setWidget(self.detail_scroll_content)
        outer.addWidget(self.detail_scroll, 1)
        self.detail_playtime = _ClickableLabel('')
        self.detail_playtime.setWordWrap(True)
        self.detail_playtime.setStyleSheet('color: #8ab4f8; font-size: 11px;')
        self.detail_playtime.setCursor(Qt.CursorShape.PointingHandCursor)
        self.detail_playtime.clicked.connect(self._on_detail_playtime_clicked)
        self.detail_playtime.hoverChanged.connect(self._on_playtime_hover)
        outer.addWidget(self.detail_playtime)
        self._detail_gallery = []
        self._detail_screenshots = []
        self.detail_refresh_btn.clicked.connect(self._on_detail_refresh)
        self.detail_open_btn.clicked.connect(self._on_detail_open_vndb)
        return card

    def _reset_detail_panel(self):
        self._detail_key = None
        self.detail_title.setText('Select a visual novel')
        self.detail_cover.setPixmap(QPixmap())
        self.detail_cover.setText('no cover')
        self.detail_playtime.setText('')
        self.detail_open_btn.setEnabled(False)
        self.detail_refresh_btn.setEnabled(False)
        for name, val in self.detail_rows.items():
            val.setText('N/A')
            val.setOpenExternalLinks(False)
        self.detail_summary.setText('')
        self._desc_segments = []
        self._revealed_spoilers = set()
        self._revealed_explicit = set()
        self._detail_cover_pm = None
        self._clear_gallery_layout()
        self.detail_gallery_status.setText('')
        self._clear_screenshots_layout()
        self.detail_screenshots_status.setText('')

    def _show_game_details(self, game_key):
        self._reset_detail_panel()
        self._detail_key = game_key
        cfg = self.rpc_core.config.get(game_key) or {}
        vndb_url = (cfg.get('vndb_url') or '').strip()
        self.detail_title.setText(self.get_game_display_name(game_key))
        self.detail_open_btn.setEnabled(bool(vndb_url))
        self.detail_refresh_btn.setEnabled(bool(vndb_url))
        self._render_detail_rows()
        info_now = self.rpc_core.library_cache.get(vndb_url) if vndb_url else None
        self._show_detail_cover(self._resolve_detail_cover_url(cfg, info_now or {}))
        self._update_detail_playtime(game_key)
        if not vndb_url:
            self.detail_summary.setText('No description available.')
            self.detail_gallery_status.setText('No VNDB link for this game, so no gallery is available.')
            self.detail_screenshots_status.setText('')
            return
        info = self.rpc_core.library_cache.get(vndb_url)
        age = self.rpc_core.library_cache_age(vndb_url)
        fresh = info is not None and age is not None and (age < self.rpc_core.LIBRARY_CACHE_TTL_SECONDS)
        schema_ok = info is not None and (info.get('schema') == 2) and all('exp' in sc for sc in (info.get('screenshots') or [])) and all('exp' in g for g in (info.get('gallery') or []))
        if fresh and schema_ok and info.get('description') and info.get('playtime_vndb') and (info.get('screenshots') is not None) and (info.get('description_segments') is not None) and (info.get('links') is not None) and (info.get('cover_explicit') is not None) and (info.get('cover_url_main') is not None):
            self._render_description(info)
            self._render_detail_rows(info)
            self._render_detail_gallery(info.get('gallery') or [])
            self._render_detail_screenshots(info.get('screenshots') or [])
            self._update_detail_gallery_status(info)
        else:
            self.detail_summary.setText('Loading description...')
            self._start_library_fetch(vndb_url, force=True)

    def _render_description(self, info):
        info = info if isinstance(info, dict) else {}
        self._desc_segments = info.get('description_segments') or []
        self._revealed_spoilers = set()
        if self._desc_segments:
            self.detail_summary.setText(self._build_description_html())
            self._update_spoiler_tooltip()
        else:
            self.detail_summary.setText(info.get('description') or 'No description available.')
            self.detail_summary.setToolTip('')

    def _update_spoiler_tooltip(self):
        hidden = any((seg.get('s') and i not in self._revealed_spoilers for i, seg in enumerate(self._desc_segments)))
        self.detail_summary.setToolTip('Black boxes hide spoilers. Click one to reveal it.' if hidden else '')

    def _build_description_html(self):
        parts = []
        for i, seg in enumerate(self._desc_segments):
            t = (seg.get('t') or '').strip()
            if not t:
                continue
            esc = html.escape(t, quote=False)
            if seg.get('s') and i not in self._revealed_spoilers:
                parts.append('<a href="spoiler:%d" style="color:#0c0d0f; background-color:#0c0d0f; text-decoration:none;">%s</a>' % (i, esc))
            else:
                parts.append(esc)
        return ' '.join(parts)

    def _on_summary_link(self, url):
        if not url.startswith('spoiler:'):
            return
        try:
            idx = int(url.split(':', 1)[1])
        except ValueError:
            return
        if idx in self._revealed_spoilers:
            return
        self._revealed_spoilers.add(idx)
        self.detail_summary.setText(self._build_description_html())
        self._update_spoiler_tooltip()

    def _render_detail_rows(self, info=None):
        game_key = self._detail_key
        cfg = self.rpc_core.config.get(game_key) or {}
        vc = cfg.get('vndb_cache') or {}
        vndb_url = (cfg.get('vndb_url') or '').strip()
        info = info if isinstance(info, dict) else self.rpc_core.library_cache.get(vndb_url) or {}

        def set_row(name, text):
            self.detail_rows[name].setText(text or 'N/A')
        set_row('Titles', info.get('title') or self.get_game_display_name(game_key))
        set_row('Aliases', info.get('aliases'))
        set_row('Play time', info.get('playtime_vndb'))
        set_row('Developer', info.get('developer') or vc.get('developer'))
        links = info.get('links') or []
        if links:
            self.detail_rows['Links'].setOpenExternalLinks(True)
            self.detail_rows['Links'].setText(', '.join((f'''<a href="{l['url']}" style="color:#8ab4f8;">{html.escape(l['name'], quote=False)}</a>''' for l in links)))
        elif vndb_url:
            self.detail_rows['Links'].setOpenExternalLinks(True)
            self.detail_rows['Links'].setText(f'''<a href="{vndb_url}" style="color:#8ab4f8;">vndb.org/{vndb_url.split('/')[-1]}</a>''')
        else:
            set_row('Links', None)
        set_row('Release date', info.get('released') or vc.get('released'))

    def _resolve_detail_cover_url(self, cfg, info):
        cover = (cfg.get('cover_url') or '').strip()
        if not self.rpc_core.is_usable_image_ref(cover):
            cover = (cfg.get('large_image') or '').strip()
        if not self.rpc_core.is_usable_image_ref(cover):
            cover = ''
        if cover:
            return cover
        main = ((info or {}).get('cover_url_main') or '').strip()
        if main:
            cfg['cover_url'] = main
            try:
                self.save_current_config()
            except Exception:
                pass
        return main

    def _show_detail_cover(self, cover_url):
        self._detail_cover_url = cover_url
        self._detail_cover_pm = None
        if not cover_url:
            self.detail_cover.setPixmap(QPixmap())
            self.detail_cover.setText('no cover')
            self.detail_cover.setToolTip('')
            return
        cached = self.rpc_core.load_cached_image(cover_url)
        if cached:
            self._apply_detail_cover(QPixmap(cached))
            return
        self.detail_cover.setPixmap(QPixmap())
        self.detail_cover.setText('loading...')
        self.detail_cover.setToolTip('')

        def on_done(path):
            if getattr(self, '_detail_cover_url', None) != cover_url:
                return
            pm = QPixmap(path) if path else QPixmap()
            if not pm.isNull():
                self._apply_detail_cover(pm)
            else:
                self.detail_cover.setText('no cover')

        def on_error(_message):
            if getattr(self, '_detail_cover_url', None) != cover_url:
                return
            self.detail_cover.setText('no cover')
        run_async_task(lambda: self.rpc_core.download_image(cover_url), on_done, on_error)

    def _apply_detail_cover(self, pixmap):
        scaled = pixmap.scaled(70, 98, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self._detail_cover_pm = scaled
        self._redraw_detail_cover()

    def _detail_cover_is_explicit(self):
        cfg = self.rpc_core.config.get(self._detail_key) or {}
        vndb_url = (cfg.get('vndb_url') or '').strip()
        if vndb_url:
            info = self.rpc_core.library_cache.get(vndb_url) or {}
            if info.get('cover_explicit') is not None:
                return bool(info.get('cover_explicit'))
        return self.rpc_core.is_image_explicit(self._detail_cover_url or '')

    def _redraw_detail_cover(self):
        url = self._detail_cover_url
        pm = self._detail_cover_pm
        if not url or pm is None:
            return
        if self.rpc_core.get_setting('pixel_explicit', True) and self._detail_cover_is_explicit() and (url not in self._revealed_explicit):
            self.detail_cover.setPixmap(self._blur_pixmap(pm, 70, 98))
            self.detail_cover.setToolTip('Explicit cover')
        else:
            self.detail_cover.setPixmap(pm)
            self.detail_cover.setToolTip(url)

    def _reveal_explicit(self, url):
        self._revealed_explicit.add(url)
        if self._detail_cover_url == url:
            self._redraw_detail_cover()
        for label, entry in list(self._detail_gallery) + list(self._detail_screenshots):
            if (entry.get('full') or '') == url:
                self._redraw_thumb(label, entry)

    def _open_image_viewer(self, url):
        if not url:
            return
        viewer = ImageViewerDialog(self, self.rpc_core, url)
        viewer.show()

    def _on_detail_cover_click(self, event):
        url = self._detail_cover_url
        pm = self._detail_cover_pm
        if not url or pm is None:
            return
        if self.rpc_core.get_setting('pixel_explicit', True) and self._detail_cover_is_explicit() and (url not in self._revealed_explicit):
            self._reveal_explicit(url)
            return
        self._open_image_viewer(url)

    @staticmethod
    def _blur_pixmap(pm, tw, th):
        scale = 10.0 / max(tw, th)
        sw = max(2, int(tw * scale))
        sh = max(2, int(th * scale))
        small = pm.scaled(sw, sh, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
        return small.scaled(tw, th, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.FastTransformation)

    def _thumb_explicit(self, entry):
        full = entry.get('full') or ''
        if not full or full in self._revealed_explicit:
            return False
        if not self.rpc_core.get_setting('pixel_explicit', True):
            return False
        if 'exp' in entry:
            return bool(entry.get('exp'))
        cfg = self.rpc_core.config.get(self._detail_key) or {}
        vndb_url = (cfg.get('vndb_url') or '').strip()
        info = self.rpc_core.library_cache.get(vndb_url) or {}
        return bool(info.get('cover_explicit'))

    def _on_thumb_click(self, label, entry):
        full = entry.get('full', '')
        if self._thumb_explicit(entry):
            self._reveal_explicit(full)
            return
        self._open_image_viewer(full)

    def _apply_thumb(self, label, entry, pm):
        if pm.isNull():
            label.setText('...')
            return
        scaled = pm.scaled(118, 66, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        label._sharp_pm = scaled
        self._redraw_thumb(label, entry)

    def _redraw_thumb(self, label, entry):
        pm = getattr(label, '_sharp_pm', None)
        if pm is None:
            return
        if self._thumb_explicit(entry):
            label.setPixmap(self._blur_pixmap(pm, 118, 66))
            label.setToolTip((entry.get('full') or '') + '\nExplicit. Click to reveal')
        else:
            label.setPixmap(pm)
            label.setToolTip(entry.get('full') or '')

    def _clear_gallery_layout(self):
        while self.detail_gallery_layout.count() > 0:
            item = self.detail_gallery_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._detail_gallery = []
        self.detail_gallery_layout.addStretch(1)

    def _render_detail_gallery(self, gallery):
        self._clear_gallery_layout()
        if not gallery:
            self.detail_gallery_status.setText('No gallery covers found on VNDB.')
            return
        for entry in gallery:
            label = QLabel()
            label.setFixedSize(100, 56)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setCursor(Qt.CursorShape.PointingHandCursor)
            label.setStyleSheet('background-color: #1e1f22; border: 1px solid #3f4147; border-radius: 3px; color: #5c5e66;')
            full_url = entry.get('full', '')
            label.setToolTip(full_url)
            label.mousePressEvent = lambda e, l=label, en=entry: self._on_thumb_click(l, en)
            self.detail_gallery_layout.insertWidget(self.detail_gallery_layout.count() - 1, label)
            self._detail_gallery.append((label, entry))
        self._download_gallery_thumbs()

    def _download_gallery_thumbs(self):
        pairs = list(self._detail_gallery)
        if not pairs:
            return
        selection = self._detail_key

        def task():
            urls = [entry.get('thumb', '') for _label, entry in pairs]
            with ThreadPoolExecutor(max_workers=4) as pool:
                return list(pool.map(self.rpc_core.download_image, urls))

        def on_done(paths):
            if getattr(self, '_detail_key', None) != selection:
                return
            for (label, entry), path in zip(pairs, paths):
                pm = QPixmap(path) if path else QPixmap()
                if pm.isNull():
                    label.setText('...')
                    continue
                self._apply_thumb(label, entry, pm)

        def on_error(message):
            if getattr(self, '_detail_key', None) != selection:
                return
            self.detail_gallery_status.setText(f'Gallery download failed: {message}')
        run_async_task(task, on_done, on_error)

    def _clear_screenshots_layout(self):
        while self.detail_screenshots_layout.count() > 0:
            item = self.detail_screenshots_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._detail_screenshots = []
        self.detail_screenshots_layout.addStretch(1)

    def _render_detail_screenshots(self, screenshots):
        self._clear_screenshots_layout()
        if not screenshots:
            self.detail_screenshots_status.setText('No screenshots found on VNDB.')
            return
        for entry in screenshots:
            label = QLabel()
            label.setFixedSize(100, 56)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setCursor(Qt.CursorShape.PointingHandCursor)
            label.setStyleSheet('background-color: #1e1f22; border: 1px solid #3f4147; border-radius: 3px; color: #5c5e66;')
            full_url = entry.get('full', '')
            label.setToolTip(full_url)
            label.mousePressEvent = lambda e, l=label, en=entry: self._on_thumb_click(l, en)
            self.detail_screenshots_layout.insertWidget(self.detail_screenshots_layout.count() - 1, label)
            self._detail_screenshots.append((label, entry))
        self._download_screenshot_thumbs()

    def _download_screenshot_thumbs(self):
        pairs = list(self._detail_screenshots)
        if not pairs:
            return
        selection = self._detail_key

        def task():
            urls = [entry.get('thumb', '') for _label, entry in pairs]
            with ThreadPoolExecutor(max_workers=4) as pool:
                return list(pool.map(self.rpc_core.download_image, urls))

        def on_done(paths):
            if getattr(self, '_detail_key', None) != selection:
                return
            for (label, entry), path in zip(pairs, paths):
                pm = QPixmap(path) if path else QPixmap()
                if pm.isNull():
                    label.setText('...')
                    continue
                self._apply_thumb(label, entry, pm)

        def on_error(message):
            if getattr(self, '_detail_key', None) != selection:
                return
            self.detail_screenshots_status.setText(f'Screenshots download failed: {message}')
        run_async_task(task, on_done, on_error)

    def _update_detail_gallery_status(self, info):
        gallery = info.get('gallery') or []
        screenshots = info.get('screenshots') or []
        age = self._age_str(self.rpc_core.library_cache_age((self.rpc_core.config.get(self._detail_key) or {}).get('vndb_url', '').strip()))
        if gallery:
            self.detail_gallery_status.setText(f'{len(gallery)} covers  ·  cached {age}')
        if screenshots:
            self.detail_screenshots_status.setText(f'{len(screenshots)} screenshots  ·  cached {age}')

    @staticmethod
    def _age_str(seconds):
        if seconds is None:
            return 'recently'
        if seconds < 90:
            return 'just now'
        if seconds < 5400:
            return f'{int(seconds // 60)}m ago'
        if seconds < 172800:
            return f'{int(seconds // 3600)}h ago'
        return f'{int(seconds // 86400)}d ago'

    def _start_library_fetch(self, vndb_url, force):
        self.detail_gallery_status.setText('Loading...')
        selection = self._detail_key

        def on_done(info):
            if getattr(self, '_detail_key', None) != selection:
                return
            if not info:
                self.detail_gallery_status.setText('VNDB returned no data.')
                return
            self._render_description(info)
            self._render_detail_rows(info)
            self._render_detail_gallery(info.get('gallery') or [])
            self._render_detail_screenshots(info.get('screenshots') or [])
            self._update_detail_gallery_status(info)
            if self._detail_cover_pm is not None:
                self._redraw_detail_cover()
            else:
                cover_cfg = self.rpc_core.config.get(selection) or {}
                cover = self._resolve_detail_cover_url(cover_cfg, info)
                if cover and getattr(self, '_detail_cover_url', None) != cover:
                    self._show_detail_cover(cover)

        def on_error(message):
            if getattr(self, '_detail_key', None) != selection:
                return
            self.detail_gallery_status.setText(f'VNDB fetch failed: {message}')
        run_async_task(lambda: self.rpc_core.fetch_vn_library_info(vndb_url, force=force), on_done, on_error)

    def _on_detail_refresh(self):
        game_key = self._detail_key
        cfg = self.rpc_core.config.get(game_key) or {}
        vndb_url = (cfg.get('vndb_url') or '').strip()
        if not vndb_url:
            return
        self.rpc_core.vndb_cache.pop(vndb_url, None)
        cfg.pop('vndb_cache', None)
        self.save_current_config()
        self._start_library_fetch(vndb_url, force=True)

    def _on_detail_open_vndb(self):
        cfg = self.rpc_core.config.get(self._detail_key) or {}
        vndb_url = (cfg.get('vndb_url') or '').strip()
        if vndb_url:
            webbrowser.open(vndb_url)

    def _update_detail_playtime(self, game_key):
        cfg = self.rpc_core.config.get(game_key) or {}
        total = self.rpc_core.get_playtime_seconds(game_key)
        live = 0
        started = self.rpc_core.start_times.get(game_key)
        if started:
            live = max(0, int(time.time()) - started)
        text = f'Your Playtime: {format_playtime(total)}'
        if self.detail_playtime.text() != text:
            self.detail_playtime.setText(text)
        tooltip_parts = []
        if live > 0:
            tooltip_parts.append(f'This Session: {format_playtime(live)}')
        last = cfg.get('last_played')
        if last:
            tooltip_parts.append(f'Last played: {last}')
        tooltip = '\n'.join(tooltip_parts)
        if self.detail_playtime.toolTip() != tooltip:
            self.detail_playtime.setToolTip(tooltip)

    def _on_playtime_hover(self, hovering):
        if hovering:
            self.detail_playtime.setStyleSheet('color: #a8c7fa; font-size: 11px; text-decoration: underline;')
        else:
            self.detail_playtime.setStyleSheet('color: #8ab4f8; font-size: 11px;')

    def _on_detail_playtime_clicked(self):
        key = self._detail_key
        if not key:
            return
        name = self.get_game_display_name(key)
        by_date = self.rpc_core.get_playtime_by_date(key)
        dlg = PlaytimeGraphDialog(self, name, by_date)

        def _cleanup(_result, _d=dlg):
            if _d in self.active_dialogs:
                self.active_dialogs.remove(_d)
        dlg.finished.connect(_cleanup)
        self.active_dialogs.append(dlg)
        dlg.show()

    def create_tray_icon(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            self.tray_icon = None
            return
        tray_menu = QMenu(self)
        tray_menu.setStyleSheet('QMenu { font-size: 12px; }\nQMenu::item { padding: 3px 20px; }\nQMenu::icon { left: 12px; width: 14px; height: 14px; }\nQMenu::separator { height: 1px; background-color: #3f4147; margin: 2px 8px; }\nQCheckBox { padding: 1px; spacing: 6px; }\nQCheckBox::indicator { width: 14px; height: 14px; }\n')
        tray_menu.addAction(QIcon(APP_ICON_PATH), 'EwE', self.show_main_window)
        tray_menu.addSeparator()
        self.tray_status_action = tray_menu.addAction('Waiting for visual novel to run')
        self.tray_status_action.setEnabled(False)
        presence_row = QWidget()
        presence_row.setStyleSheet('background: transparent;')
        presence_layout = QHBoxLayout(presence_row)
        presence_layout.setContentsMargins(10, 1, 4, 1)
        presence_layout.setSpacing(0)
        self.tray_presence_checkbox = QCheckBox('Presence is enabled')
        presence_layout.addWidget(self.tray_presence_checkbox)
        presence_action = QWidgetAction(tray_menu)
        presence_action.setDefaultWidget(presence_row)
        tray_menu.addAction(presence_action)
        self.tray_presence_checkbox.setChecked(True)
        self.tray_presence_checkbox.toggled.connect(self._on_presence_toggled)
        tray_menu.addSeparator()
        help_menu = tray_menu.addMenu('Help')
        report_action = help_menu.addAction(make_report_icon(), 'Report any problem to GitHub')
        report_action.triggered.connect(lambda: webbrowser.open('https://github.com/VaternID/EwE/issues/new'))
        star_action = help_menu.addAction(make_star_icon(), 'Star the project')
        star_action.triggered.connect(lambda: webbrowser.open('https://github.com/VaternID/EwE'))
        tray_menu.addSeparator()
        tray_menu.addAction('Exit', self.exit_application)
        self.tray_icon = QSystemTrayIcon(QIcon(APP_ICON_PATH), self)
        self.tray_icon.setToolTip('EwE')
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_activated)
        self.tray_icon.show()

    def on_tray_activated(self, reason):
        if reason in (QSystemTrayIcon.ActivationReason.DoubleClick, QSystemTrayIcon.ActivationReason.Trigger):
            self.show_main_window()

    def _on_presence_toggled(self, checked):
        self.presence_enabled = checked
        self.tray_presence_checkbox.setText('Presence is enabled' if checked else 'Presence is disabled')
        timestamp = f"""<span style="color:#5c6370;">[{time.strftime('%H:%M:%S')}]</span> """
        if checked:
            self.status_display.append(timestamp + '<span style="color:#3fb950;">Presence resumed.</span>')
        else:
            self.rpc_core.clear_rpc()
            self.status_display.append(timestamp + '<span style="color:#e3b341;">Presence paused. Rich Presence cleared.</span>')

    def _update_tray_status(self, running):
        action = getattr(self, 'tray_status_action', None)
        if action is None:
            return
        if running:
            target = min(running, key=lambda k: self.rpc_core.start_times.get(k, 0) or 0)
            text = f'{self.get_game_display_name(target)} currently running'
        else:
            text = 'Waiting for visual novel to run'
        if action.text() != text:
            action.setText(text)

    def show_main_window(self):
        screen = QApplication.primaryScreen()
        if screen is not None:
            geo = screen.availableGeometry()
            x = geo.x() + max(0, (geo.width() - self.width()) // 2)
            y = geo.y() + max(0, (geo.height() - self.height()) // 2)
            self.move(x, y)
        self.showNormal()
        self.raise_()
        self.activateWindow()
        enable_dark_title_bar(self)

    def exit_application(self):
        self._is_shutting_down = True
        try:
            self._scan_executor.shutdown(wait=False, cancel_futures=True)
        except Exception:
            pass
        try:
            self.rpc_core.flush_playtime()
        except Exception:
            pass
        try:
            self.rpc_core.shutdown_discord()
        except Exception:
            pass
        if getattr(self, 'tray_icon', None):
            self.tray_icon.hide()
        QApplication.instance().quit()

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(0, self._sync_detail_panel_visibility)

    def closeEvent(self, event):
        if not getattr(self, '_is_shutting_down', False):
            self.exit_application()
        event.accept()

    def changeEvent(self, event):
        if event.type() == QEvent.Type.WindowStateChange:
            tray = getattr(self, 'tray_icon', None)
            if self.isMinimized() and tray is not None:
                self.hide()
                tray.showMessage('EwE', 'Minimized to the system tray.', QIcon(APP_ICON_PATH))
                return
        super().changeEvent(event)

    def clear_log(self):
        self.status_display.clear()
        self._last_logged_message = None

    def _on_status_right_click(self, pos):
        menu = QMenu(self)
        menu.addAction('Clear Log', self.clear_log)
        menu.exec(self.status_display.mapToGlobal(pos))

    def update_status(self, message):
        if message == self._last_logged_message:
            return
        self._last_logged_message = message
        is_rpc_status = _RPC_UPDATED_RE.match(message) is not None
        if not is_rpc_status and (not any((k in message.lower() for k in _STATUS_ERROR_KEYWORDS))):
            return
        timestamp = f"""<span style="color:#5c6370;">[{time.strftime('%H:%M:%S')}]</span> """
        rpc_match = _RPC_UPDATED_RE.match(message)
        if rpc_match:
            g = rpc_match.groupdict()
            self.status_display.append(timestamp + f"""<span style="color:#e6edf3; font-weight:bold;">{html.escape(g['exe'])}</span> """ + '<span style="color:#3fb950;">is running. RPC updated.</span> ' + '<span style="color:#5c6370;">(name: </span>' + f"""<span style="color:#56d4dd;">{html.escape(g['name'])}</span>""" + '<span style="color:#5c6370;"> | details: </span>' + f"""<span style="color:#f778ba;">{html.escape(g['details'])}</span>""" + '<span style="color:#5c6370;"> | state: </span>' + f"""<span style="color:#e3b341;">{html.escape(g['state'])}</span>""" + '<span style="color:#5c6370;"> | </span>' + f"""<span style="color:#ffa657;">{html.escape(g['buttons'])}</span>""" + '<span style="color:#5c6370;">)</span>')
            return
        color = _status_color(message)
        self.status_display.append(timestamp + f'<span style="color:{color};">{html.escape(message)}</span>')
        max_lines = 300
        doc = self.status_display.document()
        while doc.blockCount() > max_lines:
            cursor = self.status_display.textCursor()
            cursor.movePosition(cursor.MoveOperation.Start)
            cursor.select(cursor.SelectionType.BlockUnderCursor)
            cursor.removeSelectedText()
            cursor.deleteChar()
        self.status_display.verticalScrollBar().setValue(self.status_display.verticalScrollBar().maximum())

    def _make_game_row_widget(self, game_key, display_name, icon):
        widget = _GameRowWidget(game_key)
        widget.setStyleSheet('background: transparent;')
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(6)
        status_label = QLabel('●')
        status_label.setFixedWidth(10)
        status_label.setStyleSheet('color: #5c5e66; font-size: 10px;')
        layout.addWidget(status_label)
        icon_label = QLabel()
        icon_label.setFixedSize(32, 32)
        if not icon.isNull():
            icon_label.setPixmap(icon.pixmap(32, 32))
        layout.addWidget(icon_label)
        text_label = QLabel(display_name)
        text_label.setWordWrap(True)
        text_label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        text_label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(text_label, 1)
        return (widget, text_label, status_label)

    def _update_game_row_colors(self):
        selected_keys = {item.data(Qt.ItemDataRole.UserRole) for item in self.game_list.selectedItems()}
        for game_key, label in self._game_row_labels.items():
            color = '#ffffff' if game_key in selected_keys else '#dbdee1'
            label.setStyleSheet(f'color: {color};')

    def refresh_game_list(self, refresh_details=True):
        keep_selected = self._detail_key
        self.game_list.blockSignals(True)
        self.game_list.clear()
        self._game_row_labels.clear()
        self._game_row_status.clear()
        self._game_row_state.clear()
        self._game_row_items.clear()
        self._game_row_widgets.clear()
        try:
            icon_snapshot = list(psutil.process_iter(['pid', 'name']))
        except Exception:
            icon_snapshot = None
        metrics = QFontMetrics(self.font())
        row_height = metrics.height() + 25
        game_keys = self.rpc_core.get_supported_games()
        for index, game_key in enumerate(game_keys):
            try:
                display_name = self.get_game_display_name(game_key)
                item = QListWidgetItem('')
                item.setData(Qt.ItemDataRole.UserRole, game_key)
                try:
                    icon = self.get_game_list_icon(game_key, icon_snapshot)
                except Exception:
                    icon = QIcon()
                widget, text_label, status_label = self._make_game_row_widget(game_key, display_name, icon)
            except Exception as e:
                print(f'Skipping list row for {game_key}: {e}')
                continue
            self.game_list.addItem(item)
            self.game_list.setItemWidget(item, widget)
            item.setSizeHint(QSize(1, row_height))
            self._game_row_labels[game_key] = text_label
            self._game_row_status[game_key] = status_label
            self._game_row_items[game_key] = item
            self._game_row_widgets[game_key] = widget
            widget.rowClicked.connect(lambda key=game_key: self._on_game_row_clicked(key))
            if index < len(game_keys) - 1:
                separator_item = QListWidgetItem()
                separator_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
                separator = QWidget()
                separator.setFixedHeight(1)
                separator.setStyleSheet('background-color: #3f4147;')
                self.game_list.addItem(separator_item)
                self.game_list.setItemWidget(separator_item, separator)
                separator_item.setSizeHint(QSize(1, 9))
        self.game_list.blockSignals(False)
        if keep_selected is not None and keep_selected in self._game_row_items:
            self.game_list.blockSignals(True)
            self.game_list.clearSelection()
            self._game_row_items[keep_selected].setSelected(True)
            self.game_list.blockSignals(False)
        self._update_game_row_colors()
        if not hasattr(self, 'vn_detail_card'):
            return
        if not refresh_details:
            return
        if keep_selected is not None and keep_selected in self.rpc_core.config:
            self._show_game_details(keep_selected)
        else:
            self._reset_detail_panel()
        self._sync_detail_panel_visibility()

    def _on_game_row_clicked(self, game_key):
        item = self._game_row_items.get(game_key)
        if item is not None:
            self.game_list.blockSignals(True)
            self.game_list.clearSelection()
            item.setSelected(True)
            self.game_list.blockSignals(False)
            self._update_game_row_colors()
        self._show_game_details(game_key)
        self._sync_detail_panel_visibility()

    def _sync_detail_panel_visibility(self):
        if not hasattr(self, 'vn_detail_card'):
            return
        has_selection = len(self.game_list.selectedItems()) > 0
        card = self.vn_detail_card
        if has_selection:
            card.setMinimumHeight(150)
            card.setMaximumHeight(16777215)
            self.right_splitter.setStretchFactor(1, 1)
            sizes = self.right_splitter.sizes()
            total = sum(sizes) or 600
            self.right_splitter.setSizes([total // 2, total - total // 2])
        else:
            card.setMinimumHeight(0)
            card.setMaximumHeight(0)
            self.right_splitter.setStretchFactor(1, 0)
            sizes = self.right_splitter.sizes()
            total = sum(sizes) or 600
            self.right_splitter.setSizes([total, 0])

    def move_game_to_top(self, game_key):
        config = self.rpc_core.config
        if game_key not in config:
            return
        ordered_keys = self.rpc_core.get_supported_games()
        if not ordered_keys or ordered_keys[0] == game_key:
            return
        ordered_keys.remove(game_key)
        ordered_keys.insert(0, game_key)
        self._apply_order(ordered_keys)

    def _apply_order(self, ordered_keys):
        config = self.rpc_core.config
        for i, key in enumerate(ordered_keys, 1):
            config[key]['order'] = str(i)
        self.rpc_core._save_config()
        self._reorder_game_list(ordered_keys)

    def _reorder_game_list(self, ordered_keys):
        gl = self.game_list
        top_key = ordered_keys[0]
        if self._game_row_items.get(top_key) is None:
            self.refresh_game_list(refresh_details=False)
            return
        game_keys_in_view = []
        for row in range(gl.count()):
            data = gl.item(row).data(Qt.ItemDataRole.UserRole)
            if data is not None:
                game_keys_in_view.append(data)
        if not game_keys_in_view or game_keys_in_view[0] == top_key:
            return
        if top_key not in game_keys_in_view:
            self.refresh_game_list(refresh_details=False)
            return
        k = game_keys_in_view.index(top_key)
        try:
            self._rebuild_top_row(top_key, k, ordered_keys, len(game_keys_in_view))
        except Exception:
            self.refresh_game_list(refresh_details=False)

    def _rebuild_top_row(self, top_key, k, ordered_keys, n_in_view):
        gl = self.game_list
        gl.blockSignals(True)
        try:
            old_widget = self._game_row_widgets.get(top_key)
            if k < n_in_view - 1:
                sep_item = gl.item(2 * k + 1)
                sep_widget = gl.itemWidget(sep_item)
                gl.takeItem(2 * k + 1)
                if sep_widget is not None:
                    sep_widget.deleteLater()
            moved_item = gl.item(2 * k)
            gl.takeItem(2 * k)
            if old_widget is not None:
                old_widget.deleteLater()
            last = gl.count() - 1
            if last >= 0 and gl.item(last).data(Qt.ItemDataRole.UserRole) is None:
                tail_widget = gl.itemWidget(gl.item(last))
                gl.takeItem(last)
                if tail_widget is not None:
                    tail_widget.deleteLater()
            try:
                icon = self.get_game_list_icon(top_key)
            except Exception:
                icon = QIcon()
            item = QListWidgetItem('')
            item.setData(Qt.ItemDataRole.UserRole, top_key)
            widget, text_label, status_label = self._make_game_row_widget(
                top_key, self.get_game_display_name(top_key), icon)
            gl.insertItem(0, item)
            gl.setItemWidget(item, widget)
            item.setSizeHint(QSize(1, QFontMetrics(self.font()).height() + 25))
            self._game_row_labels[top_key] = text_label
            self._game_row_status[top_key] = status_label
            self._game_row_items[top_key] = item
            self._game_row_widgets[top_key] = widget
            self._game_row_state.pop(top_key, None)
            widget.rowClicked.connect(lambda key=top_key: self._on_game_row_clicked(key))
            if len(ordered_keys) >= 2:
                separator_item = QListWidgetItem()
                separator_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
                separator = QWidget()
                separator.setFixedHeight(1)
                separator.setStyleSheet('background-color: #3f4147;')
                gl.insertItem(1, separator_item)
                gl.setItemWidget(separator_item, separator)
                separator_item.setSizeHint(QSize(1, 9))
        finally:
            gl.blockSignals(False)
        self._update_running_indicators(self._last_running_keys)

    def get_game_display_name(self, game_key):
        settings = self.rpc_core.config.get(game_key, {})
        return settings.get('vn_name') or settings.get('activity_name') or settings.get('large_text') or settings.get('exe_name') or game_key

    def get_game_list_icon(self, game_key, snapshot=None):
        settings = self.rpc_core.config.get(game_key, {})
        icon_provider = QFileIconProvider()
        exe_icon_path = settings.get('exe_icon_path', '')
        if exe_icon_path and os.path.exists(exe_icon_path):
            return QIcon(exe_icon_path)
        exe_path = settings.get('exe_path', '')
        if exe_path and os.path.exists(exe_path):
            return icon_provider.icon(QFileInfo(exe_path))
        process = self.rpc_core.get_matching_process(game_key, snapshot)
        if process is not None:
            try:
                running_exe_path = process.exe()
                if running_exe_path and os.path.exists(running_exe_path):
                    return icon_provider.icon(QFileInfo(running_exe_path))
            except Exception:
                pass
        return icon_provider.icon(QFileInfo(''))

    def _preview_fill_pixmap(self, pixmap, size=64):
        if pixmap.width() <= 0 or pixmap.height() <= 0:
            return pixmap
        scale = max(size / pixmap.width(), size / pixmap.height())
        scaled = pixmap.scaled(max(1, int(round(pixmap.width() * scale))), max(1, int(round(pixmap.height() * scale))), Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
        canvas = QPixmap(size, size)
        canvas.fill(Qt.GlobalColor.transparent)
        painter = QPainter(canvas)
        painter.drawPixmap((size - scaled.width()) // 2, (size - scaled.height()) // 2, scaled)
        painter.end()
        return canvas

    def on_game_selected(self, item):
        if item is None:
            return
        key = item.data(Qt.ItemDataRole.UserRole)
        if not key:
            return
        self._show_game_details(key)
        self._sync_detail_panel_visibility()

    def clear_rpc(self):
        result = self.rpc_core.clear_rpc()
        self.update_status(result)

    def _set_window_title(self, activity_name):
        title = 'EwE'
        if activity_name:
            title = f'EwE | {activity_name}'
        if self.windowTitle() != title:
            self.setWindowTitle(title)

    def _update_running_indicators(self, running_keys):
        for game_key, label in self._game_row_status.items():
            state = game_key in running_keys
            if self._game_row_state.get(game_key) == state:
                continue
            self._game_row_state[game_key] = state
            color = '#23a559' if state else '#5c5e66'
            label.setStyleSheet(f'color: {color}; font-size: 10px;')

    def _blur_cover_failed(self, message, game_key):
        if game_key in self._blur_cover_warned:
            return
        self._blur_cover_warned.add(game_key)
        self.update_status(f'{game_key}: explicit cover blur skipped. {message}')

    def _on_monitor_tick(self):
        if self._scan_inflight:
            return
        self._scan_inflight = True
        try:
            self._scan_executor.submit(self._scan_and_report)
        except RuntimeError:
            self._scan_inflight = False

    def _scan_and_report(self):
        try:
            result = self._run_process_scan()
        except Exception as e:
            result = {'running': [], 'activity': None, 'status': f'Error scanning processes: {e}', 'clear': False}
        finally:
            self._scan_inflight = False
        try:
            self._scan_signals.scan_done.emit(result)
        except Exception:
            pass

    def _run_process_scan(self):
        try:
            snapshot = list(psutil.process_iter(['pid', 'name']))
        except Exception:
            snapshot = []
        self.rpc_core.sync_all_tracked_pids()
        running = []
        for game_key in self.rpc_core.get_supported_games():
            proc = self.rpc_core.get_matching_process(game_key, snapshot)
            if proc is not None:
                running.append(game_key)
                self.rpc_core.track_pid(game_key, proc.pid)
                self._capture_related_name(game_key, proc)
            elif self.rpc_core.get_tracked_process(game_key) is not None:
                running.append(game_key)
        for game_key in running:
            vndb_url = self.rpc_core.config.get(game_key, {}).get('vndb_url', '')
            self._post_ui_job(self.ensure_vndb_prefetch, vndb_url)
        self._background_vndb_refresh(set(running))
        self.rpc_core.tick_playtime(set(running))
        result = {'running': running, 'activity': None, 'status': None, 'clear': False}
        newly_running = [k for k in running if k not in self._last_running_keys]
        self._last_running_keys = set(running)
        if newly_running:
            result['newly'] = newly_running
        if running:
            self.rpc_core.missed_ticks = 0
            target = min(running, key=lambda k: self.rpc_core.start_times.get(k, 0) or 0)
            result['activity'] = self.rpc_core.get_activity_name(target)
            if self.presence_enabled:
                scan_result = self.rpc_core.update_presence(target, snapshot)
                if scan_result:
                    result['status'] = scan_result
        elif self.rpc_core.current_client_id:
            self.rpc_core.missed_ticks += 1
            if self.rpc_core.missed_ticks >= 3:
                result['clear'] = True
        return result

    def _scan_ensure_blur(self, game_key):
        try:
            self.rpc_core.ensure_blurred_cover(game_key, on_error=lambda msg, k=game_key: self._blur_cover_failed(msg, k))
        except Exception as e:
            print(f'Error ensuring blurred cover: {e}')

    def check_processes(self, result):
        running = result.get('running') or []
        self._update_running_indicators(set(running))
        self._update_tray_status(running)
        if getattr(self, '_detail_key', None) is not None:
            self._update_detail_playtime(self._detail_key)
        newly = result.get('newly')
        if newly:
            most_recent = max(newly, key=lambda k: self.rpc_core.start_times.get(k, 0) or 0)
            self.move_game_to_top(most_recent)
        if result.get('status'):
            self.update_status(result['status'])
        self._set_window_title(result.get('activity'))
        if result.get('clear'):
            self.clear_rpc()

    def _post_ui_job(self, func, *args):
        def _proxy(*call_args, **_call_kwargs):
            self._scan_signals.ui_job.emit((func, args + tuple(call_args)))
        return _proxy

    def _run_ui_job(self, job):
        func, args = job
        try:
            func(*args)
        except Exception as e:
            print(f'UI job failed: {e}')

    def _capture_related_name(self, game_key, proc):
        try:
            settings = self.rpc_core.config.get(game_key, {})
            if not settings:
                return
            name = proc.info.get('name') or proc.name() if hasattr(proc, 'info') else proc.name()
            if not name:
                return
            primary = settings.get('exe_name', '')
            extra = [str(n) for n in settings.get('extra_exe_names') or [] if str(n).strip()]
            if name in {primary} | set(extra) or len(extra) >= 5:
                return
            extra.append(name)
            settings['extra_exe_names'] = extra
            self.rpc_core.config[game_key] = settings
            self.rpc_core._save_config()
            self._post_ui_job(self.update_status, f"{game_key}: detected related process '{name}'. It will be tracked automatically.")
        except Exception:
            pass

    def _background_vndb_refresh(self, running_keys):
        ordered = [k for k in self.rpc_core.get_supported_games() if k not in running_keys]
        n = len(ordered)
        if n == 0:
            self._vndb_cycle_index = 0
            return
        start = self._vndb_cycle_index % n
        for offset in range(n):
            key = ordered[(start + offset) % n]
            url = (self.rpc_core.config.get(key, {}).get('vndb_url') or '').strip()
            if not url:
                continue
            age = self.rpc_core.vndb_cache_age(url)
            if age is not None and age < self.rpc_core.VNDB_CACHE_TTL_SECONDS:
                continue
            self._post_ui_job(self.ensure_vndb_prefetch, url)
            self._vndb_cycle_index = (start + offset + 1) % n
            return
        self._vndb_cycle_index = (start + 1) % n

    def ensure_vndb_prefetch(self, vndb_url):
        vndb_url = (vndb_url or '').strip()
        if not vndb_url or self.rpc_core.has_vndb_cache(vndb_url):
            return
        if vndb_url in self._vndb_prefetching:
            return
        last_attempt = self._vndb_last_attempt.get(vndb_url)
        if last_attempt is not None and time.time() - last_attempt < 60:
            return
        self._vndb_last_attempt[vndb_url] = time.time()
        self._vndb_prefetching.add(vndb_url)

        def on_done(_result):
            self._vndb_prefetching.discard(vndb_url)

        def on_error(message):
            self._vndb_prefetching.discard(vndb_url)
            self.update_status(f'VNDB lookup failed for {vndb_url}: {message}')
        run_async_task(lambda: self.rpc_core.fetch_vndb_info(vndb_url), on_done, on_error)

    def pick_vndb(self):
        dialog = QDialog(self)
        dialog.setWindowTitle('Search VNDB')
        dialog.setMinimumWidth(520)
        dialog.setSizeGripEnabled(True)
        layout = QVBoxLayout(dialog)
        vndb_search_input = QLineEdit()
        vndb_search_input.setPlaceholderText('Search any title')
        layout.addWidget(vndb_search_input)
        unknown_check = QCheckBox('Unknown VN')
        layout.addWidget(unknown_check)
        vndb_results = QListWidget()
        vndb_results.setMinimumHeight(220)
        layout.addWidget(vndb_results)
        vndb_selected_label = QLabel('Select any title to continue.')
        vndb_selected_label.setWordWrap(True)
        layout.addWidget(vndb_selected_label)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        ok_btn = buttons.button(QDialogButtonBox.StandardButton.Ok)
        ok_btn.setText('Continue')
        ok_btn.setEnabled(False)
        layout.addWidget(buttons)
        selected_vn = {'id': '', 'title': ''}
        search_generation = [0]
        cover_labels = []
        row_states = []

        def reset_vndb_selection(message):
            selected_vn['id'] = ''
            selected_vn['title'] = ''
            vndb_selected_label.setText(message)
            ok_btn.setEnabled(False)

        def dialog_alive():
            if sip is None:
                return True
            try:
                return not sip.isdeleted(dialog)
            except Exception:
                return True

        def render_search_cover(idx):
            if idx >= len(cover_labels) or idx >= len(row_states):
                return
            st = row_states[idx]
            pm = st['pm']
            if pm is None:
                return
            if st['explicit'] and self.rpc_core.get_setting('pixel_explicit', True):
                cover_labels[idx].setPixmap(self._blur_pixmap(pm, 48, 64))
            else:
                cover_labels[idx].setPixmap(pm)

        def start_cover_loading(gen, results):

            def on_covers_done(contents):
                if gen != search_generation[0] or not dialog_alive():
                    return
                for idx, content in enumerate(contents):
                    if not content or idx >= len(row_states):
                        continue
                    pm = QPixmap()
                    if not pm.loadFromData(content):
                        continue
                    row_states[idx]['pm'] = pm.scaled(48, 64, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    render_search_cover(idx)

            def on_ratings_done(ratings):
                if gen != search_generation[0] or not dialog_alive():
                    return
                for idx, rating in enumerate(ratings):
                    if idx >= len(row_states) or not isinstance(rating, dict):
                        continue
                    if row_states[idx]['explicit'] is None:
                        row_states[idx]['explicit'] = bool(rating.get('cover_explicit'))
                        render_search_cover(idx)
            urls = [vn.get('thumbnail') or '' for vn in results]
            run_async_task(lambda: self.rpc_core.fetch_thumbnails(urls), on_covers_done, lambda _message: None)
            run_async_task(lambda: self.rpc_core.fetch_vn_cover_ratings(results), on_ratings_done, lambda _message: None)

        def run_vndb_search():
            if unknown_check.isChecked():
                return
            query = vndb_search_input.text().strip()
            if not query:
                return
            search_debounce.stop()
            search_generation[0] += 1
            gen = search_generation[0]
            cover_labels.clear()
            vndb_results.clear()
            vndb_results.addItem('Searching VNDB...')
            reset_vndb_selection('Searching VNDB...')

            def on_search_done(results):
                if gen != search_generation[0] or not dialog_alive():
                    return
                vndb_results.clear()
                if not results:
                    vndb_results.addItem('No results found.')
                    return
                cover_labels.clear()
                row_states.clear()
                row_states.extend({'pm': None, 'explicit': None} for _ in results)
                for vn in results:
                    row = QWidget()
                    row.setStyleSheet('background: transparent;')
                    row_layout = QHBoxLayout(row)
                    row_layout.setContentsMargins(4, 4, 4, 4)
                    row_layout.setSpacing(8)
                    cover = QLabel()
                    cover.setFixedSize(48, 64)
                    cover.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    cover.setText('...')
                    cover.setStyleSheet('background: #2b2b2b; color: #808080; border: 1px solid #555;')
                    text_layout = QVBoxLayout()
                    text_layout.setContentsMargins(0, 0, 0, 0)
                    text_layout.setSpacing(2)
                    title_label = QLabel(f"{vn['title']}  ({vn['id']})")
                    dev_label = QLabel(f"Developer: {vn['developer']}")
                    if vn['rating'] != 'N/A':
                        rating_label = QLabel(f"Rating: ⭐ {vn['rating']}/10")
                    else:
                        rating_label = QLabel('Rating: N/A')
                    text_layout.addWidget(title_label)
                    text_layout.addWidget(dev_label)
                    text_layout.addWidget(rating_label)
                    row_layout.addWidget(cover)
                    row_layout.addLayout(text_layout, 1)
                    for widget in (row, cover, title_label, dev_label, rating_label):
                        widget.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
                    item = QListWidgetItem()
                    item.setData(Qt.ItemDataRole.UserRole, vn)
                    item.setSizeHint(QSize(0, 72))
                    vndb_results.addItem(item)
                    vndb_results.setItemWidget(item, row)
                    cover_labels.append(cover)
                vndb_selected_label.setText('Pick a result above, then click Continue.')
                ok_btn.setEnabled(False)
                start_cover_loading(gen, list(results))

            def on_search_error(message):
                if gen != search_generation[0] or not dialog_alive():
                    return
                vndb_results.clear()
                vndb_results.addItem(f'Search failed: {message}')
                reset_vndb_selection('Search failed.')
            run_async_task(lambda: self.rpc_core.search_vndb(query), on_search_done, on_search_error)
        search_debounce = QTimer(dialog)
        search_debounce.setSingleShot(True)
        search_debounce.setInterval(400)
        search_debounce.timeout.connect(run_vndb_search)

        def on_search_text_changed(text):
            if unknown_check.isChecked():
                search_debounce.stop()
                return
            if len(text.strip()) < 2:
                search_debounce.stop()
                search_generation[0] += 1
                vndb_results.clear()
                reset_vndb_selection('Select any VN to continue, or tick Unknown VN if it is not listed on VNDB.')
                return
            search_debounce.start()

        def on_unknown_toggled(checked):
            if checked:
                search_debounce.stop()
                search_generation[0] += 1
                vndb_results.clear()
                selected_vn['id'] = ''
                selected_vn['title'] = ''
                vndb_search_input.setEnabled(False)
                vndb_selected_label.setText('Selected: Unknown VN (no VNDB data)')
                ok_btn.setEnabled(True)
            else:
                vndb_search_input.setEnabled(True)
                vndb_results.clear()
                reset_vndb_selection('Select any VN to continue, or tick Unknown VN if it is not listed on VNDB.')
                if len(vndb_search_input.text().strip()) >= 2:
                    search_debounce.start()

        def on_vndb_result_picked(_item):
            items = vndb_results.selectedItems()
            if not items:
                return
            vn = items[0].data(Qt.ItemDataRole.UserRole)
            if vn is None:
                return
            selected_vn['id'] = vn['id']
            selected_vn['title'] = vn['title']
            if vn['id']:
                vndb_selected_label.setText(f"Selected: {vn['title']}  ({vn['id']})")
            else:
                vndb_selected_label.setText('Selected: Unknown VN')
            ok_btn.setEnabled(True)
        vndb_results.itemClicked.connect(on_vndb_result_picked)
        vndb_search_input.textChanged.connect(on_search_text_changed)
        vndb_search_input.returnPressed.connect(run_vndb_search)
        unknown_check.toggled.connect(on_unknown_toggled)
        picked = {'vn': None}

        def on_accept_vn():
            if ok_btn.isEnabled():
                picked['vn'] = {'id': selected_vn['id'], 'title': selected_vn['title']}
            dialog.accept()
        vndb_results.itemDoubleClicked.connect(lambda _item: on_accept_vn() if ok_btn.isEnabled() else None)
        buttons.accepted.connect(on_accept_vn)
        buttons.rejected.connect(dialog.reject)
        dialog.exec()
        return picked['vn']

    def open_vndb_search_dialog(self):
        vn = self.pick_vndb()
        if vn is not None:
            self.open_add_game_dialog(vn)

    def open_add_game_dialog(self, selected_vn):
        dialog = QDialog(self)
        dialog.setWindowTitle('Browse .exe')
        dialog.setMinimumWidth(520)
        dialog.setSizeGripEnabled(True)
        layout = QVBoxLayout(dialog)
        vn_label_text = selected_vn.get('title') or 'Unknown VN'
        if selected_vn.get('id'):
            vn_label_text += f"  ({selected_vn['id']})"
        layout.addWidget(QLabel(f'VN: {vn_label_text}'))
        pick_label = QLabel('You can either click the game window to automatically detect the executable, or browse for the .exe file manually. Alternatively, you can select a running executable from the list below.')
        pick_label.setWordWrap(True)
        layout.addWidget(pick_label)
        pick_window_btn = QPushButton('Click the game window')
        layout.addWidget(pick_window_btn)
        choose_local_exe_btn = QPushButton('Browse .exe')
        layout.addWidget(choose_local_exe_btn)
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator)
        exe_list = QListWidget()
        running_exes = {}
        for p in psutil.process_iter(['name', 'exe']):
            try:
                if p.info['name']:
                    running_exes[p.info['name']] = p.info.get('exe', '') or ''
            except Exception:
                pass
        known_exes = set(self.rpc_core.get_supported_games())
        new_exes = sorted(set(running_exes.keys()) - known_exes)
        exe_list.addItems(new_exes)
        layout.addWidget(QLabel('Running processes:'))
        layout.addWidget(exe_list)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        layout.addWidget(buttons)

        def pick_window():
            self.update_status('Window picker armed. Click the game window within 5 seconds.')

            def capture_window_under_cursor():
                try:
                    x, y = win32gui.GetCursorPos()
                    hwnd = win32gui.WindowFromPoint((x, y))
                    hwnd = win32gui.GetAncestor(hwnd, win32con.GA_ROOT)
                    if not hwnd:
                        raise RuntimeError('No window found under cursor.')
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    if not pid:
                        raise RuntimeError('The window under the cursor has no process.')
                    if pid == os.getpid():
                        raise RuntimeError("That is this app's own window. Click on the game window instead.")
                    proc = psutil.Process(pid)
                    exe_name = proc.name()
                    exe_path = proc.exe()
                    window_title = win32gui.GetWindowText(hwnd)
                    folder_name = os.path.basename(os.path.dirname(exe_path))
                    game_key = folder_name or exe_name
                    picked_config = {'exe_name': exe_name, 'exe_path': exe_path, 'vn_name': selected_vn['title'] or folder_name or exe_name, 'extra_exe_names': self.rpc_core.resolve_related_processes(exe_name, exe_path)}
                    if selected_vn['id']:
                        picked_config['vndb_url'] = f"https://vndb.org/{selected_vn['id']}"
                    dialog.accept()
                    self.update_status(f'Picked window: {window_title or exe_name} | exe: {exe_name} | folder match: {folder_name}')
                    self.open_game_info_dialog(game_key, picked_config)
                except Exception as e:
                    pick_window_btn.setText('Click me again to pick a window')
                    pick_window_btn.setEnabled(True)
                    QMessageBox.warning(dialog, 'Window Picker Failed', str(e))
            arm_window_picker(pick_window_btn, capture_window_under_cursor)

        def choose_local_exe():
            exe_path, _ = native_open_file_dialog(dialog, 'Choose a game .exe file', '', 'Executable Files (*.exe);;All Files (*)')
            if not exe_path:
                return
            exe_name = os.path.basename(exe_path)
            folder_name = os.path.basename(os.path.dirname(exe_path))
            game_key = folder_name or exe_name
            exe_stem = os.path.splitext(exe_name)[0]
            picked_config = {'exe_name': exe_name, 'exe_path': exe_path, 'vn_name': selected_vn['title'] or folder_name or exe_stem or exe_name, 'activity_name': folder_name or exe_stem or exe_name, 'extra_exe_names': self.rpc_core.resolve_related_processes(exe_name, exe_path)}
            if selected_vn['id']:
                picked_config['vndb_url'] = f"https://vndb.org/{selected_vn['id']}"
            dialog.accept()
            self.update_status(f'Selected local game file: {exe_path}')
            self.open_game_info_dialog(game_key, picked_config)
        choose_local_exe_btn.clicked.connect(choose_local_exe)
        pick_window_btn.clicked.connect(pick_window)

        def on_accept():
            selected_items = exe_list.selectedItems()
            if selected_items:
                exe_name = selected_items[0].text()
                dialog.accept()
                config = {'exe_name': exe_name, 'exe_path': running_exes.get(exe_name, ''), 'vn_name': selected_vn['title'] or exe_name, 'extra_exe_names': self.rpc_core.resolve_related_processes(exe_name, running_exes.get(exe_name, ''))}
                if selected_vn['id']:
                    config['vndb_url'] = f"https://vndb.org/{selected_vn['id']}"
                self.open_game_info_dialog(exe_name, config)
            else:
                QMessageBox.information(dialog, 'No EXE Selected', 'Select an executable or use the window picker.')
        buttons.accepted.connect(on_accept)
        buttons.rejected.connect(dialog.reject)
        dialog.exec()

    def open_game_info_dialog(self, exe_name, existing_config=None):
        existing_config = existing_config or {}
        dialog = QDialog(self)
        self.active_dialogs.append(dialog)
        dialog.setWindowTitle(f'Game Info')
        dialog.setFixedSize(652, 622)
        outer_layout = QVBoxLayout(dialog)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        outer_layout.addWidget(scroll)
        content = QWidget()
        scroll.setWidget(content)
        layout = QVBoxLayout(content)
        default_vn_name = existing_config.get('vn_name') or existing_config.get('activity_name') or existing_config.get('large_text') or exe_name
        vn_name_input = QLineEdit(default_vn_name)
        vn_name_input.setPlaceholderText('Visual Novel Title')
        exe_path_input = QLineEdit(existing_config.get('exe_path', ''))
        exe_path_input.setReadOnly(True)
        exe_path_input.setPlaceholderText('Full path to the vn executable, e.g. D:\\Games\\MyVN\\vn.exe')
        exe_icon_path_input = QLineEdit(existing_config.get('exe_icon_path', ''))
        exe_icon_path_input.setVisible(False)

        def current_exe_name():
            path = exe_path_input.text().strip()
            if path:
                return os.path.basename(path)
            return existing_config.get('exe_name') or exe_name
        layout.addWidget(QLabel('VN Title:'))
        layout.addWidget(vn_name_input)
        activity_name_input = QLineEdit(existing_config.get('activity_name', ''))
        activity_name_input.setPlaceholderText('Shown on Discord (blank = VN title)')
        layout.addWidget(QLabel('Activity Name:'))
        layout.addWidget(activity_name_input)
        match_path_contains_input = QLineEdit(existing_config.get('match_path_contains', ''))
        match_path_contains_input.setPlaceholderText('Optional: only match processes whose path contains this')
        layout.addWidget(QLabel('Process Path Filter:'))
        layout.addWidget(match_path_contains_input)
        vndb_url_input = QLineEdit(existing_config.get('vndb_url', ''))
        vndb_url_input.setReadOnly(True)
        vndb_url_input.setPlaceholderText('No VNDB entry selected')
        vndb_url_layout = QHBoxLayout()
        vndb_url_layout.addWidget(vndb_url_input, 1)
        vndb_pick_btn = QPushButton('Search VNDB')
        vndb_clear_btn = QPushButton('Clear')
        vndb_url_layout.addWidget(vndb_pick_btn)
        vndb_url_layout.addWidget(vndb_clear_btn)

        def pick_vndb_url():
            vn = self.pick_vndb()
            if vn is None:
                return
            if vn.get('id'):
                vndb_url_input.setText(f"https://vndb.org/{vn['id']}")
                if not vn_name_input.text().strip():
                    vn_name_input.setText(vn.get('title', ''))
            else:
                vndb_url_input.clear()
        vndb_pick_btn.clicked.connect(pick_vndb_url)
        vndb_clear_btn.clicked.connect(lambda: vndb_url_input.clear())
        layout.addWidget(QLabel('VNDB URL:'))
        layout.addLayout(vndb_url_layout)
        exe_path_layout = QHBoxLayout()
        exe_path_layout.addWidget(exe_path_input)
        browse_exe_path_btn = QPushButton('Browse .exe')
        exe_path_layout.addWidget(browse_exe_path_btn)
        pick_game_window_btn = QPushButton('Click the game window')
        exe_path_layout.addWidget(pick_game_window_btn)
        layout.addWidget(QLabel('VN Executable Path:'))
        layout.addLayout(exe_path_layout)

        def browse_exact_exe_path():
            selected_path, _ = native_open_file_dialog(dialog, 'Choose exact game .exe path', exe_path_input.text().strip() or '', 'Executable Files (*.exe);;All Files (*)')
            if selected_path:
                exe_path_input.setText(selected_path)
                update_preview()

        def pick_game_window():
            self.update_status('Click the game window within 5 seconds.')

            def capture_window_under_cursor():
                try:
                    x, y = win32gui.GetCursorPos()
                    hwnd = win32gui.WindowFromPoint((x, y))
                    hwnd = win32gui.GetAncestor(hwnd, win32con.GA_ROOT)
                    if not hwnd:
                        raise RuntimeError('No window found under cursor.')
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    if not pid:
                        raise RuntimeError('The window under the cursor has no process.')
                    if pid == os.getpid():
                        raise RuntimeError("That is this app's own window. Click on the game window instead.")
                    proc = psutil.Process(pid)
                    exe_path = proc.exe()
                    if not exe_path:
                        raise RuntimeError('Could not read the .exe path of that window.')
                    exe_path_input.setText(exe_path)
                    update_preview()
                    self.update_status(f'Window picked: exe path set to {exe_path}')
                except Exception as e:
                    QMessageBox.warning(dialog, 'Window Picker Failed', str(e))
            arm_window_picker(pick_game_window_btn, capture_window_under_cursor)
        browse_exe_path_btn.clicked.connect(browse_exact_exe_path)
        pick_game_window_btn.clicked.connect(pick_game_window)
        large_image_input = QLineEdit(existing_config.get('large_image', ''))
        large_text_input = QLineEdit(existing_config.get('large_text') or default_vn_name)
        large_text_input.setPlaceholderText('Text that are shown when hovering over the image')

        def save_large_text_live():
            if exe_name not in self.rpc_core.config:
                return
            try:
                self.rpc_core.config[exe_name]['large_text'] = large_text_input.text().strip()
                self.rpc_core._save_config()
            except Exception as e:
                print(f'Error saving large text live: {e}')
        large_text_input.textChanged.connect(save_large_text_live)
        large_image_input.setVisible(False)
        cover_url_input = QLineEdit(existing_config.get('cover_url', ''))
        cover_url_input.setVisible(False)
        image_source_path_input = QLineEdit(existing_config.get('image_source_path', ''))
        image_source_path_input.setPlaceholderText('Local image path that are shown on Discord RPC')
        image_source_path_input.setReadOnly(True)
        use_exe_icon_btn = QPushButton('Use .exe Icon')
        upload_image_btn = QPushButton('Browse Local Image')
        update_image_btn = QPushButton('Refresh Image')
        upload_btn = QPushButton('Upload')
        image_edit_dialog = QDialog(dialog)
        image_edit_dialog.setWindowTitle(f'Image Settings')
        image_edit_layout = QVBoxLayout(image_edit_dialog)
        image_mode_row = QHBoxLayout()
        default_image_check = QCheckBox('Default')
        manual_image_check = QCheckBox('Manual')
        image_mode_row.addWidget(default_image_check)
        image_mode_row.addWidget(manual_image_check)
        image_mode_row.addStretch(1)
        image_edit_layout.addLayout(image_mode_row)
        explicit_rpc_note = QLabel('')
        explicit_rpc_note.setWordWrap(True)
        explicit_rpc_note.setStyleSheet('QLabel { color: #e3b341; background-color: #2a2313; border: 1px solid #57431e; border-radius: 6px; padding: 6px; font-size: 11px; }')
        explicit_rpc_note.setVisible(False)
        image_edit_layout.addWidget(explicit_rpc_note)
        image_source_path_label = QLabel('VNDB URL Image:')
        image_edit_layout.addWidget(image_source_path_label)
        image_edit_layout.addWidget(image_source_path_input)
        image_url_label = QLabel('Image URL:')
        image_url_input = QLineEdit()
        image_url_input.setReadOnly(True)
        image_url_input.setPlaceholderText('Online image URL (after upload)')
        image_edit_layout.addWidget(image_url_label)
        image_url_row = QHBoxLayout()
        image_url_row.addWidget(image_url_input)
        image_url_row.addWidget(upload_btn)
        image_edit_layout.addLayout(image_url_row)
        image_btn_row = QHBoxLayout()
        image_btn_row.addWidget(use_exe_icon_btn)
        image_btn_row.addWidget(upload_image_btn)
        image_btn_row.addWidget(update_image_btn)
        choose_vndb_cover_btn = QPushButton('Choose VNDB cover')
        choose_vndb_cover_btn.setToolTip('Pick a different cover image from the VNDB entry (if it has more than one)')
        image_btn_row.addWidget(choose_vndb_cover_btn)
        image_edit_layout.addLayout(image_btn_row)
        image_edit_layout.addStretch(1)
        self.active_dialogs.append(image_edit_dialog)
        image_edit_dialog.finished.connect(lambda _: self.active_dialogs.remove(image_edit_dialog) if image_edit_dialog in self.active_dialogs else None)
        dialog.finished.connect(lambda _: image_edit_dialog.close())
        saved_cover = (existing_config.get('cover_url') or '').strip()
        saved_large = (existing_config.get('large_image') or '').strip()
        saved_is_vndb = existing_config.get('image_host', '') == 'vndb' or saved_cover.startswith('https://i.vndb.org') or saved_large.startswith('https://i.vndb.org')
        if saved_is_vndb:
            default_source_value = (saved_large or saved_cover).strip()
            manual_source_value = ''
            manual_url_value = ''
        else:
            default_source_value = ''
            manual_source_value = (existing_config.get('image_source_path') or '').strip()
            manual_url_value = saved_cover or saved_large
        manual_image_staged = False
        game_info_saved = False

        def update_refresh_button_state():
            source_path = (manual_source_value or '').strip()
            has_image = bool(source_path) and os.path.exists(source_path)
            update_image_btn.setEnabled(game_info_saved and has_image)
        image_source_path_input.textChanged.connect(update_refresh_button_state)
        update_refresh_button_state()
        layout.addWidget(QLabel('Large Text:'))
        layout.addWidget(large_text_input)
        preview_frame = QFrame()
        preview_frame.setObjectName('discordPreviewFrame')
        preview_frame.setStyleSheet('\n            QFrame#discordPreviewFrame {\n                background-color: #2b2d31;\n                border-radius: 10px;\n                padding: 10px;\n            }\n            QLabel {\n                color: #f2f3f5;\n            }\n        ')
        preview_frame.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        preview_outer = QVBoxLayout(preview_frame)
        preview_outer.setContentsMargins(10, 4, 10, 4)
        preview_outer.setSpacing(5)
        preview_status_label = QLabel('Playing')
        preview_status_label.setStyleSheet('font-weight: 600; font-size: 11px; color: #f2f3f5;')
        preview_outer.addWidget(preview_status_label)
        preview_body = QHBoxLayout()
        preview_body.setSpacing(10)
        preview_image_label = _ClickableLabel()
        preview_image_label.setFixedSize(64, 64)
        preview_image_label.setScaledContents(False)
        preview_image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview_image_label.setStyleSheet('background-color: #1e1f22; border-radius: 8px;')

        def open_image_settings():
            image_edit_dialog.exec()
        preview_image_state = {'hovering': False, 'base_pixmap': QPixmap()}
        preview_image_cache = PREVIEW_IMAGE_CACHE
        preview_processed_cache = {}
        preview_image_failures = {}
        preview_next_retry = {}

        def apply_preview_image_overlay():
            base = preview_image_state['base_pixmap']
            size = 64
            if preview_image_state['hovering']:
                if base.isNull():
                    hover_pm = QPixmap(size, size)
                    hover_pm.fill(QColor('#1e1f22'))
                else:
                    hover_pm = base.copy()
                painter = QPainter(hover_pm)
                painter.fillRect(hover_pm.rect(), QColor(0, 0, 0, 110))
                painter.setPen(QPen(QColor('#ffffff'), 3))
                cx, cy, r = (size // 2, size // 2, 12)
                painter.drawLine(cx - r, cy, cx + r, cy)
                painter.drawLine(cx, cy - r, cx, cy + r)
                painter.end()
                preview_image_label.setPixmap(hover_pm)
            elif base.isNull():
                preview_image_label.clear()
                preview_image_label.setText('')
            else:
                preview_image_label.setPixmap(base)

        def set_preview_base_pixmap(pm):
            preview_image_state['base_pixmap'] = pm
            apply_preview_image_overlay()

        chat_bubble = _ChatBubble(dialog)
        chat_bubble.hide()

        def _position_and_show_chat_bubble():
            text = large_text_input.text().strip() or vn_name_input.text().strip() or exe_name
            chat_bubble.set_text(text)
            parent = chat_bubble.parent()
            img_pos = preview_image_label.mapTo(parent, QPoint(0, 0))
            bubble_x = img_pos.x() + preview_image_label.width() // 2 - chat_bubble.width() // 2
            bubble_y = img_pos.y() - chat_bubble.height() - 4
            min_x = 8
            max_x = parent.width() - chat_bubble.width() - 8
            if bubble_x < min_x:
                bubble_x = min_x
            if bubble_x > max_x:
                bubble_x = max(min_x, max_x)
            chat_bubble.move(bubble_x, bubble_y)
            chat_bubble.raise_()
            chat_bubble.show()

        def _on_preview_image_hover(hovering):
            preview_image_state['hovering'] = hovering
            apply_preview_image_overlay()
            if hovering:
                _position_and_show_chat_bubble()
            else:
                chat_bubble.hide()
        preview_image_label.hoverChanged.connect(_on_preview_image_hover)
        preview_image_label.setCursor(Qt.CursorShape.PointingHandCursor)
        preview_image_label.clicked.connect(open_image_settings)
        preview_body.addWidget(preview_image_label, 0, Qt.AlignmentFlag.AlignTop)
        preview_text_layout = QVBoxLayout()
        preview_text_layout.setSpacing(0)
        preview_title_label = QLabel('VN Title')
        preview_title_label.setStyleSheet('font-weight: 700; font-size: 12px; color: #ffffff;')
        preview_title_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        preview_title_label.setWordWrap(True)
        preview_details_label = QLineEdit()
        preview_details_label.setPlaceholderText('Details')
        preview_details_label.setFrame(False)
        preview_details_label.setFixedHeight(18)
        preview_details_label.setMinimumWidth(300)
        preview_details_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        preview_details_label.setStyleSheet('font-size: 12px; color: #f2f3f5; background: transparent; border: 0px; padding: 0px;')
        preview_state_label = QLineEdit()
        preview_state_label.setPlaceholderText('State')
        preview_state_label.setFrame(False)
        preview_state_label.setFixedHeight(18)
        preview_state_label.setMinimumWidth(300)
        preview_state_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        preview_state_label.setStyleSheet('font-size: 12px; color: #f2f3f5; background: transparent; border: 0px; padding: 0px;')
        preview_elapsed_label = QLabel('🎮 0:00')
        preview_elapsed_label.setStyleSheet('font-size: 11px; color: #23a559;')
        preview_text_layout.addWidget(preview_title_label)
        preview_text_layout.addWidget(preview_details_label)
        preview_text_layout.addWidget(preview_state_label)
        preview_text_layout.addWidget(preview_elapsed_label)
        preview_text_layout.addStretch(1)
        preview_body.addLayout(preview_text_layout, 1)
        preview_outer.addLayout(preview_body)
        layout.addWidget(QLabel('Preview:'))
        layout.addWidget(preview_frame)

        def run_background_task(title, label_text, task_func, on_success, error_title, on_error=None, show_progress=True):
            progress = None
            if show_progress:
                progress = QProgressDialog(label_text, None, 0, 0, dialog)
                progress.setWindowTitle(title)
                progress.setWindowModality(Qt.WindowModality.WindowModal)
                progress.setMinimumDuration(0)
                progress.setCancelButton(None)
                progress.setAutoClose(False)
                progress.setAutoReset(False)
                progress.show()
            for btn in [use_exe_icon_btn, upload_image_btn, update_image_btn, upload_btn]:
                btn.setEnabled(False)

            def cleanup():
                for btn in [use_exe_icon_btn, upload_image_btn, upload_btn]:
                    btn.setEnabled(True)
                update_refresh_button_state()
                if progress is not None:
                    progress.close()

            def handle_success(result):
                cleanup()
                on_success(result)

            def handle_error(message):
                cleanup()
                if on_error is not None:
                    on_error(message)
                else:
                    QMessageBox.warning(dialog, error_title, message)
            run_async_task(task_func, handle_success, handle_error)
        pending_image = {'path': '', 'kind': ''}
        image_host_override = {'host': ''}

        def mark_pending_image(source_path, source_kind):
            pending_image['path'] = source_path
            pending_image['kind'] = source_kind
            update_preview()
            self.update_status(f'{exe_name}: {source_kind} staged. It will save when you click OK.')

        def save_icon_frame(icon_img, exe_path):
            image_dir = self.get_image_dir(exe_path)
            safe_name = self.safe_filename(vn_name_input.text().strip() or exe_name)
            extracted_icon_path = os.path.join(image_dir, f'{safe_name}_exe_icon.png')
            from PIL import Image, ImageOps
            icon_img = ImageOps.exif_transpose(icon_img.convert('RGBA'))
            bbox = icon_img.getbbox()
            if bbox is not None:
                icon_img = icon_img.crop(bbox)
            icon_img = self._resize_to_square(icon_img, 1024)
            canvas = Image.new('RGBA', (1024, 1024), (0, 0, 0, 0))
            x = (1024 - icon_img.width) // 2
            y = (1024 - icon_img.height) // 2
            canvas.paste(icon_img, (x, y), icon_img)
            canvas.save(extracted_icon_path, 'PNG', optimize=True)
            return extracted_icon_path

        def extract_exe_icon(exe_path):
            frames = self._extract_exe_icon_frames(exe_path)
            if frames:
                return save_icon_frame(frames[0], exe_path)
            icon_provider = QFileIconProvider()
            icon = icon_provider.icon(QFileInfo(exe_path))
            if icon.isNull():
                raise RuntimeError('Could not read an icon from this .exe.')
            available = icon.availableSizes()
            if available:
                best = max(available, key=lambda s: s.width() * s.height())
                pixmap = icon.pixmap(best)
            else:
                pixmap = icon.pixmap(1024, 1024)
            if pixmap.isNull():
                raise RuntimeError('Could not read an icon from this .exe.')
            image_dir = self.get_image_dir(exe_path)
            safe_name = self.safe_filename(vn_name_input.text().strip() or exe_name)
            tmp_path = os.path.join(image_dir, f'{safe_name}_exe_icon_tmp.png')
            if not pixmap.save(tmp_path, 'PNG'):
                raise RuntimeError('Could not save extracted .exe icon as PNG.')
            from PIL import Image
            icon_img = Image.open(tmp_path).convert('RGBA')
            os.remove(tmp_path)
            return save_icon_frame(icon_img, exe_path)

        def do_image_upload(image_path, kind):
            nonlocal manual_source_value, manual_url_value, manual_image_staged
            if not image_path or not os.path.exists(image_path):
                QMessageBox.warning(dialog, 'Image Not Found', f'Image source not found:\n{image_path}')
                return
            game_title = (vn_name_input.text().strip() or exe_name).strip()

            def upload_task():
                exe_path = exe_path_input.text().strip()
                url, processed_path, host = self.process_and_upload_image(image_path, game_title, exe_path)
                return {'url': url, 'processed_path': processed_path, 'host': host}

            def on_upload_success(result):
                nonlocal manual_source_value, manual_url_value, manual_image_staged
                manual_source_value = result['processed_path']
                manual_url_value = result['url']
                manual_image_staged = True
                image_host_override['host'] = result['host']
                cover_url_input.setText(result['url'])
                large_image_input.setText(result['url'])
                image_source_path_input.setText(result['processed_path'])
                image_url_input.setText(result['url'])
                pending_image['path'] = ''
                pending_image['kind'] = ''
                update_preview()
                self.update_status(f'{exe_name}: image uploaded.')

            def on_upload_error(message):
                QMessageBox.warning(dialog, 'Image Upload Failed', message)

            run_background_task('Image Upload', f'Processing and uploading {kind}...\nPlease wait.', upload_task, on_upload_success, 'Image Upload Failed', on_error=on_upload_error)

        def use_exe_icon():
            nonlocal manual_source_value, manual_image_staged
            exe_path = exe_path_input.text().strip()
            if not exe_path:
                QMessageBox.information(dialog, 'No .exe Path', 'Fill in the "Exact .exe Path:" first.')
                return
            if not os.path.exists(exe_path):
                QMessageBox.warning(dialog, 'EXE Icon Failed', f'File not found:\n{exe_path}')
                return
            chosen_frame = self.pick_exe_icon_frame(exe_path)
            if chosen_frame is None:
                return
            try:
                extracted_icon_path = save_icon_frame(chosen_frame, exe_path)
            except Exception as e:
                QMessageBox.warning(dialog, 'EXE Icon Failed', str(e))
                return
            exe_icon_path_input.setText(extracted_icon_path)
            manual_source_value = extracted_icon_path
            manual_image_staged = True
            image_source_path_input.setText(extracted_icon_path)
            mark_pending_image(extracted_icon_path, '.exe icon')

        def upload_image():
            nonlocal manual_source_value, manual_image_staged
            exe_path_text = exe_path_input.text().strip()
            start_dir = os.path.dirname(exe_path_text) if exe_path_text else ''
            image_path, _ = native_open_file_dialog(dialog, 'Choose image to upload', start_dir, 'Images (*.png *.jpg *.jpeg *.webp *.bmp *.ico);;Game (*.exe);;All Files (*)')
            if not image_path:
                return
            kind = 'image'
            if image_path.lower().endswith('.exe'):
                try:
                    image_path = extract_exe_icon(image_path)
                    kind = '.exe icon'
                except Exception as e:
                    QMessageBox.warning(dialog, 'EXE Icon Failed', str(e))
                    return
            manual_source_value = image_path
            manual_image_staged = True
            image_source_path_input.setText(image_path)
            mark_pending_image(image_path, kind)

        def on_upload_click():
            source_path = manual_source_value
            if not source_path:
                QMessageBox.information(dialog, 'No Image', 'Select an image first (Browse Local Image or Use .exe Icon).')
                return
            do_image_upload(source_path, 'image')

        def fetch_vndb_cover_url(stage=False):
            vndb_url = vndb_url_input.text().strip()
            if not vndb_url:
                QMessageBox.information(image_edit_dialog, 'VNDB URL Required', 'Fill in the VNDB URL first, for example: https://vndb.org/v47937')
                return

            def task():
                return {'url': self.get_vndb_cover_url(vndb_url)}

            def on_success(result):
                nonlocal default_source_value
                if default_source_value.startswith(('http://', 'https://')):
                    return
                default_source_value = result['url']
                if default_image_check.isChecked():
                    image_source_path_input.setText(result['url'])
                cover_url_input.setText(result['url'])
                large_image_input.setText(result['url'])
                if stage:
                    mark_pending_image(vndb_url, 'vndb cover')
                update_preview()
                update_explicit_rpc_note()
                self.update_status(f'{exe_name}: VNDB cover fetched.')
            run_background_task('VNDB Cover', 'Fetching VNDB cover URL...\nPlease wait.', task, on_success, 'VNDB Cover Failed', show_progress=False)

        def choose_vndb_cover():
            nonlocal default_source_value, image_settings_dirty
            vndb_url = vndb_url_input.text().strip()
            if not vndb_url:
                QMessageBox.information(image_edit_dialog, 'VNDB URL Required', 'Fill in the VNDB URL first, for example: https://vndb.org/v47937')
                return
            picker = QDialog(image_edit_dialog)
            picker.setWindowTitle(f'Choose VNDB cover')
            picker.setModal(True)
            picker.setFixedSize(620, 450)
            self.active_dialogs.append(picker)
            picker.finished.connect(lambda _: self.active_dialogs.remove(picker) if picker in self.active_dialogs else None)
            image_edit_dialog.finished.connect(lambda _: picker.close())
            pick_layout = QVBoxLayout(picker)
            pick_status = QLabel('Loading covers from VNDB...')
            pick_status.setStyleSheet('color: #5c5e66;')
            pick_layout.addWidget(pick_status)
            pick_scroll = QScrollArea()
            pick_scroll.setWidgetResizable(True)
            pick_grid_host = QWidget()
            pick_grid = FlowLayout(pick_grid_host, 8)
            pick_grid.setContentsMargins(4, 4, 4, 4)
            pick_scroll.setWidget(pick_grid_host)
            pick_layout.addWidget(pick_scroll, 1)
            pick_btn_row = QHBoxLayout()
            pick_btn_row.addStretch(1)
            use_cover_btn = QPushButton('Use cover')
            use_cover_btn.setDefault(True)
            cancel_pick_btn = QPushButton('Cancel')
            pick_btn_row.addWidget(use_cover_btn)
            pick_btn_row.addWidget(cancel_pick_btn)
            pick_layout.addLayout(pick_btn_row)
            use_cover_btn.setEnabled(False)
            selected_cover = {'full': ''}
            cover_cells = []
            cell_thumbs = []

            def refresh_cover_selection():
                for cell, full, _img in cover_cells:
                    border = '#4a9eff' if full == selected_cover['full'] else '#3f4147'
                    cell.setStyleSheet(f'QWidget {{ border: 2px solid {border}; border-radius: 6px; background-color: #1e1f22; }}')
                use_cover_btn.setEnabled(bool(selected_cover['full']))

            def select_cover(full):
                if selected_cover['full'] != full:
                    selected_cover['full'] = full
                    refresh_cover_selection()

            def use_selected_cover():
                nonlocal default_source_value
                if not selected_cover['full']:
                    return
                default_source_value = selected_cover['full']
                pending_image['path'] = ''
                pending_image['kind'] = ''
                image_host_override['host'] = 'vndb'
                image_source_path_input.setText(selected_cover['full'])
                cover_url_input.setText(selected_cover['full'])
                large_image_input.setText(selected_cover['full'])
                image_settings_dirty = True
                update_preview()
                update_explicit_rpc_note()
                self.update_status(f'{exe_name}: VNDB cover selected.')
                picker.accept()
            use_cover_btn.clicked.connect(use_selected_cover)
            cancel_pick_btn.clicked.connect(picker.reject)

            def load_covers():
                def task():
                    covers = self.rpc_core.fetch_vn_gallery(vndb_url, limit=36)
                    try:
                        main_url = self.get_vndb_cover_url(vndb_url)
                    except Exception:
                        main_url = ''
                    return {'covers': covers, 'main': main_url}

                def on_success(result):
                    covers = result.get('covers') or []
                    main_url = (result.get('main') or '').replace('/cv.t/', '/cv/')
                    if not covers:
                        pick_status.setText('No covers found on VNDB for this entry.')
                        return
                    pick_status.setText(f'{len(covers)} covers found on VNDB. Click one to select it, then press "Use cover".')
                    for entry in covers:
                        full = (entry.get('full') or '').replace('/cv.t/', '/cv/')
                        if not full:
                            continue
                        is_main = bool(main_url) and full == main_url
                        is_explicit = bool(entry.get('exp'))
                        cell = QWidget()
                        cell.setFixedSize(104, 150)
                        cell_layout = QVBoxLayout(cell)
                        cell_layout.setContentsMargins(3, 3, 3, 3)
                        cell_layout.setSpacing(2)
                        img_label = QLabel('...')
                        img_label.setFixedSize(98, 128)
                        img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                        img_label.setStyleSheet('background-color: #0d0e12; border-radius: 3px; color: #5c5e66;')
                        badge = QLabel('')
                        badge.setFixedHeight(14)
                        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
                        badge_parts = []
                        if is_main:
                            badge_parts.append('Main')
                        if is_explicit:
                            badge_parts.append('Explicit')
                        if badge_parts:
                            badge.setText('  ·  '.join(badge_parts))
                            badge.setStyleSheet(f'font-size: 10px; font-weight: bold; color: {"#f85149" if is_explicit else "#3fb950"};')
                        cell_layout.addWidget(img_label)
                        cell_layout.addWidget(badge)
                        cell.setToolTip(full)
                        cell.mousePressEvent = lambda e, f=full: select_cover(f)
                        cell.mouseDoubleClickEvent = lambda e, f=full: (select_cover(f), use_selected_cover())
                        img_label.mousePressEvent = lambda e, f=full: select_cover(f)
                        img_label.mouseDoubleClickEvent = lambda e, f=full: (select_cover(f), use_selected_cover())
                        cover_cells.append((cell, full, img_label))
                        cell_thumbs.append(entry.get('thumb', ''))
                        pick_grid.addWidget(cell)
                    current = (default_source_value or '').replace('/cv.t/', '/cv/')
                    for _cell, full, _img in cover_cells:
                        if full == current:
                            selected_cover['full'] = full
                            break
                    refresh_cover_selection()

                    def thumbs_task():
                        urls = list(cell_thumbs)
                        with ThreadPoolExecutor(max_workers=4) as pool:
                            return list(pool.map(self.rpc_core.download_image, urls))

                    def thumbs_done(paths):
                        for (_cell, _full, img_label), entry, path in zip(cover_cells, covers, paths):
                            pm = QPixmap(path) if path else QPixmap()
                            if pm.isNull():
                                continue
                            pm = pm.scaled(98, 128, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                            if entry.get('exp') and self.rpc_core.get_setting('pixel_explicit', True):
                                pm = self._blur_pixmap(pm, 98, 128)
                            img_label.setPixmap(pm)

                    def thumbs_error(message):
                        pick_status.setText(f'{pick_status.text()}\nCould not load thumbnails: {message}')
                    run_async_task(thumbs_task, thumbs_done, thumbs_error)

                def on_error(message):
                    pick_status.setText(f'Could not load VNDB covers: {message}')
                run_async_task(task, on_success, on_error)
            load_covers()
            picker.exec()

        def apply_image_settings():
            nonlocal default_source_value, manual_source_value, manual_url_value, manual_image_staged
            if default_image_check.isChecked():
                vndb_url = vndb_url_input.text().strip()
                if not vndb_url:
                    QMessageBox.information(image_edit_dialog, 'VNDB URL Required', 'Fill in the VNDB URL first, for example: https://vndb.org/v47937')
                    return
                if default_source_value.startswith(('http://', 'https://')):
                    pending_image['path'] = ''
                    pending_image['kind'] = ''
                    image_host_override['host'] = 'vndb'
                    cover_url_input.setText(default_source_value)
                    large_image_input.setText(default_source_value)
                    update_preview()
                    self.update_status(f'{exe_name}: keeping existing VNDB cover (no refetch).')
                else:
                    mark_pending_image(vndb_url, 'vndb cover')
                    fetch_vndb_cover_url(stage=True)
                    self.update_status(f'{exe_name}: VNDB cover staged. It will save when you click OK.')
            elif manual_image_check.isChecked():
                src = manual_source_value
                if manual_image_staged and src:
                    mark_pending_image(src, 'image')
                    update_preview()
                    self.update_status(f'{exe_name}: manual image staged. It will save when you click OK.')
                elif src:
                    pending_image['path'] = ''
                    pending_image['kind'] = ''
                    self.update_status(f'{exe_name}: keeping existing image (no reupload). Use Refresh Image to force.')
                else:
                    pending_image['path'] = ''
                    pending_image['kind'] = ''
                    QMessageBox.information(image_edit_dialog, 'No Image', 'Fill in the Image Source Path first.')
            else:
                pending_image['path'] = ''
                pending_image['kind'] = ''
                default_source_value = ''
                manual_source_value = ''
                manual_url_value = ''
                image_source_path_input.setText('')
                image_url_input.setText('')
                cover_url_input.setText('')
                large_image_input.setText('')
                update_preview()
                self.update_status(f'{exe_name}: image cleared.')

        def update_image_mode_visibility():
            is_manual = manual_image_check.isChecked()
            image_source_path_label.setText('Local Image Path:' if is_manual else 'VNDB URL Image:')
            image_url_label.setVisible(is_manual)
            image_url_input.setVisible(is_manual)
            for btn in [use_exe_icon_btn, upload_image_btn, update_image_btn, upload_btn]:
                btn.setVisible(is_manual)
            choose_vndb_cover_btn.setVisible(not is_manual)
            note_h = 0
            if explicit_rpc_note.isVisible():
                explicit_rpc_note.setWidth(430)
                note_h = explicit_rpc_note.sizeHint().height() + 8
            image_edit_dialog.setFixedSize(462, (229 if is_manual else 172) + note_h)
            update_refresh_button_state()

        def update_explicit_rpc_note():
            show = False
            if default_image_check.isChecked():
                cover = (default_source_value or '').strip()
                if cover and self.rpc_core.settings.get('replace_rpc_explicit', True) and self.rpc_core.is_vndb_cover_url(cover):
                    vndb_url = vndb_url_input.text().strip()
                    known_explicit = None
                    if vndb_url:
                        info = self.rpc_core.library_cache.get(vndb_url)
                        if isinstance(info, dict) and info.get('cover_explicit') is not None:
                            known_explicit = bool(info.get('cover_explicit'))
                    show = known_explicit if known_explicit is not None else self.rpc_core.is_image_explicit(cover)
            explicit_rpc_note.setVisible(show)
            if show:
                explicit_rpc_note.setText('This cover is marked <b>explicit</b> on VNDB. Your Discord Rich Presence will use the <b>VNDB logo</b> instead of this cover, because "Blur explicit covers in RPC" is enabled.')
            update_image_mode_visibility()

        def on_default_image_check(checked):
            nonlocal image_settings_dirty
            image_settings_dirty = True
            if checked:
                if manual_image_check.isChecked():
                    manual_image_check.blockSignals(True)
                    manual_image_check.setChecked(False)
                    manual_image_check.blockSignals(False)
                image_source_path_input.setText(default_source_value)
                if not default_source_value.startswith(('http://', 'https://')):
                    fetch_vndb_cover_url(stage=False)
            update_explicit_rpc_note()

        def on_manual_image_check(checked):
            nonlocal image_settings_dirty
            image_settings_dirty = True
            if checked:
                if default_image_check.isChecked():
                    default_image_check.blockSignals(True)
                    default_image_check.setChecked(False)
                    default_image_check.blockSignals(False)
                host = (self.rpc_core.settings.get('image_host', 'none') or 'none').strip().lower()
                host_requirements = {'imgbb': ('imgbb_api_key', 'ImgBB API key', 'imgbb.com (login -> account -> API)'), 'postimages': ('postimages_api_key', 'PostImages API key', 'postimages.org (login -> API tab)'), 'imgbs': ('imgbs_cookie', 'IMG.BS cookie', 'imgbs.com (log in, then copy the session cookie)'), 'freeimage': ('freeimage_api_key', 'FreeImage API key', 'freeimage.host/api/')}
                req = host_requirements.get(host)
                if req:
                    setting_key, label, source = req
                    if not (self.rpc_core.settings.get(setting_key, '') or '').strip():
                        QMessageBox.information(image_edit_dialog, f'{label} Required', f'Manual image mode uploads via {host}, but no {label.lower()} is set.\nGet one at {source} and add it in Settings > API Settings.')
                image_source_path_input.setText(manual_source_value)
                manual_url = manual_url_value
                if manual_url == default_source_value:
                    manual_url = ''
                image_url_input.setText(manual_url)
            update_explicit_rpc_note()
        default_image_check.toggled.connect(on_default_image_check)
        manual_image_check.toggled.connect(on_manual_image_check)

        def update_image():
            source_path = manual_source_value
            if not source_path or not os.path.exists(source_path):
                return
            do_image_upload(source_path, 'updated image')
        use_exe_icon_btn.clicked.connect(use_exe_icon)
        upload_image_btn.clicked.connect(upload_image)
        update_image_btn.clicked.connect(update_image)
        upload_btn.clicked.connect(on_upload_click)
        choose_vndb_cover_btn.clicked.connect(choose_vndb_cover)
        layout.addWidget(QLabel('<center><b>Details and State Configuration:</b></center>'))
        mode_group = QButtonGroup(dialog)
        vndb_radio = QRadioButton('Default')
        custom_radio = QRadioButton('Custom')
        manual_radio = QRadioButton('Manual')
        saved_mode = existing_config.get('details_mode')
        has_vndb_url = bool((existing_config.get('vndb_url') or '').strip())
        if saved_mode == 'vndb' or (not saved_mode and has_vndb_url):
            vndb_radio.setChecked(True)
        elif saved_mode == 'custom':
            custom_radio.setChecked(True)
        else:
            manual_radio.setChecked(True)
        mode_group.addButton(vndb_radio)
        mode_group.addButton(custom_radio)
        mode_group.addButton(manual_radio)
        layout.addWidget(vndb_radio)
        layout.addWidget(manual_radio)
        layout.addWidget(custom_radio)
        manual_fields = QWidget()
        m_layout = QVBoxLayout(manual_fields)
        m_details = QLineEdit(existing_config.get('details', '   '))
        m_details.setPlaceholderText("Discord 'details' line, e.g. My Visual Novel")
        m_state = QLineEdit(existing_config.get('state', '   '))
        m_state.setPlaceholderText("Discord 'state' line, e.g. Reading chapter 3")
        m_layout.addWidget(QLabel('Details:'))
        m_layout.addWidget(m_details)
        m_layout.addWidget(QLabel('State:'))
        m_layout.addWidget(m_state)
        vndb_fields = QWidget()
        v_layout = QVBoxLayout(vndb_fields)
        swap_checkbox = QCheckBox('Swap Details and State')
        swap_checkbox.setChecked(existing_config.get('vndb_swap_details_state', False))
        v_layout.addWidget(swap_checkbox)

        vndb_state_template = QLineEdit(existing_config.get('vndb_state_template') or DEFAULT_VNDB_STATE_TEMPLATE)
        vndb_state_template.setPlaceholderText(DEFAULT_VNDB_STATE_TEMPLATE)
        vndb_details_cycle_seconds = QLineEdit(str(existing_config.get('vndb_details_cycle_seconds', 5)))
        vndb_details_cycle_seconds.setPlaceholderText('5')
        vndb_details_cycle_items = _CodeEditor()
        vndb_details_cycle_items.setPlaceholderText('One template per line')
        vndb_details_cycle_items.setPlainText(CUSTOM_HELPER_CYCLE_ITEMS + '\n' + '\n'.join(existing_config.get('vndb_details_cycle_items') or DEFAULT_VNDB_DETAILS_ITEMS))
        vndb_details_cycle_items.setFixedHeight(90)
        custom_fields = QWidget()
        c_layout = QVBoxLayout(custom_fields)
        help_label = QLabel('Variables (click one to insert it at the cursor of the field you were last editing. Click + to create a custom Python variable):')
        help_label.setStyleSheet('color: gray; font-style: italic;')
        help_label.setWordWrap(True)
        c_layout.addWidget(help_label)
        var_values = {}

        class _VarButton(QPushButton):
            hovered = pyqtSignal(object)
            unhovered = pyqtSignal(object)

            def minimumSizeHint(self):
                return QSize(20, 22)

            def enterEvent(self, event):
                try:
                    self.hovered.emit(self)
                except Exception:
                    pass
                super().enterEvent(event)

            def leaveEvent(self, event):
                try:
                    self.unhovered.emit(self)
                except Exception:
                    pass
                super().leaveEvent(event)

        class _VarValuePopup(QLabel):

            def __init__(self, parent):
                super().__init__(parent)
                self.setObjectName('varValuePopup')
                self.setStyleSheet('QLabel#varValuePopup { background-color: #1e1f22; color: #f2f3f5; border: 1px solid #57606a; border-radius: 6px; padding: 6px 10px; font-size: 12px;}')
                self.setWordWrap(True)
                self.setMaximumWidth(320)
                self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
                self._target = None
                self._var = ''
                self._pending = None
                self._watchdog = QTimer(self)
                self._watchdog.setInterval(100)
                self._watchdog.timeout.connect(self._watchdog_tick)
                self.hide()

            def _watchdog_tick(self):
                target = self._target
                if target is None:
                    self._watchdog.stop()
                    return
                try:
                    if not self.isVisible() or not target.isVisible() or (not target.isEnabled()):
                        self._watchdog.stop()
                        self._target = None
                        return
                    pos = QCursor.pos()
                    over_target = target.rect().contains(target.mapFromGlobal(pos))
                    over_popup = self.rect().contains(self.mapFromGlobal(pos))
                    if not (over_target or over_popup):
                        self._target = None
                        self.hide()
                except Exception:
                    self._watchdog.stop()
                    self._target = None
                    try:
                        self.hide()
                    except Exception:
                        pass

            def show_for(self, button, var_name, value):
                self._pending = (button, var_name, value)
                try:
                    QTimer.singleShot(0, self._flush_pending)
                except Exception:
                    pass

            def _flush_pending(self):
                pending = self._pending
                self._pending = None
                if pending is None:
                    return
                button, var_name, value = pending
                try:
                    if not button.isVisible():
                        return
                    self._target = button
                    self._var = var_name
                    self._set_text(value)
                    self._reposition()
                    self.show()
                    self.raise_()
                    if not self._watchdog.isActive():
                        self._watchdog.start()
                except Exception:
                    self._target = None
                    try:
                        self.hide()
                    except Exception:
                        pass

            def refresh(self, button, value):
                if self._pending is not None and self._pending[0] is button:
                    self._pending = (button, self._pending[1], value)
                    return
                if self._target is button:
                    try:
                        self._set_text(value)
                        self._reposition()
                    except Exception:
                        pass

            def hide_for(self, button):
                if self._pending is not None and self._pending[0] is button:
                    self._pending = None
                if self._target is button:
                    self._target = None
                    try:
                        self.hide()
                    except Exception:
                        pass
                    self._watchdog.stop()

            def _set_text(self, value):
                value = str(value if value is not None else '')
                shown = value if value.strip() else '(empty)'
                shown = shown.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                self.setText(f'<span style="color:#9aa0a6;">{{{self._var}}}</span><br><span style="color:#f2f3f5; font-weight:600;">{shown}</span>')

            def _reposition(self):
                if self._target is None:
                    return
                self.adjustSize()
                pos = self._target.mapTo(self.parent(), self._target.rect().bottomLeft())
                x = pos.x()
                limit = self.parent().width() - self.width() - 8
                if x > limit:
                    x = max(8, limit)
                self.move(x, pos.y() + 6)
        var_value_popup = _VarValuePopup(dialog)
        var_buttons = []
        custom_var_buttons = []
        _var_rows_state = {'sig': None}
        var_row_widget = QWidget()
        var_row_layout = QVBoxLayout(var_row_widget)
        var_row_layout.setSpacing(3)
        var_row_layout.setContentsMargins(0, 0, 0, 0)

        def _clear_var_rows():
            while var_row_layout.count():
                item = var_row_layout.takeAt(0)
                w = item.widget()
                if w is not None:
                    w.deleteLater()
                else:
                    sub = item.layout()
                    if sub is not None:
                        while sub.count():
                            sub_item = sub.takeAt(0)
                            sub_w = sub_item.widget()
                            if sub_w is not None:
                                sub_w.deleteLater()
                        sub.deleteLater()
            var_buttons.clear()
            custom_var_buttons.clear()

        def _rebuild_var_rows():
            _clear_var_rows()
            all_names = list(CUSTOM_VARIABLES)
            for i in range(0, len(CUSTOM_VARIABLES), 4):
                var_row = QHBoxLayout()
                var_row.setSpacing(4)
                for name in CUSTOM_VARIABLES[i:i + 4]:
                    btn = _VarButton(f'{{{name}}}')
                    btn.setFixedHeight(22)
                    btn.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
                    btn.setStyleSheet('font-size: 11px; padding: 0px 4px;')
                    btn.clicked.connect(lambda _checked=False, n=name: insert_variable(n))
                    btn.hovered.connect(lambda b, n=name: var_value_popup.show_for(b, n, var_values.get(n, '')))
                    btn.unhovered.connect(var_value_popup.hide_for)
                    var_buttons.append(btn)
                    var_row.addWidget(btn)
                var_row.addStretch(1)
                var_row_layout.addLayout(var_row)
            try:
                entries = self.rpc_core.custom_python_entries()
            except Exception:
                entries = []
            if entries:
                var_row = QHBoxLayout()
                var_row.setSpacing(4)
                for path, name in entries:
                    btn = _VarButton(f'{{{name}}}' if name else 'Custom Python Processing')
                    btn.setFixedHeight(22)
                    btn.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
                    btn.setMaximumWidth(100)
                    btn.setStyleSheet('font-size: 11px; padding: 0px 4px; color: #7ec67e;')
                    btn.setToolTip(f'Custom Python Processing\n{path}\n\nClick: insert variable\nRight click: script options')
                    btn.clicked.connect(lambda _checked=False, n=name: insert_variable(n))
                    btn.hovered.connect(lambda b, n=name: var_value_popup.show_for(b, n, var_values.get(n, '')))
                    btn.unhovered.connect(var_value_popup.hide_for)
                    btn.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
                    btn.customContextMenuRequested.connect(lambda pos, b=btn, p=path: _on_custom_var_menu(pos, b, p))
                    var_buttons.append(btn)
                    custom_var_buttons.append(btn)
                    if name and name not in all_names:
                        all_names.append(name)
                    var_row.addWidget(btn)
                var_row.addStretch(1)
                var_row_layout.addLayout(var_row)
            plus_row = QHBoxLayout()
            plus_row.setSpacing(4)
            plus_btn = _VarButton('+')
            plus_btn.setFixedHeight(22)
            plus_btn.setFixedWidth(28)
            plus_btn.setStyleSheet('font-size: 13px; font-weight: bold; padding: 0px 4px;')
            plus_btn.setToolTip('Create a new custom variable\n\nA .py script is created in the Custom folder and opened in your editor.\nEverything the script prints becomes the value of the new variable.')
            plus_btn.clicked.connect(_on_add_custom_var)
            plus_row.addWidget(plus_btn)
            plus_row.addStretch(1)
            var_row_layout.addLayout(plus_row)
            try:
                _var_rows_state['sig'] = self.rpc_core.custom_scripts_signature()
            except Exception:
                _var_rows_state['sig'] = None
            try:
                editors = custom_template_widgets
            except NameError:
                editors = []
            for ed in editors:
                ed.set_known_variables(all_names)
            var_row_layout.invalidate()
            var_row_layout.activate()

        c_layout.addWidget(var_row_widget)
        custom_vndb_url_hint = QLabel("<b>VNDB URL required:</b> 'Default' mode and Custom variables are disabled until a VNDB entry is selected. Without a VNDB URL, this game will run with blank (space) details and state.")
        custom_vndb_url_hint.setWordWrap(True)
        custom_vndb_url_hint.setStyleSheet('color: #e0b341; font-style: italic;')
        c_layout.addWidget(custom_vndb_url_hint)
        custom_details_template = _CodeEditor()
        custom_details_template.setPlaceholderText('e.g. {vndb_status}')
        custom_details_template.setPlainText(CUSTOM_HELPER_DETAILS + '\n' + str(existing_config.get('custom_details_template', '{vndb_status}')))
        custom_details_template.setFixedHeight(48)
        custom_state_template = _CodeEditor()
        custom_state_template.setPlaceholderText(DEFAULT_VNDB_STATE_TEMPLATE)
        custom_state_template.setPlainText(CUSTOM_HELPER_STATE + '\n' + str(existing_config.get('custom_state_template', DEFAULT_VNDB_STATE_TEMPLATE)))
        custom_state_template.setFixedHeight(48)
        custom_details_template_label = QLabel('Details:')
        c_layout.addWidget(custom_details_template_label)
        custom_details_cycle_mode_group = QButtonGroup(dialog)
        custom_details_template_radio = QRadioButton('Manual Custom Details')
        custom_details_cycle_radio = QRadioButton('Use Details Cycle')
        custom_details_cycle_mode_group.addButton(custom_details_template_radio)
        custom_details_cycle_mode_group.addButton(custom_details_cycle_radio)
        if existing_config.get('custom_details_cycle_enabled', True):
            custom_details_cycle_radio.setChecked(True)
        else:
            custom_details_template_radio.setChecked(True)
        details_cycle_radio_layout = QHBoxLayout()
        details_cycle_radio_layout.addWidget(custom_details_template_radio)
        details_cycle_radio_layout.addWidget(custom_details_cycle_radio)
        c_layout.addLayout(details_cycle_radio_layout)
        c_layout.addWidget(custom_details_template)
        custom_details_live_label = QLabel()
        custom_details_live_label.setWordWrap(True)
        custom_details_live_label.setStyleSheet('color: #7ec67e; font-size: 11px;')
        c_layout.addWidget(custom_details_live_label)
        custom_details_cycle_seconds = QLineEdit(str(max(5, int(existing_config.get('custom_details_cycle_seconds', 5) or 5))))
        custom_details_cycle_seconds.setPlaceholderText('5')
        custom_details_cycle_seconds_label = QLabel('Details cycle every seconds (minimum 5):')
        c_layout.addWidget(custom_details_cycle_seconds_label)
        c_layout.addWidget(custom_details_cycle_seconds)
        custom_details_cycle_items = _CodeEditor()
        custom_details_cycle_items.setPlaceholderText('One item per line, e.g. {vndb_status}')
        custom_details_cycle_items.setPlainText(CUSTOM_HELPER_CYCLE_ITEMS + '\n' + '\n'.join(existing_config.get('custom_details_cycle_items', DEFAULT_VNDB_DETAILS_ITEMS)))
        custom_details_cycle_items.setFixedHeight(110)
        custom_details_cycle_items_label = QLabel('Details Cycle Items, one per line:')
        c_layout.addWidget(custom_details_cycle_items_label)
        c_layout.addWidget(custom_details_cycle_items)
        custom_state_template_label = QLabel('State:')
        c_layout.addWidget(custom_state_template_label)
        custom_state_cycle_mode_group = QButtonGroup(dialog)
        custom_state_template_radio = QRadioButton('Manual Custom State')
        custom_state_cycle_radio = QRadioButton('Use State Cycle')
        custom_state_cycle_mode_group.addButton(custom_state_template_radio)
        custom_state_cycle_mode_group.addButton(custom_state_cycle_radio)
        if existing_config.get('custom_state_cycle_enabled', False):
            custom_state_cycle_radio.setChecked(True)
        else:
            custom_state_template_radio.setChecked(True)
        state_cycle_radio_layout = QHBoxLayout()
        state_cycle_radio_layout.addWidget(custom_state_template_radio)
        state_cycle_radio_layout.addWidget(custom_state_cycle_radio)
        c_layout.addLayout(state_cycle_radio_layout)
        c_layout.addWidget(custom_state_template)
        custom_state_live_label = QLabel()
        custom_state_live_label.setWordWrap(True)
        custom_state_live_label.setStyleSheet('color: #7ec67e; font-size: 11px;')
        c_layout.addWidget(custom_state_live_label)
        custom_state_cycle_seconds = QLineEdit(str(max(5, int(existing_config.get('custom_state_cycle_seconds', 5) or 5))))
        custom_state_cycle_seconds.setPlaceholderText('5')
        custom_state_cycle_seconds_label = QLabel('State cycle every seconds (minimum 5):')
        c_layout.addWidget(custom_state_cycle_seconds_label)
        c_layout.addWidget(custom_state_cycle_seconds)
        custom_state_cycle_items = _CodeEditor()
        custom_state_cycle_items.setPlaceholderText('One item per line, e.g. ★ {vndb_rating}/10 · {vndb_year} · {vndb_length}')
        custom_state_cycle_items.setPlainText(CUSTOM_HELPER_CYCLE_ITEMS + '\n' + '\n'.join(existing_config.get('custom_state_cycle_items', [DEFAULT_VNDB_STATE_TEMPLATE])))
        custom_state_cycle_items.setFixedHeight(110)
        custom_state_cycle_items_label = QLabel('State Cycle Items, one per line:')
        c_layout.addWidget(custom_state_cycle_items_label)
        c_layout.addWidget(custom_state_cycle_items)
        custom_template_widgets = [custom_details_template, custom_state_template, custom_details_cycle_items, custom_state_cycle_items]
        last_custom_focus = {'widget': None}

        class _CustomFocusTracker(QObject):

            def __init__(self, parent=None):
                super().__init__(parent)

            def eventFilter(self, obj, event):
                if event.type() == QEvent.Type.FocusIn and obj in custom_template_widgets:
                    last_custom_focus['widget'] = obj
                return False
        _custom_focus_tracker = _CustomFocusTracker(dialog)
        for _w in custom_template_widgets:
            _w.installEventFilter(_custom_focus_tracker)

        def _on_add_custom_var():
            try:
                path = self.rpc_core.create_custom_script()
            except Exception as e:
                QMessageBox.warning(dialog, 'Custom Variable Failed', str(e))
                return
            self.update_status(f'Created custom variable script: {path}')
            _rebuild_var_rows()
            try:
                os.startfile(path)
            except Exception as e:
                QMessageBox.information(dialog, 'Custom Variable', f'Script created:\n{path}\n\nCould not open it automatically: {e}')

        def _open_custom_script_file(path):
            try:
                os.startfile(path)
            except Exception as e:
                QMessageBox.warning(dialog, 'Custom Variable Failed', f'Could not open the script:\n{e}')

        def _on_rename_custom_var(path):
            try:
                current = self.rpc_core._read_custom_script_name(path)
            except Exception:
                current = ''
            new_name, ok = QInputDialog.getText(dialog, 'Rename Variable', 'New variable name:', QLineEdit.EchoMode.Normal, current)
            if not ok:
                return
            try:
                renamed = self.rpc_core.rename_custom_script(path, new_name.strip())
            except Exception as e:
                QMessageBox.warning(dialog, 'Rename Variable Failed', str(e))
                return
            _rebuild_var_rows()
            self.update_status(f'Custom variable renamed to {{{renamed}}}.')

        def _on_delete_custom_var(path):
            try:
                name = self.rpc_core._read_custom_script_name(path)
            except Exception:
                name = ''
            reply = QMessageBox.question(dialog, 'Delete Variable', f"Delete custom variable '{{{name}}}'?\nThis removes the script file:\n{path}", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
            if reply != QMessageBox.StandardButton.Yes:
                return
            try:
                self.rpc_core.delete_custom_script(path)
            except Exception as e:
                QMessageBox.warning(dialog, 'Delete Variable Failed', str(e))
                return
            _rebuild_var_rows()
            self.update_status(f'Deleted custom variable {{{name}}}.')

        def _on_custom_var_menu(pos, btn, path):
            menu = QMenu(self)
            menu.addAction('Open script in editor', lambda: _open_custom_script_file(path))
            menu.addAction('Refresh value now', lambda: self.rpc_core.refresh_custom_python_variables(force=True))
            menu.addSeparator()
            menu.addAction('Rename variable...', lambda: _on_rename_custom_var(path))
            menu.addAction('Delete variable', lambda: _on_delete_custom_var(path))
            try:
                menu.exec(btn.mapToGlobal(pos))
            except Exception:
                pass

        _rebuild_var_rows()

        def insert_variable(name):
            token = f'{{{name}}}'
            widget = last_custom_focus['widget']
            if widget is None or not widget.isVisible() or (not widget.isEnabled()):
                widget = custom_details_template
            if isinstance(widget, QLineEdit):
                widget.insert(token)
            else:
                cursor = widget.textCursor()
                cursor.insertText(token)
                widget.setTextCursor(cursor)
            widget.setFocus()
            update_preview()

        def make_transform_editor(title, transform, use_code_editor=False):
            box = QWidget()
            box_layout = QVBoxLayout(box)
            box_layout.addWidget(QLabel(f'<b>{title} Text Transform</b>'))
            transform = transform or {}
            remove_lines = '\n'.join(transform.get('remove', []) or [])
            replace_lines = '\n'.join((f'{k}={v}' for k, v in (transform.get('replace', {}) or {}).items()))
            if use_code_editor:
                prefix = _CodeEditor()
                prefix.setPlaceholderText('Text added before the processed text')
                prefix.setPlainText(CUSTOM_HELPER_PREFIX + '\n' + str(transform.get('prefix', '')))
                prefix.setFixedHeight(48)
                suffix = _CodeEditor()
                suffix.setPlaceholderText('Text added after the processed text')
                suffix.setPlainText(CUSTOM_HELPER_SUFFIX + '\n' + str(transform.get('suffix', '')))
                suffix.setFixedHeight(48)
                remove = _CodeEditor()
                remove.setPlaceholderText('One substring per line to delete')
                remove.setPlainText(CUSTOM_HELPER_REMOVE + '\n' + remove_lines)
                remove.setFixedHeight(80)
                replace = _CodeEditor()
                replace.setPlaceholderText('One rule per line: old=new')
                replace.setPlainText(CUSTOM_HELPER_REPLACE + '\n' + replace_lines)
                replace.setFixedHeight(90)
            else:
                prefix = QLineEdit(str(transform.get('prefix', '')))
                prefix.setPlaceholderText('Text added before the processed text')
                suffix = QLineEdit(str(transform.get('suffix', '')))
                suffix.setPlaceholderText('Text added after the processed text')
                remove = QTextEdit()
                remove.setPlaceholderText('One substring per line to delete')
                remove.setPlainText(remove_lines)
                remove.setFixedHeight(70)
                replace = QTextEdit()
                replace.setPlaceholderText('One rule per line: old=new')
                replace.setPlainText(replace_lines)
                replace.setFixedHeight(80)
            trim = QCheckBox('Trim spaces after processing')
            trim.setChecked(bool(transform.get('trim', True)))
            box_layout.addWidget(QLabel('Prefix:'))
            box_layout.addWidget(prefix)
            box_layout.addWidget(QLabel('Suffix:'))
            box_layout.addWidget(suffix)
            box_layout.addWidget(QLabel('Remove text, one item per line:'))
            box_layout.addWidget(remove)
            box_layout.addWidget(QLabel('Replace text, one rule per line: old=new'))
            box_layout.addWidget(replace)
            box_layout.addWidget(trim)
            return (box, prefix, suffix, remove, replace, trim)
        details_transform = existing_config.get('custom_details_transform', {})
        state_transform = existing_config.get('custom_state_transform', {})
        custom_details_transform_widget, custom_details_prefix, custom_details_suffix, custom_details_remove, custom_details_replace, custom_details_trim = make_transform_editor('Details', details_transform, use_code_editor=True)
        custom_state_transform_widget, custom_state_prefix, custom_state_suffix, custom_state_remove, custom_state_replace, custom_state_trim = make_transform_editor('State', state_transform, use_code_editor=True)
        c_layout.addWidget(custom_details_transform_widget)
        c_layout.addWidget(custom_state_transform_widget)
        vndb_details_transform_widget, vndb_details_prefix, vndb_details_suffix, vndb_details_remove, vndb_details_replace, vndb_details_trim = make_transform_editor('VNDB Details', existing_config.get('vndb_details_transform', {}))
        vndb_state_transform_widget, vndb_state_prefix, vndb_state_suffix, vndb_state_remove, vndb_state_replace, vndb_state_trim = make_transform_editor('VNDB State', existing_config.get('vndb_state_transform', {}))
        layout.addWidget(custom_fields)
        layout.addWidget(manual_fields)
        layout.addWidget(vndb_fields)

        def preview_first_line(text):
            lines = [line.strip() for line in str(text or '').splitlines() if line.strip()]
            return lines[0] if lines else ''
        window_title_cache = {'value': '', 'at': 0.0}

        def preview_active_window_title():
            now = time.time()
            if now - window_title_cache['at'] < 1.0:
                return window_title_cache['value']
            exact_exe_path = exe_path_input.text().strip() or ''
            normalized_exact_path = None
            if exact_exe_path:
                try:
                    normalized_exact_path = os.path.normcase(os.path.abspath(exact_exe_path))
                except Exception:
                    normalized_exact_path = os.path.normcase(exact_exe_path)
            process_name = existing_config.get('exe_name') or exe_name
            target_pid = None
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if proc.info.get('name') != process_name:
                        continue
                    if normalized_exact_path:
                        try:
                            proc_path = proc.exe()
                        except Exception:
                            continue
                        try:
                            normalized_proc_path = os.path.normcase(os.path.abspath(proc_path))
                        except Exception:
                            normalized_proc_path = os.path.normcase(proc_path)
                        if normalized_proc_path != normalized_exact_path:
                            continue
                    target_pid = proc.info.get('pid')
                    break
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
            result = ''
            if target_pid:
                titles = []

                def callback(hwnd, _):
                    if win32gui.IsWindowVisible(hwnd) and win32gui.IsWindowEnabled(hwnd):
                        _, found_pid = win32process.GetWindowThreadProcessId(hwnd)
                        if found_pid == target_pid:
                            title = win32gui.GetWindowText(hwnd)
                            if title:
                                titles.append(title)
                try:
                    win32gui.EnumWindows(callback, None)
                except Exception:
                    titles = []
                result = titles[0] if titles else ''
            window_title_cache['value'] = result
            window_title_cache['at'] = now
            return result

        def preview_elapsed():
            start = self.rpc_core.start_times.get(exe_name)
            if not start:
                return '0:00'
            seconds = max(0, int(time.time() - start))
            return f'{seconds // 60}:{seconds % 60:02d}'

        def preview_context():
            vn_name = vn_name_input.text().strip() or exe_name
            activity_name = activity_name_input.text().strip() or vn_name
            vndb_rating = ''
            vndb_developer = ''
            vndb_status = ''
            vndb_length = ''
            vndb_released = ''
            vndb_url = vndb_url_input.text().strip()
            if vndb_url:
                self.ensure_vndb_prefetch(vndb_url)
                vndb_data = self.rpc_core.fetch_vndb_info(vndb_url, cache_only=True)
                if vndb_data:
                    vndb_rating = str(vndb_data.get('rating', '') or '')
                    vndb_developer = str(vndb_data.get('developer', '') or '')
                    vndb_status = str(vndb_data.get('user_status', '') or '')
                    vndb_length = vndb_data.get('length') or ''
                    vndb_released = str(vndb_data.get('released') or '')
            if vndb_status == 'Playing':
                vndb_status = 'Reading'
            if not vndb_status:
                vndb_status = 'Reading'
            if vndb_released[:4].isdigit():
                vndb_year = vndb_released[:4]
            else:
                vndb_year = ''
            try:
                vndb_length = self.rpc_core.VNDB_LENGTH_LABELS.get(int(vndb_length), '')
            except (TypeError, ValueError):
                vndb_length = ''
            context = {'vn_name': vn_name, 'activity_name': activity_name, 'window_title': preview_active_window_title(), 'exe_name': current_exe_name(), 'game_key': exe_name, 'large_text': large_text_input.text().strip() or vn_name, 'vndb_url': vndb_url, 'vndb_rating': vndb_rating, 'vndb_developer': vndb_developer, 'vndb_status': vndb_status, 'vndb_length': vndb_length, 'vndb_year': vndb_year, 'vndb_released': vndb_released, 'elapsed_time': preview_elapsed(), 'date': time.strftime('%Y-%m-%d'), 'time': time.strftime('%H:%M')}
            try:
                for key, value in self.rpc_core.get_custom_python_context().items():
                    context.setdefault(key, value)
            except Exception:
                pass
            return context

        def preview_render_template(template, context):
            text = str(template or '')

            def repl(match):
                key = match.group(1).strip()
                return str(context.get(key, match.group(0)))
            return re.sub('\\{([A-Za-z0-9_]+)\\}', repl, text)

        def _single_line_value(widget):
            if hasattr(widget, 'toPlainText'):
                for line in widget.toPlainText().splitlines():
                    line = line.strip()
                    if line and not line.startswith('#'):
                        return line
                return ''
            return widget.text().strip()

        def preview_apply_transform(text, prefix_widget, suffix_widget, remove_widget, replace_widget, trim_widget):
            text = str(text or '')
            for sub in self.parse_multiline_list(remove_widget.toPlainText()):
                text = text.replace(sub, '')
            for old, new in self.parse_replace_lines(replace_widget.toPlainText()).items():
                text = text.replace(old, new)
            text = f'{_single_line_value(prefix_widget)}{text}{_single_line_value(suffix_widget)}'
            if trim_widget.isChecked():
                text = text.strip()
            return text

        def preview_cycle_seconds(line_edit):
            try:
                return max(5, int(line_edit.text().strip() or '5'))
            except Exception:
                return 5

        def preview_cycle_item(text_edit, fallback, seconds_line_edit):
            lines = self.parse_multiline_list(text_edit.toPlainText())
            if not lines:
                lines = [fallback]
            if not lines:
                return ''
            seconds = preview_cycle_seconds(seconds_line_edit)
            index = int(time.time() // seconds) % len(lines)
            return lines[index]
        preview_image_inflight = set()
        preview_image_loading = {'url': None}

        def draw_loading_spinner(angle):
            pm = QPixmap(64, 64)
            pm.fill(QColor('#1e1f22'))
            painter = QPainter(pm)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            rect = QRect(20, 20, 24, 24)
            segments = 18
            total_span = 270
            seg_deg = total_span / segments
            for i in range(segments):
                frac = i / segments
                val = int(255 - (255 - 90) * frac)
                start = (angle - seg_deg * i) * 16
                span = -int(round((seg_deg + 1) * 16))
                painter.setPen(QPen(QColor(val, val, val), 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap))
                painter.drawArc(rect, int(start), span)
            painter.end()
            return pm
        spinner_state = {'angle': 0}
        preview_spinner_timer = QTimer(dialog)
        preview_spinner_timer.setInterval(16)

        def _tick_preview_spinner():
            spinner_state['angle'] = (spinner_state['angle'] + 5) % 360
            set_preview_base_pixmap(draw_loading_spinner(spinner_state['angle']))
        preview_spinner_timer.timeout.connect(_tick_preview_spinner)

        def start_preview_image_loading(url):
            if preview_image_loading['url'] == url:
                return
            preview_image_loading['url'] = url
            spinner_state['angle'] = 0
            set_preview_base_pixmap(draw_loading_spinner(0))
            preview_spinner_timer.start()

        def stop_preview_image_loading(url=None):
            if url is not None and preview_image_loading['url'] != url:
                return
            preview_image_loading['url'] = None
            preview_spinner_timer.stop()

        def preview_cover_explicit(vndb_url, fetch_if_unknown=False):
            vndb_url = (vndb_url or '').strip()
            if not vndb_url:
                return False
            info = self.rpc_core.library_cache.get(vndb_url)
            if isinstance(info, dict) and info.get('cover_explicit') is not None:
                return bool(info.get('cover_explicit'))
            if fetch_if_unknown:
                try:
                    self.rpc_core.fetch_vn_cover_rating(vndb_url)
                except Exception:
                    pass
                info = self.rpc_core.library_cache.get(vndb_url)
                if isinstance(info, dict) and info.get('cover_explicit') is not None:
                    return bool(info.get('cover_explicit'))
            return False

        preview_vndb_url_state = vndb_url_input.text().strip()

        def preview_refresh_vndb_url():
            nonlocal preview_vndb_url_state
            preview_vndb_url_state = vndb_url_input.text().strip()

        def preview_current_explicit():
            if not preview_vndb_url_state:
                return False
            return preview_cover_explicit(preview_vndb_url_state)

        def preview_cover_should_blur(url):
            if not self.rpc_core.is_vndb_cover_url(url):
                return False
            if not self.rpc_core.get_setting('pixel_explicit', True):
                return False
            return preview_current_explicit()

        def fetch_preview_image(url):
            vndb_url_now = preview_vndb_url_state

            def task():
                resp = _vndb_session.get(url, timeout=10)
                if resp.status_code != 200:
                    raise RuntimeError(f'HTTP {resp.status_code}')
                data = resp.content
                if self.rpc_core.is_vndb_cover_url(url):
                    preview_cover_explicit(vndb_url_now, fetch_if_unknown=True)
                return {'data': data}

            def _note_preview_failure():
                preview_image_failures[url] = preview_image_failures.get(url, 0) + 1
                preview_next_retry[url] = time.time() + min(10.0, 2.0 * preview_image_failures[url])
                preview_image_cache.pop(url, None)
                preview_image_inflight.discard(url)

            def on_success(result):
                pm = None
                if result.get('data'):
                    pm = QPixmap()
                    if not pm.loadFromData(result['data']):
                        pm = None
                if pm is None:
                    _note_preview_failure()
                else:
                    preview_image_failures.pop(url, None)
                    preview_next_retry.pop(url, None)
                    preview_image_cache[url] = pm
                if dialog.isVisible():
                    stop_preview_image_loading(url)
                    update_preview()

            def on_error(message):
                _note_preview_failure()
                if dialog.isVisible():
                    stop_preview_image_loading(url)
                    update_preview()
            run_async_task(task, on_success, on_error)

        def update_preview():
            try:
                sig = self.rpc_core.custom_scripts_signature()
            except Exception:
                sig = None
            if sig != _var_rows_state['sig']:
                _var_rows_state['sig'] = sig
                _rebuild_var_rows()
            context = preview_context()
            title = context['activity_name'] or context['vn_name'] or exe_name
            if manual_radio.isChecked():
                details_preview = m_details.text().strip()
                state_preview = m_state.text().strip()
            elif vndb_radio.isChecked():
                vndb_preview_lines = self.parse_multiline_list(vndb_details_cycle_items.toPlainText())
                if not vndb_preview_lines:
                    vndb_preview_lines = list(DEFAULT_VNDB_DETAILS_ITEMS)
                vndb_seconds = preview_cycle_seconds(vndb_details_cycle_seconds)
                details_preview = preview_render_template(vndb_preview_lines[int(time.time() // vndb_seconds) % len(vndb_preview_lines)], context)
                state_preview = preview_render_template(vndb_state_template.text().strip() or DEFAULT_VNDB_STATE_TEMPLATE, context)
                details_preview = preview_apply_transform(details_preview, vndb_details_prefix, vndb_details_suffix, vndb_details_remove, vndb_details_replace, vndb_details_trim)
                state_preview = preview_apply_transform(state_preview, vndb_state_prefix, vndb_state_suffix, vndb_state_remove, vndb_state_replace, vndb_state_trim)
                if swap_checkbox.isChecked():
                    details_preview, state_preview = (state_preview, details_preview)
            elif not vndb_url_input.text().strip():
                details_preview = '   '
                state_preview = '   '
                custom_details_live_label.setText('(empty)')
                custom_state_live_label.setText('(empty)')
            else:
                details_template_preview = preview_cycle_item(custom_details_cycle_items, 'Rating: {vndb_rating}/10', custom_details_cycle_seconds) if custom_details_cycle_radio.isChecked() else _single_line_value(custom_details_template)
                state_template_preview = preview_cycle_item(custom_state_cycle_items, 'Status: {vndb_status}', custom_state_cycle_seconds) if custom_state_cycle_radio.isChecked() else _single_line_value(custom_state_template)
                details_rendered = preview_render_template(details_template_preview, context)
                state_rendered = preview_render_template(state_template_preview, context)
                custom_details_live_label.setText(details_rendered if details_rendered.strip() else '(empty)')
                custom_state_live_label.setText(state_rendered if state_rendered.strip() else '(empty)')
                details_preview = details_rendered
                state_preview = state_rendered
                details_preview = preview_apply_transform(details_preview, custom_details_prefix, custom_details_suffix, custom_details_remove, custom_details_replace, custom_details_trim)
                state_preview = preview_apply_transform(state_preview, custom_state_prefix, custom_state_suffix, custom_state_remove, custom_state_replace, custom_state_trim)
            for btn in var_buttons:
                try:
                    _name = btn.text().strip('{}')
                    _value = str(context.get(_name, '') or '')
                    var_values[_name] = _value
                    var_value_popup.refresh(btn, _value)
                except Exception:
                    pass
            preview_title_label.setText(preview_first_line(title) or 'VN Title')
            preview_status_label.setText("Playing")
            preview_details_label.blockSignals(True)
            preview_state_label.blockSignals(True)
            details_line = preview_first_line(details_preview)
            state_line = preview_first_line(state_preview)
            if preview_details_label.text() != details_line:
                preview_details_label.setText(details_line)
                preview_details_label.setCursorPosition(0)
            if preview_state_label.text() != state_line:
                preview_state_label.setText(state_line)
                preview_state_label.setCursorPosition(0)
            preview_details_label.setToolTip(details_line)
            preview_state_label.setToolTip(state_line)
            preview_details_label.blockSignals(False)
            preview_state_label.blockSignals(False)
            manual_preview_editable = manual_radio.isChecked()
            preview_details_label.setReadOnly(not manual_preview_editable)
            preview_state_label.setReadOnly(not manual_preview_editable)
            preview_details_label.setCursor(Qt.CursorShape.IBeamCursor if manual_preview_editable else Qt.CursorShape.ArrowCursor)
            preview_state_label.setCursor(Qt.CursorShape.IBeamCursor if manual_preview_editable else Qt.CursorShape.ArrowCursor)
            edit_tip = 'Manual mode: edit this text here or in the Manual fields.'
            preview_details_label.setToolTip((details_line + '\n' + edit_tip).strip() if manual_preview_editable else details_line)
            preview_state_label.setToolTip((state_line + '\n' + edit_tip).strip() if manual_preview_editable else state_line)
            preview_elapsed_label.setText(f"🎮 {context.get('elapsed_time', '0:00')}")
            hover_text = large_text_input.text().strip() or context.get('large_text', '')
            preview_image_label.setToolTip(f'{hover_text}\nClick to edit image' if hover_text else 'Click to edit image')
            if pending_image.get('kind') == 'vndb cover':
                image_path = large_image_input.text().strip()
            else:
                image_path = image_source_path_input.text().strip() or exe_icon_path_input.text().strip() or large_image_input.text().strip()
            display_path = image_path
            if display_path and self.rpc_core.is_vndb_cover_url(display_path):
                if preview_current_explicit() and self.rpc_core.get_setting('replace_rpc_explicit', True):
                    display_path = VNDB_DEFAULT_COVER_URL
            pixmap = QPixmap()
            if display_path:
                if os.path.exists(display_path):
                    pixmap = QPixmap(display_path)
                    stop_preview_image_loading()
                elif display_path.startswith(('http://', 'https://')):
                    if display_path in preview_image_cache:
                        cached = preview_image_cache[display_path]
                        if cached is not None:
                            pixmap = cached
                        stop_preview_image_loading()
                    else:
                        if time.time() >= preview_next_retry.get(display_path, 0):
                            if display_path not in preview_image_inflight:
                                preview_image_inflight.add(display_path)
                                fetch_preview_image(display_path)
                        start_preview_image_loading(display_path)
                        return
            else:
                stop_preview_image_loading()
            if not pixmap.isNull():
                should_blur = (display_path == image_path and preview_cover_should_blur(image_path))
                proc_key = (display_path, should_blur)
                processed = preview_processed_cache.get(proc_key)
                if processed is None or processed.isNull():
                    base_pm = self._blur_pixmap(pixmap, 64, 64) if should_blur else pixmap
                    processed = self._preview_fill_pixmap(base_pm, 64)
                    preview_processed_cache[proc_key] = processed
                pixmap = processed
            set_preview_base_pixmap(QPixmap() if pixmap.isNull() else pixmap)

        def sync_manual_details_from_preview(text):
            if manual_radio.isChecked() and m_details.text() != text:
                m_details.setText(text)

        def sync_manual_state_from_preview(text):
            if manual_radio.isChecked() and m_state.text() != text:
                m_state.setText(text)
        preview_details_label.textEdited.connect(sync_manual_details_from_preview)
        preview_state_label.textEdited.connect(sync_manual_state_from_preview)

        def update_custom_cycle_visibility():
            details_use_cycle = custom_details_cycle_radio.isChecked()
            custom_details_template_label.setVisible(not details_use_cycle)
            custom_details_template.setVisible(not details_use_cycle)
            custom_details_cycle_seconds_label.setVisible(details_use_cycle)
            custom_details_cycle_seconds.setVisible(details_use_cycle)
            custom_details_cycle_items_label.setVisible(details_use_cycle)
            custom_details_cycle_items.setVisible(details_use_cycle)
            state_use_cycle = custom_state_cycle_radio.isChecked()
            custom_state_template_label.setVisible(not state_use_cycle)
            custom_state_template.setVisible(not state_use_cycle)
            custom_state_cycle_seconds_label.setVisible(state_use_cycle)
            custom_state_cycle_seconds.setVisible(state_use_cycle)
            custom_state_cycle_items_label.setVisible(state_use_cycle)
            custom_state_cycle_items.setVisible(state_use_cycle)

        def update_vndb_availability():
            has_vndb_url = bool(vndb_url_input.text().strip())
            vndb_radio.setEnabled(has_vndb_url)
            if not has_vndb_url and vndb_radio.isChecked():
                manual_radio.setChecked(True)
            for widget in (*[b for b in var_buttons if b not in custom_var_buttons], vndb_state_template, vndb_details_cycle_seconds, vndb_details_cycle_items, vndb_details_transform_widget, vndb_state_transform_widget, custom_details_template, custom_details_template_radio, custom_details_cycle_radio, custom_details_cycle_seconds, custom_details_cycle_items, custom_state_template, custom_state_template_radio, custom_state_cycle_radio, custom_state_cycle_seconds, custom_state_cycle_items, custom_details_transform_widget, custom_state_transform_widget):
                widget.setEnabled(has_vndb_url)
            custom_vndb_url_hint.setVisible(not has_vndb_url)

        def sync_content_min_height():
            total = 0
            n_items = 0
            for i in range(layout.count()):
                item = layout.itemAt(i)
                w = item.widget()
                if w is not None:
                    if w.isVisibleTo(content):
                        total += max(w.sizeHint().height(), w.minimumSizeHint().height())
                        n_items += 1
                else:
                    sub = item.layout()
                    if sub is not None:
                        total += sub.sizeHint().height()
                        n_items += 1
            spacing = layout.spacing()
            if spacing < 0:
                spacing = 6
            if n_items > 1:
                total += spacing * (n_items - 1)
            margins = layout.contentsMargins()
            total += margins.top() + margins.bottom()
            content.setMinimumHeight(max(total, 1))

        def update_mode():
            preview_refresh_vndb_url()
            manual_fields.setVisible(manual_radio.isChecked())
            vndb_fields.setVisible(vndb_radio.isChecked())
            custom_fields.setVisible(custom_radio.isChecked())
            sync_content_min_height()
            update_custom_cycle_visibility()
            update_vndb_availability()
            update_preview()
        manual_radio.toggled.connect(update_mode)
        vndb_radio.toggled.connect(update_mode)
        custom_radio.toggled.connect(update_mode)
        custom_details_template_radio.toggled.connect(update_mode)
        custom_details_cycle_radio.toggled.connect(update_mode)
        custom_state_template_radio.toggled.connect(update_mode)
        custom_state_cycle_radio.toggled.connect(update_mode)
        preview_line_edits = [vn_name_input, activity_name_input, match_path_contains_input, exe_path_input, exe_icon_path_input, large_text_input, image_source_path_input, m_details, m_state, vndb_state_template, vndb_details_cycle_seconds, vndb_details_prefix, vndb_details_suffix, vndb_state_prefix, vndb_state_suffix, custom_details_cycle_seconds, custom_state_cycle_seconds]
        for widget in preview_line_edits:
            widget.textChanged.connect(update_preview)
        vndb_url_input.textChanged.connect(update_mode)
        preview_text_edits = [vndb_details_cycle_items, vndb_details_remove, vndb_details_replace, vndb_state_remove, vndb_state_replace, custom_details_cycle_items, custom_state_cycle_items, custom_details_template, custom_state_template, custom_details_prefix, custom_details_suffix, custom_state_prefix, custom_state_suffix, custom_details_remove, custom_details_replace, custom_state_remove, custom_state_replace]
        for widget in preview_text_edits:
            widget.textChanged.connect(update_preview)
        for widget in [manual_radio, vndb_radio, custom_radio, swap_checkbox, vndb_details_trim, vndb_state_trim, custom_details_template_radio, custom_details_cycle_radio, custom_state_template_radio, custom_state_cycle_radio, custom_details_trim, custom_state_trim]:
            widget.toggled.connect(update_preview)
        preview_timer = QTimer(dialog)
        preview_timer.timeout.connect(update_preview)
        preview_timer.start(1000)
        saved_img_host = existing_config.get('image_host', '')
        saved_source = (existing_config.get('image_source_path') or '').strip()
        saved_large = (existing_config.get('large_image') or '').strip()
        if saved_img_host == 'vndb' and saved_large.startswith(('http://', 'https://')):
            default_source_value = saved_large
            default_image_check.setChecked(True)
        elif saved_source and (not saved_source.startswith(('http://', 'https://'))):
            manual_image_check.setChecked(True)
        elif vndb_url_input.text().strip():
            default_image_check.setChecked(True)
        update_image_mode_visibility()
        image_settings_dirty = False
        update_mode()
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        outer_layout.addWidget(buttons)

        def close_dialog():
            if dialog in self.active_dialogs:
                self.active_dialogs.remove(dialog)
            try:
                chat_bubble.hide()
            except Exception:
                pass
            dialog.close()

        def on_accept():
            nonlocal game_info_saved
            game_info_saved = True
            update_refresh_button_state()
            if image_settings_dirty or manual_image_staged:
                apply_image_settings()
            config = {'vn_name': vn_name_input.text().strip() or exe_name, 'exe_name': current_exe_name(), 'exe_path': exe_path_input.text().strip(), 'exe_icon_path': exe_icon_path_input.text().strip(), 'extra_exe_names': existing_config.get('extra_exe_names', []), 'match_path_contains': match_path_contains_input.text().strip(), 'activity_name': activity_name_input.text().strip() or vn_name_input.text().strip() or exe_name, 'large_image': large_image_input.text().strip(), 'cover_url': cover_url_input.text().strip(), 'image_source_path': image_source_path_input.text().strip() or existing_config.get('image_source_path', ''), 'image_host': image_host_override['host'] or existing_config.get('image_host') or self.rpc_core.settings.get('image_host', 'none'), 'large_text': large_text_input.text().strip() or vn_name_input.text().strip() or exe_name, 'vndb_url': vndb_url_input.text().strip(), 'details_mode': 'manual' if manual_radio.isChecked() else 'vndb' if vndb_radio.isChecked() else 'custom'}
            if manual_radio.isChecked():
                config['details'] = m_details.text().strip() or '   '
                config['state'] = m_state.text().strip() or '   '
            elif vndb_radio.isChecked():
                config['vndb_swap_details_state'] = swap_checkbox.isChecked()
                config['vndb_state_template'] = vndb_state_template.text().strip() or DEFAULT_VNDB_STATE_TEMPLATE
                try:
                    config['vndb_details_cycle_seconds'] = max(5, int(vndb_details_cycle_seconds.text().strip() or '5'))
                except Exception:
                    config['vndb_details_cycle_seconds'] = 5
                config['vndb_details_cycle_items'] = self.parse_multiline_list(vndb_details_cycle_items.toPlainText()) or list(DEFAULT_VNDB_DETAILS_ITEMS)
                config['vndb_details_transform'] = {'prefix': vndb_details_prefix.text(), 'suffix': vndb_details_suffix.text(), 'remove': self.parse_multiline_list(vndb_details_remove.toPlainText()), 'replace': self.parse_replace_lines(vndb_details_replace.toPlainText()), 'trim': vndb_details_trim.isChecked()}
                config['vndb_state_transform'] = {'prefix': vndb_state_prefix.text(), 'suffix': vndb_state_suffix.text(), 'remove': self.parse_multiline_list(vndb_state_remove.toPlainText()), 'replace': self.parse_replace_lines(vndb_state_replace.toPlainText()), 'trim': vndb_state_trim.isChecked()}
            elif custom_radio.isChecked():
                config['custom_details_template'] = _single_line_value(custom_details_template)
                config['custom_details_cycle_enabled'] = custom_details_cycle_radio.isChecked()
                try:
                    config['custom_details_cycle_seconds'] = max(5, int(custom_details_cycle_seconds.text().strip() or '5'))
                except Exception:
                    config['custom_details_cycle_seconds'] = 5
                config['custom_details_cycle_items'] = self.parse_multiline_list(custom_details_cycle_items.toPlainText())
                config['custom_state_template'] = _single_line_value(custom_state_template)
                config['custom_state_cycle_enabled'] = custom_state_cycle_radio.isChecked()
                try:
                    config['custom_state_cycle_seconds'] = max(5, int(custom_state_cycle_seconds.text().strip() or '5'))
                except Exception:
                    config['custom_state_cycle_seconds'] = 5
                config['custom_state_cycle_items'] = self.parse_multiline_list(custom_state_cycle_items.toPlainText())
                config['custom_details_transform'] = {'prefix': _single_line_value(custom_details_prefix), 'suffix': _single_line_value(custom_details_suffix), 'remove': self.parse_multiline_list(custom_details_remove.toPlainText()), 'replace': self.parse_replace_lines(custom_details_replace.toPlainText()), 'trim': custom_details_trim.isChecked()}
                config['custom_state_transform'] = {'prefix': _single_line_value(custom_state_prefix), 'suffix': _single_line_value(custom_state_suffix), 'remove': self.parse_multiline_list(custom_state_remove.toPlainText()), 'replace': self.parse_replace_lines(custom_state_replace.toPlainText()), 'trim': custom_state_trim.isChecked()}
            source_path = pending_image['path'].strip()
            if source_path:
                kind = pending_image['kind'] or 'image'
                if kind == 'vndb cover':
                    ok_btn = buttons.button(QDialogButtonBox.StandardButton.Ok)
                    ok_btn.setEnabled(False)

                    def vndb_url_task():
                        return {'url': self.get_vndb_cover_url(source_path)}

                    def on_vndb_url_success(result):
                        ok_btn.setEnabled(True)
                        config['cover_url'] = result['url']
                        config['large_image'] = result['url']
                        config['image_source_path'] = ''
                        config['image_host'] = 'vndb'
                        cover_url_input.setText(result['url'])
                        large_image_input.setText(result['url'])
                        update_preview()
                        save_config(config)

                    def on_vndb_url_error(message):
                        ok_btn.setEnabled(True)
                        reply = QMessageBox.question(dialog, 'VNDB Cover Failed', f'{message}\n\nSave the game without a cover image?', QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
                        if reply == QMessageBox.StandardButton.Yes:
                            save_config(config)
                    run_background_task('VNDB Cover', 'Fetching VNDB cover URL...\nPlease wait.', vndb_url_task, on_vndb_url_success, 'VNDB Cover Failed', on_error=on_vndb_url_error, show_progress=False)
                    return
            save_config(config)

        def save_config(config):
            self.rpc_core.add_new_game_config(exe_name, config)
            vndb_url = vndb_url_input.text().strip()
            if vndb_url:
                self.ensure_vndb_prefetch(vndb_url)
            self.refresh_game_list()
            self.update_status(f'{exe_name} saved.')
            close_dialog()
        buttons.accepted.connect(on_accept)
        buttons.rejected.connect(close_dialog)
        dialog.finished.connect(lambda _: close_dialog() if dialog in self.active_dialogs else None)
        dialog.setModal(True)
        dialog.show()
        sync_content_min_height()
        var_row_layout.invalidate()
        var_row_layout.activate()

    def get_image_cache_dir(self):
        cache_dir = os.path.join(self.rpc_core.base_dir, 'Saved')
        os.makedirs(cache_dir, exist_ok=True)
        return cache_dir

    def get_image_dir(self, exe_path=''):
        return self.get_image_cache_dir()

    def safe_filename(self, name):
        name = re.sub('[^A-Za-z0-9_.-]+', '_', name.strip())
        return name.strip('._') or 'vn_cover'

    def _read_exe_icon_groups(self, exe_path):
        import struct
        from ctypes import wintypes
        try:
            from PIL import Image
        except ImportError:
            return []

        class _BITMAPINFOHEADER(ctypes.Structure):
            _fields_ = [('biSize', wintypes.DWORD), ('biWidth', ctypes.c_long), ('biHeight', ctypes.c_long), ('biPlanes', wintypes.WORD), ('biBitCount', wintypes.WORD), ('biCompression', wintypes.DWORD), ('biSizeImage', wintypes.DWORD), ('biXPelsPerMeter', ctypes.c_long), ('biYPelsPerMeter', ctypes.c_long), ('biClrUsed', wintypes.DWORD), ('biClrImportant', wintypes.DWORD)]

        class _BITMAPINFO(ctypes.Structure):
            _fields_ = [('bmiHeader', _BITMAPINFOHEADER), ('bmiColors', wintypes.DWORD * 3)]

        class _ICONINFO(ctypes.Structure):
            _fields_ = [('fIcon', wintypes.BOOL), ('xHotspot', wintypes.DWORD), ('yHotspot', wintypes.DWORD), ('hbmMask', wintypes.HBITMAP), ('hbmColor', wintypes.HBITMAP)]
        kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel32.LoadLibraryExW.argtypes = [wintypes.LPCWSTR, wintypes.HANDLE, wintypes.DWORD]
        kernel32.LoadLibraryExW.restype = wintypes.HMODULE
        kernel32.EnumResourceNamesW.argtypes = [wintypes.HMODULE, wintypes.LPWSTR, ctypes.c_void_p]
        kernel32.FindResourceW.argtypes = [wintypes.HMODULE, ctypes.c_void_p, ctypes.c_void_p]
        kernel32.FindResourceW.restype = wintypes.HANDLE
        kernel32.SizeofResource.argtypes = [wintypes.HMODULE, wintypes.HANDLE]
        kernel32.SizeofResource.restype = wintypes.DWORD
        kernel32.LockResource.argtypes = [wintypes.HANDLE]
        kernel32.LockResource.restype = wintypes.LPVOID
        kernel32.FreeLibrary.argtypes = [wintypes.HMODULE]
        user32 = ctypes.WinDLL('user32', use_last_error=True)
        user32.LoadImageW.argtypes = [wintypes.HMODULE, wintypes.LPCWSTR, wintypes.UINT, ctypes.c_int, ctypes.c_int, wintypes.DWORD]
        user32.LoadImageW.restype = wintypes.HANDLE
        user32.GetIconInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(_ICONINFO)]
        user32.GetIconInfo.restype = wintypes.BOOL
        user32.DestroyIcon.argtypes = [wintypes.HANDLE]
        user32.DestroyIcon.restype = wintypes.BOOL
        user32.GetDC.argtypes = [wintypes.HWND]
        user32.GetDC.restype = wintypes.HDC
        user32.ReleaseDC.argtypes = [wintypes.HANDLE, wintypes.HDC]
        gdi32 = ctypes.WinDLL('gdi32', use_last_error=True)
        gdi32.GetDIBits.argtypes = [wintypes.HDC, wintypes.HBITMAP, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID, ctypes.POINTER(_BITMAPINFO), wintypes.UINT]
        gdi32.GetDIBits.restype = ctypes.c_int
        gdi32.DeleteObject.argtypes = [wintypes.HANDLE]
        gdi32.DeleteObject.restype = wintypes.BOOL

        class _BITMAP(ctypes.Structure):
            _fields_ = [('bmType', ctypes.c_long), ('bmWidth', ctypes.c_long), ('bmHeight', ctypes.c_long), ('bmWidthBytes', ctypes.c_long), ('bmPlanes', ctypes.c_ulong), ('bmBitsPixel', ctypes.c_ulong), ('bmBits', ctypes.c_void_p)]
        gdi32.GetObjectW.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p]
        gdi32.GetObjectW.restype = ctypes.c_int
        RT_GROUP_ICON = 14
        LOAD_IMAGE_RESOURCE = 32
        LOAD_DATAFILE = 2
        IMAGE_ICON = 1
        LR_DEFAULTSIZE = 64
        MAX_ICON_SIZE = 256
        h_mod = kernel32.LoadLibraryExW(exe_path, None, LOAD_IMAGE_RESOURCE | LOAD_DATAFILE)
        if not h_mod:
            return []
        names = []
        ENUM_CB = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HMODULE, ctypes.c_void_p, wintypes.DWORD)

        def _enum_cb(_hmod, name, res_id):
            names.append(res_id if res_id else name)
            return True

        def _hicon_to_pil(hicon, hdc):
            ii = _ICONINFO()
            ii.fIcon = True
            if not user32.GetIconInfo(hicon, ctypes.byref(ii)):
                return None
            try:
                if not ii.hbmColor:
                    return None
                bm = _BITMAP()
                gdi32.GetObjectW(ii.hbmColor, ctypes.sizeof(bm), ctypes.byref(bm))
                w, h = (int(bm.bmWidth), abs(int(bm.bmHeight)))
                if w <= 0 or h <= 0 or w > 1024 or (h > 1024):
                    return None
                bi = _BITMAPINFO()
                bi.bmiHeader.biSize = ctypes.sizeof(_BITMAPINFOHEADER)
                bi.bmiHeader.biWidth = w
                bi.bmiHeader.biHeight = h
                bi.bmiHeader.biPlanes = 1
                bi.bmiHeader.biBitCount = 32
                bi.bmiHeader.biCompression = 0
                buf = (ctypes.c_byte * (w * h * 4))()
                n = gdi32.GetDIBits(hdc, ii.hbmColor, 0, h, buf, ctypes.byref(bi), 0)
                if n != h:
                    return None
                raw = bytearray(bytes(buf))
                for i in range(0, len(raw), 4):
                    raw[i], raw[i + 2] = (raw[i + 2], raw[i])
                img = Image.frombytes('RGBA', (w, h), bytes(raw))
                return img.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
            finally:
                gdi32.DeleteObject(ii.hbmMask)
                if ii.hbmColor:
                    gdi32.DeleteObject(ii.hbmColor)

        def _parse_group_entries(data):
            if len(data) < 6:
                return None
            _reserved, _rtype, count = struct.unpack_from('<HHH', data, 0)
            if count == 0 or count > 64:
                return None
            base = 6 + count * 16
            if base > len(data):
                return None
            entries = []
            for i in range(count):
                e = 6 + i * 16
                w, h, _colors, _res, planes, bpp, blen, off = struct.unpack_from('<BBBBHHII', data, e)
                w = 256 if w == 0 else w
                h = 256 if h == 0 else h
                if not (1 <= w <= 256 and 1 <= h <= 256):
                    return None
                if blen < 40 or off < base or off + blen > len(data):
                    return None
                entries.append((w, h, off, blen, planes, bpp))
            return entries

        def _entry_to_pil(data, w, h, off, blen, planes, bpp):
            ico = struct.pack('<HHH', 0, 1, 1)
            ico += struct.pack('<BBBBHHII', w % 256, h % 256, 0, 0, planes, bpp, blen, 22)
            ico += data[off:off + blen]
            with io.BytesIO(ico) as bio:
                img = Image.open(bio)
                img.load()
                return img.convert('RGBA')
        PNG_SIG = b'\x89PNG\r\n\x1a\n'
        fmap = None
        _fmap_file = None
        _rsrc_sections = []
        try:
            import mmap as _mmap
            _fmap_file = open(exe_path, 'rb')
            fmap = _mmap.mmap(_fmap_file.fileno(), 0, access=_mmap.ACCESS_READ)
            _pe = struct.unpack_from('<I', fmap, 60)[0]
            _nsec = struct.unpack_from('<H', fmap, _pe + 6)[0]
            _opt = struct.unpack_from('<H', fmap, _pe + 20)[0]
            _sec = _pe + 24 + _opt
            for _i in range(_nsec):
                _o = _sec + _i * 40
                _vsize, _vaddr, _rawsize, _rawptr = struct.unpack_from('<IIII', fmap, _o + 8)
                _rsrc_sections.append((_vaddr, max(_vsize, _rawsize), _rawptr))
        except Exception:
            fmap = None

        def _rva2off(rva):
            for vaddr, size, rawptr in _rsrc_sections:
                if vaddr <= rva < vaddr + size:
                    return rva - vaddr + rawptr
            return None

        def _png_total(data, off=0):
            o = off + 8
            total = 8
            while o + 8 <= len(data):
                ln = struct.unpack_from('>I', data, o)[0]
                typ = data[o + 4:o + 8]
                total += 12 + ln
                if typ == b'IEND':
                    return total
                o += 12 + ln
                if ln > 67108864:
                    return None
            return None

        def _png_to_pil(png):
            with io.BytesIO(png) as bio:
                img = Image.open(bio)
                img.load()
                return img.convert('RGBA')

        def _dib_ok(d):
            if len(d) < 40:
                return False
            bi_size, bi_w, bi_h = struct.unpack_from('<Iii', d, 0)
            bpp = struct.unpack_from('<H', d, 14)[0]
            return bi_size == 40 and 1 <= bi_w <= 256 and (1 <= abs(bi_h) <= 512) and (bpp in (1, 4, 8, 24, 32))

        def _dib_size(d):
            bi_w, bi_h = struct.unpack_from('<ii', d, 4)
            bpp = struct.unpack_from('<H', d, 14)[0]
            si = struct.unpack_from('<I', d, 20)[0]
            h = abs(bi_h)
            if si >= 40:
                return 40 + si
            if bpp == 32:
                return 40 + bi_w * h * 4
            xor = bi_w * h * bpp // 8
            androw = (bi_w + 31) // 32 * 4
            return 40 + xor + androw * h

        def _dib_to_pil(dib):
            bi_w, bi_h = struct.unpack_from('<ii', dib, 4)
            bpp = struct.unpack_from('<H', dib, 14)[0]
            si = struct.unpack_from('<I', dib, 20)[0]
            w = bi_w
            row = w * bpp // 8
            if si and row and (si % row == 0):
                h = si // row
            else:
                h = abs(bi_h) // 2 if abs(bi_h) % 2 == 0 else abs(bi_h)
            xor = w * h * bpp // 8
            androw = (w + 31) // 32 * 4
            mask = bytes(androw * h)
            ico = struct.pack('<HHH', 0, 1, 1)
            ico += struct.pack('<BBBBHHII', w, h, 0, 0, 1, bpp, 40 + xor + len(mask), 22)
            ico += dib[0:40] + dib[40:40 + xor] + mask
            with io.BytesIO(ico) as bio:
                img = Image.open(bio)
                img.load()
                return img.convert('RGBA')

        def _res_to_pil(d):
            if not d:
                return None
            if d[:8] == PNG_SIG:
                tot = _png_total(d, 0)
                if tot:
                    try:
                        return _png_to_pil(d[:tot])
                    except Exception:
                        return None
            if _dib_ok(d):
                try:
                    return _dib_to_pil(d)
                except Exception:
                    return None
            if fmap is not None and len(d) >= 8:
                trva = struct.unpack_from('<I', d, 0)[0]
                toff = _rva2off(trva)
                if toff is not None and 0 <= toff < len(fmap) - 8:
                    if fmap[toff:toff + 8] == PNG_SIG:
                        tot = _png_total(fmap, toff)
                        if tot:
                            try:
                                return _png_to_pil(bytes(fmap[toff:toff + tot]))
                            except Exception:
                                return None
                    hd = bytes(fmap[toff:toff + 40])
                    if _dib_ok(hd):
                        tot = _dib_size(hd)
                        if toff + tot <= len(fmap):
                            try:
                                return _dib_to_pil(bytes(fmap[toff:toff + tot]))
                            except Exception:
                                return None
            return None

        def _add_icon(img):
            if img is None:
                return
            img = img.convert('RGBA')
            if img.getchannel('A').getextrema()[1] == 0:
                return
            key = img.tobytes()
            if key in seen:
                return
            seen.add(key)
            icons.append(img)
        icons = []
        seen = set()
        try:
            enum_cb = ENUM_CB(_enum_cb)
            kernel32.EnumResourceNamesW(h_mod, ctypes.cast(RT_GROUP_ICON, wintypes.LPWSTR), enum_cb)
            hdc = user32.GetDC(None)
            try:
                for name in names:
                    h_res = kernel32.FindResourceW(h_mod, ctypes.cast(name, wintypes.LPCWSTR), ctypes.cast(RT_GROUP_ICON, wintypes.LPWSTR))
                    if not h_res:
                        continue
                    rsize = kernel32.SizeofResource(h_mod, h_res)
                    ptr = kernel32.LockResource(h_res)
                    if not ptr or not rsize:
                        continue
                    data = bytes((ctypes.c_byte * rsize).from_address(ptr))
                    entries = _parse_group_entries(data)
                    if entries:
                        for w, h, off, blen, planes, bpp in entries:
                            try:
                                img = _entry_to_pil(data, w, h, off, blen, planes, bpp)
                            except Exception:
                                continue
                            _add_icon(img)
                        continue
                    try:
                        img = _res_to_pil(data)
                    except Exception:
                        img = None
                    if img is None:
                        hicon = user32.LoadImageW(h_mod, ctypes.cast(name, wintypes.LPWSTR), IMAGE_ICON, MAX_ICON_SIZE, MAX_ICON_SIZE, LR_DEFAULTSIZE)
                        if hicon:
                            img = _hicon_to_pil(hicon, hdc)
                            user32.DestroyIcon(hicon)
                    _add_icon(img)
                icon_names = []

                def _icon_enum_cb(_hmod, name, res_id):
                    icon_names.append(res_id if res_id else name)
                    return True
                icon_cb = ENUM_CB(_icon_enum_cb)
                kernel32.EnumResourceNamesW(h_mod, ctypes.cast(3, wintypes.LPWSTR), icon_cb)
                for name in icon_names:
                    h_res = kernel32.FindResourceW(h_mod, ctypes.cast(name, wintypes.LPCWSTR), ctypes.cast(3, wintypes.LPWSTR))
                    if not h_res:
                        continue
                    rsize = kernel32.SizeofResource(h_mod, h_res)
                    ptr = kernel32.LockResource(h_res)
                    if not ptr or not rsize:
                        continue
                    data = bytes((ctypes.c_byte * rsize).from_address(ptr))
                    try:
                        _add_icon(_res_to_pil(data))
                    except Exception:
                        continue
            finally:
                user32.ReleaseDC(None, hdc)
        finally:
            kernel32.FreeLibrary(h_mod)
            if fmap is not None:
                try:
                    fmap.close()
                except Exception:
                    pass
            if _fmap_file is not None:
                try:
                    _fmap_file.close()
                except Exception:
                    pass
        icons.sort(key=lambda im: im.width * im.height, reverse=True)
        return icons

    def _extract_exe_icon_frames(self, exe_path):
        return self._read_exe_icon_groups(exe_path)

    def _extract_exe_icon_candidates(self, exe_path):
        return [{'group': i, 'image': img} for i, img in enumerate(self._read_exe_icon_groups(exe_path), start=1)]

    def pick_exe_icon_frame(self, exe_path):
        try:
            candidates = self._extract_exe_icon_candidates(exe_path)
        except Exception as e:
            QMessageBox.warning(self, 'EXE Icon Failed', str(e))
            return None
        if not candidates:
            QMessageBox.information(self, 'No Icons Found', f'No icons could be read from:\n{exe_path}')
            return None
        dialog = QDialog(self)
        dialog.setWindowTitle(f'Choose .exe Icon')
        dialog.setFixedSize(520, 430)
        layout = QVBoxLayout(dialog)
        count_label = QLabel(f'{len(candidates)} icon image(s) found in {os.path.basename(exe_path)}. Pick the one to use:')
        count_label.setWordWrap(True)
        layout.addWidget(count_label)
        icon_list = QListWidget()
        icon_list.setViewMode(QListWidget.ViewMode.IconMode)
        icon_list.setIconSize(QSize(64, 64))
        icon_list.setResizeMode(QListWidget.ResizeMode.Adjust)
        icon_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        icon_list.setMovement(QListWidget.Movement.Static)
        icon_list.setWrapping(True)
        icon_list.setSpacing(4)
        layout.addWidget(icon_list, 1)
        selected_label = QLabel('No icon selected')
        layout.addWidget(selected_label)
        chosen = {'image': None}
        best_index = max(range(len(candidates)), key=lambda i: candidates[i]['image'].width * candidates[i]['image'].height)
        for index, candidate in enumerate(candidates):
            frame = candidate['image']
            pm = QPixmap()
            png_buf = io.BytesIO()
            frame.convert('RGBA').save(png_buf, 'PNG')
            pm.loadFromData(png_buf.getvalue())
            if pm.isNull():
                pm = QPixmap(64, 64)
                pm.fill(QColor('#2b2d31'))
            item = QListWidgetItem(f'{frame.width}×{frame.height}')
            item.setSizeHint(QSize(72, 92))
            item.setData(Qt.ItemDataRole.UserRole, frame)
            item.setIcon(QIcon(pm))
            item.setToolTip(f'Icon image {index + 1} - {frame.width}x{frame.height}')
            icon_list.addItem(item)
            if index == best_index:
                icon_list.setCurrentItem(item)

        def on_current_changed(current, _previous):
            if current is None:
                chosen['image'] = None
                selected_label.setText('No icon selected')
                return
            frame = current.data(Qt.ItemDataRole.UserRole)
            chosen['image'] = frame
            selected_label.setText(f'Selected: icon image of {current.text()}')
        icon_list.currentItemChanged.connect(on_current_changed)
        on_current_changed(icon_list.currentItem(), None)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        layout.addWidget(buttons)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return chosen['image']
        return None

    def process_and_upload_image(self, source_path, game_title, exe_path=''):
        processed_path = self.process_rpc_image(source_path, game_title, exe_path)
        host = (self.rpc_core.settings.get('image_host', 'none') or 'none').strip().lower()
        if host == 'none':
            raise RuntimeError('No image host is configured. Open Settings > API Settings and choose one.')
        uploads = {'catbox': self.upload_to_catbox, 'imgbb': self.upload_to_imgbb, 'postimages': self.upload_to_postimages, 'imgbs': self.upload_to_imgbs, 'freeimage': self.upload_to_freeimage}
        url = uploads.get(host, self.upload_to_freeimage)(processed_path)
        return (url, processed_path, host)

    @staticmethod
    def _resize_to_square(img, target_size):
        from PIL import Image
        width, height = img.size
        scale = target_size / max(width, height)
        if abs(scale - 1.0) > 0.001:
            new_w = max(1, int(round(width * scale)))
            new_h = max(1, int(round(height * scale)))
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        return img

    def process_rpc_image(self, source_path, game_title, exe_path=''):
        try:
            from PIL import Image, ImageOps
        except ImportError as exc:
            raise RuntimeError('Pillow is required for image resizing. Install it with:\npython -m pip install pillow') from exc
        if not os.path.exists(source_path):
            raise RuntimeError(f'Image source not found:\n{source_path}')
        image_dir = self.get_image_dir(exe_path)
        safe_name = self.safe_filename(game_title)
        out_path = os.path.join(image_dir, f'{safe_name}_rpc_cover.png')
        target_height = 1024
        with Image.open(source_path) as img:
            img = ImageOps.exif_transpose(img)
            img = img.convert('RGBA')
            width, height = img.size
            new_width = max(1, int(round(width * (target_height / height))))
            new_height = target_height
            if (width, height) != (new_width, new_height):
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            img.save(out_path, 'PNG', optimize=True)
        return out_path

    def process_list_icon(self, source_path, game_title, exe_path=''):
        try:
            from PIL import Image, ImageOps
        except ImportError as exc:
            raise RuntimeError('Pillow is required for image resizing. Install it with:\npython -m pip install pillow') from exc
        if not os.path.exists(source_path):
            raise RuntimeError(f'Image source not found:\n{source_path}')
        image_dir = self.get_image_dir(exe_path)
        safe_name = self.safe_filename(game_title)
        out_path = os.path.join(image_dir, f'{safe_name}_list_icon.png')
        target_size = 1024
        with Image.open(source_path) as img:
            img = ImageOps.exif_transpose(img)
            img = img.convert('RGBA')
            img = self._resize_to_square(img, target_size)
            canvas = Image.new('RGBA', (target_size, target_size), (0, 0, 0, 0))
            x = (target_size - img.width) // 2
            y = (target_size - img.height) // 2
            canvas.paste(img, (x, y), img)
            canvas.save(out_path, 'PNG', optimize=True)
        return out_path

    def upload_to_freeimage(self, file_path):
        if not os.path.exists(file_path):
            raise RuntimeError(f'Upload file not found:\n{file_path}')
        api_key = self.rpc_core.settings.get('freeimage_api_key', '').strip() or self.rpc_core.settings.get('imgur_client_id', '').strip() or os.environ.get('FREEIMAGE_API_KEY', '').strip() or os.environ.get('IMGUR_CLIENT_ID', '').strip()
        if not api_key:
            raise RuntimeError("FreeImage.host upload requires an API key. Add 'freeimage_api_key' to settings.json or set FREEIMAGE_API_KEY in your environment.")
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            try:
                with open(file_path, 'rb') as f:
                    response = requests.post('https://freeimage.host/api/1/upload', data={'key': api_key, 'action': 'upload', 'format': 'json'}, files={'source': (os.path.basename(file_path), f, 'image/png')}, timeout=60)
                try:
                    payload = response.json()
                except ValueError as exc:
                    raise RuntimeError(f'FreeImage.host upload returned invalid JSON:\n{response.text[:500]}') from exc
                success = payload.get('success')
                if response.status_code != 200 and payload.get('status_code') not in (None, 200):
                    error = payload.get('error') or payload.get('message') or (success.get('message') if isinstance(success, dict) else None) or response.text
                    raise RuntimeError(f'FreeImage.host upload failed: {error}')
                if success is False or (isinstance(success, dict) and success.get('code') not in (None, 200)):
                    error = payload.get('error') or (success.get('message') if isinstance(success, dict) else None) or response.text
                    raise RuntimeError(f'FreeImage.host upload failed: {error}')
                image_url = extract_freeimage_url(payload)
                if not image_url:
                    raise RuntimeError(f'FreeImage.host upload returned no image URL:\n{payload}')
                return image_url
            except (requests.exceptions.RequestException, RuntimeError):
                if attempt >= max_attempts:
                    raise
                time.sleep(2 * attempt)
        raise RuntimeError('FreeImage.host upload failed after all attempts.')

    def upload_to_catbox(self, file_path):
        if not os.path.exists(file_path):
            raise RuntimeError(f'Upload file not found:\n{file_path}')
        with open(file_path, 'rb') as f:
            response = requests.post('https://catbox.moe/user/api.php', data={'reqtype': 'fileupload'}, files={'fileToUpload': f}, headers={'User-Agent': HEADERS['User-Agent']}, timeout=60)
        response.raise_for_status()
        url = response.text.strip()
        if not url.startswith('http'):
            raise RuntimeError(f"Catbox upload failed: {url[:200] or 'no response'}")
        return url

    def upload_to_imgbb(self, file_path):
        api_key = (self.rpc_core.settings.get('imgbb_api_key', '') or '').strip()
        if not api_key:
            raise RuntimeError('ImgBB API key missing.\nGet one at imgbb.com (login -> account -> API) and add it in Settings > API Settings.')
        if not os.path.exists(file_path):
            raise RuntimeError(f'Upload file not found:\n{file_path}')
        with open(file_path, 'rb') as f:
            image_b64 = base64.b64encode(f.read()).decode()
        response = requests.post('https://api.imgbb.com/1/upload', data={'key': api_key, 'image': image_b64}, headers=BROWSER_HEADERS, timeout=60)
        try:
            payload = response.json()
        except ValueError:
            raise RuntimeError(f'ImgBB upload failed (HTTP {response.status_code}): {response.text[:150]}')
        url = (payload.get('data') or {}).get('url')
        if not url:
            error = (payload.get('error') or {}).get('message') or response.text[:150]
            raise RuntimeError(f'ImgBB upload failed: {error}')
        return url

    def upload_to_postimages(self, file_path):
        api_key = (self.rpc_core.settings.get('postimages_api_key', '') or '').strip()
        if not api_key:
            raise RuntimeError('PostImages API key missing.\nGet one at postimages.org (login -> API tab) and add it in Settings > API Settings.')
        if not os.path.exists(file_path):
            raise RuntimeError(f'Upload file not found:\n{file_path}')
        with open(file_path, 'rb') as f:
            response = requests.post('https://api.postimages.org/v1/upload', files={'file': (os.path.basename(file_path), f, 'image/png')}, headers={'User-Agent': HEADERS['User-Agent'], 'Authorization': f'Bearer {api_key}'}, timeout=60)
        if not response.text.strip():
            raise RuntimeError('PostImages upload failed: empty response (check the API key).')
        try:
            payload = response.json()
        except ValueError:
            raise RuntimeError(f'PostImages upload failed (HTTP {response.status_code}): {response.text[:150]}')
        url = payload.get('url') or (payload.get('image') or {}).get('url')
        if not url:
            raise RuntimeError(f'PostImages upload failed: {payload}')
        return url

    def upload_to_imgbs(self, file_path):
        cookie = (self.rpc_core.settings.get('imgbs_cookie', '') or '').strip()
        if not cookie:
            raise RuntimeError('IMG.BS session cookie missing (guest uploads are currently disabled).\nLog in at imgbs.com, copy the session cookie, and paste it in Settings > API Settings.')
        if not os.path.exists(file_path):
            raise RuntimeError(f'Upload file not found:\n{file_path}')
        with open(file_path, 'rb') as f:
            response = requests.post('https://imgbs.com/api/upload.php', files={'image': (os.path.basename(file_path), f, 'image/png')}, data={'title': 'EwE cover'}, headers={'User-Agent': BROWSER_HEADERS['User-Agent'], 'Cookie': cookie}, timeout=60)
        text = response.text
        start = text.rfind('{"')
        try:
            payload = json.loads(text[start:] if start >= 0 else text)
        except ValueError:
            raise RuntimeError(f'IMG.BS upload failed: {text[:150] or response.status_code}')
        if not payload.get('success'):
            raise RuntimeError(f"IMG.BS upload failed: {payload.get('error') or text[:150]}")
        url = payload.get('url')
        if not url and payload.get('id'):
            url = f"https://imgbs.com/i/{payload['id']}/{payload.get('slug', 'image')}"
        if not url:
            raise RuntimeError(f'IMG.BS upload returned no URL: {payload}')
        return url

    def get_vndb_cover_url(self, vndb_url):
        match = re.search('v(\\d+)', vndb_url or '')
        if not match:
            raise RuntimeError('Invalid VNDB URL. Example: https://vndb.org/v47937')
        vn_id = f'v{match.group(1)}'
        data = vndb_post('vn', {'filters': ['id', '=', vn_id], 'fields': 'image.url'}, token=self.rpc_core.settings.get('vndb_api_token'), timeout=30)
        results = data.get('results') or []
        if not results:
            raise RuntimeError(f'No VNDB result found for {vn_id}.')
        image = results[0].get('image') or {}
        url = image.get('url')
        if not url:
            raise RuntimeError(f'VNDB entry {vn_id} has no cover image URL.')
        return url

    def parse_multiline_list(self, text):
        out = []
        for line in (text or '').splitlines():
            line = line.strip()
            if line and not line.startswith('#'):
                out.append(line)
        return out

    def parse_replace_lines(self, text):
        mapping = {}
        for line in (text or '').splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=>' in line:
                old, new = line.split('=>', 1)
            elif '=' in line:
                old, new = line.split('=', 1)
            else:
                continue
            old = old.strip()
            if old:
                mapping[old] = new.strip()
        return mapping

    def save_current_config(self):
        self.rpc_core._save_config()

    def delete_game(self, game_key):
        display_name = self.get_game_display_name(game_key)
        reply = QMessageBox.question(self, 'Delete Game', f"Delete '{display_name}' from the supported games list?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        if game_key in self.rpc_core.config:
            del self.rpc_core.config[game_key]
            self.rpc_core.clear_game_state(game_key)
            self.save_current_config()
            self._last_running_keys.discard(game_key)
            self._game_row_labels.pop(game_key, None)
            self._game_row_status.pop(game_key, None)
            self._game_row_items.pop(game_key, None)
            self._game_row_widgets.pop(game_key, None)
            QTimer.singleShot(0, self.refresh_game_list)
            self.update_status(f'Deleted {display_name}.')

    def set_manual_list_icon(self, game_key):
        try:
            self.activateWindow()
            self.raise_()
            icon_path, _ = native_open_file_dialog(self, 'Choose a list icon', '', 'Icon Files (*.ico);;Images (*.ico *.png *.jpg *.jpeg *.bmp);;All Files (*)')
        except Exception as e:
            QMessageBox.warning(self, 'Change Icon Failed', str(e))
            return
        if not icon_path:
            return
        settings = self.rpc_core.config.setdefault(game_key, {})
        exe_path = settings.get('exe_path', '')
        try:
            processed_path = self.process_list_icon(icon_path, self.get_game_display_name(game_key), exe_path)
        except Exception as e:
            QMessageBox.warning(self, 'Change Icon Failed', str(e))
            return
        settings['exe_icon_path'] = processed_path
        self.save_current_config()
        self.refresh_game_list()
        self.update_status(f'Updated list icon for {self.get_game_display_name(game_key)}.')

    def set_exe_list_icon(self, game_key):
        self.activateWindow()
        self.raise_()
        settings = self.rpc_core.config.get(game_key, {})
        exe_path = settings.get('exe_path', '')
        if not exe_path or not os.path.exists(exe_path):
            exe_path, _ = native_open_file_dialog(self, 'Game .exe path not found. Choose the game .exe file', '', 'Executable Files (*.exe);;All Files (*)')
            if not exe_path:
                return
            settings = self.rpc_core.config.setdefault(game_key, {})
            settings['exe_path'] = exe_path
            settings['exe_name'] = os.path.basename(exe_path)
            self.save_current_config()
        chosen_frame = self.pick_exe_icon_frame(exe_path)
        if chosen_frame is None:
            return
        try:
            from PIL import Image, ImageOps
            icon_img = ImageOps.exif_transpose(chosen_frame.convert('RGBA'))
            bbox = icon_img.getbbox()
            if bbox is not None:
                icon_img = icon_img.crop(bbox)
            icon_img = self._resize_to_square(icon_img, 1024)
            canvas = Image.new('RGBA', (1024, 1024), (0, 0, 0, 0))
            x = (1024 - icon_img.width) // 2
            y = (1024 - icon_img.height) // 2
            canvas.paste(icon_img, (x, y), icon_img)
            image_dir = self.get_image_dir(exe_path)
            safe_name = self.safe_filename(self.get_game_display_name(game_key))
            out_path = os.path.join(image_dir, f'{safe_name}_exe_icon.png')
            canvas.save(out_path, 'PNG', optimize=True)
        except Exception as e:
            QMessageBox.warning(self, 'Use .exe Icon Failed', str(e))
            return
        settings = self.rpc_core.config.setdefault(game_key, {})
        settings['exe_icon_path'] = out_path
        self.save_current_config()
        self.refresh_game_list()
        self.update_status(f'Updated list icon for {self.get_game_display_name(game_key)}.')

    def start_game(self, game_key):
        settings = self.rpc_core.config.get(game_key, {})
        exe_path = settings.get('exe_path', '')
        if not exe_path or not os.path.exists(exe_path):
            exe_path, _ = native_open_file_dialog(self, 'Game .exe path not found. Choose the game .exe file', '', 'Executable Files (*.exe);;All Files (*)')
            if not exe_path:
                return
            settings['exe_path'] = exe_path
            settings['exe_name'] = os.path.basename(exe_path)
            self.save_current_config()
            self.refresh_game_list()
        try:
            proc = subprocess.Popen([exe_path], cwd=os.path.dirname(exe_path) or None)
            self.rpc_core.track_pid(game_key, proc.pid)
            self.update_status(f'Started {self.get_game_display_name(game_key)}.')
        except Exception as e:
            QMessageBox.warning(self, 'Start Game Failed', str(e))

    def on_game_right_click(self, pos):
        item = self.game_list.itemAt(pos)
        if not item:
            return
        exe_name = item.data(Qt.ItemDataRole.UserRole) or item.text()
        if not exe_name:
            return
        menu = QMenu(self)
        menu.addAction('Start Game', lambda: QTimer.singleShot(0, lambda: self.start_game(exe_name)))
        menu.addSeparator()
        menu.addAction('Edit Game Info', lambda: QTimer.singleShot(0, lambda: self.open_game_info_dialog(exe_name, self.rpc_core.config.get(exe_name, {}))))
        icon_menu = menu.addMenu('Change Icon')
        icon_menu.addAction('Browse local .ico', lambda: QTimer.singleShot(0, lambda: self.set_manual_list_icon(exe_name)))
        icon_menu.addAction('Use .exe icon', lambda: QTimer.singleShot(0, lambda: self.set_exe_list_icon(exe_name)))
        menu.addSeparator()
        menu.addAction('Delete', lambda: QTimer.singleShot(0, lambda: self.delete_game(exe_name)))
        menu.exec(self.game_list.mapToGlobal(pos))

    def open_vndb_settings(self):
        dialog = QDialog(self)
        self.active_dialogs.append(dialog)
        dialog.finished.connect(lambda _r, d=dialog: self.active_dialogs.remove(d) if d in self.active_dialogs else None)
        dialog.setWindowTitle('VNDB Settings')
        dialog.setFixedWidth(420)
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel('Your VNDB Profile URL:  (e g. https://vndb.org/u272299)'))
        vndb_profile_input = QLineEdit(self.rpc_core.get_setting('my_vndb_link', ''))
        layout.addWidget(vndb_profile_input)
        layout.addWidget(QLabel('VNDB API token (optional, raises the rate limit):'))
        vndb_token_input = QLineEdit(self.rpc_core.get_setting('vndb_api_token', ''))
        vndb_token_input.setPlaceholderText('')
        layout.addWidget(vndb_token_input)
        show_vndb_list_checkbox = QCheckBox("Show 'My VNDB List' button in Discord RPC")
        show_vndb_list_checkbox.setChecked(self.rpc_core.get_setting('show_my_vndb_list', True))
        layout.addWidget(show_vndb_list_checkbox)
        layout.addWidget(QLabel('<b>Explicit content</b>'))
        blur_imgs_checkbox = QCheckBox('Pixelate explicit images in the library')
        blur_imgs_checkbox.setChecked(self.rpc_core.get_setting('pixel_explicit', True))
        layout.addWidget(blur_imgs_checkbox)
        blur_rpc_checkbox = QCheckBox("Don't show explicit covers in Discord Rich Presence")
        blur_rpc_checkbox.setChecked(self.rpc_core.get_setting('replace_rpc_explicit', True))
        layout.addWidget(blur_rpc_checkbox)
        blur_rpc_warn = QLabel('⚠ With this off, Visual Novels with explicit cover art are shown on your Discord profile. Discord can <b>BAN</b> accounts for that.')
        blur_rpc_warn.setWordWrap(True)
        blur_rpc_warn.setStyleSheet('color: #f0883e;')
        blur_rpc_warn.setVisible(not blur_rpc_checkbox.isChecked())
        layout.addWidget(blur_rpc_warn)
        blur_rpc_checkbox.toggled.connect(lambda checked: blur_rpc_warn.setVisible(not checked))
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        layout.addWidget(buttons)

        def on_accept():
            new_profile_url = vndb_profile_input.text().strip()
            if new_profile_url:
                self.rpc_core.update_settings('my_vndb_link', new_profile_url)
            self.rpc_core.update_settings('vndb_api_token', vndb_token_input.text().strip())
            self.rpc_core.update_settings('show_my_vndb_list', show_vndb_list_checkbox.isChecked())
            self.rpc_core.update_settings('pixel_explicit', blur_imgs_checkbox.isChecked())
            self.rpc_core.update_settings('replace_rpc_explicit', blur_rpc_checkbox.isChecked())
            if getattr(self, '_detail_key', None) is not None:
                self._show_game_details(self._detail_key)
            if self.rpc_core.last_running_exe:
                self.rpc_core.update_presence(self.rpc_core.last_running_exe)
                self.update_status('VNDB settings updated. RPC refreshed.')
            else:
                self.update_status('VNDB settings saved.')
            dialog.accept()
        buttons.accepted.connect(on_accept)
        buttons.rejected.connect(dialog.reject)
        dialog.exec()

    def open_api_settings(self):
        dialog = QDialog(self)
        self.active_dialogs.append(dialog)
        dialog.setWindowTitle('API Settings')
        dialog.setFixedSize(502, 312)
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel('<b>Image upload host:</b>'))
        host_options = [('none', 'None'), ('catbox', 'Catbox (Recommended)'), ('imgbb', 'ImgBB'), ('postimages', 'PostImages'), ('imgbs', 'IMG.BS (session cookie)'), ('freeimage', 'FreeImage')]
        saved_host = (self.rpc_core.get_setting('image_host', 'none') or 'none').strip().lower()
        field_specs = {'imgbb': ('ImgBB API key:', 'imgbb_api_key', 'imgbb.com -> login -> account -> API key'), 'postimages': ('PostImages API key:', 'postimages_api_key', 'postimages.org -> login -> API tab'), 'imgbs': ('IMG.BS session cookie:', 'imgbs_cookie', 'imgbs.com -> log in -> copy the session cookie'), 'freeimage': ('FreeImage API key:', 'freeimage_api_key', 'Get one at freeimage.host/api/')}
        host_inputs = {}
        for host_id, (label_text, setting_key, placeholder) in field_specs.items():
            lbl = QLabel(label_text)
            inp = QLineEdit(self.rpc_core.get_setting(setting_key, ''))
            inp.setPlaceholderText(placeholder)
            host_inputs[host_id] = (lbl, inp, setting_key)
        host_buttons = {}
        for host_id, label in host_options:
            btn = QRadioButton(label)
            btn.setChecked(host_id == saved_host)
            host_buttons[host_id] = btn
            layout.addWidget(btn)
        if saved_host not in host_buttons:
            host_buttons['none'].setChecked(True)
        layout.addSpacing(8)
        for lbl, inp, _key in host_inputs.values():
            layout.addWidget(lbl)
            layout.addWidget(inp)
        no_key_note = QLabel('Catbox needs no API key, recommended for most users, choose another service if this one \nnot working.    \n')
        no_key_note.setStyleSheet('color: gray; font-style: italic;')
        layout.addWidget(no_key_note)
        no_host_note = QLabel("Choosing 'None' will limit some EwE customization features. \n \n")
        no_host_note.setStyleSheet('color: gray; font-style: italic;')
        layout.addWidget(no_host_note)

        def update_host_visibility(_checked=None):
            selected = next((h for h, b in host_buttons.items() if b.isChecked()), 'none')
            for host_id, (lbl, inp, _key) in host_inputs.items():
                visible = host_id == selected
                lbl.setVisible(visible)
                inp.setVisible(visible)
            no_key_note.setVisible(selected == 'catbox')
            no_host_note.setVisible(selected == 'none')
        for btn in host_buttons.values():
            btn.toggled.connect(update_host_visibility)
        update_host_visibility()
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        layout.addWidget(buttons)

        def on_accept():
            checked = next((h for h, b in host_buttons.items() if b.isChecked()), 'catbox')
            self.rpc_core.update_settings('image_host', checked)
            for host_id, (_lbl, inp, setting_key) in host_inputs.items():
                self.rpc_core.update_settings(setting_key, inp.text().strip())
            self.update_status(f'API settings saved (host: {checked}).')
            dialog.accept()
        buttons.accepted.connect(on_accept)
        buttons.rejected.connect(dialog.reject)
        dialog.finished.connect(lambda _: self.active_dialogs.remove(dialog) if dialog in self.active_dialogs else None)
        dialog.exec()

    def open_startup_guide(self):
        guide = StartupGuideDialog(self.rpc_core, self, on_changed=self.refresh_game_list)
        guide.exec()
        self.refresh_game_list()
        timestamp = f"""<span style="color:#5c6370;">[{time.strftime('%H:%M:%S')}]</span> """
        if guide.completed:
            self.status_display.append(timestamp + '<span style="color:#3fb950; font-weight:bold;">Startup guide complete. Welcome to EwE!</span> ' + '<span style="color:#5c6370;">Add more games with the "Add Game" button. Right click a game to edit it.</span>')
        else:
            self.status_display.append(timestamp + '<span style="color:#e3b341;">Setup saved. Reopen the guide anytime from Settings &gt; Startup Guide.</span>')

    def open_update_checker(self):
        dialog = QDialog(self)
        self.active_dialogs.append(dialog)
        dialog.finished.connect(lambda _r, d=dialog: self.active_dialogs.remove(d) if d in self.active_dialogs else None)
        dialog.setWindowTitle('Check for Updates')
        dialog.setFixedSize(540, 560)
        dialog.setWindowIcon(QIcon(APP_ICON_PATH))
        layout = QVBoxLayout(dialog)
        layout.setSpacing(8)
        header = QLabel(f'<b>EwE</b> | current version: <b>{APP_VERSION}</b>')
        header.setWordWrap(True)
        layout.addWidget(header)
        status_label = QLabel('Checking for updates...')
        status_label.setWordWrap(True)
        status_label.setStyleSheet('color: #8b949e; font-size: 13px;')
        layout.addWidget(status_label)
        notes = QTextEdit()
        notes.setReadOnly(True)
        notes.setPlaceholderText('Release notes will appear here.')
        layout.addWidget(notes, 1)
        assets_box = QWidget()
        assets_layout = QVBoxLayout(assets_box)
        assets_layout.setContentsMargins(0, 0, 0, 0)
        assets_layout.setSpacing(4)
        layout.addWidget(assets_box)
        assets_layout.addStretch(1)
        startup_check_box = QCheckBox('Check for updates on startup')
        startup_check_box.setChecked(self.rpc_core.get_setting('check_updates_on_startup', True))
        startup_check_box.toggled.connect(lambda checked: self.rpc_core.update_settings('check_updates_on_startup', checked))
        layout.addWidget(startup_check_box)
        btn_row = QHBoxLayout()
        release_btn = QPushButton('Open release page')
        close_btn = QPushButton('Close')
        btn_row.addStretch(1)
        btn_row.addWidget(release_btn)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)
        state = {'release_url': f'{GITHUB_REPO_URL}/releases'}
        release_btn.clicked.connect(lambda: webbrowser.open(state['release_url']))
        close_btn.clicked.connect(dialog.accept)

        def fill_with_release(release):
            try:
                if sip is not None and sip.isdeleted(dialog):
                    return
            except Exception:
                pass
            if release.get('no_release'):
                status_label.setText('No releases have been published yet.')
                status_label.setStyleSheet('color: #e3b341; font-size: 13px;')
                notes.setPlainText('Check back later, or open the release page once one is published.')
                return
            tag = str(release.get('tag_name') or '').strip().lstrip('vV')
            state['release_url'] = release.get('html_url') or f'{GITHUB_REPO_URL}/releases'
            body = release.get('body') or 'No release notes.'
            if _is_newer_version(tag, APP_VERSION):
                status_label.setText(f'New version available: {tag}  (you are running {APP_VERSION})')
                status_label.setStyleSheet('color: #3fb950; font-weight: bold; font-size: 13px;')
                notes.setPlainText(f"Release notes for {release.get('name') or tag}:\n\n{body}\n\nTo update: download the file below, close EwE, then run the new .exe from the same folder. Your games and settings are stored beside the program and are kept.")
            elif _parse_version_text(tag) == _parse_version_text(APP_VERSION):
                status_label.setText(f'You are running the latest version ({APP_VERSION}).')
                status_label.setStyleSheet('color: #3fb950; font-size: 13px;')
                notes.setPlainText(f"Release notes for {release.get('name') or tag}:\n\n{body}")
            else:
                status_label.setText(f'Your version ({APP_VERSION}) is newer than the latest release ({tag}).')
                status_label.setStyleSheet('color: #e3b341; font-size: 13px;')
                notes.setPlainText(body)
            while assets_layout.count() > 1:
                item = assets_layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
            assets = release.get('assets') or []
            if not assets:
                hint = QLabel('This release has no downloadable files. Use "Open release page" to see it on GitHub.')
                hint.setWordWrap(True)
                hint.setStyleSheet('color: #8b949e;')
                assets_layout.insertWidget(assets_layout.count() - 1, hint)
            for asset in assets:
                name = str(asset.get('name') or 'download')
                size_text = _format_file_size(asset.get('size'))
                url = asset.get('browser_download_url') or state['release_url']
                row = QWidget()
                row_layout = QHBoxLayout(row)
                row_layout.setContentsMargins(0, 0, 0, 0)
                row_layout.setSpacing(6)
                label = QLabel(f'{name}  ({size_text})' if size_text else name)
                label.setWordWrap(True)
                download_btn = QPushButton('Download')
                copy_btn = QPushButton('Copy link')
                download_btn.clicked.connect(lambda _checked=False, u=url: webbrowser.open(u))
                copy_btn.clicked.connect(lambda _checked=False, u=url: QApplication.clipboard().setText(u))
                row_layout.addWidget(label, 1)
                row_layout.addWidget(download_btn)
                row_layout.addWidget(copy_btn)
                assets_layout.insertWidget(assets_layout.count() - 1, row)

        def work():
            try:
                return fetch_latest_github_release()
            except UpdateCheckNoRelease:
                return {'no_release': True}

        def on_success(release):
            fill_with_release(release)

        def on_error(message):
            try:
                if sip is not None and sip.isdeleted(dialog):
                    return
            except Exception:
                pass
            text = str(message).strip()
            short = text.splitlines()[0][:300] if text else 'unknown error'
            status_label.setText(f'Update check failed: {short}')
            status_label.setStyleSheet('color: #f85149; font-size: 13px;')
        run_async_task(work, on_success, on_error)
        dialog.exec()

    def _startup_update_check(self):
        if getattr(self, '_startup_update_done', False):
            return
        self._startup_update_done = True
        if not self.rpc_core.get_setting('check_updates_on_startup', True):
            return

        def work():
            try:
                return fetch_latest_github_release()
            except UpdateCheckNoRelease:
                return None

        def on_success(release):
            if not release:
                return
            tag = str(release.get('tag_name') or '').strip().lstrip('vV')
            if not tag or not _is_newer_version(tag, APP_VERSION):
                return
            summary = f'EwE {tag} is available (you are running {APP_VERSION}).'
            timestamp = f"""<span style="color:#5c6370;">[{time.strftime('%H:%M:%S')}]</span> """
            self.status_display.append(timestamp + f'<span style="color:#3fb950;">{html.escape(summary)}</span> ' + '<span style="color:#8b949e;">Open Settings &gt; Check for Updates to download it.</span>')
            tray = getattr(self, 'tray_icon', None)
            if tray is not None:
                tray.showMessage('EwE update available', summary, QIcon(APP_ICON_PATH), 5000)

        def on_error(_message):
            pass
        run_async_task(work, on_success, on_error)
DARK_STYLESHEET = '\nQWidget {\n    background-color: #1e1f22;\n    color: #dbdee1;\n    font-family: \'Segoe UI\';\n    font-size: 13px;\n}\n\nQLabel {\n    background: transparent;\n    color: #dbdee1;\n}\n\nQMainWindow, QDialog, QMessageBox, QMenu, QToolTip {\n    background-color: #1e1f22;\n}\n\n/* --- inputs --- */\nQLineEdit, QTextEdit {\n    background-color: #2b2d31;\n    border: 1px solid #3f4147;\n    border-radius: 4px;\n    padding: 4px;\n    color: #dbdee1;\n    selection-background-color: #5865f2;\n    selection-color: #ffffff;\n}\n\nQLineEdit:focus, QTextEdit:focus {\n    border: 1px solid #5865f2;\n}\n\nQLineEdit:disabled, QTextEdit:disabled {\n    color: #80848e;\n    background-color: #232428;\n}\n\n/* --- lists --- */\nQListWidget {\n    background-color: #2b2d31;\n    border: 1px solid #3f4147;\n    border-radius: 4px;\n    padding: 2px;\n    outline: 0;\n}\n\nQListWidget::item {\n    color: #dbdee1;\n    padding: 4px;\n    border-radius: 4px;\n}\n\nQListWidget::item:selected {\n    background-color: #5865f2;\n    color: #ffffff;\n}\n\n/* --- buttons --- */\nQPushButton {\n    background-color: #313338;\n    border: 1px solid #3f4147;\n    border-radius: 4px;\n    padding: 6px 18px;\n    color: #dbdee1;\n}\n\nQPushButton:hover {\n    background-color: #3a3c42;\n}\n\nQPushButton:pressed {\n    background-color: #2b2d31;\n}\n\nQPushButton:disabled {\n    color: #80848e;\n    background-color: #26272b;\n    border-color: #2b2d31;\n}\n\n/* --- menu bar / menus --- */\nQMenuBar {\n    background-color: #1e1f22;\n    color: #dbdee1;\n}\n\nQMenuBar::item {\n    background: transparent;\n    padding: 5px 10px;\n}\n\nQMenuBar::item:selected {\n    background-color: #313338;\n    border-radius: 4px;\n}\n\nQMenu {\n    background-color: #2b2d31;\n    border: 1px solid #3f4147;\n}\n\nQMenu::item {\n    padding: 6px 24px;\n    border-radius: 4px;\n}\n\nQMenu::item:selected {\n    background-color: #5865f2;\n    color: #ffffff;\n}\n\nQMenu::item:disabled {\n    color: #80848e;\n}\n\nQMenu::separator {\n    height: 1px;\n    background-color: #3f4147;\n    margin: 4px 8px;\n}\n\n/* --- checkboxes & radio buttons --- */\nQCheckBox, QRadioButton {\n    background: transparent;\n    color: #dbdee1;\n    spacing: 8px;\n    padding: 2px;\n}\n\nQCheckBox:disabled, QRadioButton:disabled {\n    color: #80848e;\n}\n\nQCheckBox::indicator, QRadioButton::indicator {\n    width: 16px;\n    height: 16px;\n    background-color: #2b2d31;\n    border: 1px solid #80848e;\n}\n\nQCheckBox::indicator {\n    border-radius: 3px;\n}\n\nQRadioButton::indicator {\n    border-radius: 8px;\n}\n\nQCheckBox::indicator:hover, QRadioButton::indicator:hover {\n    border-color: #5865f2;\n}\n\nQCheckBox::indicator:checked {\n    background-color: #5865f2;\n    border-color: #7984f5;\n    image: url("__CHECK_ICON__");\n}\n\nQRadioButton::indicator:checked {\n    background-color: #5865f2;\n    border-color: #5865f2;\n}\n\n/* --- scroll areas & scrollbars --- */\nQScrollArea {\n    border: none;\n    background: transparent;\n}\n\nQScrollArea > QWidget > QWidget {\n    background: transparent;\n}\n\nQScrollBar:vertical {\n    background: #1e1f22;\n    width: 12px;\n    margin: 0;\n}\n\nQScrollBar::handle:vertical {\n    background: #A8A1C9;\n    border-radius: 6px;\n    min-height: 30px;\n}\n\nQScrollBar::handle:vertical:hover, QScrollBar::handle:vertical:pressed {\n    background: #A8A1C9;\n}\n\nQScrollBar:horizontal {\n    background: #1e1f22;\n    height: 12px;\n    margin: 0;\n}\n\nQScrollBar::handle:horizontal {\n    background: #A8A1C9;\n    border-radius: 6px;\n    min-width: 30px;\n}\n\nQScrollBar::handle:horizontal:hover, QScrollBar::handle:horizontal:pressed {\n    background: #A8A1C9;\n}\n\nQScrollBar::add-line, QScrollBar::sub-line {\n    width: 0;\n    height: 0;\n}\n\nQScrollBar::add-page, QScrollBar::sub-page {\n    background: transparent;\n}\n\n/* --- tooltips & progress --- */\nQToolTip {\n    background-color: #2b2d31;\n    color: #dbdee1;\n    border: 1px solid #3f4147;\n    padding: 4px;\n}\n\nQMessageBox {\n    background-color: #2b2d31;\n}\n\nQProgressDialog {\n    background-color: #2b2d31;\n}\n\nQProgressBar {\n    background-color: #1e1f22;\n    border: 1px solid #3f4147;\n    border-radius: 4px;\n    text-align: center;\n    color: #dbdee1;\n}\n\nQProgressBar::chunk {\n    background-color: #5865f2;\n    border-radius: 3px;\n}\n'

_dark_title_bar_handles = set()
DWMWA_USE_IMMERSIVE_DARK_MODE = 20

def enable_dark_title_bar(widget):
    try:
        hwnd = int(widget.winId())
    except Exception:
        return
    if not hwnd or hwnd in _dark_title_bar_handles:
        return
    if not widget.isVisible():
        return
    _dark_title_bar_handles.add(hwnd)
    try:
        value = ctypes.c_int(1)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(ctypes.c_void_p(hwnd), ctypes.c_int(DWMWA_USE_IMMERSIVE_DARK_MODE), ctypes.byref(value), ctypes.sizeof(value))
        SWP_NOSIZE = 1
        SWP_NOMOVE = 2
        SWP_NOZORDER = 4
        SWP_FRAMECHANGED = 32
        ctypes.windll.user32.SetWindowPos(ctypes.c_void_p(hwnd), None, 0, 0, 0, 0, SWP_NOSIZE | SWP_NOMOVE | SWP_NOZORDER | SWP_FRAMECHANGED)
        RDW_INVALIDATE = 1
        RDW_FRAME = 256
        ctypes.windll.user32.RedrawWindow(ctypes.c_void_p(hwnd), None, None, RDW_INVALIDATE | RDW_FRAME)
    except Exception:
        _dark_title_bar_handles.discard(hwnd)

class DarkTitleBarFilter(QObject):

    def eventFilter(self, obj, event):
        try:
            if event.type() == QEvent.Type.Show and isinstance(obj, QWidget) and obj.isWindow() and (not isinstance(obj, (QMenu, QToolTip))):
                enable_dark_title_bar(obj)
        except Exception:
            pass
        return super().eventFilter(obj, event)

def ensure_checkmark_png():
    path = os.path.join(_RES_DIR, 'Elements', 'checkbox_check.png')
    if os.path.exists(path):
        return path
    path = os.path.join(BASE_DIR, 'Elements', 'checkbox_check.png')
    pm = QPixmap(16, 16)
    pm.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pm)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QPen(QColor('#ffffff'), 2.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    painter.drawPolyline([QPointF(2.8, 8.8), QPointF(6.6, 12.4), QPointF(13.2, 4.2)])
    painter.end()
    pm.save(path, 'PNG')
    return path

def make_report_icon():
    pm = QPixmap(32, 32)
    pm.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pm)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QPen(QColor('#8b949e'), 1))
    painter.setBrush(QColor('#e3b341'))
    painter.drawPolygon(QPolygonF([QPointF(16, 3.5), QPointF(29.5, 27), QPointF(2.5, 27)]))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor('#0c0c0c'))
    painter.drawRoundedRect(QRectF(14.2, 11.5, 3.6, 7.5), 1.6, 1.6)
    painter.drawEllipse(QPointF(16, 23.2), 2.0, 2.0)
    painter.end()
    return QIcon(pm)

def make_star_icon():
    cx, cy, outer, inner = (16.0, 17.0, 13.0, 5.5)
    points = []
    for i in range(10):
        radius = outer if i % 2 == 0 else inner
        angle = -math.pi / 2 + i * math.pi / 5
        points.append(QPointF(cx + radius * math.cos(angle), cy + radius * math.sin(angle)))
    pm = QPixmap(32, 32)
    pm.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pm)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QPen(QColor('#8b949e'), 1))
    painter.setBrush(QColor('#e3b341'))
    painter.drawPolygon(QPolygonF(points))
    painter.end()
    return QIcon(pm)

def main():
    try:
        _crash_log = open(os.path.join(BASE_DIR, 'ewe_crash.log'), 'a', encoding='utf-8', buffering=1)
        _original_stderr = sys.stderr

        class _TeeStderr(io.TextIOBase):

            def write(self, data):
                try:
                    _original_stderr.write(data)
                except Exception:
                    pass
                try:
                    _crash_log.write(data)
                    _crash_log.flush()
                except Exception:
                    pass
                return len(data) if data else 0

            def flush(self):
                try:
                    _original_stderr.flush()
                except Exception:
                    pass
        sys.stderr = _TeeStderr()
        faulthandler.enable(file=_crash_log)

        def _log_excepthook(exc_type, exc_value, exc_tb):
            try:
                _crash_log.write(''.join(traceback.format_exception(exc_type, exc_value, exc_tb)))
                _crash_log.flush()
            except Exception:
                pass
        sys.excepthook = _log_excepthook
    except Exception:
        pass
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(APP_ICON_PATH))
    app.setQuitOnLastWindowClosed(False)
    app.setAttribute(Qt.ApplicationAttribute.AA_DontUseNativeDialogs)
    check_icon = ensure_checkmark_png().replace('\\', '/')
    app.setStyleSheet(DARK_STYLESHEET.replace('__CHECK_ICON__', check_icon.replace('\\', '/')))
    app.dark_title_bar_filter = DarkTitleBarFilter()
    app.installEventFilter(app.dark_title_bar_filter)
    window = RPCMainWindow()
    window.show_main_window()
    sys.exit(app.exec())
if __name__ == '__main__':
    main()
