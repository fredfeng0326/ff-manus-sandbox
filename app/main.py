#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2026-05-27 10:51
@Author  : fred.feng0326@gmail.com
@File    : main.py
"""
import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.middleware import auto_extend_timeout_middleware
from app.interfaces.endpoints.routes import router
from app.interfaces.errors.exception_handler import register_exception_handlers


def setup_logging() -> None:
    """Configure logging for the sandbox API application."""
    # 1. Load project settings
    settings = get_settings()

    # 2. Get the root logger
    root_logger = logging.getLogger()

    # 3. Set root logger level
    log_level = getattr(logging, settings.log_level)
    root_logger.setLevel(log_level)

    # 4. Define the log output format
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 5. Create a console log handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)

    # 6. Add the console handler to the root logger
    root_logger.addHandler(console_handler)

    root_logger.info("Sandbox system logging module initialized")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan context manager."""
    # 1. Operations before application startup
    logger.info("MoocManus sandbox is initializing")

    try:
        # 2. Lifespan checkpoint
        yield
    finally:
        # 3. Operations after application shutdown
        logger.info("MoocManus sandbox shut down successfully")


# 1. Initialize the logging system
setup_logging()
logger = logging.getLogger(__name__)

# 2. Define FastAPI route tags
openapi_tags = [
    {
        "name": "File module",
        "description": "Includes API endpoints for **file CRUD operations** to manage sandbox files.",
    },
    {
        "name": "Shell module",
        "description": "Includes API endpoints for **executing/inspecting shell sessions** inside the sandbox.",
    },
    {
        "name": "Supervisor module",
        "description": "Implements sandbox system management logic through APIs plus Supervisor.",
    },
]

# 3. Create FastAPI application instance
app = FastAPI(
    title="FF Manus sandbox system",
    description="This sandbox comes preinstalled with Chrome, Python, and Node.js, and supports shell execution and file management.",
    openapi_tags=openapi_tags,
    lifespan=lifespan,
    version="1.0.0",
)

# 4. Add auto-extend and CORS middleware
app.middleware("http")(auto_extend_timeout_middleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 5. Register exception handlers
register_exception_handlers(app)

# 6. Include routes
app.include_router(router, prefix="/api")
