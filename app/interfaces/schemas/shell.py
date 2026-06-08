#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2026-05-27 11:10
@Author  : fred.feng0326@gmail.com
@File    : shell.py
"""
from typing import Optional

from pydantic import BaseModel, Field


class ShellExecuteRequest(BaseModel):
    """Request schema for executing a shell command."""
    session_id: Optional[str] = Field(default=None, description="Unique identifier of the target shell session")
    exec_dir: Optional[str] = Field(default=None, description="Working directory for command execution (must be an absolute path)")
    command: str = Field(..., description="Shell command to execute")


class ShellReadRequest(BaseModel):
    """Request schema for reading shell output."""
    session_id: str = Field(..., description="Unique identifier of the target shell session")
    console: Optional[bool] = Field(default=None, description="Whether to return the console record list")


class ShellWaitRequest(BaseModel):
    """Request schema for waiting on shell command execution."""
    session_id: str = Field(..., description="Unique identifier of the target shell session")
    seconds: Optional[int] = Field(default=None, description="Wait duration in seconds")


class ShellWriteRequest(BaseModel):
    """Request schema for writing data to a subprocess."""
    session_id: str = Field(..., description="Unique identifier of the target shell session")
    input_text: str = Field(..., description="Text content to write")
    press_enter: bool = Field(default=True, description="Whether to press Enter after writing")


class ShellKillRequest(BaseModel):
    """Request schema for terminating a process."""
    session_id: str = Field(..., description="Unique identifier of the target shell session")
