#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2026-06-08 10:27
@Author  : fred.feng0326@gmail.com
@File    : supervisor.py
"""
import asyncio
import http.client
import logging
import socket
import threading
import xmlrpc.client
from datetime import datetime, timedelta
from typing import List, Any, Optional

from app.core.config import get_settings
from app.interfaces.errors.exceptions import BadRequestException, AppException
from app.models.supervisor import ProcessInfo, SupervisorActionResult, SupervisorTimeout

"""
1. After Supervisor starts, it communicates via a Unix socket file (RPC protocol).
2. Connect to /tmp/supervisor.sock (XML-RPC connection).
3. Use an adapter so XML-RPC can connect to supervisor.sock.
4. After connecting, call RPC methods such as getAllProcessInfo().
"""

logger = logging.getLogger(__name__)


class UnixStreamHTTPConnection(http.client.HTTPConnection):
    """HTTP connection handler based on Unix stream sockets."""

    def __init__(self, host: str, socket_path: str, timeout=None) -> None:
        """Initialize the connection handler."""
        http.client.HTTPConnection.__init__(self, host, timeout)
        self.socket_path = socket_path

    def connect(self) -> None:
        """Override connect so XML-RPC believes it is using a network connection."""
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.connect(self.socket_path)


class UnixStreamTransport(xmlrpc.client.Transport):
    """Transport adapter for Unix stream sockets."""

    def __init__(self, socket_path: str) -> None:
        """Initialize the transport adapter."""
        xmlrpc.client.Transport.__init__(self)
        self.socket_path = socket_path

    def make_connection(self, host) -> http.client.HTTPConnection:
        return UnixStreamHTTPConnection(host, self.socket_path)


class SupervisorService:
    """Supervisor service."""

    def __init__(self) -> None:
        """Initialize the Supervisor service connection."""
        # 1. Connect to Supervisor RPC
        self.rpc_url = "/tmp/supervisor.sock"
        self._connect_rpc()

        # 2. Supervisor timeout configuration
        settings = get_settings()
        self.timeout_active = settings.server_timeout_minutes is not None
        self.shutdown_task = None
        self.shutdown_time = None
        self.shutdown_timer = None
        self._expand_enabled = True  # Auto keep-alive (extend timeout on each API call)

        # 3. Check whether auto-shutdown is configured
        if settings.server_timeout_minutes is not None:
            # 4. Set shutdown time and timer
            self.shutdown_time = datetime.now() + timedelta(minutes=settings.server_timeout_minutes)
            self._setup_timer(settings.server_timeout_minutes)

    @property
    def expand_enabled(self) -> bool:
        """Read-only property indicating whether auto keep-alive is enabled."""
        return self._expand_enabled

    def enable_expand(self) -> None:
        """Enable auto keep-alive."""
        self._expand_enabled = True

    def disable_expand(self) -> None:
        """Disable auto keep-alive."""
        self._expand_enabled = False

    def _setup_timer(self, minutes: int) -> None:
        """Create a timer for the given minutes, then shut down supervisord when it expires."""
        # 1. Cancel existing shutdown task if present
        if self.shutdown_task:
            try:
                self.shutdown_task.cancel()
            except Exception as e:
                logger.warning(f"Failed to cancel shutdown task: {str(e)}")

        # 2. Async timer task function
        async def shutdown_after_timeout():
            await asyncio.sleep(minutes * 60)
            await self.shutdown()

        try:
            # 3. Schedule task on the event loop
            loop = asyncio.get_event_loop()
            self.shutdown_task = loop.create_task(shutdown_after_timeout())
        except Exception as _:
            # 4. Fall back to a thread-based timer when event loop setup fails
            if hasattr(self, "shutdown_timer") and self.shutdown_timer:
                self.shutdown_timer.cancel()

            # 5. Start a background shutdown timer thread
            self.shutdown_timer = threading.Timer(
                minutes * 60,
                lambda: asyncio.run(self.shutdown())
            )
            self.shutdown_timer.daemon = True
            self.shutdown_timer.start()

    def _connect_rpc(self) -> None:
        """Connect to the local RPC service via XML-RPC over a Unix socket file."""
        try:
            self.server = xmlrpc.client.ServerProxy(
                "http://localhost",
                transport=UnixStreamTransport(self.rpc_url),
            )
        except Exception as e:
            logger.error(f"Failed to connect to Supervisor service: {str(e)}")
            raise BadRequestException(f"Failed to connect to Supervisor service: {str(e)}")

    @classmethod
    async def _call_rpc(cls, method, *args) -> Any:
        """Call an RPC method with the given arguments."""
        try:
            return await asyncio.to_thread(method, *args)
        except Exception as e:
            logger.error(f"RPC method call failed: {str(e)}")
            raise BadRequestException(f"RPC method call failed: {str(e)}")

    async def get_all_processes(self) -> List[ProcessInfo]:
        """Get all processes managed by Supervisor."""
        try:
            processes = await self._call_rpc(self.server.supervisor.getAllProcessInfo)
            return [ProcessInfo(**process) for process in processes]
        except Exception as e:
            logger.error(f"Failed to get process info: {str(e)}")
            raise AppException(f"Failed to get process info: {str(e)}")

    async def stop_all_processes(self) -> SupervisorActionResult:
        """Stop all processes managed by Supervisor."""
        try:
            result = await self._call_rpc(self.server.supervisor.stopAllProcesses)
            return SupervisorActionResult(status="stopped", result=result)
        except Exception as e:
            logger.error(f"Failed to stop all Supervisor processes: {str(e)}")
            raise AppException(f"Failed to stop all Supervisor processes: {str(e)}")

    async def shutdown(self) -> SupervisorActionResult:
        """Shut down the supervisord service."""
        try:
            shutdown_result = await self._call_rpc(self.server.supervisor.shutdown)
            return SupervisorActionResult(status="shutdown", shutdown_result=shutdown_result)
        except Exception as e:
            logger.error(f"Failed to shut down supervisord service: {str(e)}")
            raise AppException(f"Failed to shut down supervisord service: {str(e)}")

    async def restart(self) -> SupervisorActionResult:
        """Restart processes managed by Supervisor."""
        try:
            stop_result = await self._call_rpc(self.server.supervisor.stopAllProcesses)
            start_result = await self._call_rpc(self.server.supervisor.startAllProcesses)
            return SupervisorActionResult(
                status="restarted",
                stop_result=stop_result,
                start_result=start_result,
            )
        except Exception as _:
            logger.error("Failed to restart Supervisor processes")
            raise AppException("Failed to restart Supervisor processes")

    async def activate_timeout(self, minutes: Optional[int] = None) -> SupervisorTimeout:
        """Activate timed shutdown for the given minutes and disable auto keep-alive."""
        # 1. Resolve timeout minutes
        setting = get_settings()
        timeout_minutes = minutes or setting.server_timeout_minutes
        if timeout_minutes is None:
            raise BadRequestException("Timeout is not configured and no system default was found")

        # 2. Update timeout configuration
        self.timeout_active = True
        self.shutdown_time = datetime.now() + timedelta(minutes=timeout_minutes)

        # 3. Create a new timer
        self._setup_timer(timeout_minutes)

        return SupervisorTimeout(
            status="timeout_activated",
            active=True,
            shutdown_time=self.shutdown_time.isoformat(),
            timeout_minutes=timeout_minutes,
            remaining_seconds=(self.shutdown_time - datetime.now()).total_seconds(),
        )

    async def extend_timeout(self, minutes: Optional[int] = 3) -> SupervisorTimeout:
        """Extend the shutdown timeout by the given minutes; defaults to 3 minutes."""
        # 1. Resolve timeout minutes
        if minutes is None:
            raise BadRequestException("Timeout is not configured. Please verify and try again.")
        remaining = self.shutdown_time - datetime.now()
        timeout_minutes = round(max(0, remaining.total_seconds()) / 60) + minutes

        # 2. Update timeout configuration
        self.timeout_active = True
        self.shutdown_time = datetime.now() + timedelta(minutes=timeout_minutes)

        # 3. Create a new timer
        self._setup_timer(timeout_minutes)

        return SupervisorTimeout(
            status="timeout_extended",
            active=True,
            shutdown_time=self.shutdown_time.isoformat(),
            timeout_minutes=timeout_minutes,
            remaining_seconds=(self.shutdown_time - datetime.now()).total_seconds(),
        )

    async def cancel_timeout(self) -> SupervisorTimeout:
        """Cancel the timed shutdown setting."""
        # 1. Check whether timed shutdown is active
        if not self.timeout_active:
            return SupervisorTimeout(status="no_timeout_active", activate=False)

        # 2. Cancel shutdown task
        if self.shutdown_task:
            try:
                self.shutdown_task.cancel()
                self.shutdown_task = None
            except Exception as e:
                logger.warning(f"Failed to cancel shutdown task: {str(e)}")

        # 3. Cancel thread-based timer if present
        if hasattr(self, 'shutdown_timer') and self.shutdown_timer:
            self.shutdown_timer.cancel()
            self.shutdown_timer = None

        # 4. Update timeout configuration
        self.timeout_active = False
        self.shutdown_time = None
        self._expand_enabled = True

        return SupervisorTimeout(status="timeout_cancelled", active=False)

    async def get_timeout_status(self) -> SupervisorTimeout:
        """Get the current Supervisor timeout status."""
        # 1. Check whether timed shutdown is enabled
        if not self.timeout_active:
            return SupervisorTimeout(active=False)

        # 2. Calculate remaining seconds
        remaining_seconds = 0
        if self.shutdown_time:
            remaining = self.shutdown_time - datetime.now()
            remaining_seconds = max(0, remaining.total_seconds())

        return SupervisorTimeout(
            active=self.timeout_active,
            shutdown_time=self.shutdown_time.isoformat() if self.shutdown_time else None,
            remaining_seconds=remaining_seconds,
        )
