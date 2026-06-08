#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2026-06-01 14:07
@Author  : fred.feng0326@gmail.com
@File    : shell.py
"""
import asyncio
import codecs
import getpass
import logging
import os.path
import re
import socket
import uuid
from typing import Dict, Optional, List

from app.interfaces.errors.exceptions import (
    BadRequestException,
    AppException,
    NotFoundException,
)
from app.models.shell import (
    Shell,
    ConsoleRecord,
    ShellWaitResult,
    ShellWriteResult,
    ShellKillResult, ShellReadResult, ShellExecuteResult,
)

logger = logging.getLogger(__name__)


class ShellService:
    """Shell command service."""
    active_shells: Dict[str, Shell]

    def __init__(self) -> None:
        self.active_shells = {}

    @classmethod
    def _get_display_path(cls, path: str) -> str:
        """Get display path, replacing the home directory with ~."""
        # 1. Resolve the user home directory in a cross-platform way
        home_dir = os.path.expanduser("~")
        logger.debug(f"Home directory: {home_dir}, path: {path}")

        # 2. Replace home directory prefix with ~ when applicable
        if path.startswith(home_dir):
            return path.replace(home_dir, "~", 1)
        return path

    def _format_ps1(self, exec_dir: str) -> str:
        """Format the command prompt for better UX, e.g. root@myserver:/var/log $"""
        username = getpass.getuser()
        hostname = socket.gethostname()
        display_dir = self._get_display_path(exec_dir)
        return f"{username}@{hostname}:{display_dir} $"

    @classmethod
    async def _create_process(cls, exec_dir: str, command: str) -> asyncio.subprocess.Process:
        """Create an asyncio-managed subprocess for the given directory and command."""
        # 1. Use /bin/bash as the shell interpreter on Ubuntu
        logger.debug(f"Creating subprocess in {exec_dir} with command {command}")
        shell_exec = "/bin/bash"

        # 3. Create a system subprocess to run the shell command
        return await asyncio.create_subprocess_shell(
            command,  # Command to execute
            executable=shell_exec,  # Shell interpreter
            cwd=exec_dir,
            stdout=asyncio.subprocess.PIPE,  # Pipe to capture stdout
            stderr=asyncio.subprocess.STDOUT,  # Redirect stderr to stdout
            stdin=asyncio.subprocess.PIPE,  # Pipe for stdin
            limit=1024 * 1024,  # Buffer size limit (1MB)
        )

    async def _start_output_reader(self, session_id: str, process: asyncio.subprocess.Process) -> None:
        """Start a coroutine to continuously read process output into the session."""
        # 1. Use UTF-8 encoding on Ubuntu
        logger.debug(f"Starting session output reader: {session_id}")
        encoding = "utf-8"

        # 2. Incremental decoder to avoid split multibyte characters
        decoder = codecs.getincrementaldecoder(encoding)(errors="replace")
        shell = self.active_shells.get(session_id)

        while True:
            # 3. Check whether the subprocess has a stdout pipe
            if process.stdout:
                try:
                    # 4. Read from the buffer (4096 bytes per read)
                    buffer = await process.stdout.read(4096)
                    if not buffer:
                        break

                    # 5. Decode with final=False while stream may continue
                    output = decoder.decode(buffer, final=False)

                    # 6. Ensure the session still exists
                    if shell:
                        # 7. Update session output and console records
                        shell.output += output
                        if shell.console_records:
                            shell.console_records[-1].output += output
                except Exception as e:
                    logger.error(f"Error reading process output: {str(e)}")
                    break
            else:
                break

        logger.debug(f"Output reader finished for session {session_id}")

    @classmethod
    def _remove_ansi_escape_codes(cls, text: str) -> str:
        """Remove ANSI escape sequences from text."""
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        return ansi_escape.sub("", text)

    @classmethod
    def create_session_id(cls) -> str:
        """Create a session id using uuid4."""
        session_id = str(uuid.uuid4())
        logger.info(f"Created new shell session ID: {session_id}")
        return session_id

    def get_console_records(self, session_id: str) -> List[ConsoleRecord]:
        """Get console records for the given session."""
        # 1. Validate session exists
        logger.debug(f"Fetching console records for shell session: {session_id}")
        if session_id not in self.active_shells:
            logger.error(f"Shell session not found: {session_id}")
            raise NotFoundException(f"Shell session not found: {session_id}")

        # 2. Get raw console records
        console_records = self.active_shells[session_id].console_records
        clean_console_records = []

        # 3. Strip ANSI codes from each record output
        for console_record in console_records:
            clean_console_records.append(ConsoleRecord(
                ps1=console_record.ps1,
                command=console_record.command,
                output=self._remove_ansi_escape_codes(console_record.output),
            ))

        return clean_console_records

    async def wait_process(self, session_id: str, seconds: Optional[int] = None) -> ShellWaitResult:
        """Wait for the subprocess to finish by session id and timeout."""
        # 1. Validate session exists
        logger.debug(f"Waiting for process in shell session: {session_id}, timeout: {seconds}s")
        if session_id not in self.active_shells:
            logger.error(f"Shell session not found: {session_id}")
            raise NotFoundException(f"Shell session not found: {session_id}")

        # 2. Get session and subprocess
        shell = self.active_shells[session_id]
        process = shell.process

        try:
            # 3. Default timeout to 60 seconds when unset or invalid
            seconds = 60 if seconds is None or seconds <= 0 else seconds
            await asyncio.wait_for(process.wait(), timeout=seconds)

            # 4. Log and return wait result
            logger.info(f"Process finished with return code: {process.returncode}")
            return ShellWaitResult(returncode=process.returncode)
        except asyncio.TimeoutError:
            # Log and raise BadRequestException
            logger.warning(f"Shell session process wait timed out: {seconds}s")
            raise BadRequestException(f"Shell session process wait timed out: {seconds}s")
        except Exception as e:
            # Log and raise AppException
            logger.error(f"Error while waiting for shell session process: {str(e)}")
            raise AppException(f"Error while waiting for shell session process: {str(e)}")

    async def read_shell_output(self, session_id: str, console: bool = False) -> ShellReadResult:
        """Read shell command output by session id and optional console records flag."""
        # 1. Validate session exists
        logger.debug(f"Reading shell session output: {session_id}")
        if session_id not in self.active_shells:
            logger.error(f"Shell session not found: {session_id}")
            raise NotFoundException(f"Shell session not found: {session_id}")

        # 2. Get session
        shell = self.active_shells[session_id]

        # 3. Clean raw output
        raw_output = shell.output
        clean_output = self._remove_ansi_escape_codes(raw_output)

        # 4. Optionally include console records
        if console:
            console_records = self.get_console_records(session_id)
        else:
            console_records = []

        return ShellReadResult(
            session_id=session_id,
            output=clean_output,
            console_records=console_records,
        )

    async def exec_command(
            self,
            session_id: str,
            exec_dir: Optional[str],
            command: str,
    ) -> ShellExecuteResult:
        """Execute a command in the sandbox by session id, directory, and command."""
        # 1. Log and validate execution directory
        logger.info(f"Executing command in session {session_id}: {command}")
        if not exec_dir or exec_dir == "":
            exec_dir = os.path.expanduser("~")
        if not os.path.exists(exec_dir):
            logger.error(f"Directory does not exist: {exec_dir}")
            raise BadRequestException(f"Directory does not exist: {exec_dir}")

        try:
            # 2. Format PS1 prompt
            ps1 = self._format_ps1(exec_dir)

            # 3. Create or reuse shell session
            if session_id not in self.active_shells:
                # 4. Create a new subprocess
                logger.debug(f"Creating new shell session: {session_id}")
                process = await self._create_process(exec_dir, command)
                self.active_shells[session_id] = Shell(
                    process=process,
                    exec_dir=exec_dir,
                    output="",
                    console_records=[ConsoleRecord(ps1=ps1, command=command, output="")],
                )

                # 5. Start background output reader task
                await asyncio.create_task(self._start_output_reader(session_id, process))
            else:
                # 6. Reuse existing session
                logger.debug(f"Reusing existing shell session: {session_id}")
                shell = self.active_shells[session_id]
                old_process = shell.process

                # 7. Terminate previous process if still running before starting a new command
                if old_process.returncode is None:
                    logger.debug(f"Terminating previous process in session: {session_id}")
                    try:
                        # 8. Gracefully terminate and wait up to 1s
                        old_process.terminate()
                        await asyncio.wait_for(old_process.wait(), timeout=1)
                    except Exception as e:
                        # 9. Fall back to kill on graceful termination failure
                        logger.warning(f"Failed to gracefully terminate process in session {session_id}: {str(e)}")
                        old_process.kill()

                # 10. Create a new subprocess after stopping the old one
                process = await self._create_process(exec_dir, command)

                # 11. Update session state
                shell.process = process
                shell.exec_dir = exec_dir
                shell.output = ""
                shell.console_records.append(ConsoleRecord(ps1=ps1, command=command, output=""))

                # 12. Start background output reader task
                await asyncio.create_task(self._start_output_reader(session_id, process))

            try:

                # 13. Wait for subprocess completion (up to 5s)
                logger.debug(f"Waiting for process to finish in session: {session_id}")
                wait_result = await self.wait_process(session_id, seconds=5)

                # 14. Return completed result when return code is available
                if wait_result.returncode is not None:
                    # 15. Log and read final output
                    logger.debug(f"Shell session process finished with code: {wait_result.returncode}")
                    view_result = await self.read_shell_output(session_id)

                    return ShellExecuteResult(
                        session_id=session_id,
                        command=command,
                        status="completed",
                        returncode=wait_result.returncode,
                        output=view_result.output,
                    )
            except BadRequestException as _:
                # 16. On timeout, let the command continue in the background
                logger.warning(f"Process still running after session wait timeout: {session_id}")
                pass
            except Exception as e:
                # 17. Ignore other wait errors and continue
                logger.warning(f"Exception while waiting for process: {str(e)}")
                pass

            # 18. Return running status while shell execution continues
            return ShellExecuteResult(
                session_id=session_id,
                command=command,
                status="running",
            )
        except Exception as e:
            # 19. Log and raise on execution failure
            logger.error(f"Command execution failed: {str(e)}", exc_info=True)
            raise AppException(
                msg=f"Command execution failed: {str(e)}",
                data={"session_id": session_id, "command": command}
            )

    async def write_shell_input(
            self,
            session_id: str,
            input_text: str,
            press_enter: bool
    ) -> ShellWriteResult:
        """Write data to the subprocess for the given session."""
        # 1. Validate session exists
        logger.debug(f"Writing to subprocess in shell session: {session_id}, press_enter: {press_enter}")
        if session_id not in self.active_shells:
            logger.error(f"Shell session not found: {session_id}")
            raise NotFoundException(f"Shell session not found: {session_id}")

        # 2. Get session and subprocess
        shell = self.active_shells[session_id]
        process = shell.process

        try:
            # 3. Ensure subprocess is still running
            if process.returncode is not None:
                logger.error(f"Subprocess already finished, cannot write input: {session_id}")
                raise BadRequestException("Subprocess already finished; cannot write input")

            # 4. Use UTF-8 and newline on Ubuntu
            encoding = "utf-8"
            line_ending = "\n"

            # 5. Prepare payload
            text_to_send = input_text
            if press_enter:
                text_to_send += line_ending

            # 6. Encode string to bytes for the process
            input_data = text_to_send.encode(encoding)

            # 7. Mirror input in session output (use raw string, not re-encoded bytes)
            log_text = input_text + ("\n" if press_enter else "")
            shell.output += log_text
            if shell.console_records:
                shell.console_records[-1].output += log_text

            # 8. Write to subprocess stdin
            process.stdin.write(input_data)
            await process.stdin.drain()

            # 9. Log and return write result
            logger.info("Successfully wrote data to subprocess")
            return ShellWriteResult(status="success")
        except UnicodeError as e:
            # 10. Handle encoding errors
            logger.error(f"Encoding error: {str(e)}")
            raise AppException(f"Encoding error: {str(e)}")
        except Exception as e:
            # 11. Handle generic errors
            logger.error(f"Error writing data to subprocess: {str(e)}")
            raise AppException(f"Error writing data to subprocess: {str(e)}")

    async def kill_process(self, session_id: str) -> ShellKillResult:
        """Terminate the process for the given shell session id."""
        # 1. Validate session exists
        logger.debug(f"Terminating process in session: {session_id}")
        if session_id not in self.active_shells:
            logger.error(f"Shell session not found: {session_id}")
            raise NotFoundException(f"Shell session not found: {session_id}")

        # 2. Get session and subprocess
        shell = self.active_shells[session_id]
        process = shell.process

        try:
            # 3. Check whether subprocess is still running
            if process.returncode is None:
                # 4. Attempt graceful termination first
                logger.info(f"Attempting graceful process termination: {session_id}")
                process.terminate()

                try:
                    # 5. Wait up to 3 seconds
                    await asyncio.wait_for(process.wait(), timeout=3)
                except asyncio.TimeoutError as _:
                    # 6. Force kill if graceful shutdown fails
                    logger.warning(f"Attempting forced process kill: {session_id}")
                    process.kill()

                # 7. Log and return termination result
                logger.info(f"Process terminated with return code: {process.returncode}")
                return ShellKillResult(status="terminated", returncode=process.returncode)
            else:
                # 8. Process already finished
                logger.info(f"Process already finished with return code: {process.returncode}")
                return ShellKillResult(status="already_terminated", returncode=process.returncode)
        except Exception as e:
            # 9. Log and raise on failure
            logger.error(f"Failed to terminate process: {str(e)}", exc_info=True)
            raise AppException(f"Failed to terminate process: {str(e)}")
