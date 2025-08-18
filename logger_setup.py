# logger_setup.py

import logging

logger = logging.getLogger("g-ai-j")
logger.setLevel(logging.INFO)

handler = logging.StreamHandler()
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
handler.setFormatter(formatter)

if not logger.handlers:
    logger.addHandler(handler)
