#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2026-05-27 11:14
@Author  : fred.feng0326@gmail.com
@File    : service_dependencies.py
"""
from functools import lru_cache

from app.services.file import FileService
from app.services.shell import ShellService
from app.services.supervisor import SupervisorService


@lru_cache()
def get_shell_service() -> ShellService:
    return ShellService()


@lru_cache()
def get_file_service() -> FileService:
    return FileService()


@lru_cache()
def get_supervisor_service() -> SupervisorService:
    return SupervisorService()
