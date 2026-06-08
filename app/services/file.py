#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2026-06-08 10:26
@Author  : fred.feng0326@gmail.com
@File    : file.py
"""
import asyncio
import glob
import logging
import os.path
import re
from typing import Optional

from fastapi import UploadFile

from app.interfaces.errors.exceptions import (
    NotFoundException,
    BadRequestException,
    AppException
)
from app.models.file import (
    FileReadResult,
    FileWriteResult,
    FileReplaceResult,
    FileSearchResult,
    FileFindResult,
    FileUploadResult,
    FileCheckResult,
    FileDeleteResult
)

logger = logging.getLogger(__name__)


class FileService:
    """File sandbox service."""

    def __init__(self) -> None:
        pass

    @classmethod
    async def read_file(
            cls,
            filepath: str,
            start_line: Optional[int] = None,
            end_line: Optional[int] = None,
            sudo: bool = False,
            max_length: Optional[int] = 10000,
    ) -> FileReadResult:
        """Read file content by filepath, line range, privileges, and max length."""
        try:
            # 1. Check whether the file is accessible with current privileges
            if not os.path.exists(filepath) and not sudo:
                logger.error(f"File to read does not exist or is not accessible: {filepath}")
                raise NotFoundException(f"File to read does not exist or is not accessible: {filepath}")

            # 2. Use UTF-8 encoding on Ubuntu
            encoding = "utf-8"

            # 3. Use shell command when sudo is enabled
            if sudo:
                # 4. Read file content with sudo cat
                command = f"sudo cat '{filepath}'"
                process = await asyncio.create_subprocess_shell(
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )

                # 5. Read subprocess output and wait for completion
                stdout, stderr = process.communicate()

                # 6. Ensure subprocess exited successfully
                if process.returncode != 0:
                    raise BadRequestException(f"Failed to read file: {stderr.decode()}")

                # 7. Decode output content
                content = stdout.decode(encoding, errors="replace")
            else:
                # 8. Inner function for file reading
                def async_read_file() -> str:
                    try:
                        with open(filepath, "r", encoding=encoding) as f:
                            return f.read()
                    except Exception as async_read_file_exception:
                        raise AppException(msg=f"Failed to read file: {str(async_read_file_exception)}")

                # 9. Read file in a worker thread via asyncio
                content = await asyncio.to_thread(async_read_file)

            # 10. Apply line range when provided
            if start_line is not None or end_line is not None:
                # 11. Split content into lines and extract the requested range
                lines = content.splitlines()
                start = start_line if start_line is not None else 0
                end = end_line if end_line is not None else len(lines)
                content = "\n".join(lines[start:end])

            # 12. Truncate content when exceeding max length
            if max_length is not None and 0 < max_length < len(content):
                content = content[:max_length] + "(truncated)"

            return FileReadResult(filepath=filepath, content=content)
        except Exception as e:
            # 13. Re-raise known exceptions, wrap others
            if isinstance(e, BadRequestException) or isinstance(e, AppException):
                raise
            raise AppException(f"File read failed: {str(e)}")

    @classmethod
    async def write_file(
            cls,
            filepath: str,
            content: str,
            append: bool = False,
            leading_newline: bool = False,
            trailing_newline: bool = False,
            sudo: bool = False,
    ) -> FileWriteResult:
        """Write content to the specified file by filepath."""
        try:
            # 1. Build the final content to write
            if leading_newline:
                content = "\n" + content
            if trailing_newline:
                content = content + "\n"

            # 2. For sudo, write to a temp file first, then copy to target file
            if sudo:
                # 3. Choose append or overwrite mode for shell redirection
                mode = ">>" if append else ">"

                # 4. Create a temporary file
                temp_file = f"/tmp/file_write_{os.getpid()}.tmp"

                # 5. Inner function to write temp file in a worker thread
                def async_write_temp_file() -> int:
                    with open(temp_file, "w", encoding="utf-8") as f:
                        f.write(content)
                    return len(content.encode("utf-8"))

                # 6. Write temp file via asyncio worker thread
                bytes_written = await asyncio.to_thread(async_write_temp_file)

                # 7. Copy temp file to target file via shell command
                command = f"sudo bash -c \"cat {temp_file} {mode} {filepath}\""
                process = await asyncio.create_subprocess_shell(
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )

                # 8. Wait for subprocess completion
                stdout, stderr = await process.communicate()

                # 9. Ensure subprocess exited successfully
                if process.returncode != 0:
                    raise BadRequestException(f"Failed to write file content: {stderr.decode()}")

                # 10. Remove temporary file
                os.unlink(temp_file)
            else:
                # 11. Non-sudo path: ensure parent directory exists
                os.makedirs(os.path.dirname(filepath), exist_ok=True)

                # 12. Inner function for async file writing
                def async_write_file() -> int:
                    write_mode = "a" if append else "w"
                    with open(filepath, write_mode, encoding="utf-8") as f:
                        return f.write(content)

                # 13. Write file via asyncio worker thread
                bytes_written = await asyncio.to_thread(async_write_file)

            return FileWriteResult(
                filepath=filepath,
                bytes_written=bytes_written,
            )
        except Exception as e:
            # 14. Re-raise known exceptions, wrap others
            logger.error(f"Failed to write file content: {str(e)}")
            if isinstance(e, BadRequestException):
                raise
            raise AppException(f"Failed to write file content: {str(e)}")

    async def replace_in_file(
            self,
            filepath: str,
            old_str: str,
            new_str: str,
            sudo: bool = False,
    ) -> FileReplaceResult:
        """Replace specified content in a file."""
        # 1. Read current file content
        file_read_result = await self.read_file(filepath=filepath, sudo=sudo, max_length=None)
        content = file_read_result.content

        # 2. Count occurrences; skip write when none found
        replaced_count = content.count(old_str)
        if replaced_count == 0:
            return FileReplaceResult(filepath=filepath, replaced_count=replaced_count)

        # 3. Replace old content
        new_content = content.replace(old_str, new_str)

        # 4. Write updated content back to file
        await self.write_file(
            filepath=filepath,
            content=new_content,
            sudo=sudo,
        )

        return FileReplaceResult(filepath=filepath, replaced_count=replaced_count)

    async def search_in_file(
            self,
            filepath: str,
            regex: str,
            sudo: bool = False,
    ) -> FileSearchResult:
        """Search file content by filepath and regex pattern."""
        # 1. Read current file content
        file_read_result = await self.read_file(filepath=filepath, sudo=sudo, max_length=None)
        content = file_read_result.content

        # 2. Split content into lines
        lines = content.splitlines()
        matches = []
        line_numbers = []

        # 3. Compile regex pattern
        try:
            pattern = re.compile(regex)
        except Exception as e:
            raise BadRequestException(f"Invalid regular expression [{regex}]: {str(e)}")

        # 4. Match lines in a worker thread to avoid long IO blocking
        def async_matches():
            nonlocal matches, line_numbers
            for idx, line in enumerate(lines):
                if pattern.match(line):
                    matches.append(line)
                    line_numbers.append(idx)

        # 5. Run matching via asyncio worker thread
        await asyncio.to_thread(async_matches)

        return FileSearchResult(
            filepath=filepath,
            matches=matches,
            line_numbers=line_numbers,
        )

    @classmethod
    async def find_files(cls, dir_path: str, glob_pattern: str) -> FileFindResult:
        """Find files by directory path and glob pattern."""
        # 1. Ensure directory exists
        if not os.path.exists(dir_path):
            raise NotFoundException(f"Directory does not exist: {dir_path}")

        # 2. Run glob in a worker thread to avoid IO blocking
        def async_glob():
            search_pattern = os.path.join(dir_path, glob_pattern)
            return glob.glob(search_pattern, recursive=True)

        # 3. Execute glob via asyncio worker thread
        files = await asyncio.to_thread(async_glob)

        return FileFindResult(dir_path=dir_path, files=files)

    @classmethod
    async def upload_file(cls, file: UploadFile, filepath: str) -> FileUploadResult:
        """Upload a file to the sandbox from file source and target path."""
        try:
            # 1. Upload in 8KB chunks
            chunk_size = 1024 * 8
            file_size = 0

            # 2. Ensure upload directory exists
            os.makedirs(os.path.dirname(filepath), exist_ok=True)

            # 3. Inner function for chunked upload to avoid blocking
            def async_write_file():
                nonlocal file_size
                with open(filepath, "wb") as f:
                    while True:
                        chunk = file.file.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        file_size += len(chunk)

            # 4. Run upload via asyncio worker thread
            await asyncio.to_thread(async_write_file)

            return FileUploadResult(
                filepath=filepath,
                file_size=file_size,
                success=True,
            )
        except Exception as e:
            logger.error(f"Failed to upload file to sandbox: {str(e)}")
            raise AppException(f"Failed to upload file to sandbox: {str(e)}")

    @classmethod
    async def ensure_file(cls, filepath: str) -> None:
        """Ensure the file at filepath exists."""
        if not os.path.exists(filepath):
            raise NotFoundException(f"File does not exist: {filepath}")

    @classmethod
    async def check_file_exists(cls, filepath: str) -> FileCheckResult:
        """Check whether a file exists at the given path."""
        return FileCheckResult(
            filepath=filepath,
            exists=os.path.exists(filepath),
        )

    async def delete_file(self, filepath: str) -> FileDeleteResult:
        """Delete the file at the given path."""
        # 1. Ensure file exists
        await self.ensure_file(filepath)

        try:
            # 2. Delete file
            os.remove(filepath)
            return FileDeleteResult(filepath=filepath, deleted=True)
        except Exception as e:
            logger.error(f"Failed to delete file {filepath}: {str(e)}")
            raise AppException(f"Failed to delete file {filepath}: {str(e)}")
