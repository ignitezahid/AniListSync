import sys
import os
import shutil
import tempfile
import signal
import atexit

LOCK_FILE = os.path.join(tempfile.gettempdir(), "anilistsync.lock")


def _check_single_instance():
    try:
        with open(LOCK_FILE) as f:
            old_pid = int(f.read().strip())
        try:
            os.kill(old_pid, 0)
            return False
        except OSError:
            pass
        try:
            os.unlink(LOCK_FILE)
        except Exception:
            pass
    except (FileNotFoundError, ValueError):
        pass

    try:
        fd = os.open(LOCK_FILE, os.O_CREAT | os.O_EXCL | os.O_RDWR)
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
        return True
    except FileExistsError:
        return False


def _remove_lock():
    try:
        if os.path.exists(LOCK_FILE):
            with open(LOCK_FILE) as f:
                pid = int(f.read().strip())
            if pid == os.getpid():
                os.unlink(LOCK_FILE)
    except Exception:
        pass


signal.signal(signal.SIGTERM, lambda *_: (_remove_lock(), sys.exit(0)))
signal.signal(signal.SIGINT, lambda *_: (_remove_lock(), sys.exit(0)))

if not _check_single_instance():
    sys.exit(0)

atexit.register(_remove_lock)


if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'AniListSync')
    os.makedirs(BASE_DIR, exist_ok=True)
    for name in ['app_icon.ico', 'config.example.py']:
        src = os.path.join(sys._MEIPASS, name)
        dst = os.path.join(BASE_DIR, name)
        if os.path.exists(src) and not os.path.exists(dst):
            shutil.copy2(src, dst)
    # Seed plugin subfolders from MEIPASS (overwrite stale flat files)
    meipass_plugins = os.path.join(sys._MEIPASS, 'plugins')
    if os.path.isdir(meipass_plugins):
        dst_plugins = os.path.join(BASE_DIR, 'plugins')
        os.makedirs(dst_plugins, exist_ok=True)
        for item in os.listdir(meipass_plugins):
            src = os.path.join(meipass_plugins, item)
            dst = os.path.join(dst_plugins, item)
            if os.path.isdir(src) and (not os.path.exists(dst) or not os.path.isdir(dst)):
                shutil.copytree(src, dst, dirs_exist_ok=True)
    # Migrate existing data on first run from project root
    for old_root in [os.path.dirname(os.path.dirname(os.path.abspath(sys.executable))),
                     os.path.dirname(os.path.abspath(sys.executable))]:
        if not os.path.isdir(old_root):
            continue
        for dirname in ['data', 'backups', 'exports', 'logs']:
            src = os.path.join(old_root, dirname)
            dst = os.path.join(BASE_DIR, dirname)
            if os.path.isdir(src) and not os.path.exists(dst):
                shutil.copytree(src, dst, dirs_exist_ok=True)
        for fname in ['state.json', 'aliases.json', 'search_cache.json']:
            src = os.path.join(old_root, fname)
            dst = os.path.join(BASE_DIR, fname)
            if os.path.isfile(src):
                if not os.path.exists(dst):
                    shutil.copy2(src, dst)
                else:
                    try:
                        src_size = os.path.getsize(src)
                        dst_size = os.path.getsize(dst)
                        if src_size > dst_size:
                            shutil.copy2(src, dst)
                    except Exception:
                        pass
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

os.chdir(BASE_DIR)

if getattr(sys, 'frozen', False):
    import logging
    log_path = os.path.join(BASE_DIR, 'data', 'crash.log')
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    logging.basicConfig(filename=log_path, level=logging.DEBUG,
                        format='%(asctime)s %(levelname)s %(message)s')
    sys.excepthook = lambda t, v, tb: (
        logging.critical('Unhandled', exc_info=(t, v, tb)),
        sys.__excepthook__(t, v, tb) if sys.__excepthook__ is not None else None
    )

from gui.app import launch_gui

try:
    launch_gui()
except Exception:
    import traceback
    try:
        with open(os.path.join(BASE_DIR, 'data', 'crash.log'), 'a') as f:
            traceback.print_exc(file=f)
    except Exception:
        pass
    raise
finally:
    _remove_lock()
