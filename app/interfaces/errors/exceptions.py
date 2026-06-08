#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2026-05-28 11:18
@Author  : fred.feng0326@gmail.com
@File    : exceptions.py
"""
import logging
from typing import Any

from fastapi import status

logger = logging.getLogger(__name__)


class AppException(Exception):
    """Base application exception."""

    def __init__(
            self,
            msg: str = "Application error occurred. Please try again later.",
            status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
            data: Any = None
    ) -> None:
        """Initialize exception fields."""
        # 1. Initialize payload fields
        self.msg = msg
        self.status_code = status_code
        self.data = data

        # 2. Log details and call the parent constructor
        logger.error(f"Sandbox error occurred: {msg} (code: {status_code})")
        super().__init__(self.msg)


class NotFoundException(AppException):
    """Resource not found exception."""

    def __init__(self, msg: str = "Resource not found. Please verify and try again.") -> None:
        super().__init__(msg=msg, status_code=status.HTTP_404_NOT_FOUND)


class BadRequestException(AppException):
    """Bad request exception."""

    def __init__(self, msg: str = "Invalid client request. Please check and retry.") -> None:
        super().__init__(msg=msg, status_code=status.HTTP_400_BAD_REQUEST)
