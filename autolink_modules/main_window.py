# 主窗口与UI相关逻辑
import sys
from pathlib import Path
import json
import requests
import io
from PIL import Image, ImageSequence
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLineEdit, QPushButton, QLabel,
    QComboBox, QTextEdit, QHBoxLayout, QFileDialog, QSizePolicy
)
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl, QTimer
from PyQt5.QtGui import QTextOption
from autolink_modules.config_manager import load_config

class AutoLoginWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TYUT教学管理服务平台自动登录")
        self.resize(1200, 700)
        
        # 主布局
        main_layout = QHBoxLayout()
        
        # === 左侧区域：表单和网页浏览器 ===
        left_widget = QWidget()
        left_layout = QVBoxLayout()
        
        # 表单区域
        form_layout = QVBoxLayout()
        form_layout.addWidget(QLabel("账号:"))
        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("学号")
        form_layout.addWidget(self.username_edit)
        
        form_layout.addWidget(QLabel("VPN 密码:"))
        self.vpn_password_edit = QLineEdit()
        self.vpn_password_edit.setPlaceholderText("VPN 密码 (vpn.tyut.edu.cn)")
        self.vpn_password_edit.setEchoMode(QLineEdit.Password)
        form_layout.addWidget(self.vpn_password_edit)
        
        form_layout.addWidget(QLabel("教学管理服务平台密码:"))
        self.local_password_edit = QLineEdit()
        self.local_password_edit.setPlaceholderText("教学管理服务平台密码 (192.168.200.100)")
        self.local_password_edit.setEchoMode(QLineEdit.Password)
        form_layout.addWidget(self.local_password_edit)
        
        url_layout = QHBoxLayout()
        url_layout.addWidget(QLabel("登录地址:"))
        self.url_combo = QComboBox()
        url_layout.addWidget(self.url_combo)
        form_layout.addLayout(url_layout)
        
        self.status_label = QLabel()
        form_layout.addWidget(self.status_label)
        
        left_layout.addLayout(form_layout)
        
        # 网页浏览器
        self.webview = QWebEngineView()
        self.webview.setZoomFactor(0.8)
        left_layout.addWidget(self.webview, stretch=1)
        
        left_widget.setLayout(left_layout)
        main_layout.addWidget(left_widget, stretch=3)
        
        # === 右侧区域：按钮和日志 ===
        right_widget = QWidget()
        right_layout = QVBoxLayout()
        
        # 按钮区域
        self.login_btn = QPushButton("登录一次")
        self.auto_btn = QPushButton("开始自动重试")
        self.stop_btn = QPushButton("停止自动重试")
        self.stop_btn.setEnabled(False)
        self.save_btn = QPushButton("保存账号密码")
        self.switch_btn = QPushButton("切换账号密码")
        
        right_layout.addWidget(self.login_btn)
        right_layout.addWidget(self.auto_btn)
        right_layout.addWidget(self.stop_btn)
        right_layout.addWidget(self.save_btn)
        right_layout.addWidget(self.switch_btn)
        
        # 日志区域
        right_layout.addWidget(QLabel("日志:"))
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setMinimumWidth(300)
        self.log_area.setWordWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)
        right_layout.addWidget(self.log_area, stretch=1)
        
        right_widget.setLayout(right_layout)
        main_layout.addWidget(right_widget, stretch=1)
        
        self.setLayout(main_layout)

        # --- State and Timers ---
        self._auto_active = False
        self._manual_login_active = False
        self._is_ongoing_login = False
        self._auto_index = 0
        self._url_index = 0
        self._retry_limit = 6
        self._login_phase = 'vpn'
        self._local_auth_url = 'http://192.168.200.100/'

        self.status_check_timer = QTimer(self)
        self.status_check_timer.timeout.connect(self.check_login_status)
        self.status_check_timer.setSingleShot(True)

        self.captcha_poll_timer = QTimer(self)
        self.captcha_poll_timer.timeout.connect(self.poll_for_captcha)
        self._captcha_poll_attempts = 0
        self._captcha_poll_max_attempts = 10

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
        """页面加载完成回调"""
        self.adjust_webview_to_page()

        if not self._is_ongoing_login:
            self._log(f"页面加载完成: {self.webview.url().toString()}, 但无活动任务，已忽略。")
            return

        if not ok:
            self._log(f"URL: {self.webview.url().toString()} 加载失败。")
            if self._auto_active:
                self._try_next_url()
            else:
                self.stop_auto_retry()
            return

        current_url = self.webview.url().toString()
        self._log(f"页面加载完成: {current_url} (Phase: {self._login_phase})")

        if self._login_phase == 'local_auth':
            if self._local_auth_url in current_url:
                self._log("教学管理服务平台页面加载完成，自动填充账号密码（暂不识别验证码和登录）...")
                # 临时屏蔽验证码识别功能，只填充账号密码
                self.fill_local_auth_fields_only()
            else:
                self._log("警告: 处于教学管理服务平台登录阶段，但加载了非预期的URL。")
                if self._auto_active:
                    self._try_next_url()
                else:
                    self.stop_auto_retry()
        
        elif self._login_phase == 'vpn':
            self._log("VPN页面加载完成，直接尝试登录 (无验证码)...")
            self.fill_form_and_click(None)
        
        else:
            self._log(f"未知的登录阶段: {self._login_phase}，停止操作。")
            self.stop_auto_retry()

    def poll_for_captcha(self):
        """轮询检查验证码图片是否加载"""
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

    def check_login_status(self):
        """使用JS检查登录状态"""
        js = """
        (function() {
            if (typeof motionpro !== 'undefined' && motionpro.vpn && motionpro.vpn.status === 1) {
                return 'vpn_success_api';
            }
            var vpnOffButton = document.querySelector('#vpnOff');
            if (vpnOffButton && vpnOffButton.className === 'btn') {
                return 'vpn_success_ui';
            }
            var vpnOnButton = document.querySelector('#vpnOn');
            var unameField = document.querySelector('[name="uname"]');
            var loginButton = document.querySelector('#login');
            if (!loginButton && !unameField && window.location.href.includes('192.168.200.100')) {
                return 'local_auth_success';
            }
            if (vpnOnButton && vpnOnButton.hasAttribute('disabled')) {
                return 'connecting';
            }
            if (unameField) {
                return 'failure';
            }
            return 'unknown';
        })();
        """
        page = self.webview.page()
        if page:
            page.runJavaScript(js, self.handle_login_status_result)

    def handle_login_status_result(self, status):
        """处理登录状态检查结果"""
        current_url = self.webview.url().toString()
        is_vpn_page = self._local_auth_url not in current_url

        if status in ['vpn_success_api', 'vpn_success_ui']:
            if self._login_phase == 'vpn' and is_vpn_page:
                self._log(f"VPN登录成功 (检测方式: {status})。立即跳转...")
                self.redirect_to_local_auth()
            else:
                self._log(f"在非VPN阶段检测到VPN成功状态，停止。")
                self.stop_auto_retry()
        elif status == 'local_auth_success':
            if self._login_phase == 'local_auth' and not is_vpn_page:
                self._log("教学管理服务平台认证成功！所有登录流程完成。")
                self.stop_auto_retry()
            else:
                self._log(f"在非教学管理服务平台认证阶段检测到成功状态，停止。")
                self.stop_auto_retry()
        elif status == 'connecting':
            self._log("检测到 '启动连接' 按钮禁用，正在连接中，请稍候...")
            self.status_check_timer.start(3000)
        elif status == 'failure':
            self._log("仍在登录页面，此地址尝试失败。")
            if self._auto_active:
                self._try_next_url()
        else:
            self._log(f"状态未知 ({status})，等待后再次检查...")
            self.status_check_timer.start(3000)

    def redirect_to_local_auth(self):
        """跳转到内网认证平台"""
        self._log("正在跳转到内网认证平台...")
        self._login_phase = 'local_auth'
        self.webview.setUrl(QUrl(self._local_auth_url))

    def _load_config(self):
        """加载配置文件"""
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
        """手动触发单次登录"""
        self.stop_auto_retry()
        self._is_ongoing_login = True
        self._manual_login_active = True

        current_url = self.url_combo.currentText().strip()
        if not current_url:
            self._log("当前无可用地址。")
            self.stop_auto_retry()
            return
        
        if self._local_auth_url in current_url:
            self._login_phase = 'local_auth'
        else:
            self._login_phase = 'vpn'

        self._log(f"手动登录: 正在加载地址: {current_url}")
        self.webview.setUrl(QUrl(current_url))

    def fill_local_auth_fields_only(self):
        """仅填充教学管理服务平台的账号密码字段，不处理验证码和登录"""
        username = self.username_edit.text().strip()
        password = self.local_password_edit.text().strip()
        
        self._log(f"自动填充账号: {username}，请手动输入验证码并登录。")
        
        js_code = f"""
        (function() {{
            var unameField = document.getElementById('txt_username');
            var pwdField = document.getElementById('txt_password');

            if (unameField && pwdField) {{
                console.log('找到教学管理服务平台登录表单字段，自动填充账号密码。');
                unameField.value = "{username}";
                pwdField.value = "{password}";
                console.log('账号密码已填充，请手动输入验证码并点击登录按钮。');
            }} else {{
                console.error('未找到教学管理服务平台登录表单字段。');
                if (!unameField) console.error('Username field (txt_username) not found.');
                if (!pwdField) console.error('Password field (txt_password) not found.');
            }}
        }})();
        """
        
        page = self.webview.page()
        if page:
            page.runJavaScript(js_code)

    def start_captcha_login_process(self):
        """开始验证码登录流程"""
        self._log("开始识别验证码...")
        js_get_captcha_url = "document.getElementById('img_lazycaptcha').src;"
        page = self.webview.page()
        if page:
            page.runJavaScript(js_get_captcha_url, self.solve_captcha)

    def solve_captcha(self, captcha_url):
        """下载并识别验证码"""
        if not captcha_url:
            self._log("未找到验证码图片URL，直接尝试登录...")
            self.fill_form_and_click(None)
            return

        self._log(f"获取到验证码地址: {captcha_url}")
        try:
            response = requests.get(captcha_url, timeout=10)
            response.raise_for_status()

            self._log("正在处理GIF验证码...")
            processed_image_bytes = self._process_gif_captcha(response.content)
            
            # 删除依赖 ddddocr 的代码
            # captcha_text = self.ocr.classification(processed_image_bytes)
            # 替换为占位符
            captcha_text = ""

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
            self._log(f"OCR 识别或GIF处理时发生未知错误: {e}")
            self.fill_form_and_click(None)

    def _process_gif_captcha(self, image_bytes, background_threshold=220):
        """处理GIF验证码：提取帧、去背景、合成"""
        with Image.open(io.BytesIO(image_bytes)) as img:
            canvas = Image.new('RGBA', img.size, (255, 255, 255, 0))
            
            for frame in ImageSequence.Iterator(img):
                frame = frame.convert('RGBA')
                processed_frame = Image.new('RGBA', frame.size, (255, 255, 255, 0))
                
                frame_data = frame.load()
                processed_data = processed_frame.load()

                if not frame_data or not processed_data:
                    continue

                for y in range(frame.height):
                    for x in range(frame.width):
                        pixel = frame_data[x, y]
                        if pixel[0] < background_threshold or pixel[1] < background_threshold or pixel[2] < background_threshold:
                            processed_data[x, y] = pixel
                
                canvas = Image.alpha_composite(canvas, processed_frame)

            final_image_bytes = io.BytesIO()
            canvas.save(final_image_bytes, format='PNG')
            return final_image_bytes.getvalue()

    def _safe_eval(self, expr_str):
        """安全地计算简单算术表达式"""
        expr_str = expr_str.replace('x', '*').replace('÷', '/')
        if not all(c in '0123456789+-*/. ' for c in expr_str):
            raise ValueError("表达式包含不允许的字符")
        return eval(expr_str)

    def fill_form_and_click(self, captcha_result):
        """填充表单并点击登录"""
        username = self.username_edit.text().strip()
        
        current_url = self.webview.url().toString()
        if self._local_auth_url in current_url:
            password = self.local_password_edit.text().strip()
            self._log("使用内网认证密码。")
        else:
            password = self.vpn_password_edit.text().strip()
            self._log("使用VPN密码。")

        js_code = f"""
        (function() {{
            var unameField = document.querySelector('[name="uname"]') || document.getElementById('txt_username');
            var pwdField = document.querySelector('[name="pwd"]') || document.getElementById('txt_password');
            var captchaField = document.getElementById('captcha') || document.getElementById('txt_lazycaptcha');
            var loginButton = document.querySelector('#login') || document.getElementById('btn_login');

            if (unameField && pwdField && loginButton) {{
                console.log('找到登录表单字段。');
                unameField.value = "{username}";
                pwdField.value = "{password}";

                var captchaVal = "{captcha_result or ''}";
                if (captchaField && captchaVal) {{
                    console.log('填充验证码...');
                    captchaField.value = captchaVal;
                }}

                console.log('尝试点击登录按钮...');
                loginButton.click();
            }} else {{
                console.error('登录表单字段或按钮未找到。无法执行登录。');
                if (!unameField) console.error('Username field not found.');
                if (!pwdField) console.error('Password field not found.');
                if (!loginButton) console.error('Login button not found.');
            }}
        }})();
        """

        page = self.webview.page()
        if page:
            page.runJavaScript(js_code)
        
        self.status_check_timer.start(3000)

    def start_auto_retry(self):
        """开始自动重试"""
        if self._auto_active:
            return
        self._log(f"开始智能自动重试 (上限 {self._retry_limit} 次)...")
        self._is_ongoing_login = True
        self._auto_active = True
        self.auto_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self._auto_index = 0
        self._url_index = 0
        self._login_phase = 'vpn'
        self._try_next_url()

    def _try_next_url(self):
        """尝试下一个URL"""
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
        """停止自动重试"""
        self._auto_active = False
        self._manual_login_active = False
        self._is_ongoing_login = False
        self.status_check_timer.stop()
        self.captcha_poll_timer.stop()
        self.auto_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self._log("已停止所有登录活动。")

    def _log(self, msg: str):
        """记录日志"""
        self.status_label.setText(msg)
        self.log_area.append(msg)

    def save_credentials(self):
        """保存凭证到文件"""
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
        """切换配置文件"""
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
        """调整webview大小以适应页面"""
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
