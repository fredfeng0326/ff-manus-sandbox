#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2026-06-08 10:23
@Author  : fred.feng0326@gmail.com
@File    : file.py
"""
from typing import Optional, List

from pydantic import BaseModel, Field


class FileReadResult(BaseModel):
    """File read result."""
    filepath: str = Field(..., description="Absolute path of the file read")
    content: str = Field(..., description="File content read")


class FileWriteResult(BaseModel):
    """File write result."""
    filepath: str = Field(..., description="Absolute path of the file written")
    bytes_written: Optional[int] = Field(default=None, description="Number of bytes written")


class FileReplaceResult(BaseModel):
    """File content replacement result model."""
    filepath: str = Field(..., description="Absolute path of the modified file")
    replaced_count: int = Field(default=0, description="Number of replacements made")


class FileSearchResult(BaseModel):
    """File search result."""
    filepath: str = Field(..., description="Absolute path of the searched file")
    matches: List[str] = Field(default_factory=list, description="List of matched content")
    line_numbers: List[int] = Field(default_factory=list, description="List of matched line numbers")


class FileFindResult(BaseModel):
    """File find result."""
    dir_path: str = Field(..., description="Absolute path of the searched directory")
    files: List[str] = Field(default_factory=list, description="List of files found")


class FileUploadResult(BaseModel):
    """File upload result."""
    filepath: str = Field(..., description="Absolute path of the uploaded file")
    file_size: int = Field(default=0, description="Uploaded file size in bytes")
    success: bool = Field(..., description="Whether the upload succeeded")


class FileCheckResult(BaseModel):
    """File existence check result."""
    filepath: str = Field(..., description="Absolute path of the file checked")
    exists: bool = Field(..., description="Whether the file exists")


class FileDeleteResult(BaseModel):
    """File deletion result model."""
    filepath: str = Field(..., description="Absolute path of the deleted file")
    deleted: bool = Field(..., description="Whether the file was deleted successfully")
