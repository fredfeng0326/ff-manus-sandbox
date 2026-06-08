#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2026-05-27 11:03
@Author  : fred.feng0326@gmail.com
@File    : routes.py
"""
from fastapi import APIRouter

from . import file, shell, supervisor


def create_api_routes() -> APIRouter:
    """Create API routes covering all sandbox project endpoints."""
    # 1. Create the APIRouter instance
    api_router = APIRouter()

    # 2. Include routers from each module
    api_router.include_router(file.router)
    api_router.include_router(shell.router)
    api_router.include_router(supervisor.router)

    return api_router


router = create_api_routes()
