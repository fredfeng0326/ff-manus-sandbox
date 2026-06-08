#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2026-05-27 11:16
@Author  : fred.feng0326@gmail.com
@File    : config.py
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Base configuration for the sandbox API service."""
    log_level: str = "INFO"  # Log level
    server_timeout_minutes: int = 60  # Server timeout in minutes

    # Pydantic v2 settings for environment variable loading
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache()
def get_settings() -> Settings:
    return Settings()
