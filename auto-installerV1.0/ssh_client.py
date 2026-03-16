"""SSH client for executing commands on a remote machine."""

import os
import re
import paramiko


def _strip_ansi(text: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*[mGKHF]", "", text)


class SSHClient:
    def __init__(self, host: str, username: str, password: str, port: int = 22):
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self._client = None
        self.os_type: str = "linux"   # "linux" or "windows"
        self.os_info: str = "Linux"   # full distro string e.g. "Ubuntu 22.04"

    def connect(self):
        self._client = paramiko.SSHClient()
        self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self._client.connect(
            hostname=self.host,
            port=self.port,
            username=self.username,
            password=self.password,
            timeout=30,
        )
        self.os_info = self._detect_os()   # also sets self.os_type
        if self.os_type == "linux":
            self._setup_askpass()

    def _detect_os(self) -> str:
        """
        Detect remote OS and distro.
        Sets self.os_type to 'linux' or 'windows'.
        Returns a human-readable string e.g. 'Ubuntu 22.04' or 'Windows Server 2022'.
        """
        # Try Linux /etc/os-release first
        _, stdout, _ = self._client.exec_command(
            "cat /etc/os-release 2>/dev/null | grep -E '^(NAME|VERSION_ID)' || echo NOT_LINUX",
            timeout=10,
        )
        result = stdout.read().decode(errors="replace").strip()

        if result and "NOT_LINUX" not in result:
            name, version = "", ""
            for line in result.splitlines():
                if line.startswith("NAME="):
                    name = line.split("=", 1)[1].strip().strip('"')
                elif line.startswith("VERSION_ID="):
                    version = line.split("=", 1)[1].strip().strip('"')
            self.os_type = "linux"
            return f"{name} {version}".strip() or "Linux"

        # Try Windows
        _, stdout, _ = self._client.exec_command("ver", timeout=10)
        win_result = stdout.read().decode(errors="replace").strip()
        if win_result:
            self.os_type = "windows"
            return win_result  # e.g. "Microsoft Windows [Version 10.0.20348.3328]"

        # Fallback
        self.os_type = "linux"
        return "Linux"

    def _setup_askpass(self):
        """Create a SUDO_ASKPASS script on the remote Linux machine."""
        script = f'#!/bin/sh\necho "{self.password}"\n'
        stdin, stdout, _ = self._client.exec_command(
            "cat > /tmp/.sudo_askpass.sh && chmod 700 /tmp/.sudo_askpass.sh",
            timeout=10,
        )
        stdin.write(script)
        stdin.channel.shutdown_write()
        stdout.channel.recv_exit_status()

    def _wrap_sudo(self, command: str) -> str:
        """Wrap sudo commands to use SUDO_ASKPASS for non-interactive execution."""
        # Inject SUDO_ASKPASS for any sudo call
        if "sudo" in command:
            command = f"SUDO_ASKPASS=/tmp/.sudo_askpass.sh {command.replace('sudo ', 'sudo -A ', 1)}"

        # For apt/dpkg commands, wait until the dpkg lock is free before running.
        # Must wrap in bash -c '...' so the while loop is valid shell syntax
        # when passed as a single string to exec_command.
        apt_cmds = ("apt-get", "apt ", "dpkg")
        if any(c in command for c in apt_cmds):
            inner = command.replace("'", "'\\''")  # escape any single quotes inside
            command = (
                "bash -c '"
                "while ! SUDO_ASKPASS=/tmp/.sudo_askpass.sh sudo -A flock -n "
                "/var/lib/dpkg/lock-frontend true 2>/dev/null; "
                f"do sleep 2; done; {inner}'"
            )

        return command

    def execute(self, command: str) -> tuple[int, str]:
        """Execute a command and return (exit_code, combined_output)."""
        if not self._client:
            raise RuntimeError("Not connected. Call connect() first.")

        wrapped = self._wrap_sudo(command) if self.os_type == "linux" else command
        stdin, stdout, stderr = self._client.exec_command(wrapped, timeout=300, get_pty=True)
        exit_code = stdout.channel.recv_exit_status()
        out = stdout.read().decode(errors="replace")
        err = stderr.read().decode(errors="replace")
        combined = _strip_ansi((out + err).strip())
        return exit_code, combined

    def upload_directory(self, local_dir: str, remote_dir: str, on_log=None) -> int:
        """
        Upload all files from local_dir to remote_dir on the remote machine via SFTP.
        Creates remote_dir if it doesn't exist.
        Returns the number of files uploaded.
        """
        if not self._client:
            raise RuntimeError("Not connected. Call connect() first.")

        sftp = self._client.open_sftp()
        try:
            # Ensure remote dir exists
            try:
                sftp.stat(remote_dir)
            except FileNotFoundError:
                sftp.mkdir(remote_dir)

            count = 0
            for entry in os.scandir(local_dir):
                if entry.is_file():
                    remote_path = f"{remote_dir}/{entry.name}"
                    if on_log:
                        on_log(f"Uploading {entry.name} → {remote_path}")
                    sftp.put(entry.path, remote_path)
                    count += 1
            return count
        finally:
            sftp.close()

    def disconnect(self):
        if self._client:
            if self.os_type == "linux":
                try:
                    self._client.exec_command("rm -f /tmp/.sudo_askpass.sh", timeout=5)
                except Exception:
                    pass
            self._client.close()
            self._client = None
