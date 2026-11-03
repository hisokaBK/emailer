import logging
from pathlib import Path

from config.settings import LOGS_DIR

LOGS_DIR.mkdir(parents=True, exist_ok=True)
LOGGER_NAME = "auto_candidature"


def get_logger(name: str = LOGGER_NAME) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        file_handler = logging.FileHandler(LOGS_DIR / "app.log", encoding="utf-8")
        file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
        logger.addHandler(file_handler)
    return logger
