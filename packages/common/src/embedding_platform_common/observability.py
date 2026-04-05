from __future__ import annotations

import json
import logging
import os
from typing import Any


def configure_logging(service_name: str) -> logging.Logger:
    level_name = os.getenv("APP_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(level=level, format="%(message)s")
    logger = logging.getLogger(service_name)
    logger.setLevel(level)
    return logger


def log_event(logger: logging.Logger, event: str, **fields: Any) -> None:
    payload = {"event": event, **fields}
    logger.info(json.dumps(payload, ensure_ascii=False, sort_keys=True))

