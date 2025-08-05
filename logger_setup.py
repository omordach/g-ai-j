"""Application logging setup.

This configuration logs messages to STDOUT so that container orchestrators can
collect log output without relying on a file inside the container.
"""

import logging
import sys

logger = logging.getLogger("g-ai-j")
logger.setLevel(logging.INFO)

codex/map-g-ai-j.log-to-docker-volume
# Stream handler that writes to STDOUT
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)

# Formatter
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
handler.setFormatter(formatter)

# Avoid adding handlers multiple times
if not logger.hasHandlers():
    logger.addHandler(handler)

