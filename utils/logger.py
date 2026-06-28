import logging
from datetime import datetime
from pathlib import Path


LOG_DIR = Path("logs")

LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    filename=LOG_DIR / "app.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)


def timestamp():

    return datetime.now().strftime("%H:%M:%S")


def info(message):

    logging.info(message)

    print(
        message
    )


def success(message):

    logging.info(message)

    print(
        message
    )


def warning(message):

    logging.warning(message)

    print(
        message
    )


def error(message):

    logging.error(message)

    print(
        message
    )
