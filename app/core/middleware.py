#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2026-05-28 11:17
@Author  : fred.feng0326@gmail.com
@File    : middleware.py
"""
import logging

from fastapi import Request

from app.core.config import get_settings
from app.interfaces.service_dependencies import get_supervisor_service

logger = logging.getLogger(__name__)


async def auto_extend_timeout_middleware(request: Request, call_next):
    """Use middleware to extend timeout-destroy duration for each API request."""
    # 1. Get system settings and supervisor service
    settings = get_settings()
    supervisor_service = get_supervisor_service()

    # 2. Extend timeout by 3 minutes only when conditions are met
    ignore_paths = (
        "/api/supervisor/activate-timeout",
        "/api/supervisor/extend-timeout",
        "/api/supervisor/cancel-timeout",
        "/api/supervisor/timeout-status",
    )
    if (
            settings.server_timeout_minutes is not None
            and supervisor_service.timeout_active
            and request.url.path.startswith("/api/")
            and not request.url.path.startswith(ignore_paths)
            and supervisor_service.expand_enabled
    ):
        try:
            await supervisor_service.extend_timeout(3)
            logger.debug("Auto-extended timeout due to API request: %s", request.url.path)
        except Exception as e:
            logger.warning("Failed to auto-extend timeout: %s", str(e))

    response = await call_next(request)
    return response
