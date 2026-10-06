import logging
from logging.handlers import RotatingFileHandler


def setup_logger(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger('morning_news')
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    for handler in (RotatingFileHandler(path, maxBytes=2_000_000, backupCount=3, encoding='utf-8'), logging.StreamHandler()):
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger
