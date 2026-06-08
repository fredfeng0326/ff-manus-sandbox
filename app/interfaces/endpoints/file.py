#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2026-05-27 10:52
@Author  : fred.feng0326@gmail.com
@File    : file.py
"""
import os.path

from app.interfaces.schemas.base import Response
from app.interfaces.schemas.file import (
    FileReadRequest,
    FileWriteRequest,
    FileReplaceRequest,
    FileSearchRequest,
    FileFindRequest,
    FileCheckRequest,
    FileDeleteRequest
)
from app.interfaces.service_dependencies import get_file_service
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
from app.services.file import FileService
from fastapi import APIRouter, Depends, UploadFile, File, Form
from fastapi.responses import FileResponse

# File module routes
router = APIRouter(prefix="/file", tags=["File module"])


@router.post(
    path="/read-file",
    response_model=Response[FileReadResult],
)
async def read_file(
        request: FileReadRequest,
        file_service: FileService = Depends(get_file_service),
) -> Response[FileReadResult]:
    """Read file content in the sandbox from the request payload."""
    result = await file_service.read_file(
        filepath=request.filepath,
        start_line=request.start_line,
        end_line=request.end_line,
        sudo=request.sudo,
        max_length=request.max_length,
    )

    return Response.success(
        msg="File content read successfully",
        data=result,
    )


@router.post(
    path="/write-file",
    response_model=Response[FileWriteResult],
)
async def write_file(
        request: FileWriteRequest,
        file_service: FileService = Depends(get_file_service),
) -> Response[FileWriteResult]:
    """Write content to the specified file from the request payload."""
    result = await file_service.write_file(
        filepath=request.filepath,
        content=request.content,
        append=request.append,
        leading_newline=request.leading_newline,
        trailing_newline=request.trailing_newline,
        sudo=request.sudo,
    )

    return Response.success(
        msg="File content written successfully",
        data=result,
    )


@router.post(
    path="/replace-in-file",
    response_model=Response[FileReplaceResult],
)
async def replace_in_file(
        request: FileReplaceRequest,
        file_service: FileService = Depends(get_file_service),
) -> Response[FileReplaceResult]:
    """Replace part of the file content from the request payload."""
    result = await file_service.replace_in_file(
        filepath=request.filepath,
        old_str=request.old_str,
        new_str=request.new_str,
        sudo=request.sudo,
    )

    return Response.success(
        msg=f"File content replaced; {result.replaced_count} occurrence(s) updated",
        data=result,
    )


@router.post(
    path="/search-in-file",
    response_model=Response[FileSearchResult],
)
async def search_in_file(
        request: FileSearchRequest,
        file_service: FileService = Depends(get_file_service),
) -> Response[FileSearchResult]:
    """Search the specified file content from the request payload."""
    result = await file_service.search_in_file(
        filepath=request.filepath,
        regex=request.regex,
        sudo=request.sudo,
    )

    return Response.success(
        msg=f"File search completed; found {len(result.matches)} match(es)",
        data=result,
    )


@router.post(
    path="/find-files",
    response_model=Response[FileFindResult],
)
async def find_files(
        request: FileFindRequest,
        file_service: FileService = Depends(get_file_service),
) -> Response[FileFindRequest]:
    """Find files by directory and glob pattern from the request payload."""
    result = await file_service.find_files(
        dir_path=request.dir_path,
        glob_pattern=request.glob_pattern,
    )

    return Response.success(
        msg=f"Search completed; found {len(result.files)} file(s)",
        data=result,
    )


@router.post(
    path="/upload-file",
    response_model=Response[FileUploadResult],
)
async def upload_file(
        file: UploadFile = File(...),  # Uploaded file source
        filepath: str = Form(None),  # Target upload path
        file_service: FileService = Depends(get_file_service),
) -> Response[FileUploadResult]:
    """Upload a file to the sandbox from the file source and path."""
    # 1. Use a temp path if filepath is not provided
    if not filepath:
        filepath = f"/tmp/{file.filename}"

    # 2. Upload the file to the sandbox via the service
    result = await file_service.upload_file(file=file, filepath=filepath)

    return Response.success(
        msg="File uploaded successfully",
        data=result,
    )


@router.get(path="/download-file")
async def download_file(
        filepath: str,
        file_service: FileService = Depends(get_file_service),
) -> FileResponse:
    """Download the file at the given filepath."""
    # 1. Ensure the file exists
    await file_service.ensure_file(filepath)

    # 2. Extract the filename
    filename = os.path.basename(filepath)

    # 3. Return the file download response
    return FileResponse(
        path=filepath,
        filename=filename,
        media_type="application/octet-stream",
    )


@router.post(
    path="/check-file-exists",
    response_model=Response[FileCheckResult],
)
async def check_file_exists(
        request: FileCheckRequest,
        file_service: FileService = Depends(get_file_service),
) -> Response[FileCheckResult]:
    """Check whether a file exists at the given path."""
    result = await file_service.check_file_exists(filepath=request.filepath)

    return Response.success(
        msg="File exists" if result.exists else "File does not exist",
        data=result,
    )


@router.post(
    path="/delete-file",
    response_model=Response[FileDeleteResult],
)
async def delete_file(
        request: FileDeleteRequest,
        file_service: FileService = Depends(get_file_service),
) -> Response[FileDeleteResult]:
    """Delete the file at the given path."""
    result = await file_service.delete_file(
        filepath=request.filepath,
    )

    return Response.success(
        msg="File deleted successfully",
        data=result,
    )
