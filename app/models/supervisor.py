#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2026-06-08 10:28
@Author  : fred.feng0326@gmail.com
@File    : supervisor.py
"""
from typing import Optional, Any

from pydantic import BaseModel, Field


class ProcessInfo(BaseModel):
    """Process information model."""
    name: str = Field(..., description="Process name")
    group: str = Field(..., description="Process group")
    description: str = Field(..., description="Process description")
    start: int = Field(..., description="Process start timestamp")
    stop: int = Field(..., description="Process stop timestamp")
    now: int = Field(..., description="Current timestamp")
    state: int = Field(..., description="State code")
    statename: str = Field(..., description="State name")
    spawnerr: str = Field(..., description="Spawn error")
    exitstatus: int = Field(..., description="Exit status")
    logfile: str = Field(..., description="Log file")
    stdout_logfile: str = Field(..., description="Stdout log file")
    stderr_logfile: str = Field(..., description="Stderr log file")
    pid: int = Field(..., description="Process ID")


class SupervisorActionResult(BaseModel):
    """Supervisor action execution result."""
    status: str = Field(..., description="Execution status")
    result: Optional[Any] = Field(default=None, description="Execution result")
    stop_result: Optional[Any] = Field(default=None, description="Stop result")
    start_result: Optional[Any] = Field(default=None, description="Start result")
    shutdown_result: Optional[Any] = Field(default=None, description="Shutdown result")


class SupervisorTimeout(BaseModel):
    """Supervisor timed shutdown model."""
    status: Optional[str] = Field(default=None, description="Timeout setting status")
    active: bool = Field(default=False, description="Whether timed shutdown is active")
    shutdown_time: Optional[str] = Field(default=None, description="Shutdown time")
    timeout_minutes: Optional[float] = Field(default=None, description="Timeout duration in minutes")
    remaining_seconds: Optional[float] = Field(default=None, description="Remaining timeout seconds")
