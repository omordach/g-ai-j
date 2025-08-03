# logger_setup.py

import logging

logger = logging.getLogger("g-ai-j")
logger.setLevel(logging.INFO)

# Console handler
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)

# File handler writing to mounted volume
fh = logging.FileHandler("/data/g-ai-j.log", encoding='utf-8')
fh.setLevel(logging.INFO)

# Formatter
formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
ch.setFormatter(formatter)
fh.setFormatter(formatter)

# Avoid adding handlers multiple times
if not logger.handlers:
    logger.addHandler(ch)
    logger.addHandler(fh)
