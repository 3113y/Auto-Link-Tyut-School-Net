import sys
from pathlib import Path
import json
import requests
import ddddocr
import io
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLineEdit, QPushButton, QLabel,
    QComboBox, QTextEdit, QHBoxLayout, QFileDialog, QSizePolicy
)
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl, QTimer
from tyutnet.config import load_config
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
        self.vpn_password_edit = QLineEdit()
        self.vpn_password_edit.setPlaceholderText("VPN 密码 (vpn.tyut.edu.cn)")
        self.vpn_password_edit.setEchoMode(QLineEdit.Password)
        self.local_password_edit = QLineEdit()
        self.local_password_edit.setPlaceholderText("内网认证密码 (192.168.200.100)")
        self.local_password_edit.setEchoMode(QLineEdit.Password)
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
        layout.addWidget(QLabel("VPN 密码:"))
        layout.addWidget(self.vpn_password_edit)
        layout.addWidget(QLabel("内网认证密码:"))
        layout.addWidget(self.local_password_edit)
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
        self._manual_login_active = False
        self._auto_index = 0      # Overall retry attempts
        self._url_index = 0       # Index for which VPN URL to try
        self._retry_limit = 6
        self._login_phase = 'vpn' # 'vpn' or 'local_auth'
        self._local_auth_url = 'http://192.168.200.100/'

        self.status_check_timer = QTimer(self)
        self.status_check_timer.timeout.connect(self.check_login_status)
        self.status_check_timer.setSingleShot(True)

        self.captcha_poll_timer = QTimer(self)
        self.captcha_poll_timer.timeout.connect(self.poll_for_captcha)
        self._captcha_poll_attempts = 0
        self._captcha_poll_max_attempts = 10  # 10 * 500ms = 5 seconds

        self.ocr = ddddocr.DdddOcr()

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
        """Callback when a page finishes loading. Acts as a dispatcher."""
        self.adjust_webview_to_page()

        is_manual_login = self._manual_login_active
        if is_manual_login:
            self._manual_login_active = False # Reset flag immediately

        if not self._auto_active and not is_manual_login:
            return

        if not ok:
            self._log(f"URL: {self.webview.url().toString()} 加载失败。")
            if self._auto_active:
                self._try_next_url()
            return

        current_url = self.webview.url().toString()
        if self._local_auth_url in current_url:
            self._log("内网认证页面加载完成，开始轮询查找验证码...")
            self._captcha_poll_attempts = 0
            self.captcha_poll_timer.start(500)
        else: # VPN page
            self._log("VPN页面加载完成，直接尝试登录 (无验证码)...")
            self.fill_form_and_click(None) # No captcha on VPN page

    def poll_for_captcha(self):
        """Periodically check if the captcha image has loaded."""
        js_check_captcha = "document.getElementById('img_lazycaptcha') && document.getElementById('img_lazycaptcha').src"
        page = self.webview.page()
        if page:
            page.runJavaScript(js_check_captcha, self.handle_poll_for_captcha_result)

    def handle_poll_for_captcha_result(self, result):
        self._captcha_poll_attempts += 1
        if result:
            self._log("成功找到验证码图片。")
            self.captcha_poll_timer.stop()
            self.start_captcha_login_process()
        elif self._captcha_poll_attempts >= self._captcha_poll_max_attempts:
            self._log(f"轮询超时 ({self._captcha_poll_max_attempts * 0.5}秒)，未找到验证码，将直接尝试登录。")
            self.captcha_poll_timer.stop()
            self.start_captcha_login_process()
        else:
            self._log(f"第 {self._captcha_poll_attempts}/{self._captcha_poll_max_attempts} 次轮询，未找到验证码...")
            # The timer will fire again automatically

    def check_login_status(self):
        """Use JS to check the precise login status based on button states."""
        # This check should run for both manual and auto modes to handle redirects
        js = """
        (function() {
            // Primary, most reliable check using the internal API for VPN status
            if (typeof motionpro !== 'undefined' && motionpro.vpn && motionpro.vpn.status === 1) {
                return 'vpn_success_api';
            }

            // Fallback check using UI elements
            var vpnOnButton = document.querySelector('#vpnOn');
            var vpnOffButton = document.querySelector('#vpnOff');
            var unameField = document.querySelector('[name="uname"]');
            var loginButton = document.querySelector('#login');

            if (vpnOffButton) {
                // Fallback success if the "Disconnect" button is present (VPN success)
                return 'vpn_success_ui';
            }
            
            // For local auth, success might mean the login form is gone
            if (!loginButton && !unameField && window.location.href.includes('192.168.200.100')) {
                return 'local_auth_success';
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
        page = self.webview.page()
        if page:
            page.runJavaScript(js, self.handle_login_status_result)

    def handle_login_status_result(self, status):
        """Handle the result from check_login_status."""
        current_url = self.webview.url().toString()
        is_vpn_page = self._local_auth_url not in current_url

        if status in ['vpn_success_api', 'vpn_success_ui']:
            if self._login_phase == 'vpn' and is_vpn_page:
                self._log(f"VPN登录成功 (检测方式: {status})。等待2秒以确保隧道稳定...")
                # Wait 2 seconds to ensure tunnel is stable before redirecting
                QTimer.singleShot(2000, self.redirect_to_local_auth)
            else:
                self._log(f"在非VPN阶段检测到VPN成功状态，停止。")
                self.stop_auto_retry()

        elif status == 'local_auth_success':
            if self._login_phase == 'local_auth' and not is_vpn_page:
                self._log("内网认证成功！所有登录流程完成。")
                self.stop_auto_retry()
            else:
                self._log(f"在非内网认证阶段检测到成功状态，停止。")
                self.stop_auto_retry()

        elif status == 'connecting':
            self._log("检测到 '启动连接' 按钮禁用，正在连接中，请稍候...")
            self.status_check_timer.start(3000)
        elif status == 'failure':
            self._log("仍在登录页面，此地址尝试失败。")
            if self._auto_active:
                self._try_next_url()
        else: # 'unknown' or other
            self._log(f"状态未知 ({status})，等待后再次检查...")
            self.status_check_timer.start(3000)

    def redirect_to_local_auth(self):
        """Changes phase and redirects to the local authentication page."""
        self._log("正在跳转到内网认证平台...")
        self._login_phase = 'local_auth'
        self.webview.setUrl(QUrl(self._local_auth_url))

    def _load_config(self):
        try:
            cfg = load_config(Path.cwd())
            self.username_edit.setText(cfg.username)
            if hasattr(cfg, 'password'):
                self.vpn_password_edit.setText(cfg.password)
                self.local_password_edit.setText(cfg.password)
            else:
                self.vpn_password_edit.setText(getattr(cfg, 'vpn_password', ''))
                self.local_password_edit.setText(getattr(cfg, 'local_password', ''))

            self.url_combo.clear()
            for u in cfg.server_url:
                self.url_combo.addItem(u)
            if cfg.server_url:
                self.webview.setUrl(QUrl(cfg.server_url[0]))
        except Exception as e:
            self.status_label.setText(f"加载配置失败：{e}")

    def login_once(self):
        """Manually trigger a single login attempt on the current URL."""
        self.stop_auto_retry() # Stop any previous activity
        self._manual_login_active = True # Set flag for manual login

        current_url = self.url_combo.currentText().strip()
        if not current_url:
            self._log("当前无可用地址。")
            self._manual_login_active = False
            return
        
        # Determine phase based on selected URL for manual login
        if self._local_auth_url in current_url:
            self._login_phase = 'local_auth'
        else:
            self._login_phase = 'vpn'

        self._log(f"手动登录: 正在加载地址: {current_url}")
        self.webview.setUrl(QUrl(current_url))

    def start_captcha_login_process(self):
        """
        Starts the captcha-based login. Gets URL, then calls solve_captcha.
        """
        self._log("开始识别验证码...")
        js_get_captcha_url = "document.getElementById('img_lazycaptcha').src;"
        page = self.webview.page()
        if page:
            page.runJavaScript(js_get_captcha_url, self.solve_captcha)

    def solve_captcha(self, captcha_url):
        """
        Downloads captcha, runs OCR, and then calls fill_form_and_click.
        """
        if not captcha_url:
            self._log("未找到验证码图片URL，直接尝试登录...")
            self.fill_form_and_click(None)
            return

        self._log(f"获取到验证码地址: {captcha_url}")
        try:
            response = requests.get(captcha_url, timeout=10)
            response.raise_for_status()
            captcha_text = self.ocr.classification(response.content)
            self._log(f"OCR 识别结果: {captcha_text}")

            try:
                captcha_result = self._safe_eval(captcha_text)
                self._log(f"验证码计算结果: {captcha_result}")
                self.fill_form_and_click(str(captcha_result))
            except Exception as e:
                self._log(f"验证码计算失败: {e}。将使用原始识别文本。")
                self.fill_form_and_click(captcha_text)

        except requests.RequestException as e:
            self._log(f"下载验证码失败: {e}")
            self.fill_form_and_click(None)
        except Exception as e:
            self._log(f"OCR 识别或处理时发生未知错误: {e}")
            self.fill_form_and_click(None)

    def _safe_eval(self, expr_str):
        """Safely evaluate a simple arithmetic string."""
        expr_str = expr_str.replace('x', '*').replace('÷', '/')
        if not all(c in '0123456789+-*/. ' for c in expr_str):
            raise ValueError("表达式包含不允许的字符")
        return eval(expr_str)

    def fill_form_and_click(self, captcha_result):
        """Executes JS to fill the form and click login."""
        username = self.username_edit.text().strip()
        
        current_url = self.webview.url().toString()
        if self._local_auth_url in current_url:
            password = self.local_password_edit.text().strip()
            self._log("使用内网认证密码。")
        else:
            password = self.vpn_password_edit.text().strip()
            self._log("使用VPN密码。")

        js_parts = [
            "var unameField = document.querySelector('[name=\"uname\"]');",
            "var pwdField = document.querySelector('[name=\"pwd\"]');",
            "var captchaField = document.getElementById('captcha');",
            "var loginButton = document.querySelector('#login');",
            "if (unameField && pwdField && loginButton) {",
            f"    unameField.value = \"{username}\";",
            f"    pwdField.value = \"{password}\";"
        ]

        if captcha_result is not None and captcha_result.strip():
            js_parts.append(f"    if (captchaField) captchaField.value = \"{captcha_result}\";")

        js_parts.extend([
            "    loginButton.click();",
            "    console.log('尝试点击登录按钮...');",
            "} else {",
            "    console.error('登录字段或按钮未找到');",
            "}"
        ])

        js = "\n".join(js_parts)
        page = self.webview.page()
        if page:
            page.runJavaScript(js)
        
        # After clicking, always start a status check
        self.status_check_timer.start(3000)

    def start_auto_retry(self):
        if self._auto_active:
            return
        self._log(f"开始智能自动重试 (上限 {self._retry_limit} 次)...")
        self._auto_active = True
        self.auto_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self._auto_index = 0
        self._url_index = 0
        self._login_phase = 'vpn' # Start with VPN phase
        self._try_next_url()

    def _try_next_url(self):
        """The core sequential logic: try the next available URL."""
        if not self._auto_active:
            return

        if self._auto_index >= self._retry_limit:
            self._log(f"已达到最大重试次数 ({self._retry_limit})，停止重试。")
            self.stop_auto_retry()
            return

        all_urls = [self.url_combo.itemText(i) for i in range(self.url_combo.count())]
        vpn_urls = [url for url in all_urls if self._local_auth_url not in url]

        if self._login_phase == 'vpn':
            if not vpn_urls:
                self._log("未找到可用的VPN地址，停止重试。")
                self.stop_auto_retry()
                return
            
            self._url_index = self._auto_index % len(vpn_urls)
            current_url = vpn_urls[self._url_index]
            self._log(f"VPN阶段 - 第 {self._auto_index + 1}/{self._retry_limit} 次尝试: 目标 {current_url}")
            self.webview.setUrl(QUrl(current_url))
            self._auto_index += 1
        else:
            self._log("已进入内网认证阶段，等待页面加载和操作...")
            self._auto_index += 1

    def stop_auto_retry(self):
        self._auto_active = False
        self._manual_login_active = False
        self.status_check_timer.stop()
        self.captcha_poll_timer.stop()
        self.auto_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self._log("已停止所有登录活动。")

    def _log(self, msg: str):
        self.status_label.setText(msg)
        self.log_area.append(msg)

    def save_credentials(self):
        username = self.username_edit.text().strip()
        vpn_password = self.vpn_password_edit.text().strip()
        local_password = self.local_password_edit.text().strip()

        if not username or not vpn_password:
            self._log("账号和VPN密码不能为空，无法保存！")
            return
        try:
            cfg_path, _ = QFileDialog.getSaveFileName(self, "保存配置文件", str(Path.cwd() / "config.json"), "JSON Files (*.json)")
            if cfg_path:
                urls = [self.url_combo.itemText(i) for i in range(self.url_combo.count())]
                config_data = {
                    "username": username,
                    "vpn_password": vpn_password,
                    "local_password": local_password,
                    "server_url": urls
                }
                with open(cfg_path, "w", encoding="utf-8") as f:
                    json.dump(config_data, f, ensure_ascii=False, indent=4)
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
                
                if "password" in cfg:
                    self.vpn_password_edit.setText(cfg.get("password", ""))
                    self.local_password_edit.setText(cfg.get("password", ""))
                else:
                    self.vpn_password_edit.setText(cfg.get("vpn_password", ""))
                    self.local_password_edit.setText(cfg.get("local_password", ""))

                self.url_combo.clear()
                for url in cfg.get("server_url", []):
                    self.url_combo.addItem(url)
                self._log(f"已切换到配置文件 {cfg_path}")
        except Exception as e:
            self._log(f"切换失败：{e}")

    def adjust_webview_to_page(self):
        page = self.webview.page()
        if page:
            page.runJavaScript(
                "document.body.scrollWidth + ',' + document.body.scrollHeight",
                self._resize_webview
            )

    def _resize_webview(self, result):
        try:
            if result:
                width, height = map(int, result.split(','))
                if width > 0 and height > 0:
                    self.webview.setMinimumSize(width, height)
        except (ValueError, AttributeError):
            pass

    def debug_log_area_size(self):
        pass

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = AutoLoginWindow()
    win.show()
    sys.exit(app.exec_())
