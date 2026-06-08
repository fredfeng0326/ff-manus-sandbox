#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2026-06-01 14:08
@Author  : fred.feng0326@gmail.com
@File    : shell.py
"""
import asyncio.subprocess
from typing import Optional, List

from pydantic import BaseModel, Field, ConfigDict


class ConsoleRecord(BaseModel):
    """Shell console record for a command line."""
    ps1: str = Field(..., description="PS1 prompt")
    command: str = Field(..., description="Executed command")
    output: str = Field(default="", description="Command output")


class Shell(BaseModel):
    """Shell session model."""
    process: asyncio.subprocess.Process = Field(..., description="Subprocess in the session")
    exec_dir: str = Field(..., description="Session working directory")
    output: str = Field(..., description="Session output")
    console_records: List[ConsoleRecord] = Field(default_factory=list, description="Console records for the shell session")

    # Pydantic v2 config (v1 used an inner Config class)
    model_config = ConfigDict(
        arbitrary_types_allowed=True,  # Allow native or custom Python types as field types
    )


class ShellWaitResult(BaseModel):
    """Result model for waiting on a session."""
    returncode: int = Field(..., description="Subprocess return code")


class ShellReadResult(BaseModel):
    """Shell command output result model."""
    session_id: str = Field(..., description="Shell session id")
    output: str = Field(..., description="Shell session output")
    console_records: List[ConsoleRecord] = Field(default_factory=list, description="Console records")


class ShellExecuteResult(BaseModel):
    """Shell command execution result."""
    session_id: str = Field(..., description="Shell session id")
    command: str = Field(..., description="Executed command")
    status: str = Field(..., description="Command execution status")
    returncode: Optional[int] = Field(default=None, description="Process return code; set only when the process has finished")
    output: Optional[str] = Field(default=None, description="Process output; set only when the process has finished")


class ShellWriteResult(BaseModel):
    """Shell write operation result model."""
    status: str = Field(..., description="Write status")


class ShellKillResult(BaseModel):
    """Shell process termination result."""
    status: str = Field(..., description="Process status")
    returncode: int = Field(..., description="Process return code")
