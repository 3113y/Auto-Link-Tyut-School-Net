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
        self.log_area.setMaximumWidth(400)  # 限制日志区域的最大宽度为400像素
        self.log_area.setWordWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)  # 启用自动换行
        self.log_area.setFixedWidth(400)  # 设置日志区域的固定宽度为400像素
        self.webview = QWebEngineView()
        self.webview.setUrl(QUrl(LOGIN_URL))
        self.webview.setZoomFactor(0.8)  # 调整网页缩放比例以适应显示
        self.save_btn = QPushButton("保存账号密码")
        self.switch_btn = QPushButton("切换账号密码")

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

        # 加载配置并自动填充
        self._load_config()

        self.login_btn.clicked.connect(self.login_once)
        self.auto_btn.clicked.connect(self.start_auto_retry)
        self.stop_btn.clicked.connect(self.stop_auto_retry)
        self.save_btn.clicked.connect(self.save_credentials)
        self.switch_btn.clicked.connect(self.switch_credentials)
        
        # --- 修改重试逻辑 ---
        self.webview.loadFinished.connect(self.on_load_finished) # 核心：页面加载完后触发
        self.webview.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.log_area.textChanged.connect(self.debug_log_area_size)

        # 用于检查登录状态的计时器
        self.login_status_timer = QTimer(self)
        self.login_status_timer.timeout.connect(self.check_login_status)
        self.login_status_timer.setSingleShot(True) # 只触发一次

    def on_load_finished(self, ok):
        """页面加载完成后触发."""
        self.adjust_webview_to_page() # 调整视图大小
        if not ok:
            self._log("页面加载失败，准备重试...")
            if getattr(self, "_auto_active", False):
                QTimer.singleShot(5000, self._auto_tick) # 5秒后重试
            return
        
        self._log("页面加载完成，开始检查登录状态...")
        # 延迟检查，确保JS执行环境稳定
        self.login_status_timer.start(2000)

    def check_login_status(self):
        """使用JS检查登录是否成功."""
        js = """
        (function() {
            // 检查是否有登录表单元素
            var unameField = document.querySelector('[name="uname"]');
            var pwdField = document.querySelector('[name="pwd"]');
            if (unameField || pwdField) {
                return 'failure'; // 仍在登录页
            }
            // 检查是否有明确的错误消息（可根据实际页面调整选择器）
            var errorMsg = document.querySelector('.error-msg, .error, #error_note');
            if (errorMsg && errorMsg.innerText.length > 0) {
                return 'failure'; // 发现错误消息
            }
            // 如果都找不到，则认为成功
            return 'success';
        })();
        """
        self.webview.page().runJavaScript(js, self.handle_login_status_result)

    def handle_login_status_result(self, status):
        """处理登录状态检查结果."""
        if status == "success":
            self._log("登录成功！已停止自动重试。")
            self.stop_auto_retry()
        elif status == "failure":
            self._log("登录失败或仍在登录页面。")
            if getattr(self, "_auto_active", False):
                self._log("准备下一次自动重试...")
                # 尝试填充和点击，如果页面就是登录页的话
                self.attempt_fill_and_click()
                # 设置一个定时器以防万一，如果页面没反应，还能继续
                QTimer.singleShot(5000, self._auto_tick)
        else:
            self._log(f"未知的登录状态: {status}，将继续重试。")
            if getattr(self, "_auto_active", False):
                QTimer.singleShot(5000, self._auto_tick)

    def _load_config(self):
        try:
            cfg = load_config(Path.cwd())
            self.username_edit.setText(cfg.username)
            self.password_edit.setText(cfg.password)
            self.url_combo.clear()
            for u in cfg.server_url:
                self.url_combo.addItem(u)
            # 设置初始页面
            if cfg.server_url:
                self.webview.setUrl(QUrl(cfg.server_url[0]))
        except Exception as e:
            self.status_label.setText(f"加载配置失败：{e}")

    def login_once(self):
        """触发一次登录尝试，加载或刷新页面."""
        username = self.username_edit.text().strip()
        password = self.password_edit.text().strip()
        if not username or not password:
            self.status_label.setText("账号和密码不能为空！")
            return
            
        current_url = self.url_combo.currentText().strip() or LOGIN_URL
        # 如果URL没变，就尝试填充，否则加载新URL
        if self.webview.url().toString() == current_url:
             self.attempt_fill_and_click()
        else:
             self.webview.setUrl(QUrl(current_url))
        
    def attempt_fill_and_click(self):
        """仅执行JS填充和点击操作."""
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
        if getattr(self, "_auto_active", False):
            return
        self._log("开始智能自动重试(上限6次)...")
        self._auto_active = True
        self.auto_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self._auto_index = 0
        self._retry_limit = 6  # 设置重试上限
        self._auto_tick() # 立即开始第一次尝试

    def _auto_tick(self):
        """执行一次重试周期."""
        if not getattr(self, "_auto_active", False):
            return

        if self._auto_index >= self._retry_limit:
            self._log(f"已达到最大重试次数 ({self._retry_limit})，停止重试。")
            self.stop_auto_retry()
            return
        
        self._log(f"执行第 {self._auto_index + 1}/{self._retry_limit} 次尝试...")
        total = self.url_combo.count()
        if total == 0:
            self._log("无可用登录地址")
            self.stop_auto_retry()
            return
        self.url_combo.setCurrentIndex(self._auto_index % total)
        self.login_once()
        self._auto_index += 1
        # 注意：不再在这里设置下一次定时器，而是由登录状态检查结果来驱动

    def stop_auto_retry(self):
        self._auto_active = False
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
            cfg_path = QFileDialog.getSaveFileName(self, "保存配置文件", str(Path.cwd() / "config.json"), "JSON Files (*.json)")[0]
            if cfg_path:
                with open(cfg_path, "w", encoding="utf-8") as f:
                    json.dump({"username": username, "password": password, "server_url": [self.url_combo.itemText(i) for i in range(self.url_combo.count())]}, f, ensure_ascii=False, indent=4)
                self._log(f"账号密码已保存到 {cfg_path}")
        except Exception as e:
            self._log(f"保存失败：{e}")

    def switch_credentials(self):
        try:
            cfg_path = QFileDialog.getOpenFileName(self, "选择配置文件", str(Path.cwd()), "JSON Files (*.json)")[0]
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

    def adjust_window_to_page(self):
        self.webview.page().runJavaScript(
            """
            var width = document.body.scrollWidth;
            var height = document.body.scrollHeight;
            [width, height];
            """,
            self._resize_window
        )

    def _resize_window(self, dimensions):
        if dimensions and len(dimensions) == 2:
            width, height = dimensions
            self.resize(width + 50, height + 100)  # 添加一些边距

    def adjust_webview_to_page(self):
        self.webview.page().runJavaScript(
            """
            var width = document.body.scrollWidth;
            var height = document.body.scrollHeight;
            [width, height];
            """,
            self._resize_webview
        )

    def _resize_webview(self, dimensions):
        if dimensions and len(dimensions) == 2:
            width, height = dimensions
            if width > 0 and height > 0:
                self.webview.setMinimumSize(width, height)

    def debug_log_area_size(self):
        current_width = self.log_area.width()
        current_height = self.log_area.height()
        print(f"[DEBUG] 日志区域当前宽度: {current_width}, 高度: {current_height}")  # 使用 print 输出调试信息，避免递归

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = AutoLoginWindow()
    win.show()
    sys.exit(app.exec_())
