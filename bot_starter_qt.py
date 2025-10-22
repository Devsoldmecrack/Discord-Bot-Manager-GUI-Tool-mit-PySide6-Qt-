import sys
from PySide6.QtCore import Qt, QSize, QEvent, QProcess, QTimer, QEasingCurve, QPoint, QPropertyAnimation
from PySide6.QtGui import (
    QFont,
    QIcon,
    QPainter,
    QLinearGradient,
    QColor,
    QPainterPath,
    QPixmap,
    QTextCursor,
    QTextCharFormat,
)
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QSizePolicy,
    QPushButton,
    QListWidget,
    QFileDialog,
    QPlainTextEdit,
    QLineEdit,
    QAbstractItemView,
    QCheckBox,
    QTextEdit,
    QDialog,
    QInputDialog,
)
from PySide6.QtWidgets import QProgressBar, QGraphicsOpacityEffect


COLOR_BG = "#1A1A24"
COLOR_ACCENT = "#FFD700"
COLOR_BTN_BG = "#2A2F55"
COLOR_BTN_HOVER = "#3A3F70"
COLOR_BTN_PRESS = "#2B305C"
COLOR_FG = "white"
HELP_GRAY = "#8C8C8C"
HELP_GRAY_HOVER = "#B3B3B3"


BOT_DATA_FILE = "bot_manager_data.json"
TEMP_EXTRACT_DIR = "bot_temp"
SETTINGS_FILE = "settings.json"
ICON_CANDIDATES = [
    "app_icon.ico",
    "app.ico",
    "icon.ico",
    "app_icon.png",
    "icon.png",
]

import os
import json
import shutil
import sys as _sys
import dotenv as _dotenv
import hashlib
import base64
import secrets
import socket
import threading
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlencode, urlparse, parse_qs
try:
    import requests
except Exception:
    requests = None
try:
    import winreg as _winreg
except Exception:
    _winreg = None
try:
    import psutil as _psutil
except Exception:
    _psutil = None
try:
    import GPUtil as _gputil
except Exception:
    _gputil = None


def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "auto_restart": False,
        "auto_start_app": False,
        "auto_start_bots": False,
        "notifications": True,
        "cleanup_temp_on_close": False,
        "env_vars": {},
        "start_with_windows": False,
    }


def save_settings(settings: dict):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=4)


SETTINGS = load_settings()

def load_app_icon() -> QIcon | None:
    for name in ICON_CANDIDATES:
        p = os.path.join(os.path.dirname(__file__), name)
        if os.path.exists(p):
            return QIcon(p)
    return None

def _generate_icon_pixmap(size: int = 512) -> QPixmap:
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)

    
    rect = pm.rect().adjusted(8, 8, -8, -8)
    grad = QLinearGradient(rect.topLeft(), rect.bottomRight())
    grad.setColorAt(0.0, QColor("#2A2F55"))
    grad.setColorAt(1.0, QColor("#3A3F70"))
    path_bg = QPainterPath()
    path_bg.addRoundedRect(rect, rect.width() * 0.12, rect.width() * 0.12)
    p.fillPath(path_bg, grad)

    
    inner = rect.adjusted(int(rect.width()*0.14), int(rect.height()*0.18), int(-rect.width()*0.14), int(-rect.height()*0.26))
    path_inner = QPainterPath()
    radius = inner.height() * 0.18
    path_inner.addRoundedRect(inner, radius, radius)
    p.fillPath(path_inner, QColor(255, 255, 255, 18))

    
    tail_w = inner.width() * 0.18
    tail_h = inner.height() * 0.22
    tail = QPainterPath()
    tail.moveTo(inner.left() + inner.width()*0.18, inner.bottom())
    tail.lineTo(tail.currentPosition().x() + tail_w*0.6, inner.bottom() + tail_h)
    tail.lineTo(tail.currentPosition().x() + tail_w*0.6, inner.bottom() - tail_h*0.2)
    tail.closeSubpath()
    p.fillPath(tail, QColor(255, 255, 255, 18))

    
    bolt = QPainterPath()
    cx = rect.center().x()
    cy = rect.center().y()
    s = rect.width() * 0.22
    bolt.moveTo(cx - s*0.2, cy - s*0.8)
    bolt.lineTo(cx + s*0.15, cy - s*0.15)
    bolt.lineTo(cx - s*0.05, cy - s*0.15)
    bolt.lineTo(cx + s*0.2, cy + s*0.8)
    bolt.lineTo(cx - s*0.15, cy + s*0.1)
    bolt.lineTo(cx + s*0.05, cy + s*0.1)
    bolt.closeSubpath()
    p.fillPath(bolt, QColor("#FFD700"))

    
    pen = QColor(255, 255, 255, 28)
    p.setPen(pen)
    p.drawPath(path_bg)
    p.end()
    return pm

def ensure_generated_icon_files() -> QIcon:
    base_dir = os.path.dirname(__file__)
    pm = _generate_icon_pixmap(512)
    png_path = os.path.join(base_dir, "app_icon.png")
    ico_path = os.path.join(base_dir, "app_icon.ico")
    pm.save(png_path, "PNG")
    
    try:
        pm.save(ico_path, "ICO")
    except Exception:
        pass
    return QIcon(png_path if os.path.exists(png_path) else ico_path)

def add_to_registry_autostart():
    if os.name != "nt" or _winreg is None:
        return
    if not SETTINGS.get("start_with_windows", False):
        return
    exe_path = os.path.abspath(_sys.argv[0])
    try:
        key = _winreg.OpenKey(
            _winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            _winreg.KEY_SET_VALUE,
        )
        _winreg.SetValueEx(key, "DiscordBotManagerQt", 0, _winreg.REG_SZ, exe_path)
        _winreg.CloseKey(key)
    except Exception:
        pass


class PillButton(QPushButton):
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.setMinimumSize(120, 36)

        
        self._bg = COLOR_BTN_BG
        self._hover = COLOR_BTN_HOVER
        self._press = COLOR_BTN_PRESS
        self._fg = COLOR_FG

        
        self._apply_style(self._bg)

    def sizeHint(self) -> QSize:
        sh = super().sizeHint()
        return QSize(max(sh.width() + 16, 120), max(sh.height() + 8, 36))

    def enterEvent(self, e):
        super().enterEvent(e)
        self._apply_style(self._hover)

    def leaveEvent(self, e):
        super().leaveEvent(e)
        self._apply_style(self._bg)

    def mousePressEvent(self, e):
        super().mousePressEvent(e)
        if e.button() == Qt.LeftButton:
            self._apply_style(self._press)

    def mouseReleaseEvent(self, e):
        super().mouseReleaseEvent(e)
        
        if self.rect().contains(e.position().toPoint()):
            
            self._apply_style(self._hover)
        else:
            self._apply_style(self._bg)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        
        current_color = self.palette().color(self.backgroundRole()).name() if self.backgroundRole() else self._bg
        
        if self.underMouse():
            current_color = self._hover
        else:
            current_color = self._bg
        self._apply_style(current_color)

    def _apply_style(self, bg_color: str):
        radius = max(1, int(self.height() / 2))
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg_color};
                color: {self._fg};
                border: 1px solid {COLOR_BTN_HOVER if bg_color != self._bg else self._bg};
                border-radius: {radius}px;
                padding: 6px 14px;
            }}
            QPushButton:disabled {{
                background-color: #30334f;
                color: #bbbbbb;
                border-color: #30334f;
            }}
        """)


class BotListWidget(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QAbstractItemView.DropOnly)
        self.setDefaultDropAction(Qt.CopyAction)
        self.setStyleSheet(
            f"background-color: {COLOR_BTN_BG}; color: white; border: none;"
        )

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.setDropAction(Qt.CopyAction)
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.setDropAction(Qt.CopyAction)
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            paths = []
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    p = url.toLocalFile()
                else:
                    
                    p = url.toString().replace('file:///', '').replace('file://', '')
                if p:
                    paths.append(p)
            self.parent().handle_drop_paths(paths)
            event.setDropAction(Qt.CopyAction)
            event.acceptProposedAction()
        else:
            super().dropEvent(event)


class BotManagerWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Bot Manager – py-cord + dotenv (Qt)")
        self.setMinimumSize(900, 850)
        self.setStyleSheet(
            f"""
            QWidget {{
                background-color: {COLOR_BG};
                color: {COLOR_FG};
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 1px solid #50579E;
                background: transparent;
                margin-right: 6px;
            }}
            QCheckBox::indicator:hover {{
                border-color: #6b73c6;
            }}
            QCheckBox::indicator:checked {{
                background: {COLOR_BTN_HOVER};
                border-color: {COLOR_BTN_HOVER};
            }}
            QCheckBox::indicator:disabled {{
                background: transparent;
                border-color: #2c2f4a;
            }}
            """
        )

        self.bot_files = self._load_bots()
        self.process: QProcess | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        # Top controls
        top = QHBoxLayout()
        for text, handler in [
            ("➕ Add", self.add_bot_file),
            ("❌ Remove", self.remove_bot_file),
            ("💾 Save", self.save_bots),
            ("📦 Install requirements", self.install_requirements),
        ]:
            btn = PillButton(text)
            btn.clicked.connect(handler)
            top.addWidget(btn)
        top.addStretch(1)
        root.addLayout(top)

        
        self.list_widget = BotListWidget(self)
        self.list_widget.itemSelectionChanged.connect(self.on_select)
        root.addWidget(self.list_widget)
        self.refresh_list()

        
        info = QHBoxLayout()
        self.token_label = QLabel("Token: —")
        info.addWidget(self.token_label)
        reload_btn = PillButton("🔁 Load token from .env")
        reload_btn.clicked.connect(self.load_token_preview)
        info.addStretch(1)
        info.addWidget(reload_btn)
        root.addLayout(info)

    
        self.console = QPlainTextEdit()
        self.console.setReadOnly(True)
        self.console.setStyleSheet(f"background-color: #111119; color: {COLOR_ACCENT};")
        self.console.setMaximumBlockCount(5000)
        root.addWidget(self.console, stretch=1)

        
        self.error_banner = QLabel("")
        self.error_banner.setVisible(False)
        self.error_banner.setWordWrap(True)
        self.error_banner.setStyleSheet(
            "background-color: #3a1b1e; color: #ffb3b3; "
            "border: 1px solid #7a2b32; border-radius: 8px; padding: 8px;"
        )
        root.addWidget(self.error_banner)

        
        self.command_entry = QLineEdit()
        self.command_entry.setPlaceholderText("Enter a PowerShell command and press Enter…")
        self.command_entry.returnPressed.connect(self.run_powershell_command)
        self.command_entry.setStyleSheet(f"background-color: {COLOR_BTN_BG}; color: white; border: none; padding: 6px;")
        root.addWidget(self.command_entry)

        
        ctrl = QHBoxLayout()
        for text, handler in [
            ("▶️ Start bot", self.start_bot),
            ("⏹ Stop bot", self.stop_bot),
            ("🧹 Clean temp", self.cleanup_temp),
        ]:
            b = PillButton(text)
            b.clicked.connect(handler)
            ctrl.addWidget(b)
        ctrl.addStretch(1)
        root.addLayout(ctrl)

        status = QHBoxLayout()
        self.lbl_net = QLabel("Net: —")
        self.lbl_cpu = QLabel("CPU: —")
        self.lbl_ram = QLabel("RAM: —")
        self.lbl_gpu = QLabel("GPU: —")
        self.lbl_bot = QLabel("Bot: —")
        for w in [self.lbl_net, self.lbl_cpu, self.lbl_ram, self.lbl_gpu, self.lbl_bot]:
            status.addWidget(w)
            status.addSpacing(12)
        status.addStretch(1)
        root.addLayout(status)

        self._ps_proc = None
        self.status_timer = QTimer(self)
        self.status_timer.setInterval(1500)
        self.status_timer.timeout.connect(self.update_status)
        self.status_timer.start()
    
    
    def append_console(self, text: str):
        self.console.appendPlainText(text)
        self.console.ensureCursorVisible()

    def append_console_error(self, text: str):
        cursor = self.console.textCursor()
        cursor.movePosition(QTextCursor.End)
        fmt = QTextCharFormat()
        fmt.setForeground(QColor("#ff5555"))
        cursor.setCharFormat(fmt)
        cursor.insertText(text + "\n")
        
        fmt.setForeground(QColor(COLOR_ACCENT))
        cursor.setCharFormat(fmt)
        self.console.setTextCursor(cursor)
        self.console.ensureCursorVisible()

    def _show_error_banner(self, message: str):
        self.error_banner.setText("⚠ " + message)
        self.error_banner.setVisible(True)
        
    def _clear_error_banner(self):
        self.error_banner.clear()
        self.error_banner.setVisible(False)

    def selected_path(self) -> str | None:
        items = self.list_widget.selectedItems()
        return items[0].text() if items else None

    def _load_bots(self):
        if os.path.exists(BOT_DATA_FILE):
            try:
                with open(BOT_DATA_FILE, "r", encoding="utf-8") as f:
                    return json.load(f).get("bot_files", [])
            except Exception:
                pass
        return []

    def refresh_list(self):
        self.list_widget.clear()
        for p in self.bot_files:
            mark = "⚠️ " if not os.path.exists(p) else ""
            self.list_widget.addItem(f"{mark}{p}")

    def handle_drop_paths(self, paths: list[str]):
        for p in paths:
            if p not in self.bot_files:
                self.bot_files.append(p)
        self.refresh_list()

    
    def add_bot_file(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Bot-Dateien oder Ordner wählen")
        for p in files:
            if p not in self.bot_files:
                self.bot_files.append(p)
        self.refresh_list()

    def remove_bot_file(self):
        items = self.list_widget.selectedItems()
        if not items:
            return
        idx = self.list_widget.row(items[0])
        del self.bot_files[idx]
        self.refresh_list()

    def save_bots(self):
        try:
            with open(BOT_DATA_FILE, "w", encoding="utf-8") as f:
                json.dump({"bot_files": self.bot_files}, f, indent=4)
            QMessageBox.information(self, "Saved", "Bot list saved.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not save:\n{e}")

    def on_select(self):
        self.load_token_preview()

    def load_token_preview(self):
        sel = self.selected_path()
        if not sel:
            self.token_label.setText("Token: —")
            return
        path = sel.replace("⚠️ ", "")
        folder = path if os.path.isdir(path) else os.path.dirname(path)
        dotenv_path = os.path.join(folder, ".env")
        if os.path.exists(dotenv_path):
            try:
                vals = _dotenv.dotenv_values(dotenv_path)
                token = vals.get("DISCORD_TOKEN") or vals.get("TOKEN")
                if token:
                    masked = token[:4] + "●" * max(0, len(token) - 8) + token[-4:]
                    self.token_label.setText("Token: " + masked)
                    return
            except Exception:
                pass
        enc = SETTINGS.get("encrypted_tokens", {}).get(folder)
        if enc:
            self.token_label.setText("Token: (verschlüsselt)")
        else:
            self.token_label.setText("Token: .env nicht gefunden")

    def save_token(self):
        sel = self.selected_path()
        if not sel:
            QMessageBox.warning(self, "Warning", "Please select a bot project.")
            return
        path = sel.replace("⚠️ ", "")
        folder = path if os.path.isdir(path) else os.path.dirname(path)
        dotenv_path = os.path.join(folder, ".env")
        token = self.token_input.text()
        if not token:
            QMessageBox.warning(self, "Warning", "Please enter a token.")
            return
        try:
            with open(dotenv_path, "w", encoding="utf-8") as f:
                f.write(f"DISCORD_TOKEN={token}")
            QMessageBox.information(self, "Saved", "Token saved.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not save token:\n{e}")

    def _python_executable(self) -> str:
        if getattr(_sys, "frozen", False):
            py = shutil.which("python") or shutil.which("python3")
            if not py:
                raise RuntimeError("Python nicht gefunden. Bots können nicht gestartet werden.")
            return py
        return _sys.executable

    
    def start_bot(self):
        sel = self.selected_path()
        if not sel:
            QMessageBox.warning(self, "Warning", "Please select a bot project.")
            return
        path = sel.replace("⚠️ ", "")
        folder = path if os.path.isdir(path) else os.path.dirname(path)
        try:
            py_files = [f for f in os.listdir(folder) if f.endswith('.py')]
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not read folder:\n{e}")
            return
        if not py_files:
            QMessageBox.critical(self, "Error", "No Python (.py) file found in the folder!")
            return
        main_py = os.path.join(folder, py_files[0])

        
        self.stop_bot()
        self._clear_error_banner()

        self.append_console(f"▶️ Starting bot: {os.path.basename(main_py)}")
        self.process = QProcess(self)
        self.process.setProgram(self._python_executable())
        self.process.setArguments([main_py])
        self.process.setWorkingDirectory(folder)
        self.process.setProcessChannelMode(QProcess.SeparateChannels)
        self.process.readyReadStandardOutput.connect(self._read_output)
        self.process.readyReadStandardError.connect(self._read_error)
        self.process.finished.connect(self._on_bot_finished)
        self.process.errorOccurred.connect(self._on_bot_error)
        self.process.start()

    def _read_output(self):
        if not self.process:
            return
        data = self.process.readAllStandardOutput()
        try:
            text = bytes(data).decode(errors='ignore')
        except Exception:
            text = str(data)
        for line in text.splitlines():
            if line.strip():
                self.append_console(line)

    def _on_bot_finished(self, code, status):
        self.append_console(f"⏹ Bot exited (code {code}).")
        if code not in (0, None):
            self._show_error_banner(f"Bot crashed or exited with code {code}. Check errors above.")
        self.process = None

    def _on_bot_error(self, err):
        msg = f"✖ Bot process error: {err}"
        self.append_console_error(msg)
        self._show_error_banner(msg)

    def _read_error(self):
        data = self.process.readAllStandardError()
        try:
            text = bytes(data).decode(errors='ignore')
        except Exception:
            text = str(data)
        for line in text.splitlines():
            if line.strip():
                self.append_console_error(line)
        
        lines = [l for l in text.splitlines() if l.strip()]
        if lines:
            self._show_error_banner(lines[-1])


    def stop_bot(self):
        if self.process and self.process.state() != QProcess.NotRunning:
            self.process.terminate()
            self.append_console("⏹ Bot stopped.")
            self.process = None

    def cleanup_temp(self):
        try:
            if os.path.exists(TEMP_EXTRACT_DIR):
                shutil.rmtree(TEMP_EXTRACT_DIR, ignore_errors=True)
                QMessageBox.information(self, "Cleaned", "Temp folder deleted.")
                self.append_console("🧹 Temp folder deleted.")
            else:
                QMessageBox.information(self, "Info", "No temp folder present.")
                self.append_console("ℹ️ No temp folder present.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not delete temp folder:\n{e}")
            self.append_console(f"Error while deleting temp folder: {e}")

    def install_requirements(self):
        sel = self.selected_path()
        if not sel:
            QMessageBox.warning(self, "Fehler", "Bitte wähle ein Bot-Projekt aus.")
            return
        folder = sel.replace("⚠️ ", "")
        if not os.path.isdir(folder):
            folder = os.path.dirname(folder)
        req_path = os.path.join(folder, "requirements.txt")
        if not os.path.exists(req_path):
            QMessageBox.information(self, "Info", "No requirements.txt found.")
            return

        self.append_console("📦 Installing requirements...")
        proc = QProcess(self)
        proc.setProgram(self._python_executable())
        proc.setArguments(["-m", "pip", "install", "-r", req_path])
        proc.setProcessChannelMode(QProcess.MergedChannels)
        proc.readyReadStandardOutput.connect(lambda: self.append_console(bytes(proc.readAllStandardOutput()).decode(errors='ignore')))
        proc.finished.connect(lambda c, s: QMessageBox.information(self, "Done", "Installed requirements.txt.") if c == 0 else QMessageBox.critical(self, "Error", "Installation failed."))
        proc.start()

    
    def run_powershell_command(self):
        cmd = self.command_entry.text().strip()
        if not cmd:
            return

        self.append_console(f"> {cmd}")
        self.command_entry.clear()

       
        self.ps_proc = QProcess(self)
        if os.name == 'nt':
            self.ps_proc.setProgram("powershell")
            self.ps_proc.setArguments(["-Command", cmd])
        else:
            self.ps_proc.setProgram("bash")
            self.ps_proc.setArguments(["-lc", cmd])
        self.ps_proc.setProcessChannelMode(QProcess.MergedChannels)
        self.ps_proc.readyReadStandardOutput.connect(lambda: self.append_console(bytes(self.ps_proc.readAllStandardOutput()).decode(errors='ignore')))
        self.ps_proc.finished.connect(lambda c, s: self.append_console(f"✔ Command finished (code {c})."))
        self.ps_proc.start()

    def _fmt_bytes(self, n: float) -> str:
        units = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        while n >= 1024 and i < len(units) - 1:
            n /= 1024.0
            i += 1
        return f"{n:.1f} {units[i]}"

    def _internet_ok(self) -> bool:
        try:
            socket.create_connection(("1.1.1.1", 53), timeout=1).close()
            return True
        except Exception:
            return False

    def update_status(self):
        net = "OK" if self._internet_ok() else "Offline"
        self.lbl_net.setText(f"Net: {net}")

        if _psutil is not None:
            try:
                cpu = _psutil.cpu_percent(interval=None)
                vm = _psutil.virtual_memory()
                self.lbl_cpu.setText(f"CPU: {cpu:.0f}%")
                self.lbl_ram.setText(f"RAM: {vm.percent:.0f}% ({self._fmt_bytes(vm.used)}/{self._fmt_bytes(vm.total)})")
            except Exception:
                self.lbl_cpu.setText("CPU: —")
                self.lbl_ram.setText("RAM: —")
        else:
            self.lbl_cpu.setText("CPU: —")
            self.lbl_ram.setText("RAM: —")

        if _gputil is not None:
            try:
                gpus = _gputil.getGPUs()
                if gpus:
                    g = gpus[0]
                    self.lbl_gpu.setText(f"GPU: {g.load*100:.0f}% ({int(g.memoryUsed)}MB/{int(g.memoryTotal)}MB)")
                else:
                    self.lbl_gpu.setText("GPU: —")
            except Exception:
                self.lbl_gpu.setText("GPU: —")
        else:
            self.lbl_gpu.setText("GPU: —")

        if _psutil is not None and self.process and self.process.state() != QProcess.NotRunning:
            try:
                pid = int(self.process.processId())
                if pid and (self._ps_proc is None or self._ps_proc.pid != pid):
                    self._ps_proc = _psutil.Process(pid)
                    try:
                        self._ps_proc.cpu_percent(interval=None)
                    except Exception:
                        pass
                if self._ps_proc is not None:
                    p_cpu = self._ps_proc.cpu_percent(interval=None)
                    p_mem = self._ps_proc.memory_info().rss
                    self.lbl_bot.setText(f"Bot: {p_cpu:.0f}% CPU, {self._fmt_bytes(p_mem)} RAM")
                else:
                    self.lbl_bot.setText("Bot: —")
            except Exception:
                self.lbl_bot.setText("Bot: —")
        else:
            self.lbl_bot.setText("Bot: —")

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Discord Bot Manager (Beta)")
        self.setMinimumSize(800, 650)
        self.setStyleSheet(
            f"""
            QWidget {{
                background-color: {COLOR_BG};
                color: {COLOR_FG};
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 1px solid #50579E;
                background: transparent;
                margin-right: 6px;
            }}
            QCheckBox::indicator:hover {{
                border-color: #6b73c6;
            }}
            QCheckBox::indicator:checked {{
                background: {COLOR_BTN_HOVER};
                border-color: {COLOR_BTN_HOVER};
            }}
            QCheckBox::indicator:disabled {{
                background: transparent;
                border-color: #2c2f4a;
            }}
            """
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        title = QLabel("Discord Bot Manager")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignHCenter)
        layout.addWidget(title)

        btn_open = PillButton("🤖 Open Bot Manager")
        btn_open.clicked.connect(self.open_bot_manager)
        btn_open.setFixedWidth(260)
        layout.addWidget(btn_open, alignment=Qt.AlignHCenter)

        btn_settings = PillButton("⚙️ Settings")
        btn_settings.clicked.connect(self.open_settings)
        btn_settings.setFixedWidth(260)
        layout.addWidget(btn_settings, alignment=Qt.AlignHCenter)

        
        layout.addStretch(1)
        layout.addSpacing(8)

        
        footer2 = QLabel("Discord: devsoldmecrack")
        footer2.setStyleSheet("color: gray;")
        layout.addWidget(footer2, alignment=Qt.AlignHCenter)
        layout.addSpacing(10)

        
        bottom_bar = QHBoxLayout()
        bottom_bar.setContentsMargins(0, 0, 0, 0)
        bottom_bar.setSpacing(0)

        help = QLabel("❓")
        help.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        help.setStyleSheet(f"color: {HELP_GRAY};")
        help.setAlignment(Qt.AlignLeft)
        help.setToolTip("Help")
        self._help_label = help
        help.installEventFilter(self)

        footer1 = QLabel("© Devsoldmecrack Inc. – All rights reserved.")
        footer1.setStyleSheet("color: gray;")

        bottom_bar.addWidget(help, 0, Qt.AlignLeft | Qt.AlignVCenter)
        bottom_bar.addStretch(1)
        bottom_bar.addWidget(footer1, 0, Qt.AlignRight | Qt.AlignVCenter)
        layout.addLayout(bottom_bar)


    def eventFilter(self, obj, event):
        if getattr(self, "_help_label", None) is obj:
            et = event.type()
            if et == QEvent.Enter:
                self._help_label.setStyleSheet(f"color: {HELP_GRAY_HOVER};")
            elif et == QEvent.Leave:
                self._help_label.setStyleSheet(f"color: {HELP_GRAY};")
            elif et == QEvent.MouseButtonRelease:
                QMessageBox.information(
                    self,
                    "Help",
                    "Drag & drop: Add bot folders or files here.\n"
                    "Start/Stop: Start or stop your bot.\n"
                    "Settings: Configure environment variables and auto-start.",
                )
        return super().eventFilter(obj, event)

    def open_bot_manager(self):
        self._bot_window = BotManagerWindow()
        self._bot_window.show()

    def open_settings(self):
        dlg = SettingsWindow(self)
        dlg.setWindowModality(Qt.ApplicationModal)
        dlg.exec()


class SettingsWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumSize(520, 520)
        self.setStyleSheet(
            f"""
            QWidget {{
                background-color: {COLOR_BG};
                color: {COLOR_FG};
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 1px solid #50579E;
                background: transparent;
                margin-right: 6px;
            }}
            QCheckBox::indicator:hover {{
                border-color: #6b73c6;
            }}
            QCheckBox::indicator:checked {{
                background: {COLOR_BTN_HOVER};
                border-color: {COLOR_BTN_HOVER};
            }}
            QCheckBox::indicator:disabled {{
                background: transparent;
                border-color: #2c2f4a;
            }}
            """
        )

        v = QVBoxLayout(self)
        v.setContentsMargins(16, 16, 16, 16)
        v.setSpacing(10)

        title = QLabel("Settings")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        v.addWidget(title)

        
        self.chk_auto_start_app = QCheckBox("Automatically start Bot Manager")
        self.chk_auto_start_bots = QCheckBox("Auto-open first bot on launch")
        self.chk_notifications = QCheckBox("Notifications on crash/connectivity loss")
        self.chk_cleanup = QCheckBox("Delete temp folder on close")
        self.chk_start_with_windows = QCheckBox("Start with Windows")
        self.chk_auto_restart = QCheckBox("Auto-restart bots on crash")

        for cb, key in [
            (self.chk_auto_start_app, "auto_start_app"),
            (self.chk_auto_start_bots, "auto_start_bots"),
            (self.chk_notifications, "notifications"),
            (self.chk_cleanup, "cleanup_temp_on_close"),
            (self.chk_start_with_windows, "start_with_windows"),
            (self.chk_auto_restart, "auto_restart"),
        ]:
            cb.setChecked(SETTINGS.get(key, False))
            v.addWidget(cb)

        
        v.addWidget(QLabel("Environment variables (global, optional):"))
        self.env_edit = QTextEdit()
        self.env_edit.setStyleSheet(f"background-color: {COLOR_BTN_BG}; color: white;")
        env_text = "\n".join(f"{k}={v}" for k, v in SETTINGS.get("env_vars", {}).items())
        self.env_edit.setPlainText(env_text)
        self.env_edit.setFixedHeight(160)
        v.addWidget(self.env_edit)

        # Token updater for .env
        v.addWidget(QLabel(".env token update (only token line is changed):"))
        # Select from saved bots
        bot_sel_row = QHBoxLayout()
        self.env_bot_combo = QListWidget()
        self.env_bot_combo.setFixedHeight(100)
        self._populate_env_bot_combo()
        bot_sel_row.addWidget(self.env_bot_combo)
        v.addLayout(bot_sel_row)

        token_row1 = QHBoxLayout()
        self.env_path_edit = QLineEdit()
        self.env_path_edit.setPlaceholderText("Path to .env or bot folder")
        btn_browse_env = PillButton("📂 Browse")
        btn_browse_env.clicked.connect(self._browse_env_path)
        token_row1.addWidget(self.env_path_edit)
        token_row1.addWidget(btn_browse_env)
        v.addLayout(token_row1)

        token_row2 = QHBoxLayout()
        self.env_token_edit = QLineEdit()
        self.env_token_edit.setPlaceholderText("New token (DISCORD_TOKEN)")
        self.env_token_edit.setEchoMode(QLineEdit.Password)
        btn_save_token = PillButton("💾 Save token")
        btn_save_token.clicked.connect(self.save_env_token)
        token_row2.addWidget(self.env_token_edit)
        token_row2.addWidget(btn_save_token)
        v.addLayout(token_row2)

        
        save_btn = PillButton("💾 Save")
        save_btn.clicked.connect(self.save_settings)
        v.addWidget(save_btn)

    def showEvent(self, event):
        super().showEvent(event)
        
        parent = self.parent()
        if parent is not None:
            geo = self.frameGeometry()
            geo.moveCenter(parent.frameGeometry().center())
            self.move(geo.topLeft())

    def save_settings(self):
        SETTINGS["auto_start_app"] = self.chk_auto_start_app.isChecked()
        SETTINGS["auto_start_bots"] = self.chk_auto_start_bots.isChecked()
        SETTINGS["notifications"] = self.chk_notifications.isChecked()
        SETTINGS["cleanup_temp_on_close"] = self.chk_cleanup.isChecked()
        SETTINGS["start_with_windows"] = self.chk_start_with_windows.isChecked()
        SETTINGS["auto_restart"] = self.chk_auto_restart.isChecked()

        env_dict = {}
        for line in self.env_edit.toPlainText().splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                env_dict[k.strip()] = v.strip()
        SETTINGS["env_vars"] = env_dict

        save_settings(SETTINGS)
        add_to_registry_autostart()
        QMessageBox.information(self, "Saved", "Settings updated.")

    def _browse_env_path(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select .env", filter="Env files (*.env);;All files (*.*)")
        if not path:
            
            folder = QFileDialog.getExistingDirectory(self, "Select bot folder")
            if folder:
                path = folder
        if path:
            self.env_path_edit.setText(path)

    def _populate_env_bot_combo(self):
        self.env_bot_combo.clear()
        paths = []
        try:
            if os.path.exists(BOT_DATA_FILE):
                with open(BOT_DATA_FILE, "r", encoding="utf-8") as f:
                    paths = json.load(f).get("bot_files", [])
        except Exception:
            paths = []
        for p in paths:
            self.env_bot_combo.addItem(p)
        
        self.env_bot_combo.itemSelectionChanged.connect(self._on_env_bot_select)

    def _on_env_bot_select(self):
        items = self.env_bot_combo.selectedItems()
        if not items:
            return
        path = items[0].text()
        target = path if os.path.isdir(path) else os.path.join(os.path.dirname(path), ".env")
        
        if os.path.isdir(path):
            self.env_path_edit.setText(path)
        else:
            self.env_path_edit.setText(target)

    def save_env_token(self):
        path = (self.env_path_edit.text() or "").strip()
        token = (self.env_token_edit.text() or "").strip()
        if not path or not token:
            QMessageBox.warning(self, "Notice", "Please provide path and new token.")
            return
        
        env_path = path
        if os.path.isdir(env_path):
            env_path = os.path.join(env_path, ".env")
        
        lines = []
        if os.path.exists(env_path):
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    lines = f.read().splitlines()
            except Exception as e:
                QMessageBox.critical(self, "Fehler", f".env konnte nicht gelesen werden:\n{e}")
                return
        
        updated = False
        for i, line in enumerate(lines):
            if line.startswith("DISCORD_TOKEN="):
                lines[i] = f"DISCORD_TOKEN={token}"
                updated = True
                break
            if line.startswith("TOKEN="):
                lines[i] = f"TOKEN={token}"
                updated = True
                break
        if not updated:
            lines.append(f"DISCORD_TOKEN={token}")
        
        try:
            with open(env_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")
            QMessageBox.information(self, "Gespeichert", f"Token in {env_path} aktualisiert.")
        except Exception as e:
            QMessageBox.critical(self, "Fehler", f".env konnte nicht geschrieben werden:\n{e}")


def main():
    app = QApplication(sys.argv)
    
    if os.name == "nt":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("DamonInc.DiscordBotManagerQt")
        except Exception:
            pass

    
    icon = load_app_icon()
    if icon is not None:
        app.setWindowIcon(icon)
    else:
        try:
            gen_icon = ensure_generated_icon_files()
            app.setWindowIcon(gen_icon)
        except Exception:
            pass

    class AnimatedSplash(QWidget):
        def __init__(self):
            super().__init__(None, Qt.FramelessWindowHint | Qt.SplashScreen)
            self.setAttribute(Qt.WA_TranslucentBackground)
            if app.windowIcon().isNull() is False:
                self.setWindowIcon(app.windowIcon())

            
            card = QWidget(self)
            card.setObjectName("card")
            card.setStyleSheet(
                f"""
                QWidget#card {{
                    background-color: {COLOR_BG};
                    border-radius: 16px;
                }}
                QProgressBar {{
                    background: #222641;
                    border: 1px solid #3d4170;
                    border-radius: 8px;
                    color: white;
                }}
                QProgressBar::chunk {{
                    background-color: {COLOR_BTN_HOVER};
                    border-radius: 8px;
                }}
                """
            )

            v = QVBoxLayout(card)
            v.setContentsMargins(24, 24, 24, 24)
            v.setSpacing(12)

            title = QLabel("Discord Bot Manager")
            title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
            title.setStyleSheet("color: white;")
            title.setAlignment(Qt.AlignHCenter)
            v.addWidget(title)

            subtitle = QLabel("Loading…")
            subtitle.setStyleSheet("color: #bfc3ff;")
            subtitle.setAlignment(Qt.AlignHCenter)
            v.addWidget(subtitle)

            bar = QProgressBar()
            bar.setRange(0, 0)  
            bar.setFixedHeight(12)
            bar.setTextVisible(False)
            v.addWidget(bar)

            lay = QVBoxLayout(self)
            lay.setContentsMargins(0, 0, 0, 0)
            lay.addWidget(card)

            self.setFixedSize(420, 200)
            
            screen_geo = QApplication.primaryScreen().availableGeometry()
            self.move(screen_geo.center() - QPoint(self.width()//2, self.height()//2))

            
            self._eff = QGraphicsOpacityEffect(self)
            self._eff.setOpacity(0.0)
            self.setGraphicsEffect(self._eff)

        def run_then(self, callback):
            self.show()

            fade_in = self._animate_opacity(0.0, 1.0, 350)

            def after_in():
                QTimer.singleShot(1200, start_out)

            def start_out():
                fade_out = self._animate_opacity(1.0, 0.0, 350)
                fade_out.finished.connect(lambda: (self.close(), callback()))

            fade_in.finished.connect(after_in)

        def _animate_opacity(self, start, end, ms):
            anim = self._eff.animation if hasattr(self._eff, 'animation') else None
            if anim:
                anim.stop()
            anim = self._eff.animation = QPropertyAnimation(self._eff, b"opacity", self)
            anim.setStartValue(start)
            anim.setEndValue(end)
            anim.setDuration(ms)
            anim.setEasingCurve(QEasingCurve.InOutQuad)
            anim.start()
            return anim

    
    class LoginDialog(QDialog):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.setWindowTitle("Discord Login")
            self.setModal(True)
            
            self.setMinimumSize(420, 200)
            
            if os.name == "nt":
                self.setWindowFlag(Qt.MSWindowsFixedSizeDialogHint, True)
            lay = QVBoxLayout(self)
            title = QLabel("Sign in with Discord")
            title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
            lay.addWidget(title)

            self.banner = QLabel("")
            self.banner.setVisible(False)
            self.banner.setStyleSheet("background:#3a1b1e; color:#ffb3b3; border:1px solid #7a2b32; border-radius:8px; padding:8px;")
            lay.addWidget(self.banner)

            self.info = QLabel("Your default browser will open. After logging in, you'll return automatically.")
            self.info.setWordWrap(True)
            lay.addWidget(self.info)

            btn = PillButton("Sign in with Discord")
            btn.clicked.connect(self.start_login)
            lay.addWidget(btn)

            self._server = None
            self._server_thread = None
            self._port = 53135
            self._token = None
            self._code = None
            self._code_verifier = None
            
            self.adjustSize()

        def _show_error(self, msg: str):
            self.banner.setText("⚠ " + msg)
            self.banner.setVisible(True)
            
            eff = QGraphicsOpacityEffect(self.banner)
            self.banner.setGraphicsEffect(eff)

        def _start_http(self):
            class Handler(BaseHTTPRequestHandler):
                outer = self
                def log_message(self, format, *args):
                    return
                def do_GET(self):
                    if self.path.startswith("/callback"):
                        
                        q = urlparse(self.path).query
                        params = parse_qs(q)
                        code_vals = params.get('code')
                        outer = self.__class__.outer
                        if code_vals and code_vals[0]:
                            outer._code = code_vals[0]
                            msg = "<html><body>Login processed. You can close this window.</body></html>"
                            self.send_response(200)
                            self.send_header('Content-Type','text/html')
                            self.end_headers()
                            self.wfile.write(msg.encode('utf-8'))
                        else:
                            self.send_response(400); self.end_headers()
                    else:
                        self.send_response(404); self.end_headers()
                def do_POST(self):
                    self.send_response(404); self.end_headers()

            
            for p in (53135, 53136):
                try:
                    srv = HTTPServer(('127.0.0.1', p), Handler)
                    self._port = p
                    self._server = srv
                    break
                except Exception:
                    continue
            if not self._server:
                self._show_error("Local port is busy. Please try again later.")
                return False
            th = threading.Thread(target=self._server.serve_forever, daemon=True)
            th.start()
            self._server_thread = th
            return True

        def start_login(self):
            if requests is None:
                self._show_error("Python package 'requests' is missing. Please run: pip install requests")
                return
            if not self._start_http():
                return
            client_id = "1429597807161114624"
            redirect = f"http://127.0.0.1:{self._port}/callback"
            scope = "identify"
            
            import os as _os, base64 as _b64, hashlib as _hh
            raw = _b64.urlsafe_b64encode(_os.urandom(40)).decode('ascii').rstrip('=')
            self._code_verifier = raw[:128]
            digest = _hh.sha256(self._code_verifier.encode('ascii')).digest()
            code_challenge = _b64.urlsafe_b64encode(digest).decode('ascii').rstrip('=')
            qs = urlencode({
                "client_id": client_id,
                "redirect_uri": redirect,
                "response_type": "code",
                "scope": scope,
                "prompt": "consent",
                "code_challenge": code_challenge,
                "code_challenge_method": "S256",
            })
            auth_url = f"https://discord.com/oauth2/authorize?{qs}"
            try:
                webbrowser.open(auth_url)
            except Exception:
                self._show_error("Could not open the browser. Open this URL manually: " + auth_url)
                return
            
            if not hasattr(self, "_auth_link"):
                self._auth_link = QLabel()
                self._auth_link.setTextFormat(Qt.RichText)
                self._auth_link.setOpenExternalLinks(True)
                self.layout().addWidget(self._auth_link)
            self._auth_link.setText(f"<a href='{auth_url}'>If your browser didn't open, click here to sign in with Discord.</a>")

            
            self._poll_timer = QTimer(self)
            self._poll_timer.setInterval(200)
            self._poll_timer.timeout.connect(self._check_token)
            self._poll_timer.start()
            self._deadline = QTimer(self)
            self._deadline.setSingleShot(True)
            self._deadline.setInterval(60000)  
            self._deadline.timeout.connect(lambda: self._show_error("Timeout: No code received. Check redirect URLs (53135/53136) and Public Client in the Developer Portal."))
            self._deadline.start()

        def _check_token(self):
            
            if not self._code:
                return
            self._poll_timer.stop()
            if hasattr(self, "_deadline"):
                self._deadline.stop()
            
            try:
                if self._server:
                    self._server.shutdown()
            except Exception:
                pass
        
            try:
                data = {
                    "client_id": "1429597807161114624",
                    "grant_type": "authorization_code",
                    "code": self._code,
                    "redirect_uri": f"http://127.0.0.1:{self._port}/callback",
                    "code_verifier": self._code_verifier,
                }
                token_resp = requests.post("https://discord.com/api/oauth2/token", data=data, timeout=8)
                if token_resp.status_code != 200:
                    self._show_error(f"Token exchange failed: HTTP {token_resp.status_code} {token_resp.text[:120]}")
                    return
                token_json = token_resp.json()
                self._token = token_json.get("access_token")
                if not self._token:
                    self._show_error("No access_token in token response.")
                    return
                
                resp = requests.get("https://discord.com/api/users/@me", headers={"Authorization": f"Bearer {self._token}"}, timeout=5)
                if resp.status_code != 200:
                    self._show_error(f"Login failed: HTTP {resp.status_code}")
                    return
                app.discord_token = self._token
                app.discord_user = resp.json()
                self.accept()
            except Exception as e:
                self._show_error(f"Network error: {e}")

    
    splash = AnimatedSplash()
    def show_login_then_main():
        dlg = LoginDialog()
        if dlg.exec() == QDialog.Accepted:
            app.main_window = MainWindow()
            if app.windowIcon().isNull() is False:
                app.main_window.setWindowIcon(app.windowIcon())
            app.main_window.show()
        else:
            
            app.quit()
    splash.run_then(show_login_then_main)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
