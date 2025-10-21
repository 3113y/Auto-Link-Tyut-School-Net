import sys
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLineEdit, QPushButton, QLabel,
    QComboBox, QTextEdit, QHBoxLayout, QFileDialog, QSizePolicy
)
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl, QTimer
from tyutnet.config import load_config
import json
from PyQt5.QtGui import QTextOption

LOGIN_URL = "https://vpn3.tyut.edu.cn/prx/000/http/localhost/login"

class AutoLoginWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("校园网自动登录（内置浏览器）")
        self.resize(800, 600)
        layout = QVBoxLayout()

        # --- UI Elements ---
        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("学号")
        self.password_edit = QLineEdit()
        self.password_edit.setPlaceholderText("密码")
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.url_combo = QComboBox()
        self.login_btn = QPushButton("登录一次")
        self.auto_btn = QPushButton("开始自动重试")
        self.stop_btn = QPushButton("停止自动重试")
        self.stop_btn.setEnabled(False)
        self.status_label = QLabel()
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setFixedWidth(400)
        self.log_area.setWordWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)
        self.webview = QWebEngineView()
        self.webview.setZoomFactor(0.8)
        self.save_btn = QPushButton("保存账号密码")
        self.switch_btn = QPushButton("切换账号密码")

        # --- Layout ---
        layout.addWidget(QLabel("账号:"))
        layout.addWidget(self.username_edit)
        layout.addWidget(QLabel("密码:"))
        layout.addWidget(self.password_edit)
        url_layout = QHBoxLayout()
        url_layout.addWidget(QLabel("登录地址:"))
        url_layout.addWidget(self.url_combo)
        layout.addLayout(url_layout)
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.login_btn)
        btn_layout.addWidget(self.auto_btn)
        btn_layout.addWidget(self.stop_btn)
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.switch_btn)
        layout.addLayout(btn_layout)
        layout.addWidget(self.status_label)
        layout.addWidget(QLabel("日志:"))
        layout.addWidget(self.log_area)
        layout.addWidget(self.webview)
        self.setLayout(layout)

        # --- State and Timers ---
        self._auto_active = False
        self._auto_index = 0      # Overall retry attempts
        self._url_index = 0       # Index for which VPN URL to try
        self._retry_limit = 6
        self.status_check_timer = QTimer(self)
        self.status_check_timer.timeout.connect(self.check_login_status)
        self.status_check_timer.setSingleShot(True)

        # --- Connections ---
        self._load_config()
        self.login_btn.clicked.connect(self.login_once)
        self.auto_btn.clicked.connect(self.start_auto_retry)
        self.stop_btn.clicked.connect(self.stop_auto_retry)
        self.save_btn.clicked.connect(self.save_credentials)
        self.switch_btn.clicked.connect(self.switch_credentials)
        self.webview.loadFinished.connect(self.on_load_finished)
        self.log_area.textChanged.connect(self.debug_log_area_size)

    def on_load_finished(self, ok):
        """Callback when a page finishes loading."""
        self.adjust_webview_to_page()
        if not self._auto_active:
            return

        if not ok:
            self._log(f"URL: {self.webview.url().toString()} 加载失败。")
            self._try_next_url() # Try the next URL
            return

        self._log("页面加载完成，尝试填充表单并登录...")
        self.attempt_fill_and_click()
        # After clicking, wait a bit before starting to check the status
        self.status_check_timer.start(3000) # Start checking status after 3s

    def check_login_status(self):
        """Use JS to check the precise login status based on button states."""
        if not self._auto_active:
            return

        js = """
        (function() {
            var vpnOnButton = document.querySelector('#vpnOn');
            var vpnOffButton = document.querySelector('#vpnOff');
            var unameField = document.querySelector('[name="uname"]');

            if (vpnOffButton) {
                // Success if the "Disconnect" button is present
                return 'success';
            }
            if (vpnOnButton && vpnOnButton.hasAttribute('disabled')) {
                // Still connecting if "Connect" button is disabled
                return 'connecting';
            }
            if (unameField) {
                // Still on the login page
                return 'failure';
            }
            // Default/unknown state, maybe a transitional page
            return 'unknown';
        })();
        """
        self.webview.page().runJavaScript(js, self.handle_login_status_result)

    def handle_login_status_result(self, status):
        """Handle the result from check_login_status."""
        if not self._auto_active:
            return

        if status == 'success':
            self._log("检测到 '断开连接' 按钮，登录成功！")
            self.stop_auto_retry()
        elif status == 'connecting':
            self._log("检测到 '启动连接' 按钮禁用，正在连接中，请稍候...")
            # Wait another 3 seconds and check again on the same page
            self.status_check_timer.start(3000)
        elif status == 'failure':
            self._log("仍在登录页面，此地址尝试失败。")
            self._try_next_url() # Move to the next URL
        else: # 'unknown' or other
            self._log(f"状态未知 ({status})，等待后再次检查...")
            # Could be a transitional page, wait and check again
            self.status_check_timer.start(3000)

    def _load_config(self):
        try:
            cfg = load_config(Path.cwd())
            self.username_edit.setText(cfg.username)
            self.password_edit.setText(cfg.password)
            self.url_combo.clear()
            for u in cfg.server_url:
                self.url_combo.addItem(u)
            if cfg.server_url:
                self.webview.setUrl(QUrl(cfg.server_url[0]))
        except Exception as e:
            self.status_label.setText(f"加载配置失败：{e}")

    def login_once(self):
        """Manually trigger a single login attempt on the current URL."""
        self._url_index = self.url_combo.currentIndex()
        current_url = self.url_combo.currentText().strip()
        if not current_url:
            self._log("当前无可用地址。")
            return
        
        self._log(f"正在加载地址: {current_url}")
        self.webview.setUrl(QUrl(current_url))
        # The rest is handled by on_load_finished

    def attempt_fill_and_click(self):
        """Executes JS to fill the form and click the login button."""
        self.status_label.setText("正在自动填充并登录...")
        username = self.username_edit.text().strip()
        password = self.password_edit.text().strip()
        js = f"""
        (function() {{
            var unameField = document.querySelector('[name=\\"uname\\"]');
            var pwdField = document.querySelector('[name=\\"pwd\\"]');
            var loginButton = document.querySelector('#login');
            if (unameField && pwdField && loginButton) {{
                unameField.value = "{username}";
                pwdField.value = "{password}";
                loginButton.click();
                console.log('尝试点击登录按钮...');
            }} else {{
                console.error('登录字段或按钮未找到');
            }}
        }})();
        """
        self.webview.page().runJavaScript(js)

    def start_auto_retry(self):
        if self._auto_active:
            return
        self._log(f"开始智能自动重试 (上限 {self._retry_limit} 次)...")
        self._auto_active = True
        self.auto_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self._auto_index = 0
        self._url_index = 0
        self._try_next_url() # Start the process

    def _try_next_url(self):
        """The core sequential logic: try the next available URL."""
        if not self._auto_active:
            return

        if self._auto_index >= self._retry_limit:
            self._log(f"已达到最大重试次数 ({self._retry_limit})，停止重试。")
            self.stop_auto_retry()
            return

        total_urls = self.url_combo.count()
        if total_urls == 0:
            self._log("无可用登录地址，停止重试。")
            self.stop_auto_retry()
            return

        self._url_index = self._auto_index % total_urls
        self.url_combo.setCurrentIndex(self._url_index)
        current_url = self.url_combo.currentText()

        self._log(f"第 {self._auto_index + 1}/{self._retry_limit} 次尝试: 目标 {current_url}")
        self.webview.setUrl(QUrl(current_url))
        self._auto_index += 1

    def stop_auto_retry(self):
        self._auto_active = False
        self.status_check_timer.stop()
        self.auto_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self._log("已停止自动重试。")

    def _log(self, msg: str):
        self.status_label.setText(msg)
        self.log_area.append(msg)

    def save_credentials(self):
        username = self.username_edit.text().strip()
        password = self.password_edit.text().strip()
        if not username or not password:
            self._log("账号和密码不能为空，无法保存！")
            return
        try:
            cfg_path, _ = QFileDialog.getSaveFileName(self, "保存配置文件", str(Path.cwd() / "config.json"), "JSON Files (*.json)")
            if cfg_path:
                urls = [self.url_combo.itemText(i) for i in range(self.url_combo.count())]
                with open(cfg_path, "w", encoding="utf-8") as f:
                    json.dump({"username": username, "password": password, "server_url": urls}, f, ensure_ascii=False, indent=4)
                self._log(f"账号密码已保存到 {cfg_path}")
        except Exception as e:
            self._log(f"保存失败：{e}")

    def switch_credentials(self):
        try:
            cfg_path, _ = QFileDialog.getOpenFileName(self, "选择配置文件", str(Path.cwd()), "JSON Files (*.json)")
            if cfg_path:
                with open(cfg_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                self.username_edit.setText(cfg.get("username", ""))
                self.password_edit.setText(cfg.get("password", ""))
                self.url_combo.clear()
                for url in cfg.get("server_url", []):
                    self.url_combo.addItem(url)
                self._log(f"已切换到配置文件 {cfg_path}")
        except Exception as e:
            self._log(f"切换失败：{e}")

    def adjust_webview_to_page(self):
        self.webview.page().runJavaScript(
            "document.body.scrollWidth + ',' + document.body.scrollHeight",
            self._resize_webview
        )

    def _resize_webview(self, result):
        try:
            width, height = map(int, result.split(','))
            if width > 0 and height > 0:
                self.webview.setMinimumSize(width, height)
        except (ValueError, AttributeError):
            pass # Ignore if result is not as expected

    def debug_log_area_size(self):
        pass # This can be removed or left empty

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = AutoLoginWindow()
    win.show()
    sys.exit(app.exec_())
