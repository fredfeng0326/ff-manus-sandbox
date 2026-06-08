#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2026-05-27 10:59
@Author  : fred.feng0326@gmail.com
@File    : file.py
"""
from typing import Optional

from pydantic import BaseModel, Field


class FileReadRequest(BaseModel):
    """Request schema for reading a file."""
    filepath: str = Field(..., description="Absolute path of the file to read")
    start_line: Optional[int] = Field(default=None, description="(Optional) Start line index, 0-based")
    end_line: Optional[int] = Field(default=None, description="(Optional) End line index, exclusive")
    sudo: Optional[bool] = Field(default=False, description="(Optional) Whether to use sudo privileges")
    max_length: Optional[int] = Field(default=10000, description="(Optional) Maximum length of content to return")


class FileWriteRequest(BaseModel):
    """Request schema for writing a file."""
    filepath: str = Field(..., description="Absolute path of the file to write")
    content: str = Field(..., description="Text content to write")
    append: Optional[bool] = Field(default=False, description="(Optional) Whether to append instead of overwrite")
    leading_newline: Optional[bool] = Field(default=False, description="(Optional) Whether to prepend a leading newline")
    trailing_newline: Optional[bool] = Field(default=False, description="(Optional) Whether to append a trailing newline")
    sudo: Optional[bool] = Field(default=False, description="(Optional) Whether to use sudo privileges")


class FileReplaceRequest(BaseModel):
    """Request schema for find-and-replace in a file."""
    filepath: str = Field(..., description="Absolute path of the file to modify")
    old_str: str = Field(..., description="String to replace")
    new_str: str = Field(..., description="Replacement string")
    sudo: Optional[bool] = Field(default=False, description="(Optional) Whether to use sudo privileges")


class FileSearchRequest(BaseModel):
    """Request schema for searching file content."""
    filepath: str = Field(..., description="Absolute path of the file to search")
    regex: str = Field(..., description="Regular expression to search for")
    sudo: Optional[bool] = Field(default=False, description="(Optional) Whether to use sudo privileges")


class FileFindRequest(BaseModel):
    """Request schema for finding files by pattern."""
    dir_path: str = Field(..., description="Absolute path of the directory to search")
    glob_pattern: str = Field(..., description="Filename pattern (glob syntax)")


class FileCheckRequest(BaseModel):
    """Request schema for checking whether a file exists."""
    filepath: str = Field(..., description="Absolute path of the file to check")


class FileDeleteRequest(BaseModel):
    """Request schema for deleting a file."""
    filepath: str = Field(..., description="Absolute path of the file to delete")
