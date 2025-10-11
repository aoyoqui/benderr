import logging
from datetime import datetime

from br_tester.config import AppConfig
from br_tester.events import log_msg


def setup_logger():
    logger = logging.getLogger("benderr")
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    if logger.handlers:
        return logger

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    if AppConfig.get("log_to_console", True):
        ch = logging.StreamHandler()
        ch.setLevel(AppConfig.get("log_level_console", logging.INFO))
        ch.setFormatter(formatter)
        logger.addHandler(ch)

    handler = SignalEmitterHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger

def get_log_path():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    return f"run_{timestamp}.log"

def reset_log_file():
    logger = logging.getLogger("benderr")

    for h in logger.handlers[:]:
        if isinstance(h, logging.FileHandler):
            logger.removeHandler(h)
            h.close()

    log_path = get_log_path()
    file_handler = logging.FileHandler(log_path)
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_handler)
    return log_path

class SignalEmitterHandler(logging.Handler):
    def emit(self, record):
        msg = self.format(record)
        log_msg.send(self, log=msg, record=record)
