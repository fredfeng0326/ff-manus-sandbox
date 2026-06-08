#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2026-05-27 11:03
@Author  : fred.feng0326@gmail.com
@File    : shell.py
"""
import os

from app.models.shell import (
    ShellWaitResult,
    ShellWriteResult,
    ShellKillResult, ShellExecuteResult, ShellReadResult,
)
from app.services.shell import ShellService
from fastapi import APIRouter, Depends

from app.interfaces.errors.exceptions import BadRequestException
from app.interfaces.schemas.base import Response
from app.interfaces.schemas.shell import ShellExecuteRequest, ShellReadRequest, ShellWaitRequest, ShellWriteRequest, \
    ShellKillRequest
from app.interfaces.service_dependencies import get_shell_service

router = APIRouter(prefix="/shell", tags=["Shell module"])


@router.post(
    path="/exec-command",
    response_model=Response[ShellExecuteResult],
)
async def exec_command(
        request: ShellExecuteRequest,
        shell_service: ShellService = Depends(get_shell_service),
) -> Response[ShellExecuteResult]:
    """Run a command in the specified shell session."""
    # 1. Create a session_id if one was not provided
    if not request.session_id or request.session_id == "":
        request.session_id = shell_service.create_session_id()

    # 2. Default exec_dir to the home directory if not provided
    if not request.exec_dir or request.exec_dir == "":
        request.exec_dir = os.path.expanduser("~")

    # 3. Execute the command via the service
    result = await shell_service.exec_command(
        session_id=request.session_id,
        exec_dir=request.exec_dir,
        command=request.command,
    )

    return Response.success(data=result)


@router.post(
    path="/read-shell-output",
    response_model=Response[ShellReadResult]
)
async def read_shell_output(
        request: ShellReadRequest,
        shell_service: ShellService = Depends(get_shell_service),
) -> Response[ShellReadResult]:
    """Read shell command output by session id and console flag."""
    # 1. Validate shell session id
    if not request.session_id or request.session_id == "":
        raise BadRequestException("Shell session ID is empty. Please verify and try again.")

    # 2. Fetch command output via the service
    result = await shell_service.read_shell_output(request.session_id, request.console)

    return Response.success(data=result)


@router.post(
    path="/wait-process",
    response_model=Response[ShellWaitResult],
)
async def wait_process(
        request: ShellWaitRequest,
        shell_service: ShellService = Depends(get_shell_service),
) -> Response[ShellWaitResult]:
    """Wait for the process by session id and return the wait result."""
    # 1. Validate shell session id
    if not request.session_id or request.session_id == "":
        raise BadRequestException("Shell session ID is empty. Please verify and try again.")

    # 2. Wait for the subprocess via the service
    result = await shell_service.wait_process(request.session_id, request.seconds)

    return Response.success(
        msg=f"Process finished with return code: {result.returncode}",
        data=result,
    )


@router.post(
    path="/write-shell-input",
    response_model=Response[ShellWriteResult],
)
async def write_shell_input(
        request: ShellWriteRequest,
        shell_service: ShellService = Depends(get_shell_service),
) -> Response[ShellWriteResult]:
    """Write input to the subprocess by session id, content, and Enter key flag."""
    # 1. Validate shell session id
    if not request.session_id or request.session_id == "":
        raise BadRequestException("Shell session ID is empty. Please verify and try again.")

    # 2. Write data to the subprocess via the service
    result = await shell_service.write_shell_input(
        session_id=request.session_id,
        input_text=request.input_text,
        press_enter=request.press_enter,
    )

    return Response.success(
        msg="Data written to process successfully",
        data=result,
    )


@router.post(
    path="/kill-process",
    response_model=Response[ShellKillResult],
)
async def kill_process(
        request: ShellKillRequest,
        shell_service: ShellService = Depends(get_shell_service),
) -> Response[ShellKillResult]:
    """Terminate the session for the given shell session id."""
    # 1. Validate shell session id
    if not request.session_id or request.session_id == "":
        raise BadRequestException("Shell session ID is empty. Please verify and try again.")

    # 2. Close the shell session via the service
    result = await shell_service.kill_process(request.session_id)

    return Response.success(
        msg="Process terminated" if result.status == "terminated" else "Process already finished",
        data=result,
    )
