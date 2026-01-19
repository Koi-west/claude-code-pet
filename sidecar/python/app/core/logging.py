# File: python/app/core/logging.py
# Project: Tip Desktop Assistant
# Description: Logging setup for the sidecar using structlog and rotating file handlers with env-controlled level.

# Copyright (C) 2025 Tencent. All rights reserved.
# License: Licensed under the License Terms of Youtu-Tip (see license at repository root).
# Warranty: Provided on an "AS IS" basis, without warranties or conditions of any kind.
# Modifications must retain this notice.

from __future__ import annotations

import logging
import os
from logging.handlers import TimedRotatingFileHandler

import structlog

from .config import LOG_DIR


def _resolve_log_level() -> int:
    level_name = os.environ.get('TIP_LOG_LEVEL', 'DEBUG').upper()
    return getattr(logging, level_name, logging.INFO)


def setup_logging() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_level = _resolve_log_level()
    file_handler = TimedRotatingFileHandler(
        LOG_DIR / 'sidecar.log',
        when='midnight',
        backupCount=7,
        encoding='utf-8',
    )
    stream_handler = logging.StreamHandler()
    file_handler.setLevel(log_level)
    stream_handler.setLevel(log_level)
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        handlers=[file_handler, stream_handler],
    )
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt='iso'),
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.dev.ConsoleRenderer(colors=False),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
    )
