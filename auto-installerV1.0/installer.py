"""Core installation orchestration logic running in a background thread."""

import os
import threading
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import Callable

from ai_client import (
    assess_install_status,
    get_alternative_commands,
    get_check_commands,
    get_fix_commands,
    get_install_commands,
    get_uninstall_commands,
    should_rerun_after_fix,
    verify_command_output,
)
from ssh_client import SSHClient


class State(Enum):
    IDLE = auto()
    RUNNING = auto()
    PAUSED = auto()
    CANCELLED = auto()
    DONE = auto()
    FAILED = auto()
    UNINSTALLING = auto()
    UNINSTALLED = auto()


@dataclass
class InstallerConfig:
    software: str
    host: str
    username: str
    password: str
    port: int = 22
    os_info: str = ""       # auto-detected after SSH connect
    local_pkg_dir: str = "" # optional local package directory to upload before install


class Installer:
    def __init__(
        self,
        config: InstallerConfig,
        on_log: Callable[[str], None],
        on_progress: Callable[[int, int], None],
        on_state_change: Callable[[State], None],
        log_dir: str = "",
    ):
        self.config = config
        self.on_log = on_log
        self.on_progress = on_progress
        self.on_state_change = on_state_change

        self.state = State.IDLE
        self._pause_event = threading.Event()
        self._pause_event.set()
        self._cancel_flag = False
        self._completed_commands: list[str] = []
        self._thread: threading.Thread | None = None
        self._log_file = None
        self._log_path: str = ""
        self._log_dir: str = log_dir  # custom log directory from settings

    # ── Public controls ──────────────────────────────────────────────────────

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def start_uninstall(self):
        self._thread = threading.Thread(target=self._run_uninstall, daemon=True)
        self._thread.start()

    def pause(self):
        if self.state == State.RUNNING:
            self._pause_event.clear()
            self._set_state(State.PAUSED)

    def resume(self):
        if self.state == State.PAUSED:
            self._set_state(State.RUNNING)
            self._pause_event.set()

    def cancel(self):
        self._cancel_flag = True
        self._pause_event.set()

    def quit_after_current(self):
        """Signal cancel and wait for thread to finish, then return."""
        self.cancel()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=60)

    # ── Internal helpers ─────────────────────────────────────────────────────

    def _set_state(self, state: State):
        self.state = state
        self.on_state_change(state)

    def _log(self, msg: str):
        self.on_log(msg)
        if self._log_file:
            try:
                self._log_file.write(msg + "\n")
                self._log_file.flush()
            except Exception:
                pass

    def _log_commands(self, label: str, commands: list[str]):
        """Log a numbered list of AI-fetched commands to the log file."""
        self._log(f"{label}:")
        for i, cmd in enumerate(commands, 1):
            self._log(f"  {i:>2}. {cmd}")
        self._log("")

    def _open_log(self):
        logs_dir = Path(self._log_dir) if self._log_dir else Path(__file__).parent / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in self.config.software)
        self._log_path = str(logs_dir / f"install_{safe_name}_{ts}.log")
        self._log_file = open(self._log_path, "w", encoding="utf-8")
        self._log(f"Log file: {self._log_path}")
        self._log(f"Software: {self.config.software} | Host: {self.config.host} | Started: {datetime.now()}\n")

    def _close_log(self):
        if self._log_file:
            try:
                self._log_file.write(f"\nEnded: {datetime.now()}\n")
                self._log_file.close()
            except Exception:
                pass
            self._log_file = None

    def _wait_if_paused(self):
        self._pause_event.wait()

    def _execute(self, ssh: SSHClient, command: str) -> tuple[int, str]:
        self._log(f"\n>>> {command}")
        exit_code, output = ssh.execute(command)
        self._log(output if output else "(no output)")
        return exit_code, output

    # ── Local package upload ──────────────────────────────────────────────────

    def _upload_local_packages(self, ssh: SSHClient) -> str:
        """
        Upload files from config.local_pkg_dir to a temp dir on the remote machine.
        Returns the remote directory path, or empty string if nothing to upload.
        """
        local_dir = self.config.local_pkg_dir.strip()
        if not local_dir:
            return ""

        from pathlib import Path as _Path
        local_path = _Path(local_dir)
        if not local_path.is_dir():
            self._log(f"Warning: Local package directory not found: {local_dir} — skipping upload.")
            return ""

        files = list(local_path.iterdir())
        pkg_files = [f for f in files if f.is_file()]
        if not pkg_files:
            self._log(f"Warning: No files found in {local_dir} — skipping upload.")
            return ""

        safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in self.config.software)
        remote_dir = f"/tmp/pkg_{safe_name}"
        self._log(f"\nUploading {len(pkg_files)} local package file(s) to {remote_dir} on remote...")
        ssh.execute(f"mkdir -p {remote_dir}")
        count = ssh.upload_directory(str(local_path), remote_dir, on_log=self._log)
        self._log(f"Upload complete: {count} file(s) uploaded to {remote_dir}\n")
        return remote_dir

    # ── Apt sources conflict fix ──────────────────────────────────────────────

    def _fix_apt_sources(self, ssh: SSHClient):
        """
        Hardcoded cleanup for known apt Signed-By conflicts.
        Removes ALL elastic keyrings and sources to eliminate any conflict.
        This runs unconditionally before any apt operation.
        """
        self._log("\nRunning apt sources conflict cleanup...")

        conflict_cmds = [
            # Remove ALL elastic keyrings from both possible locations
            "sudo rm -f /etc/apt/keyrings/elastic*.gpg",
            "sudo rm -f /usr/share/keyrings/elastic*.gpg",
            "sudo rm -f /usr/share/keyrings/elasticsearch*.gpg",
            # Remove ALL elastic sources list entries
            "sudo rm -f /etc/apt/sources.list.d/elastic*.list",
            # Remove any broken newrelic sources (wrong repo path)
            "sudo rm -f /etc/apt/sources.list.d/newrelic*.list",
            # Release any apt/dpkg locks
            "sudo rm -f /var/lib/apt/lists/lock /var/cache/apt/archives/lock /var/lib/dpkg/lock* 2>/dev/null || true",
            # Fix any broken dpkg state
            "sudo dpkg --configure -a 2>/dev/null || true",
        ]

        for cmd in conflict_cmds:
            self._execute(ssh, cmd)

        self._log("Apt sources cleanup done.\n")

    # ── Pre-flight check ──────────────────────────────────────────────────────

    def _preflight_check(self, ssh: SSHClient) -> str:
        """
        Check if software is already installed.
        Returns: 'installed', 'partial', or 'not_installed'
        """
        self._log(f"\nChecking if '{self.config.software}' is already installed...")
        check_cmds = get_check_commands(self.config.software, self.config.os_info)
        self._log_commands("Check commands", check_cmds)

        check_outputs = []
        for cmd in check_cmds:
            self._log(f"Checking: {cmd}")
            exit_code, output = ssh.execute(cmd)
            check_outputs.append((cmd, output))

        status, reason = assess_install_status(self.config.software, check_outputs, self.config.os_info)
        self._log(f"Installation status: {status} — {reason}")
        return status

    # ── Partial cleanup (hardcoded, no AI) ───────────────────────────────────

    def _cleanup_partial(self, ssh: SSHClient):
        """
        Generic cleanup for partial installs.
        Uses dpkg --purge and AI-assisted uninstall to clear the slate.
        """
        self._log("\nPartial installation detected. Cleaning up before fresh install...")

        # Step 1: Fix apt sources conflicts
        self._fix_apt_sources(ssh)

        # Step 2: Stop any running services for this software
        safe_name = self.config.software.lower().replace(" ", "")
        stop_cmds = [
            f"sudo systemctl stop {safe_name} 2>/dev/null || true",
            f"sudo systemctl disable {safe_name} 2>/dev/null || true",
        ]
        for cmd in stop_cmds:
            self._execute(ssh, cmd)

        # Step 3: Try dpkg purge by package name
        self._log("\nAttempting dpkg purge...")
        purge_cmds = [
            f"sudo dpkg --purge --force-all {safe_name} 2>/dev/null || true",
            f"sudo apt-get remove --purge -y {safe_name} 2>/dev/null || true",
        ]
        for cmd in purge_cmds:
            self._execute(ssh, cmd)

        # Step 4: Fix broken packages
        fix_cmds = [
            "sudo dpkg --configure -a 2>/dev/null || true",
            "sudo apt-get -f install -y 2>/dev/null || true",
            "sudo apt-get autoremove -y 2>/dev/null || true",
            "sudo apt-get clean 2>/dev/null || true",
        ]
        for cmd in fix_cmds:
            self._execute(ssh, cmd)

        self._log("\nPartial cleanup complete. Proceeding with fresh installation...\n")

    # ── Main flow ─────────────────────────────────────────────────────────────

    def _run(self):
        self._set_state(State.RUNNING)
        ssh = SSHClient(
            self.config.host,
            self.config.username,
            self.config.password,
            self.config.port,
        )

        try:
            self._open_log()
            self._log(f"Connecting to {self.config.host}...")
            ssh.connect()
            self._log("Connected.")
            self.config.os_info = ssh.os_info
            self._log(f"Detected OS: {self.config.os_info}")

            # Linux-only: fix apt sources conflicts before doing anything
            if ssh.os_type == "linux":
                self._fix_apt_sources(ssh)

            # Pre-flight: check existing installation
            status = self._preflight_check(ssh)

            if status == "installed":
                self._log(f"\n'{self.config.software}' is already fully installed. Nothing to do.")
                self._set_state(State.DONE)
                return

            if status == "partial":
                if ssh.os_type == "linux":
                    self._cleanup_partial(ssh)
                else:
                    self._log("\nPartial install detected. Proceeding with fresh install (Windows)...")

            # Upload local packages if a directory was configured
            remote_pkg_dir = self._upload_local_packages(ssh)

            # Proceed with installation
            self._log(f"\nAsking AI for install commands for '{self.config.software}'...")
            commands = get_install_commands(self.config.software, self.config.os_info, remote_pkg_dir)
            self._log(f"AI returned {len(commands)} command(s).")
            self._log_commands("Install commands", commands)

            total = len(commands)
            for idx, cmd in enumerate(commands):
                self._wait_if_paused()
                if self._cancel_flag:
                    break

                self.on_progress(idx, total)
                self._log(f"[{idx + 1}/{total}] Executing...")

                exit_code, output = self._execute(ssh, cmd)

                self._log("Verifying with AI...")
                success, reason = verify_command_output(cmd, output, exit_code, self.config.os_info)
                self._log(f"AI verdict: {'SUCCESS' if success else 'FAILURE'} — {reason}")

                if not success:
                    self._log("\nCommand failed. Asking AI for fix commands...")
                    fix_cmds = get_fix_commands(cmd, output, self.config.software, self.config.os_info)
                    self._log(f"AI provided {len(fix_cmds)} fix command(s).")
                    self._log_commands("Fix commands", fix_cmds)

                    fix_ok = True
                    for fix_cmd in fix_cmds:
                        self._wait_if_paused()
                        if self._cancel_flag:
                            fix_ok = False
                            break
                        fx_code, fx_out = self._execute(ssh, fix_cmd)
                        fx_success, fx_reason = verify_command_output(fix_cmd, fx_out, fx_code, self.config.os_info)
                        self._log(f"Fix AI verdict: {'SUCCESS' if fx_success else 'FAILURE'} — {fx_reason}")
                        if not fx_success:
                            fix_ok = False
                            break

                    if not fix_ok and not self._cancel_flag:
                        self._log("\nFix commands failed. Trying alternative approach...")
                        alt_cmds = get_alternative_commands(cmd, fx_out, self.config.software, self.config.os_info)
                        self._log(f"AI provided {len(alt_cmds)} alternative command(s).")
                        self._log_commands("Alternative commands", alt_cmds)

                        alt_ok = True
                        for alt_cmd in alt_cmds:
                            self._wait_if_paused()
                            if self._cancel_flag:
                                alt_ok = False
                                break
                            alt_code, alt_out = self._execute(ssh, alt_cmd)
                            alt_success, alt_reason = verify_command_output(alt_cmd, alt_out, alt_code, self.config.os_info)
                            self._log(f"Alt AI verdict: {'SUCCESS' if alt_success else 'FAILURE'} — {alt_reason}")
                            if not alt_success:
                                alt_ok = False
                                break

                        if not alt_ok and not self._cancel_flag:
                            self._log("\nAll approaches failed. Aborting installation.")
                            self._set_state(State.FAILED)
                            return

                    if not self._cancel_flag:
                        should_rerun = should_rerun_after_fix(cmd, fix_cmds, self.config.os_info)
                        if should_rerun:
                            self._log("\nRe-running original command after fix...")
                            exit_code, output = self._execute(ssh, cmd)
                            success, reason = verify_command_output(cmd, output, exit_code, self.config.os_info)
                            self._log(f"Re-run AI verdict: {'SUCCESS' if success else 'FAILURE'} — {reason}")
                            if not success:
                                self._log("Re-run also failed. Aborting.")
                                self._set_state(State.FAILED)
                                return
                        else:
                            self._log("Fix commands fully resolved the issue. Skipping re-run of original command.")

                self._completed_commands.append(cmd)

            if self._cancel_flag:
                self._log("\nCancellation requested. Starting uninstall...")
                self._set_state(State.CANCELLED)
                self._uninstall(ssh)
            else:
                self.on_progress(total, total)
                self._log("\nInstallation completed successfully.")
                self._set_state(State.DONE)

        except Exception as e:
            self._log(f"\nError: {e}")
            self._set_state(State.FAILED)
        finally:
            ssh.disconnect()
            self._log("SSH connection closed.")
            self._close_log()

    def _run_uninstall(self):
        """Standalone uninstall flow — connects SSH, detects OS, runs uninstall commands."""
        self._set_state(State.UNINSTALLING)
        ssh = SSHClient(
            self.config.host,
            self.config.username,
            self.config.password,
            self.config.port,
        )
        try:
            self._open_log()
            self._log(f"Connecting to {self.config.host}...")
            ssh.connect()
            self._log("Connected.")
            self.config.os_info = ssh.os_info
            self._log(f"Detected OS: {self.config.os_info}")

            if ssh.os_type == "linux":
                self._fix_apt_sources(ssh)

            self._log(f"\nAsking AI for uninstall commands for '{self.config.software}'...")
            cmds = get_uninstall_commands(self.config.software, [], self.config.os_info)
            self._log(f"AI returned {len(cmds)} uninstall command(s).")
            self._log_commands("Uninstall commands", cmds)

            total = len(cmds)
            all_ok = True
            for idx, cmd in enumerate(cmds):
                self._wait_if_paused()
                if self._cancel_flag:
                    break
                self.on_progress(idx, total)
                exit_code, output = self._execute(ssh, cmd)
                success, reason = verify_command_output(cmd, output, exit_code, self.config.os_info)
                self._log(f"AI verdict: {'SUCCESS' if success else 'FAILURE'} — {reason}")
                if not success:
                    all_ok = False

            self.on_progress(total, total)
            if all_ok:
                self._log(f"\n'{self.config.software}' uninstalled successfully.")
            else:
                self._log("\nSome uninstall steps may have failed. Please verify manually.")
            self._set_state(State.UNINSTALLED)

        except Exception as e:
            self._log(f"\nError: {e}")
            self._set_state(State.FAILED)
        finally:
            ssh.disconnect()
            self._log("SSH connection closed.")
            self._close_log()

    def _uninstall(self, ssh: SSHClient):
        self._log("\nAsking AI for uninstall commands...")
        cmds = get_uninstall_commands(
            self.config.software, self._completed_commands, self.config.os_info
        )
        self._log(f"AI returned {len(cmds)} uninstall command(s).")
        self._log_commands("Uninstall commands", cmds)

        total = len(cmds)
        all_ok = True
        for idx, cmd in enumerate(cmds):
            self.on_progress(idx, total)
            exit_code, output = self._execute(ssh, cmd)
            success, reason = verify_command_output(cmd, output, exit_code, self.config.os_info)
            if not success:
                all_ok = False

        self.on_progress(total, total)
        if all_ok:
            self._log("\nUninstallation completed successfully. Software has been removed.")
        else:
            self._log("\nSome uninstall steps may have failed. Please verify manually.")
