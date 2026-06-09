import gzip
import logging
import os
import shutil
import sys
from datetime import datetime

from utils.paths import DATA_DIR

DEFAULT_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
DEBUG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'


def setup_logger(name: str = "bohe-api-auto-signin", log_dir: str | None = None) -> logging.Logger:
    log_dir = log_dir or os.path.join(DATA_DIR, "logs")

    logger = logging.getLogger(name)
    log_level = getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO)
    logger.setLevel(log_level)
    if logger.handlers:
        return logger


    os.makedirs(log_dir, exist_ok=True)

    log_file = os.path.join(log_dir, "latest.log")
    if os.path.exists(log_file):
        mod_time = os.path.getmtime(log_file)
        date_str = datetime.fromtimestamp(mod_time).strftime('%Y-%m-%d_%H-%M-%S')
        archive_path = os.path.join(log_dir, f"{date_str}.log.gz")
        with open(log_file, 'rb') as f_in, gzip.open(archive_path, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)
        os.remove(log_file)

    formatter = logging.Formatter(
        DEBUG_FORMAT if log_level <= logging.DEBUG else DEFAULT_FORMAT,
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger
