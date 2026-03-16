"""Main GUI for the Auto Installer application."""

import os
import queue
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk

from config_manager import CONFIG_EXT, get_recent, load_config, save_config
from installer import Installer, InstallerConfig, State

ENV_PATH = Path(__file__).parent / ".env"
SETTINGS_PATH = Path(__file__).parent / ".settings.json"


def _load_settings() -> dict:
    import json
    if SETTINGS_PATH.exists():
        try:
            return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_settings(data: dict):
    import json
    SETTINGS_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Genius Auto Installer")
        self.geometry("900x700")
        self.resizable(True, True)
        self.configure(bg="#1e1e2e")

        self._installer: Installer | None = None
        self._log_queue: queue.Queue = queue.Queue()
        self._progress_queue: queue.Queue = queue.Queue()
        self._quitting = False
        self._current_file: str | None = None
        self._settings = _load_settings()
        self._log_dir: str = self._settings.get("log_dir", str(Path(__file__).parent / "logs"))
        self._local_pkg_dir: str = self._settings.get("local_pkg_dir", "")

        self._build_menu()
        self._build_ui()
        self._poll_queues()

        # Handle window close (X button) same as Quit
        self.protocol("WM_DELETE_WINDOW", self._on_quit)

    # ── Menu ─────────────────────────────────────────────────────────────────

    def _build_menu(self):
        mc = dict(bg="#313244", fg="#cdd6f4",
                  activebackground="#45475a", activeforeground="#cdd6f4")
        menubar = tk.Menu(self, **mc)

        # ── File menu ──
        file_menu = tk.Menu(menubar, tearoff=0, **mc)
        file_menu.add_command(label="New",          accelerator="Ctrl+N", command=self._on_new)
        file_menu.add_command(label="Open...",      accelerator="Ctrl+O", command=self._on_open)
        file_menu.add_separator()
        file_menu.add_command(label="Save",         accelerator="Ctrl+S", command=self._on_save)
        file_menu.add_command(label="Save As...",   accelerator="Ctrl+Shift+S", command=self._on_save_as)
        file_menu.add_separator()

        self._recent_menu = tk.Menu(file_menu, tearoff=0, **mc)
        file_menu.add_cascade(label="Recent Configurations", menu=self._recent_menu)
        self._rebuild_recent_menu()

        file_menu.add_separator()
        file_menu.add_command(label="Quit", command=self._on_quit)
        menubar.add_cascade(label="File", menu=file_menu)

        # ── Settings menu ──
        settings_menu = tk.Menu(menubar, tearoff=0, **mc)
        settings_menu.add_command(label="Environment Variables (.env)...", command=self._on_edit_env)
        settings_menu.add_command(label="Log File Path...", command=self._on_set_log_path)
        settings_menu.add_command(label="Local Package Directory...", command=self._on_set_local_pkg_dir)
        menubar.add_cascade(label="Settings", menu=settings_menu)

        # ── Help menu ──
        help_menu = tk.Menu(menubar, tearoff=0, **mc)
        help_menu.add_command(label="About", command=self._show_about)
        menubar.add_cascade(label="Help", menu=help_menu)

        self.config(menu=menubar)

        # Keyboard shortcuts
        self.bind_all("<Control-n>", lambda e: self._on_new())
        self.bind_all("<Control-o>", lambda e: self._on_open())
        self.bind_all("<Control-s>", lambda e: self._on_save())
        self.bind_all("<Control-S>", lambda e: self._on_save_as())

    def _rebuild_recent_menu(self):
        self._recent_menu.delete(0, tk.END)
        recent = get_recent()
        if not recent:
            self._recent_menu.add_command(label="(empty)", state=tk.DISABLED)
        for path in recent:
            # Use a default arg to capture path in closure
            self._recent_menu.add_command(
                label=path,
                command=lambda p=path: self._load_file(p)
            )

    def _show_about(self):
        messagebox.showinfo(
            "About Auto Installer Genius",
            "Auto Installer Genius\n"
            "Ver 1.0\n\n"
            "Author: Vishnu Vardhan\n"
            "Date: 15-Mar-2026"
        )

    # ── File menu handlers ────────────────────────────────────────────────────

    def _on_new(self):
        """Clear all fields and reset current file."""
        for key, var in self._vars.items():
            if key == "os_info":
                var.set("Linux/Ubuntu 22.04")
            else:
                var.set("")
        self._current_file = None
        self.title("Genius Auto Installer")

    def _on_open(self):
        path = filedialog.askopenfilename(
            title="Open Configuration",
            filetypes=[("MC Config files", f"*{CONFIG_EXT}"), ("All files", "*.*")],
            defaultextension=CONFIG_EXT,
        )
        if path:
            self._load_file(path)

    def _load_file(self, path: str):
        try:
            data = load_config(path)
            for key, var in self._vars.items():
                var.set(data.get(key, ""))
            self._current_file = path
            self.title(f"Genius Auto Installer — {path}")
            self._rebuild_recent_menu()
        except Exception as e:
            messagebox.showerror("Open Failed", f"Could not load config:\n{e}")

    def _on_save(self):
        if self._current_file:
            self._write_file(self._current_file)
        else:
            self._on_save_as()

    def _on_save_as(self):
        path = filedialog.asksaveasfilename(
            title="Save Configuration As",
            filetypes=[("MC Config files", f"*{CONFIG_EXT}"), ("All files", "*.*")],
            defaultextension=CONFIG_EXT,
        )
        if path:
            # Ensure correct extension
            if not path.endswith(CONFIG_EXT):
                path += CONFIG_EXT
            self._write_file(path)

    def _write_file(self, path: str):
        try:
            data = {key: var.get() for key, var in self._vars.items()}
            save_config(path, data)
            self._current_file = path
            self.title(f"Genius Auto Installer — {path}")
            self._rebuild_recent_menu()
        except Exception as e:
            messagebox.showerror("Save Failed", f"Could not save config:\n{e}")

    # ── Settings handlers ─────────────────────────────────────────────────────

    def _on_edit_env(self):
        """Open a dialog to view/edit the .env file."""
        dlg = tk.Toplevel(self)
        dlg.title("Environment Variables (.env)")
        dlg.geometry("640x480")
        dlg.configure(bg="#1e1e2e")
        dlg.resizable(True, True)
        dlg.grab_set()

        tk.Label(dlg, text=f"Editing: {ENV_PATH}",
                 bg="#1e1e2e", fg="#89b4fa", font=("Segoe UI", 9)).pack(anchor=tk.W, padx=12, pady=(8, 2))

        # Button frame at BOTTOM first so it's always visible
        btn_frame = tk.Frame(dlg, bg="#1e1e2e")
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=12, pady=8)

        txt = scrolledtext.ScrolledText(dlg, bg="#181825", fg="#cdd6f4",
                                        font=("Consolas", 10), insertbackground="#cdd6f4")
        txt.pack(fill=tk.BOTH, expand=True, padx=12, pady=4)

        # Load current content
        if ENV_PATH.exists():
            txt.insert(tk.END, ENV_PATH.read_text(encoding="utf-8"))
        else:
            txt.insert(tk.END, "# Add your environment variables here\nCEREBRAS_API_KEY=\n")

        def save_env():
            content = txt.get("1.0", tk.END)
            ENV_PATH.write_text(content, encoding="utf-8", newline="\n")
            from dotenv import load_dotenv
            load_dotenv(str(ENV_PATH), override=True)
            messagebox.showinfo("Saved", ".env saved and reloaded.", parent=dlg)
            dlg.destroy()

        ttk.Button(btn_frame, text="Save", style="green.TButton", command=save_env).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="Cancel", style="gray.TButton", command=dlg.destroy).pack(side=tk.LEFT, padx=4)

    def _on_set_log_path(self):
        """Open a dialog to configure the log file directory."""
        dlg = tk.Toplevel(self)
        dlg.title("Log File Path")
        dlg.geometry("520x160")
        dlg.configure(bg="#1e1e2e")
        dlg.resizable(False, False)
        dlg.grab_set()

        tk.Label(dlg, text="Log files directory:", bg="#1e1e2e", fg="#cdd6f4",
                 font=("Segoe UI", 10)).grid(row=0, column=0, sticky=tk.W, padx=12, pady=(16, 4))

        path_var = tk.StringVar(value=self._log_dir)
        entry = ttk.Entry(dlg, textvariable=path_var, width=45)
        entry.grid(row=0, column=1, sticky=tk.W, padx=(4, 4), pady=(16, 4))

        def browse():
            chosen = filedialog.askdirectory(title="Select Log Directory", initialdir=self._log_dir)
            if chosen:
                path_var.set(chosen)

        ttk.Button(dlg, text="Browse...", command=browse).grid(row=0, column=2, padx=4, pady=(16, 4))

        tk.Label(dlg, text="Log files will be saved as: install_<software>_<timestamp>.log",
                 bg="#1e1e2e", fg="#6c7086", font=("Segoe UI", 9)).grid(
            row=1, column=0, columnspan=3, sticky=tk.W, padx=12, pady=2)

        btn_frame = tk.Frame(dlg, bg="#1e1e2e")
        btn_frame.grid(row=2, column=0, columnspan=3, pady=12)

        def save_log_path():
            new_path = path_var.get().strip()
            if not new_path:
                messagebox.showwarning("Invalid", "Path cannot be empty.", parent=dlg)
                return
            self._log_dir = new_path
            self._settings["log_dir"] = new_path
            _save_settings(self._settings)
            messagebox.showinfo("Saved", f"Log directory set to:\n{new_path}", parent=dlg)
            dlg.destroy()

        ttk.Button(btn_frame, text="Save", style="green.TButton", command=save_log_path).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="Cancel", style="gray.TButton", command=dlg.destroy).pack(side=tk.LEFT, padx=4)

    def _on_set_local_pkg_dir(self):
        """Open a dialog to configure the local package directory."""
        dlg = tk.Toplevel(self)
        dlg.title("Local Package Directory")
        dlg.geometry("560x200")
        dlg.configure(bg="#1e1e2e")
        dlg.resizable(False, False)
        dlg.grab_set()

        tk.Label(dlg, text="Local package directory:", bg="#1e1e2e", fg="#cdd6f4",
                 font=("Segoe UI", 10)).grid(row=0, column=0, sticky=tk.W, padx=12, pady=(16, 4))

        path_var = tk.StringVar(value=self._local_pkg_dir)
        entry = ttk.Entry(dlg, textvariable=path_var, width=42)
        entry.grid(row=0, column=1, sticky=tk.W, padx=(4, 4), pady=(16, 4))

        def browse():
            chosen = filedialog.askdirectory(
                title="Select Local Package Directory",
                initialdir=self._local_pkg_dir or str(Path.home()),
            )
            if chosen:
                path_var.set(chosen)

        ttk.Button(dlg, text="Browse...", command=browse).grid(row=0, column=2, padx=4, pady=(16, 4))

        tk.Label(
            dlg,
            text=(
                "If set, all files in this directory will be uploaded to the remote\n"
                "machine before installation. The AI will use them instead of downloading."
            ),
            bg="#1e1e2e", fg="#6c7086", font=("Segoe UI", 9), justify=tk.LEFT,
        ).grid(row=1, column=0, columnspan=3, sticky=tk.W, padx=12, pady=4)

        btn_frame = tk.Frame(dlg, bg="#1e1e2e")
        btn_frame.grid(row=2, column=0, columnspan=3, pady=12)

        def save_pkg_dir():
            new_path = path_var.get().strip()
            self._local_pkg_dir = new_path
            self._settings["local_pkg_dir"] = new_path
            _save_settings(self._settings)
            if new_path:
                messagebox.showinfo("Saved", f"Local package directory set to:\n{new_path}", parent=dlg)
            else:
                messagebox.showinfo("Cleared", "Local package directory cleared.\nPackages will be downloaded from the internet.", parent=dlg)
            dlg.destroy()

        def clear_pkg_dir():
            path_var.set("")

        ttk.Button(btn_frame, text="Save", style="green.TButton", command=save_pkg_dir).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="Clear", style="yellow.TButton", command=clear_pkg_dir).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="Cancel", style="gray.TButton", command=dlg.destroy).pack(side=tk.LEFT, padx=4)

    # ── UI Construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TLabel", background="#1e1e2e", foreground="#cdd6f4", font=("Segoe UI", 10))
        style.configure("TEntry", fieldbackground="#313244", foreground="#cdd6f4", font=("Segoe UI", 10))
        style.configure("TButton", font=("Segoe UI", 10, "bold"), padding=6)
        style.configure("green.TButton", background="#a6e3a1", foreground="#1e1e2e")
        style.configure("red.TButton", background="#f38ba8", foreground="#1e1e2e")
        style.configure("yellow.TButton", background="#f9e2af", foreground="#1e1e2e")
        style.configure("gray.TButton", background="#6c7086", foreground="#1e1e2e")
        style.configure("orange.TButton", background="#fab387", foreground="#1e1e2e")
        style.configure("terminate.TButton", background="#ff2020", foreground="#ffffff", font=("Segoe UI", 10, "bold"))
        style.configure("TProgressbar", troughcolor="#313244", background="#89b4fa", thickness=20)

        # ── Input panel ──
        input_frame = tk.Frame(self, bg="#1e1e2e", padx=16, pady=12)
        input_frame.pack(fill=tk.X)

        fields = [
            ("Software Name:", "software"),
            ("Remote IP / Host:", "host"),
            ("Username:", "username"),
            ("Password:", "password"),
        ]
        self._vars = {}
        for row, (label, key) in enumerate(fields):
            ttk.Label(input_frame, text=label).grid(row=row, column=0, sticky=tk.W, pady=4)
            show = "*" if key == "password" else ""
            var = tk.StringVar()
            entry = ttk.Entry(input_frame, textvariable=var, width=40, show=show)
            entry.grid(row=row, column=1, sticky=tk.W, padx=(12, 0), pady=4)
            self._vars[key] = var

        # ── Control buttons ──
        btn_frame = tk.Frame(self, bg="#1e1e2e", padx=16, pady=6)
        btn_frame.pack(fill=tk.X)

        self._btn_install = ttk.Button(btn_frame, text="Install", style="green.TButton", command=self._on_install)
        self._btn_install.pack(side=tk.LEFT, padx=4)

        self._btn_uninstall = ttk.Button(btn_frame, text="Uninstall", style="orange.TButton", command=self._on_uninstall)
        self._btn_uninstall.pack(side=tk.LEFT, padx=4)

        self._btn_pause = ttk.Button(btn_frame, text="Pause", style="yellow.TButton", command=self._on_pause, state=tk.DISABLED)
        self._btn_pause.pack(side=tk.LEFT, padx=4)

        self._btn_cancel = ttk.Button(btn_frame, text="Cancel", style="red.TButton", command=self._on_cancel, state=tk.DISABLED)
        self._btn_cancel.pack(side=tk.LEFT, padx=4)

        self._btn_quit = ttk.Button(btn_frame, text="Quit", style="gray.TButton", command=self._on_quit)
        self._btn_quit.pack(side=tk.LEFT, padx=4)

        self._btn_terminate = ttk.Button(btn_frame, text="⚡ Terminate", style="terminate.TButton", command=self._on_terminate)
        self._btn_terminate.pack(side=tk.LEFT, padx=(16, 4))

        self._status_label = ttk.Label(btn_frame, text="Status: Idle", font=("Segoe UI", 10, "italic"))
        self._status_label.pack(side=tk.LEFT, padx=16)

        # ── Progress panel ──
        prog_frame = tk.LabelFrame(self, text=" Progress ", bg="#1e1e2e", fg="#89b4fa",
                                   font=("Segoe UI", 10, "bold"), padx=12, pady=8)
        prog_frame.pack(fill=tk.X, padx=16, pady=(4, 0))

        self._progress_var = tk.DoubleVar(value=0)
        self._progress_bar = ttk.Progressbar(prog_frame, variable=self._progress_var,
                                              maximum=100, style="TProgressbar")
        self._progress_bar.pack(fill=tk.X)

        self._progress_label = ttk.Label(prog_frame, text="0 / 0 commands")
        self._progress_label.pack(anchor=tk.W, pady=(4, 0))

        # ── Log panel ──
        log_frame = tk.LabelFrame(self, text=" Execution Log ", bg="#1e1e2e", fg="#89b4fa",
                                  font=("Segoe UI", 10, "bold"), padx=12, pady=8)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=16, pady=8)

        self._log_box = scrolledtext.ScrolledText(
            log_frame, bg="#181825", fg="#cdd6f4", font=("Consolas", 9),
            state=tk.DISABLED, wrap=tk.WORD, insertbackground="#cdd6f4"
        )
        self._log_box.pack(fill=tk.BOTH, expand=True)
        self._log_box.tag_config("success", foreground="#a6e3a1")
        self._log_box.tag_config("error", foreground="#f38ba8")
        self._log_box.tag_config("info", foreground="#89b4fa")
        self._log_box.tag_config("cmd", foreground="#f9e2af")


    # ── Event handlers ────────────────────────────────────────────────────────

    def _on_install(self):
        software = self._vars["software"].get().strip()
        host = self._vars["host"].get().strip()
        username = self._vars["username"].get().strip()
        password = self._vars["password"].get().strip()

        if not all([software, host, username, password]):
            messagebox.showwarning("Missing Fields", "Please fill in all required fields.")
            return

        self._clear_log()
        self._progress_var.set(0)
        self._progress_label.config(text="0 / 0 commands")

        config = InstallerConfig(
            software=software,
            host=host,
            username=username,
            password=password,
            local_pkg_dir=self._local_pkg_dir,
        )

        self._installer = Installer(
            config=config,
            on_log=self._enqueue_log,
            on_progress=self._enqueue_progress,
            on_state_change=self._on_state_change,
            log_dir=self._log_dir,
        )
        self._installer.start()

    def _on_pause(self):
        if self._installer is None:
            return
        if self._installer.state == State.RUNNING:
            self._installer.pause()
            self._btn_pause.config(text="Resume")
        elif self._installer.state == State.PAUSED:
            self._installer.resume()
            self._btn_pause.config(text="Pause")

    def _on_cancel(self):
        if self._installer is None:
            return
        if messagebox.askyesno("Cancel Installation",
                               "Are you sure you want to cancel? The software will be uninstalled."):
            self._installer.cancel()

    def _on_uninstall(self):
        software = self._vars["software"].get().strip()
        host = self._vars["host"].get().strip()
        username = self._vars["username"].get().strip()
        password = self._vars["password"].get().strip()

        if not all([software, host, username, password]):
            messagebox.showwarning("Missing Fields", "Please fill in all required fields.")
            return

        if not messagebox.askyesno(
            "Confirm Uninstall",
            f"This will completely uninstall '{software}' from {host}.\n\nAre you sure?"
        ):
            return

        self._clear_log()
        self._progress_var.set(0)
        self._progress_label.config(text="0 / 0 commands")

        config = InstallerConfig(
            software=software,
            host=host,
            username=username,
            password=password,
        )

        self._installer = Installer(
            config=config,
            on_log=self._enqueue_log,
            on_progress=self._enqueue_progress,
            on_state_change=self._on_state_change,
            log_dir=self._log_dir,
        )
        self._installer.start_uninstall()

    def _on_quit(self):
        """Quit the app. If a job is running, wait for the current command+verify to finish first."""
        is_running = (
            self._installer is not None
            and self._installer.state in (State.RUNNING, State.PAUSED, State.UNINSTALLING)
        )
        if is_running:
            if not messagebox.askyesno(
                "Quit",
                "A job is running. The app will quit after the current command and AI verification finish.\n\nProceed?"
            ):
                return
            self._quitting = True
            self._status_label.config(text="Status: Waiting to quit...")
            self._btn_quit.config(state=tk.DISABLED)
            # Signal installer to stop after current command completes
            self._installer.quit_after_current()
        else:
            self.destroy()

    def _on_terminate(self):
        """Emergency hard stop — kills SSH, drops all threads, exits immediately."""
        if not messagebox.askyesno(
            "⚡ Terminate",
            "This will immediately kill all running processes and close the app "
            "without waiting or uninstalling anything.\n\nAre you sure?",
            icon="warning"
        ):
            return
        # Force-close SSH if open
        try:
            if self._installer and self._installer._thread:
                # Disconnect SSH to unblock any blocking read in the thread
                import threading
                for t in threading.enumerate():
                    if hasattr(t, '_target') and t != threading.main_thread():
                        pass  # threads are daemon=True, will die with process
        except Exception:
            pass
        import os
        os._exit(1)  # Hard kill — no cleanup, no waiting, works on Windows & Linux

    def _on_state_change(self, state: State):
        self.after(0, self._apply_state, state)

    def _apply_state(self, state: State):
        labels = {
            State.IDLE: "Idle",
            State.RUNNING: "Running...",
            State.PAUSED: "Paused",
            State.CANCELLED: "Cancelling — Uninstalling...",
            State.DONE: "Done",
            State.FAILED: "Failed",
            State.UNINSTALLING: "Uninstalling...",
            State.UNINSTALLED: "Uninstalled",
        }
        self._status_label.config(text=f"Status: {labels.get(state, str(state))}")

        if state in (State.RUNNING, State.UNINSTALLING):
            self._btn_install.config(state=tk.DISABLED)
            self._btn_uninstall.config(state=tk.DISABLED)
            self._btn_pause.config(state=tk.NORMAL, text="Pause")
            self._btn_cancel.config(state=tk.NORMAL if state == State.RUNNING else tk.DISABLED)
        elif state == State.PAUSED:
            self._btn_pause.config(text="Resume")
        elif state in (State.DONE, State.FAILED, State.CANCELLED, State.UNINSTALLED):
            self._btn_install.config(state=tk.NORMAL)
            self._btn_uninstall.config(state=tk.NORMAL)
            self._btn_pause.config(state=tk.DISABLED, text="Pause")
            self._btn_cancel.config(state=tk.DISABLED)
            self._btn_quit.config(state=tk.NORMAL)
            if self._quitting:
                self.destroy()
                return
            if state == State.DONE:
                messagebox.showinfo("Done", f"'{self._installer.config.software}' installed successfully.")
            elif state == State.UNINSTALLED:
                messagebox.showinfo("Uninstalled", f"'{self._installer.config.software}' has been uninstalled.")
            elif state == State.FAILED:
                messagebox.showerror("Failed", "Operation failed. Check the log for details.")

    # ── Log helpers ───────────────────────────────────────────────────────────

    def _enqueue_log(self, msg: str):
        self._log_queue.put(msg)

    def _enqueue_progress(self, current: int, total: int):
        self._progress_queue.put((current, total))

    def _append_log(self, msg: str):
        self._log_box.config(state=tk.NORMAL)
        tag = None
        lower = msg.lower()
        if msg.startswith(">>>"):
            tag = "cmd"
        elif "success" in lower:
            tag = "success"
        elif "fail" in lower or "error" in lower:
            tag = "error"
        elif msg.startswith("Connecting") or msg.startswith("AI") or msg.startswith("Ask"):
            tag = "info"
        self._log_box.insert(tk.END, msg + "\n", tag or "")
        self._log_box.see(tk.END)
        self._log_box.config(state=tk.DISABLED)

    def _clear_log(self):
        self._log_box.config(state=tk.NORMAL)
        self._log_box.delete("1.0", tk.END)
        self._log_box.config(state=tk.DISABLED)

    # ── Queue polling ─────────────────────────────────────────────────────────

    def _poll_queues(self):
        try:
            while True:
                msg = self._log_queue.get_nowait()
                self._append_log(msg)
        except queue.Empty:
            pass

        try:
            while True:
                current, total = self._progress_queue.get_nowait()
                pct = (current / total * 100) if total > 0 else 0
                self._progress_var.set(pct)
                self._progress_label.config(text=f"{current} / {total} commands")
        except queue.Empty:
            pass

        self.after(100, self._poll_queues)
