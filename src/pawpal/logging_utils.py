import logging
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parents[2] / "logs"
LOG_FILE = LOG_DIR / "pawpal.log"

_configured = False


def _configure_root_logger() -> None:
    global _configured
    if _configured:
        return
    LOG_DIR.mkdir(exist_ok=True)
    handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root = logging.getLogger("pawpal")
    root.setLevel(logging.INFO)
    root.addHandler(handler)
    _configured = True


def get_logger(name: str) -> logging.Logger:
    _configure_root_logger()
    return logging.getLogger(name)
