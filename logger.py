import os
import sys
import shutil
import threading
from datetime import datetime, timedelta
from pathlib import Path
import yaml
from loguru import logger as _loguru_logger

PROJECT_ROOT = Path(__file__).parent.resolve()
CONFIG_PATH = str(PROJECT_ROOT / "config.yaml")

try:
    with open(CONFIG_PATH, "r") as config_file:
        config = yaml.safe_load(config_file)
except FileNotFoundError:
    print(f"[FATAL] Logger config file not found: {CONFIG_PATH}", file=sys.stderr)
    raise
except yaml.YAMLError as e:
    print(f"[FATAL] Failed to parse logger config YAML at {CONFIG_PATH}: {e}", file=sys.stderr)
    raise
except Exception as e:
    print(f"[FATAL] Unexpected error loading logger config at {CONFIG_PATH}: {e}", file=sys.stderr)
    raise

if not config or "logger" not in config:
    print(f"[FATAL] Logger config at {CONFIG_PATH} is missing the 'logger' section", file=sys.stderr)
    raise KeyError(f"'logger' section missing from config: {CONFIG_PATH}")

try:
    DAYS_TO_KEEP_ARCHIVE = config["logger"]["days_to_keep_archive"]
    _raw_log_dir         = config["logger"]["log_folder"]
    DEFAULT_LOG_DIR      = str(PROJECT_ROOT / _raw_log_dir.lstrip("./\\"))
    DEFAULT_LOG_LEVEL    = config["logger"]["log_level"]
except KeyError as e:
    print(f"[FATAL] Logger config at {CONFIG_PATH} missing required key: {e}", file=sys.stderr)
    raise

LOG_FORMAT = (
    "[{time:YYYY-MM-DD HH:mm:ss}] "
    "[{level:<7}] "
    "[{name}] "
    "[{function}:{line}] "
    "{message}"
)

_loguru_logger.remove()

# Stderr fallback — always visible in terminal
_loguru_logger.add(
    sink      = sys.stderr,
    level     = "INFO",
    format    = LOG_FORMAT,
    colorize  = False,
)

DEFAULT_LOG_FILE = "app.log"
MAX_SIZE         = "512 KB"

_sink_lock = threading.Lock()


def _get_dated_archive_dir(archive_root: str) -> str:
    today     = datetime.now().strftime("%Y-%m-%d")
    dated_dir = os.path.join(archive_root, today)
    try:
        os.makedirs(dated_dir, exist_ok=True)
    except OSError:
        _loguru_logger.exception(f"Failed to create archive directory: {dated_dir}")
        raise
    return dated_dir


def _move_to_archive(archive_root: str):

    def _handler(files):

        for filepath in files:
            try:
                dated_dir   = _get_dated_archive_dir(archive_root)
                filename    = os.path.basename(filepath)
                destination = os.path.join(dated_dir, filename)
                if os.path.exists(filepath):
                    shutil.move(filepath, destination)
                else:
                    _loguru_logger.warning(f"Rotated log file not found, skipping move: {filepath}")
            except (OSError, shutil.Error):
                _loguru_logger.exception(f"Failed to archive rotated log file: {filepath} "
                                          f"-> {archive_root}")

        cutoff = datetime.now() - timedelta(days=DAYS_TO_KEEP_ARCHIVE)
        if os.path.isdir(archive_root):
            try:
                folder_names = os.listdir(archive_root)
            except OSError:
                _loguru_logger.exception(f"Failed to list archive root for cleanup: {archive_root}")
                folder_names = []

            for folder_name in folder_names:
                folder_path = os.path.join(archive_root, folder_name)
                if not os.path.isdir(folder_path):
                    continue
                try:
                    folder_date = datetime.strptime(folder_name, "%Y-%m-%d")
                    if folder_date < cutoff:
                        shutil.rmtree(folder_path)
                except ValueError:
                    pass
                except OSError:
                    _loguru_logger.exception(f"Failed to delete expired archive folder: {folder_path}")
        else:
            _loguru_logger.warning(f"Archive root does not exist, skipping cleanup: {archive_root}")

    return _handler


class AppLogger:

    _configured_paths: set = set()

    def __init__(
        self,
        name: str,
        log_dir: str  = DEFAULT_LOG_DIR,
        log_file: str = DEFAULT_LOG_FILE,
        level: str    = DEFAULT_LOG_LEVEL,
    ):
        self._name  = name
        self.LOG_FORMAT = LOG_FORMAT
        self.MAX_SIZE = MAX_SIZE
        log_path    = os.path.join(log_dir, log_file)
        archive_dir = os.path.join(log_dir, "archive")

        try:
            os.makedirs(log_dir, exist_ok=True)
            os.makedirs(archive_dir, exist_ok=True)
        except OSError as e:
            print(f"[FATAL] Failed to create log directories ({log_dir}, {archive_dir}): {e}",
                  file=sys.stderr)
            raise

        with _sink_lock:
            if log_path not in AppLogger._configured_paths:
                try:
                    _loguru_logger.add(
                        sink        = log_path,
                        level       = level,
                        format      = LOG_FORMAT,
                        rotation    = MAX_SIZE,
                        retention   = _move_to_archive(archive_dir),
                        compression = None,
                        serialize   = False,
                        enqueue     = False,
                        encoding    = "utf-8",
                    )
                    AppLogger._configured_paths.add(log_path)
                except (OSError, ValueError) as e:
                    print(f"[FATAL] Failed to register log sink at {log_path} "
                          f"(level={level}): {e}", file=sys.stderr)
                    raise

        self._logger = _loguru_logger.bind(name=name)

    def debug(self, message: str):
        self._logger.opt(depth=1, lazy=True).debug(message)

    def info(self, message: str):
        self._logger.opt(depth=1, lazy=True).info(message)

    def warning(self, message: str):
        self._logger.opt(depth=1, lazy=True).warning(message)

    def error(self, message: str):
        self._logger.opt(depth=1, lazy=True).error(message)

    def log_separator(self, char: str = "─"):
        self._logger.opt(depth=1, lazy=True).info((char * 60))

    def log_timing(self, tag: str, elapsed: float):
        self._logger.opt(depth=1, lazy=True).info(f"[TIMING] {tag:<30} : {elapsed*1000:7.1f} ms")

    def exception(self, message: str):
        self._logger.opt(depth=1, exception=True).error(message)

    def catch(self, func):
        return self._logger.catch(func)
