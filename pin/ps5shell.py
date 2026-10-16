"""Minimal client for the PS5 shsrv telnet shell (port 2323)."""

from __future__ import annotations

import socket
import time


class PS5Shell:
    """Send commands to shsrv and return their output.

    The shell is a busybox sh in a chroot whose root is the real system root.
    It has no `2>&1`, `find` or `head`, uses \\r\\n line endings and prints
    '/$ ' as its prompt. Nothing marks the end of a command's output, so each
    command reads until the socket goes quiet or `wait` seconds pass.
    """

    def __init__(self, host: str, port: int, read_timeout: float = 3.0) -> None:
        self.sock = socket.create_connection((host, port), timeout=5)
        self.sock.settimeout(read_timeout)
        self._read(2)

    def __enter__(self) -> PS5Shell:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def _read(self, seconds: float) -> bytes:
        deadline = time.time() + seconds
        received = b""
        while time.time() < deadline:
            try:
                chunk = self.sock.recv(4096)
            except socket.timeout:
                break
            if not chunk:
                break
            received += chunk
        return received

    def run(self, command: str, wait: float = 3.0) -> str:
        self.sock.sendall(command.encode() + b"\n")
        output = self._read(wait).decode(errors="replace")
        lines = [line for line in output.splitlines()
                 if line.strip() and not line.strip().startswith("/$")]
        return "\n".join(lines).strip()

    def exists(self, path: str) -> bool:
        """True only if `ls` printed the path back, so a dropped stderr can't read as success."""
        return any(line.strip() == path for line in self.run(f"ls {path}").splitlines())

    def close(self) -> None:
        try:
            self.sock.close()
        except OSError:
            pass
