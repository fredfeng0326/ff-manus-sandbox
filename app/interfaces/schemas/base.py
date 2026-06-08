#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2026-05-27 10:59
@Author  : fred.feng0326@gmail.com
@File    : base.py
"""
from typing import TypeVar, Generic, Optional

from pydantic import BaseModel, Field

T = TypeVar("T")


class Response(BaseModel, Generic[T]):
    """Base API response structure, inheriting from BaseModel and defining a generic payload."""
    code: int = 200  # Business status code, consistent with the HTTP status code
    msg: str = "success"  # Response message hint
    data: Optional[T] = Field(default_factory=dict)  # Response data defaults to an empty dict

    @staticmethod
    def success(data: Optional[T] = None, msg: str = "success") -> "Response[T]":
        """Success message: pass data + msg; code is fixed to 200."""
        return Response(code=200, msg=msg, data=data if data is not None else {})

    @staticmethod
    def fail(code: int, msg: str, data: Optional[T] = None) -> "Response[T]":
        """Failure message: includes code + msg + data."""
        return Response(code=code, msg=msg, data=data if data is not None else {})
