"""Qt session orchestration; the GUI never performs privileged networking directly."""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import threading
from pathlib import Path
from uuid import uuid4

from PySide6.QtCore import QObject, QProcess, QProcessEnvironment, QThread, Signal

from captivate.config import SessionConfig
from captivate.diagnostics import report
from captivate.environment import system_environment
from captivate.portal import PortalServer


class DiagnosticsWorker(QThread):
    result = Signal(dict)

    def run(self):
        try:
            self.result.emit(report())
        except (OSError, ValueError) as exc:
            self.result.emit({"ready": False, "error": str(exc), "adapters": [], "tools": {}})


class SessionController(QObject):
    status = Signal(str)
    log = Signal(str)
    clients = Signal(list)
    send_command = Signal(str)
    completed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.process: QProcess | None = None
        self.portal: PortalServer | None = None
        self.preview: PortalServer | None = None
        self.helper_directory: tempfile.TemporaryDirectory | None = None
        self.pending: dict[str, dict] = {}
        self.pending_lock = threading.Lock()
        self.stdout_buffer = ""
        self.state = "idle"
        self.error_seen = False
        self.send_command.connect(self._write_command)

    @property
    def busy(self):
        return self.process is not None

    def set_state(self, state: str):
        self.state = state
        self.status.emit(state)

    def preview_page(self, config: SessionConfig) -> str:
        if self.preview:
            self.preview.stop()
        self.preview = PortalServer(config, preview=True, log=self.log.emit)
        self.preview.start()
        self.log.emit("Preview is running on loopback. No network configuration was changed.")
        return self.preview.url

    def start(self, config: SessionConfig):
        if self.busy:
            raise RuntimeError("A session is already running.")
        config.validate()
        self.portal = PortalServer(config, grant=self.grant, log=self.log.emit)
        self.portal.start()
        try:
            self._launch({"command": "start", "config": config.network_payload()})
        except (OSError, RuntimeError):
            self.portal.stop()
            self.portal = None
            raise

    def recover(self):
        if self.busy:
            raise RuntimeError("Stop the current session before recovery.")
        self._launch({"command": "recover"})

    def _launch(self, payload: dict):
        pkexec = shutil.which("pkexec")
        if not pkexec:
            raise RuntimeError("pkexec is missing. Install the PolicyKit package for your distribution.")
        arguments = self._helper_arguments()
        self.process = QProcess(self)
        environment = QProcessEnvironment()
        for key, value in system_environment().items():
            environment.insert(key, value)
        self.process.setProcessEnvironment(environment)
        self.process.setProgram(pkexec)
        self.process.setArguments(arguments)
        self.process.started.connect(lambda: self._write_command(json.dumps(payload)))
        self.process.readyReadStandardOutput.connect(self._read_stdout)
        self.process.readyReadStandardError.connect(self._read_stderr)
        self.process.finished.connect(self._finished)
        self.process.errorOccurred.connect(self._process_error)
        self.stdout_buffer = ""
        self.error_seen = False
        self.set_state("authorizing")
        self.log.emit("Requesting administrator authorization for the networking helper.")
        self.process.start()

    def _helper_arguments(self) -> list[str]:
        if not getattr(sys, "frozen", False):
            return ["/usr/bin/python3", "-I", str(Path(__file__).parent / "helper_entry.py")]
        bundle = Path(sys.executable).parent / "helper"
        if os.environ.get("APPIMAGE"):
            # Root cannot enter a user-mounted FUSE filesystem. Keep the helper and
            # its Python libraries on an ordinary filesystem until pkexec exits.
            cache = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "captivate"
            cache.mkdir(parents=True, exist_ok=True, mode=0o700)
            self.helper_directory = tempfile.TemporaryDirectory(prefix="helper-", dir=cache)
            staged = Path(self.helper_directory.name) / "helper"
            try:
                shutil.copytree(bundle, staged)
            except OSError:
                self._remove_staged_helper()
                raise
            bundle = staged
            self.log.emit("Prepared the networking helper outside the AppImage mount.")
        return [str(bundle / "captivate-helper")]

    def _remove_staged_helper(self):
        if self.helper_directory:
            self.helper_directory.cleanup()
            self.helper_directory = None

    def _write_command(self, command: str):
        if self.process and self.process.state() != QProcess.ProcessState.NotRunning:
            self.process.write((command + "\n").encode())

    def grant(self, address: str):
        """Called on an HTTP thread; queued Qt signals serialize the helper channel."""
        request_id = uuid4().hex
        request = {"event": threading.Event(), "ok": False}
        with self.pending_lock:
            self.pending[request_id] = request
        self.send_command.emit(json.dumps({"command": "allow", "ip": address, "request_id": request_id}))
        try:
            if not request["event"].wait(timeout=12):
                raise TimeoutError("The networking helper did not respond.")
            if not request["ok"]:
                raise RuntimeError("The networking helper rejected the access request.")
        finally:
            with self.pending_lock:
                self.pending.pop(request_id, None)

    def _read_stdout(self):
        self.stdout_buffer += bytes(self.process.readAllStandardOutput()).decode(errors="replace")
        while "\n" in self.stdout_buffer:
            line, self.stdout_buffer = self.stdout_buffer.split("\n", 1)
            try:
                message = json.loads(line)
            except ValueError:
                self.log.emit("The helper returned an unreadable status message.")
                continue
            event = message.get("event")
            if event == "log":
                self.log.emit(message["message"])
            elif event == "error":
                self.error_seen = True
                self.log.emit("Error: " + message["message"])
                self.set_state("failed")
            elif event == "started":
                self.set_state("running")
                self.log.emit(f"Portal available at http://{message['address']}/")
                if message.get("sharing"):
                    self.log.emit("Internet sharing is enabled after visitor confirmation.")
                else:
                    self.log.emit("Offline hosting is active; no internet uplink is selected.")
            elif event == "clients":
                self.clients.emit(message["clients"])
            elif event == "stopping":
                self.set_state("stopping")
            elif event == "allowed":
                with self.pending_lock:
                    request = self.pending.get(message.get("request_id"))
                    if request:
                        request["ok"] = bool(message["ok"])
                        request["event"].set()
                if not message["ok"]:
                    self.log.emit("Access denied: " + message.get("message", "Unknown helper error."))

    def _read_stderr(self):
        text = bytes(self.process.readAllStandardError()).decode(errors="replace").strip()
        if text:
            self.log.emit(text)

    def _process_error(self, error):
        if error == QProcess.ProcessError.FailedToStart:
            self.error_seen = True
            self.log.emit("Unable to launch pkexec. Check that PolicyKit is installed.")
            self._finished(1)

    def _finished(self, exit_code, _exit_status=None):
        with self.pending_lock:
            for request in self.pending.values():
                request["event"].set()
        if self.portal:
            self.portal.stop()
            self.portal = None
        if self.process:
            self.process.deleteLater()
            self.process = None
        self._remove_staged_helper()
        self.clients.emit([])
        if exit_code and not self.error_seen:
            if self.state == "authorizing":
                self.log.emit("The helper exited before startup. Administrator authorization may have been cancelled.")
            else:
                self.log.emit("The networking helper exited unexpectedly. Check the preceding errors and recover the session.")
        self.set_state("failed" if exit_code or self.error_seen else "idle")
        self.completed.emit()

    def stop(self):
        if self.process:
            self.set_state("stopping")
            self._write_command(json.dumps({"command": "stop"}))
            self.process.closeWriteChannel()

    def close_preview(self):
        if self.preview:
            self.preview.stop()
            self.preview = None
