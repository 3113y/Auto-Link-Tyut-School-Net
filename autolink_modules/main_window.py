# 主窗口与UI相关逻辑
import sys
from pathlib import Path
import json
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLineEdit, QPushButton, QLabel,
    QComboBox, QTextEdit, QHBoxLayout, QFileDialog, QSizePolicy
)
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage
from PyQt5.QtCore import QUrl, QTimer
from PyQt5.QtGui import QTextOption
from autolink_modules.config_manager import load_config
from autolink_modules.js_scripts import (
    get_check_login_status_js,
    get_check_login_message_js,
    get_fill_local_auth_fields_js,
    get_fill_form_and_login_js,
    get_check_captcha_js,
    get_captcha_url_js
)
from autolink_modules.captcha_handler import CaptchaHandler


class CustomWebEnginePage(QWebEnginePage):
    """自定义页面类，禁止创建新窗口"""
    def createWindow(self, _type):
        """禁止创建新窗口，所有链接都在当前页面打开"""
        return None


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
        # 使用自定义页面类，禁止创建新窗口
        custom_page = CustomWebEnginePage(self.webview)
        self.webview.setPage(custom_page)
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
        
        self.extract_captcha_btn = QPushButton("提取验证码样本")
        right_layout.addWidget(self.extract_captcha_btn)
        
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

        # 验证码处理器
        self.captcha_handler = CaptchaHandler()
        
        # 验证码提取相关
        self._extract_mode = False
        self._extracted_count = 0
        self._extract_target = 1000
        self._captcha_save_dir = Path.cwd() / "captcha_samples"

        # --- Connections ---
        self._load_config()
        self.login_btn.clicked.connect(self.login_once)
        self.auto_btn.clicked.connect(self.start_auto_retry)
        self.stop_btn.clicked.connect(self.stop_auto_retry)
        self.save_btn.clicked.connect(self.save_credentials)
        self.switch_btn.clicked.connect(self.switch_credentials)
        self.extract_captcha_btn.clicked.connect(self.toggle_extract_mode)
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
                self._log("登录失败，未启用自动重试，停止操作。")
                self.stop_auto_retry()
            return

        current_url = self.webview.url().toString()
        self._log(f"页面加载完成: {current_url} (Phase: {self._login_phase})")

        if self._login_phase == 'local_auth':
            if self._local_auth_url in current_url:
                self._log("教学管理服务平台页面加载完成，自动填充账号密码...")
                self.fill_local_auth_fields_only()
                if self._extract_mode:
                    self._log("📌 提取模式已开启，准备提取验证码...")
                    self._log("提示：验证码已出现在页面上，点击下方继续提取")
                else:
                    # 非提取模式下，启动自动验证码识别和登录
                    self._log("开始轮询验证码图片...")
                    self._captcha_poll_attempts = 0
                    self.captcha_poll_timer.start(500)
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
        page = self.webview.page()
        if page:
            page.runJavaScript(get_check_captcha_js(), self.handle_poll_for_captcha_result)

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

    def check_login_message(self):
        """检查并输出登录消息"""
        page = self.webview.page()
        if page:
            page.runJavaScript(get_check_login_message_js(), self.handle_login_message_result)

    def handle_login_message_result(self, result):
        """处理登录消息结果"""
        if result:
            self._log(f"登录消息: {result}")

    def check_login_status(self):
        """使用JS检查登录状态"""
        page = self.webview.page()
        if page:
            page.runJavaScript(get_check_login_status_js(), self.handle_login_status_result)

    def handle_login_status_result(self, status):
        """处理登录状态检查结果"""
        current_url = self.webview.url().toString()
        is_vpn_page = self._local_auth_url not in current_url

        if status in ['vpn_success_api', 'vpn_success_ui']:
            if self._login_phase == 'vpn' and is_vpn_page:
                self._log(f"VPN登录成功 (检测方式: {status})。立即跳转到内网平台...")
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
            elif self._manual_login_active:
                self._log("手动登录失败，停止操作。")
                self.stop_auto_retry()
        else:
            self._log(f"状态未知 ({status})，等待后再次检查...")
            if self._manual_login_active:
                # 手动登录模式下，不继续轮询检查
                self._log("手动登录模式，停止状态检查。")
                self.stop_auto_retry()
            else:
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
        
        page = self.webview.page()
        if page:
            page.runJavaScript(get_fill_local_auth_fields_js(username, password))

    def start_captcha_login_process(self):
        """开始验证码登录流程"""
        self._log("开始识别验证码...")
        page = self.webview.page()
        if page:
            page.runJavaScript(get_captcha_url_js(), self.solve_captcha)

    def solve_captcha(self, captcha_url):
        if not captcha_url:
            self._log("未找到验证码图片URL，直接尝试登录...")
            self.fill_form_and_click(None)
            return

        self._log(f"获取到验证码地址: {captcha_url}")
        success, result, error_msg = self.captcha_handler.download_and_solve(captcha_url)
        
        if success:
            if error_msg:
                self._log(error_msg)
            self._log(f"验证码识别结果: {result}")
            self.fill_form_and_click(result)
        else:
            self._log(f"验证码处理失败: {error_msg}")
            self.fill_form_and_click(None)

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

        page = self.webview.page()
        if page:
            page.runJavaScript(get_fill_form_and_login_js(username, password, captcha_result))
            # 延迟检查登录消息
            QTimer.singleShot(2000, self.check_login_message)
        
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
            # 直接保存到 scripts/config.json，不弹窗
            cfg_path = Path.cwd() / "scripts" / "config.json"
            cfg_path.parent.mkdir(parents=True, exist_ok=True)
            
            urls = [self.url_combo.itemText(i) for i in range(self.url_combo.count())]
            # 移除保存逻辑中的 password 字段，仅保留 vpn_password 和 local_password
            config_data = {
                "username": username,
                "vpn_password": vpn_password,
                "local_password": local_password,
                "server_url": urls,
                "retry_interval_secs": 5,
                "max_retries": 0
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
                
                # 修改读取逻辑，移除对 password 字段的处理
                self.vpn_password_edit.setText(cfg.get("vpn_password", ""))
                self.local_password_edit.setText(cfg.get("local_password", ""))

                self.url_combo.clear()
                for url in cfg.get("server_url", []):
                    self.url_combo.addItem(url)
                self._log(f"已切换到配置文件 {cfg_path}")
        except Exception as e:
            self._log(f"切换失败：{e}")

    def adjust_webview_to_page(self):
        """不再调整webview大小，保持窗口固定尺寸"""
        # 禁用自动调整大小功能，webview将使用滚动条显示超出视口的内容
        pass

    def _resize_webview(self, result):
        """已禁用的调整大小回调"""
        pass

    def debug_log_area_size(self):
        pass
    
    def toggle_extract_mode(self):
        """切换验证码提取模式 / 自动连续提取验证码"""
        current_url = self.webview.url().toString()
        is_local_platform = self._local_auth_url in current_url
        self._extract_mode = not self._extract_mode
        if self._extract_mode:
            self._extracted_count = 0
            self._captcha_save_dir.mkdir(exist_ok=True)
            self.extract_captcha_btn.setText(f"自动提取验证码 ({self._extracted_count}/{self._extract_target})")
            self._log(f"✓ 自动验证码提取模式已开启！目标: {self._extract_target} 张")
            self._log(f"保存目录: {self._captcha_save_dir.absolute()}")
            self._log("📌 自动流程: 自动点击验证码图片，自动保存，直到达到目标数量")
            if is_local_platform:
                self._log("开始自动提取验证码...")
                self.auto_extract_captcha()
            else:
                self._log("请先登录到教学管理服务平台，再开启自动提取模式。")
        else:
            self.extract_captcha_btn.setText("提取验证码样本")
            self._log(f"✓ 自动验证码提取模式已关闭。共提取: {self._extracted_count} 张")

    def auto_extract_captcha(self):
        """自动点击验证码图片并保存，循环直到目标数量"""
        if not self._extract_mode or self._extracted_count >= self._extract_target:
            self._log(f"自动提取已完成或已关闭。共提取: {self._extracted_count} 张")
            self.extract_captcha_btn.setText("提取验证码样本")
            self._extract_mode = False
            return
        page = self.webview.page()
        if page:
            # 1. 获取当前验证码URL
            page.runJavaScript(get_captcha_url_js(), self.handle_auto_extract_captcha)

    def handle_auto_extract_captcha(self, captcha_url):
        """自动提取验证码回调"""
        if not captcha_url:
            self._log("✗ 未找到验证码图片URL，等待页面加载...")
            QTimer.singleShot(1000, self.auto_extract_captcha)
            return
        self._log(f"✓ 检测到验证码地址: {captcha_url}")
        self.save_captcha_sample(captcha_url, after_save=self.simulate_click_and_wait)

    def simulate_click_and_wait(self):
        """模拟点击验证码图片，等待新验证码加载后继续自动提取"""
        page = self.webview.page()
        if page:
            # 2. 模拟点击验证码图片，触发刷新
            js_click = """
            var img = document.getElementById('img_lazycaptcha');
            if(img) { img.click(); }
            """
            page.runJavaScript(js_click)
            self._log("已自动点击验证码图片，等待新验证码加载...")
            # 3. 等待新验证码加载后继续提取
            QTimer.singleShot(1500, self.auto_extract_captcha)

    
    def save_captcha_sample(self, captcha_url, after_save=None):
        """保存验证码样本，支持回调"""
        if self._extracted_count >= self._extract_target:
            self._log(f"✓ 已达到目标数量 {self._extract_target} 张，停止提取")
            self._extract_mode = False
            self.extract_captcha_btn.setText("提取验证码样本")
            return
        try:
            import requests
            from datetime import datetime
            response = requests.get(captcha_url, timeout=10)
            response.raise_for_status()
            processed_bytes = self.captcha_handler.process_gif_captcha(response.content)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            filename = f"captcha_{timestamp}.png"
            filepath = self._captcha_save_dir / filename
            with open(filepath, 'wb') as f:
                f.write(processed_bytes)
            self._extracted_count += 1
            self._log(f"✓ 已保存 ({self._extracted_count}/{self._extract_target}): {filename}")
            self.extract_captcha_btn.setText(f"自动提取验证码 ({self._extracted_count}/{self._extract_target})")
            if self._extracted_count >= self._extract_target:
                self._log(f"🎉 验证码提取完成！共 {self._extracted_count} 张")
                self._log(f"保存位置: {self._captcha_save_dir.absolute()}")
                self._extract_mode = False
                self.extract_captcha_btn.setText("提取验证码样本")
            elif after_save:
                QTimer.singleShot(500, after_save)
        except Exception as e:
            self._log(f"✗ 保存验证码失败: {e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = AutoLoginWindow()
    win.show()
    sys.exit(app.exec_())
