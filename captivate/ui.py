"""Captivate's conventional Qt Widgets desktop interface."""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QSize, Qt, QUrl
from PySide6.QtGui import QColor, QDesktopServices, QFont, QIcon, QPalette
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from captivate import __version__
from captivate.config import TEMPLATES, SessionConfig, load_preferences, save_preferences
from captivate.controller import DiagnosticsWorker, SessionController
from captivate.environment import system_library_path

ASSETS = Path(__file__).parent / "assets"

STYLESHEET = """
QMainWindow, QWidget#workspace { background: #edf2f8; color: #24364b; }
QWidget { font-size: 14px; color: #24364b; }
QFrame#sidebar { background: #243b58; }
QLabel#brand { color: #fff; font-size: 23px; font-weight: 700; }
QLabel#railNote { color: #c5d4e8; font-size: 12px; }
QListWidget#navigation { background: transparent; border: none; outline: none; color: #dce7f5; }
QListWidget#navigation::item { color: #dce7f5; padding: 14px 10px; border-radius: 6px; margin-bottom: 5px; }
QListWidget#navigation::item:selected { background: #365575; color: #fff; }
QListWidget#navigation::item:hover { background: #304d6c; }
QListWidget#navigation::item:focus { border: 1px solid #a8c9f0; }
QLabel#pageTitle { font-size: 26px; font-weight: 700; }
QLabel#subtitle, QLabel#muted { color: #526276; }
QLabel#state { background: #e0e8f2; border: 1px solid #c1cedf; padding: 7px 12px; border-radius: 6px; font-weight: 600; }
QLabel#stage { color: #526276; padding: 8px 0; }
QLabel#notice { background: #e2ebf7; border: 1px solid #bfd0e5; padding: 12px; border-radius: 6px; color: #324d70; }
QGroupBox { background: #fff; border: 1px solid #ccd7e3; border-radius: 8px; margin-top: 13px; padding: 18px 14px 14px; font-weight: 600; }
QGroupBox::title { subcontrol-origin: margin; left: 14px; padding: 0 5px; }
QLineEdit, QComboBox, QSpinBox, QPlainTextEdit { background: #fff; border: 1px solid #aebed1; border-radius: 5px; padding: 8px; selection-background-color: #ccdef6; selection-color: #152f54; }
QLineEdit, QPlainTextEdit { placeholder-text-color: #647386; }
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QPlainTextEdit:focus { border: 2px solid #235daf; padding: 7px; }
QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled { background: #edf1f5; color: #647386; }
QComboBox::drop-down { border: none; width: 24px; }
QPushButton { background: #fff; border: 1px solid #aebed1; border-radius: 6px; padding: 10px 15px; font-weight: 600; }
QPushButton:hover { background: #e8eff8; border-color: #8099b8; }
QPushButton:pressed { background: #d9e5f4; }
QPushButton:focus { border: 2px solid #235daf; padding: 9px 14px; }
QPushButton#primary { background: #235daf; border-color: #235daf; color: #fff; }
QPushButton#primary:hover { background: #194b90; }
QPushButton#primary:disabled { background: #8192a9; border-color: #8192a9; }
QPushButton:disabled { color: #65758a; background: #edf1f5; }
QFrame#preview { background: #fff; border: 1px solid #ccd7e3; border-radius: 8px; }
QLabel#previewTitle { font-size: 24px; font-weight: 700; }
QLabel#previewNetwork { font-size: 16px; font-weight: 650; }
QLabel#previewAction { background: #235daf; color: #fff; padding: 12px; border-radius: 6px; font-weight: 600; }
QLabel#previewFooter { color: #526276; font-size: 12px; }
QScrollArea { background: transparent; border: none; }
QScrollArea > QWidget > QWidget { background: #edf2f8; }
QTableWidget { background: #fff; border: 1px solid #ccd7e3; border-radius: 6px; gridline-color: #e4ebf3; }
QHeaderView::section { background: #e4ecf6; padding: 10px; border: none; border-bottom: 1px solid #ccd7e3; font-weight: 600; }
QSplitter::handle { background: transparent; }
QCheckBox { spacing: 8px; }
QToolTip { background: #fff; color: #24364b; border: 1px solid #aebed1; padding: 6px; }
"""


def text_label(text: str, *, name="", wrap=True) -> QLabel:
    label = QLabel(text)
    label.setTextFormat(Qt.TextFormat.PlainText)
    label.setWordWrap(wrap)
    if name:
        label.setObjectName(name)
    return label


def scrollable(widget: QWidget) -> QScrollArea:
    area = QScrollArea()
    area.setWidgetResizable(True)
    area.setWidget(widget)
    return area


def open_browser(url: str) -> bool:
    with system_library_path():
        return QDesktopServices.openUrl(QUrl(url))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Captivate")
        self.setWindowIcon(QIcon(str(ASSETS / "captivate.svg")))
        self.resize(1160, 800)
        self.setMinimumSize(900, 660)
        self.config = load_preferences()
        self.controller = SessionController(self)
        self.controller.status.connect(self.update_status)
        self.controller.log.connect(self.add_log)
        self.controller.clients.connect(self.update_clients)
        self.controller.completed.connect(self.session_completed)
        self.close_requested = False
        self.worker = None
        self.system_report = {}
        self._build_shell()
        self._load_config()
        self._wire_fields()
        self.update_portal_summary()
        self.refresh_diagnostics()

    def _build_shell(self):
        root = QWidget()
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(198)
        rail = QVBoxLayout(sidebar)
        rail.setContentsMargins(16, 26, 16, 22)
        rail.setSpacing(20)
        brand_row = QHBoxLayout()
        mark = QLabel()
        mark.setPixmap(QIcon(str(ASSETS / "captivate.svg")).pixmap(34, 34))
        brand_row.addWidget(mark)
        brand_row.addWidget(text_label("Captivate", name="brand", wrap=False))
        rail.addLayout(brand_row)
        self.navigation = QListWidget()
        self.navigation.setObjectName("navigation")
        self.navigation.setIconSize(QSize(20, 20))
        self.navigation.setSpacing(2)
        for title, icon in (("Hotspot", "hotspot"), ("Portal page", "page"),
                            ("Devices", "devices"), ("Diagnostics", "tools"), ("About", "info")):
            item = QListWidgetItem(QIcon(str(ASSETS / "icons" / f"{icon}.svg")), title)
            self.navigation.addItem(item)
        rail.addWidget(self.navigation, 1)
        rail.addWidget(text_label(f"Version {__version__}\nOpen source by Uzair", name="railNote"))
        layout.addWidget(sidebar)
        workspace = QWidget()
        workspace.setObjectName("workspace")
        content = QVBoxLayout(workspace)
        content.setContentsMargins(28, 24, 28, 20)
        content.setSpacing(16)
        header = QHBoxLayout()
        heading = QVBoxLayout()
        self.page_title = text_label("Hotspot", name="pageTitle")
        self.subtitle = text_label("Publish a page to everyone who joins your Wi-Fi.", name="subtitle")
        heading.addWidget(self.page_title)
        heading.addWidget(self.subtitle)
        header.addLayout(heading, 1)
        self.state_label = text_label("Stopped", name="state", wrap=False)
        header.addWidget(self.state_label, 0, Qt.AlignmentFlag.AlignTop)
        content.addLayout(header)
        self.stages = text_label("Hotspot: stopped     /     Portal: ready to preview     /     Sharing: offline", name="stage")
        content.addWidget(self.stages)
        self.pages = QStackedWidget()
        self.pages.addWidget(self._hotspot_page())
        self.pages.addWidget(self._portal_page())
        self.pages.addWidget(self._devices_page())
        self.pages.addWidget(self._diagnostics_page())
        self.pages.addWidget(self._about_page())
        content.addWidget(self.pages, 1)
        self.footer_note = text_label("Preview your page before starting the hotspot.", name="muted")
        footer = QHBoxLayout()
        footer.addWidget(self.footer_note, 1)
        self.preview_button = QPushButton("Preview in browser")
        self.preview_button.clicked.connect(self.open_preview)
        self.start_button = QPushButton("Start hotspot")
        self.start_button.setObjectName("primary")
        self.start_button.setMinimumWidth(145)
        self.start_button.clicked.connect(self.toggle_session)
        footer.addWidget(self.preview_button)
        footer.addWidget(self.start_button)
        content.addLayout(footer)
        layout.addWidget(workspace, 1)
        self.setCentralWidget(root)
        self.navigation.currentRowChanged.connect(self.change_page)
        self.navigation.setCurrentRow(0)

    def _hotspot_page(self) -> QWidget:
        page = QWidget()
        columns = QHBoxLayout(page)
        columns.setContentsMargins(0, 0, 0, 0)
        columns.setSpacing(22)
        form_widget = QWidget()
        form_layout = QVBoxLayout(form_widget)
        form_layout.setContentsMargins(0, 0, 0, 0)
        form_layout.setSpacing(16)
        self.network_box = QGroupBox("Wi-Fi hotspot")
        form = QFormLayout(self.network_box)
        form.setVerticalSpacing(12)
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        self.adapter = QComboBox()
        self.adapter.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.adapter.setMinimumContentsLength(12)
        self.adapter.setAccessibleName("Wi-Fi adapter")
        form.addRow("Wi-Fi adapter", self.adapter)
        self.ssid = QLineEdit()
        self.ssid.setMaxLength(32)
        form.addRow("Network name", self.ssid)
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password.setPlaceholderText("Leave empty for an open hotspot")
        self.password.setMaxLength(63)
        form.addRow("Wi-Fi password", self.password)
        self.show_password = QCheckBox("Show password")
        self.show_password.toggled.connect(lambda shown: self.password.setEchoMode(
            QLineEdit.EchoMode.Normal if shown else QLineEdit.EchoMode.Password))
        form.addRow("", self.show_password)
        self.gateway = QLineEdit()
        form.addRow("Gateway / subnet", self.gateway)
        form.addRow("Radio", text_label("2.4 GHz · Channel 6", name="muted"))
        form_layout.addWidget(self.network_box)
        self.sharing_box = QGroupBox("Internet access")
        sharing = QFormLayout(self.sharing_box)
        sharing.setVerticalSpacing(12)
        sharing.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        sharing.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        self.uplink = QComboBox()
        self.uplink.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.uplink.setMinimumContentsLength(12)
        self.uplink.addItem("Offline — local pages only", "")
        sharing.addRow("Internet uplink", self.uplink)
        self.duration = QSpinBox()
        self.duration.setRange(1, 1440)
        self.duration.setSuffix(" minutes")
        sharing.addRow("Access duration", self.duration)
        sharing.addRow(text_label("A separate Ethernet, USB-tethering, or Wi-Fi adapter is required for internet sharing.", name="muted"))
        form_layout.addWidget(self.sharing_box)
        self.radio_note = text_label("Checking your laptop's networking capabilities…", name="notice")
        form_layout.addWidget(self.radio_note)
        self.refresh_button = QPushButton("Refresh adapters")
        self.refresh_button.clicked.connect(self.refresh_diagnostics)
        form_layout.addWidget(self.refresh_button, 0, Qt.AlignmentFlag.AlignLeft)
        form_layout.addStretch()
        columns.addWidget(scrollable(form_widget), 3)
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(14)
        right_layout.addWidget(text_label("Visitor page", name="previewNetwork"))
        self.preview_frame = self._preview_panel()
        right_layout.addWidget(self.preview_frame)
        self.template_summary = text_label("", name="muted")
        right_layout.addWidget(self.template_summary)
        edit = QPushButton("Edit portal page")
        edit.clicked.connect(lambda: self.navigation.setCurrentRow(1))
        right_layout.addWidget(edit)
        right_layout.addStretch()
        columns.addWidget(scrollable(right), 2)
        return page

    def _preview_panel(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("preview")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(24, 28, 24, 24)
        layout.setSpacing(16)
        self.preview_ssid = text_label("Captivate", name="previewNetwork")
        mark = QLabel()
        mark.setPixmap(QIcon(str(ASSETS / "captivate.svg")).pixmap(44, 44))
        brand = QHBoxLayout()
        brand.addWidget(mark)
        brand.addWidget(self.preview_ssid, 1)
        layout.addLayout(brand)
        self.preview_title = text_label("", name="previewTitle")
        self.preview_message = text_label("", name="muted")
        self.preview_action = text_label("", name="previewAction")
        self.preview_action.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_footer = text_label("", name="previewFooter")
        layout.addWidget(self.preview_title)
        layout.addWidget(self.preview_message)
        layout.addWidget(self.preview_action)
        layout.addWidget(self.preview_footer)
        return frame

    def _portal_page(self) -> QScrollArea:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        self.portal_box = QGroupBox("Page content")
        form = QFormLayout(self.portal_box)
        form.setVerticalSpacing(12)
        self.template = QComboBox()
        for key, (title, _description) in TEMPLATES.items():
            self.template.addItem(title, key)
        form.addRow("Template", self.template)
        self.template_description = text_label("", name="muted")
        form.addRow("", self.template_description)
        self.title_edit = QLineEdit()
        self.title_edit.setMaxLength(16000)
        form.addRow("Page title", self.title_edit)
        self.message_edit = QPlainTextEdit()
        self.message_edit.setMinimumHeight(100)
        self.message_edit.setMaximumHeight(140)
        form.addRow("Message", self.message_edit)
        self.button_edit = QLineEdit()
        form.addRow("Button label", self.button_edit)
        self.terms_edit = QPlainTextEdit()
        self.terms_edit.setMinimumHeight(100)
        self.terms_edit.setMaximumHeight(140)
        self.terms_label = QLabel("Terms")
        form.addRow(self.terms_label, self.terms_edit)
        self.vouchers_edit = QPlainTextEdit()
        self.vouchers_edit.setPlaceholderText("One code per line. Codes can be reused until the hotspot stops.")
        self.vouchers_edit.setMinimumHeight(100)
        self.vouchers_edit.setMaximumHeight(140)
        self.vouchers_label = QLabel("Voucher codes")
        form.addRow(self.vouchers_label, self.vouchers_edit)
        self.custom_row = QWidget()
        custom = QHBoxLayout(self.custom_row)
        custom.setContentsMargins(0, 0, 0, 0)
        self.directory_edit = QLineEdit()
        self.directory_edit.setPlaceholderText("Folder containing index.html")
        browse = QPushButton("Browse…")
        browse.clicked.connect(self.choose_directory)
        custom.addWidget(self.directory_edit, 1)
        custom.addWidget(browse)
        self.custom_label = QLabel("Website folder")
        form.addRow(self.custom_label, self.custom_row)
        layout.addWidget(self.portal_box)
        layout.addWidget(text_label(
            "Custom websites run as static files. Use /captivate/token and /captivate/continue to confirm visitor access. "
            "Payment verification requires an external service; a payment link alone does not grant access.", name="notice"))
        layout.addStretch()
        return scrollable(page)

    def _devices_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        self.device_note = text_label("No hotspot session is running. Devices appear after receiving a DHCP lease.", name="notice")
        layout.addWidget(self.device_note)
        self.device_table = QTableWidget(0, 4)
        self.device_table.setHorizontalHeaderLabels(["Device", "IP address", "MAC address", "Portal access"])
        self.device_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.device_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.device_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.device_table.verticalHeader().hide()
        layout.addWidget(self.device_table, 1)
        layout.addWidget(text_label("The list shows active DHCP leases. A lease may remain after a device disconnects. Access expires at the configured duration.", name="muted"))
        return page

    def _diagnostics_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        self.diagnostics_text = QPlainTextEdit()
        self.diagnostics_text.setReadOnly(True)
        self.diagnostics_text.setMaximumHeight(230)
        layout.addWidget(self.diagnostics_text)
        actions = QHBoxLayout()
        refresh = QPushButton("Refresh diagnostics")
        refresh.clicked.connect(self.refresh_diagnostics)
        self.recover_button = QPushButton("Recover interrupted session")
        self.recover_button.clicked.connect(self.recover_session)
        export = QPushButton("Export log…")
        export.clicked.connect(self.export_log)
        actions.addWidget(refresh)
        actions.addWidget(self.recover_button)
        actions.addStretch()
        actions.addWidget(export)
        layout.addLayout(actions)
        layout.addWidget(text_label("Session log", name="previewNetwork"))
        self.logs = QPlainTextEdit()
        self.logs.setReadOnly(True)
        self.logs.setMaximumBlockCount(1500)
        layout.addWidget(self.logs, 1)
        return page

    def _about_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        box = QGroupBox("Captivate")
        about = QVBoxLayout(box)
        about.addWidget(text_label(f"Captivate {__version__}", name="previewTitle"))
        about.addWidget(text_label("A Linux desktop utility for customizable Wi-Fi captive portals.\n\nMaintained by Uzair. Released under the MIT license.\n\nBuilt with Python and Qt for Python (PySide6). Qt and bundled components retain their respective licenses."))
        for label, url in (("Project on GitHub", "https://github.com/uzairdeveloper223/Captivate"),
                           ("Uzair's website", "https://uzair.is-a.dev")):
            button = QPushButton(label)
            button.clicked.connect(lambda _checked=False, address=url: open_browser(address))
            about.addWidget(button, 0, Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(box)
        layout.addWidget(text_label("Captive prompts are controlled by the visitor's operating system. If a prompt does not appear, open the hotspot gateway's HTTP address directly.", name="notice"))
        layout.addStretch()
        return page

    def _load_config(self):
        config = self.config
        self.ssid.setText(config.ssid)
        self.gateway.setText(config.gateway)
        self.duration.setValue(config.session_minutes)
        self.template.setCurrentIndex(max(0, self.template.findData(config.template)))
        self.title_edit.setText(config.title)
        self.message_edit.setPlainText(config.message)
        self.button_edit.setText(config.button)
        self.terms_edit.setPlainText(config.terms)
        self.directory_edit.setText(config.custom_directory)

    def _wire_fields(self):
        for field in (self.ssid, self.title_edit, self.button_edit):
            field.textChanged.connect(self.update_portal_summary)
        self.message_edit.textChanged.connect(self.update_portal_summary)
        self.template.currentIndexChanged.connect(self.update_portal_summary)
        self.uplink.currentIndexChanged.connect(self.update_portal_summary)

    def collect_config(self) -> SessionConfig:
        return SessionConfig(
            interface=self.adapter.currentData() or "", ssid=self.ssid.text().strip(),
            password=self.password.text(), gateway=self.gateway.text().strip(),
            uplink=self.uplink.currentData() or "", template=self.template.currentData(),
            title=self.title_edit.text().strip(), message=self.message_edit.toPlainText(),
            button=self.button_edit.text().strip(), terms=self.terms_edit.toPlainText(),
            vouchers=self.vouchers_edit.toPlainText(), custom_directory=self.directory_edit.text().strip(),
            session_minutes=self.duration.value(), port=self.config.port,
        )

    def update_portal_summary(self):
        template = self.template.currentData() or "welcome"
        self.preview_ssid.setText(self.ssid.text() or "Network name")
        self.preview_title.setText(self.title_edit.text() or "Page title")
        self.preview_message.setText(self.message_edit.toPlainText()[:400])
        self.preview_action.setText(self.button_edit.text() or "Continue")
        self.preview_footer.setText("Internet access after confirmation" if self.uplink.currentData() else "Local hotspot · No internet connection")
        self.template_summary.setText(TEMPLATES[template][1] + " The browser preview shows the complete page.")
        self.template_description.setText(TEMPLATES[template][1])
        for widget in (self.terms_label, self.terms_edit):
            widget.setVisible(template == "terms")
        for widget in (self.vouchers_label, self.vouchers_edit):
            widget.setVisible(template == "voucher")
        for widget in (self.custom_label, self.custom_row):
            widget.setVisible(template == "custom")
        for widget in (self.title_edit, self.message_edit, self.button_edit):
            widget.setEnabled(template != "custom")
        if template == "custom":
            self.preview_title.setText("Your custom website")
            self.preview_message.setText("The selected folder's index.html will be shown to visitors. Open the browser preview to view your website.")
            self.preview_action.setText("Custom HTML")
        if not self.controller.busy:
            self.update_status(self.controller.state)

    def change_page(self, index: int):
        self.pages.setCurrentIndex(index)
        titles = ["Hotspot", "Portal page", "Devices", "Diagnostics", "About Captivate"]
        subtitles = ["Publish a page to everyone who joins your Wi-Fi.",
                     "Choose what visitors see when they connect.",
                     "Review the devices using this hotspot session.",
                     "Check system support and inspect session activity.",
                     "An open-source captive portal utility by Uzair."]
        self.page_title.setText(titles[index])
        self.subtitle.setText(subtitles[index])

    def refresh_diagnostics(self):
        if self.worker and self.worker.isRunning():
            return
        self.refresh_button.setEnabled(False)
        self.worker = DiagnosticsWorker(self)
        self.worker.result.connect(self.apply_diagnostics)
        self.worker.finished.connect(lambda: self.refresh_button.setEnabled(not self.controller.busy))
        self.worker.start()

    def apply_diagnostics(self, report: dict):
        self.system_report = report
        selected = self.adapter.currentData() or self.config.interface
        selected_uplink = self.uplink.currentData() or self.config.uplink
        self.adapter.clear()
        self.uplink.clear()
        self.uplink.addItem("Offline — local pages only", "")
        for device in report.get("adapters", []):
            name = device["name"]
            if device["ap"]:
                self.adapter.addItem(f"{name} · {device['state']}", name)
            self.uplink.addItem(f"{name} · {device['kind']} · {device['state']}", name)
        self.adapter.setCurrentIndex(max(0, self.adapter.findData(selected)))
        self.uplink.setCurrentIndex(max(0, self.uplink.findData(selected_uplink)))
        if not self.adapter.count():
            self.adapter.addItem("No hotspot-capable adapter detected", "")
        tools = report.get("tools", {})
        missing = [name for name, path in tools.items() if not path and name != "iw"]
        self.radio_note.setText(
            "Missing system tools: " + ", ".join(missing) if missing else
            "Hotspot support detected. Starting replaces the selected adapter's current Wi-Fi connection. "
            "Enable Wi-Fi in your system settings if the adapter is unavailable."
            if self.adapter.currentData() else "No compatible Wi-Fi adapter was found. Enable Wi-Fi and refresh adapters."
        )
        lines = [report.get("system", "Unknown system"), report.get("networkmanager", "NetworkManager not detected"),
                 f"Python {report.get('python', 'unknown')}", ""]
        lines.extend(f"{name}: {path or 'not installed'}" for name, path in tools.items())
        lines.append("")
        lines.extend(f"{device['name']}: {device['kind']}, {device['state']}, AP {'yes' if device['ap'] else 'no'}" for device in report.get("adapters", []))
        self.diagnostics_text.setPlainText("\n".join(lines))
        self.update_status(self.controller.state)

    def update_status(self, state: str):
        labels = {"idle": "Stopped", "authorizing": "Starting…", "running": "Running", "stopping": "Stopping…", "failed": "Needs attention"}
        self.state_label.setText(labels.get(state, state))
        colors = {"running": ("#e0f2e9", "#236846"), "failed": ("#fff0f0", "#942e2e"),
                  "authorizing": ("#fff1d8", "#7d570e"), "stopping": ("#fff1d8", "#7d570e")}
        background, foreground = colors.get(state, ("#e0e8f2", "#24364b"))
        self.state_label.setStyleSheet(f"background: {background}; color: {foreground};")
        busy = self.controller.busy
        for box in (self.network_box, self.sharing_box, self.portal_box):
            box.setEnabled(not busy)
        self.recover_button.setEnabled(not busy)
        self.refresh_button.setEnabled(not busy and not (self.worker and self.worker.isRunning()))
        self.start_button.setText("Stop hotspot" if busy else "Start hotspot")
        self.start_button.setEnabled(state == "running" if busy else bool(self.system_report.get("ready")))
        sharing = "gated internet" if self.uplink.currentData() else "offline"
        self.stages.setText(f"Hotspot: {labels.get(state, state).lower()}     /     Portal: {'serving' if state == 'running' else 'ready to preview'}     /     Sharing: {sharing}")
        if state == "running":
            self.footer_note.setText(f"Portal address: http://{self.collect_config().address}/")
        elif state == "failed":
            self.footer_note.setText("Open Diagnostics for the error and recovery options.")
        else:
            self.footer_note.setText("Preview your page before starting the hotspot.")

    def open_preview(self):
        try:
            url = self.controller.preview_page(self.collect_config())
            if not open_browser(url):
                self.show_error(f"Unable to open a browser. Open this preview address manually: {url}")
        except (OSError, ValueError, RuntimeError) as exc:
            self.show_error(str(exc))

    def toggle_session(self):
        if self.controller.busy:
            self.controller.stop()
            return
        try:
            config = self.collect_config()
            config.validate()
            save_preferences(config)
            self.config = config
            self.controller.start(config)
        except (OSError, ValueError, RuntimeError) as exc:
            self.show_error(str(exc))

    def update_clients(self, clients: list):
        self.device_table.setRowCount(len(clients))
        for row, client in enumerate(clients):
            access = self.controller.portal and self.controller.portal.state.is_authorized(client["ip"])
            for column, value in enumerate((client["hostname"], client["ip"], client["mac"], "Confirmed" if access else "Awaiting confirmation")):
                self.device_table.setItem(row, column, QTableWidgetItem(value))
        self.device_note.setText(
            f"{len(clients)} active DHCP lease{'s' if len(clients) != 1 else ''} in this session."
            if self.controller.busy else "No hotspot session is running. Devices appear after receiving a DHCP lease."
        )

    def add_log(self, message: str):
        self.logs.appendPlainText(f"{datetime.now():%H:%M:%S}  {message}")

    def show_error(self, message: str):
        self.add_log("Error: " + message)
        QMessageBox.warning(self, "Captivate", message)

    def choose_directory(self):
        directory = QFileDialog.getExistingDirectory(self, "Choose a portal website folder")
        if directory:
            self.directory_edit.setText(directory)

    def recover_session(self):
        try:
            self.controller.recover()
        except RuntimeError as exc:
            self.show_error(str(exc))

    def export_log(self):
        filename, _ = QFileDialog.getSaveFileName(self, "Export session log", "captivate-session.log", "Log files (*.log)")
        if filename:
            try:
                Path(filename).write_text(self.logs.toPlainText() + "\n")
            except OSError as exc:
                self.show_error(str(exc))

    def session_completed(self):
        if self.close_requested:
            self.close()

    def closeEvent(self, event):
        if self.controller.busy:
            if self.close_requested or QMessageBox.question(
                self, "Stop hotspot and close?", "Closing Captivate stops the hotspot and restores the previous connection."
            ) == QMessageBox.StandardButton.Yes:
                self.close_requested = True
                self.controller.stop()
            event.ignore()
            return
        if self.worker and self.worker.isRunning():
            self.worker.wait(30000)
        self.controller.close_preview()
        try:
            save_preferences(self.collect_config())
        except OSError:
            pass
        event.accept()


def create_application() -> QApplication:
    os.environ["QT_STYLE_OVERRIDE"] = "Fusion"
    application = QApplication.instance() or QApplication([])
    application.setApplicationName("Captivate")
    application.setOrganizationName("Uzair")
    application.setDesktopFileName("dev.uzair.Captivate")
    application.setStyle("Fusion")
    font = QFont("Noto Sans", 10)
    application.setFont(font)
    palette = application.palette()
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor("#647386"))
    application.setPalette(palette)
    application.setStyleSheet(STYLESHEET + f'''
QComboBox::down-arrow {{ image: url({ASSETS / 'icons' / 'chevron-down.svg'}); width: 12px; height: 12px; }}
QSpinBox::up-button, QSpinBox::down-button {{ width: 20px; border: none; background: #edf2f8; }}
QSpinBox::up-arrow {{ image: url({ASSETS / 'icons' / 'chevron-up.svg'}); width: 10px; height: 10px; }}
QSpinBox::down-arrow {{ image: url({ASSETS / 'icons' / 'chevron-down.svg'}); width: 10px; height: 10px; }}
''')
    return application
