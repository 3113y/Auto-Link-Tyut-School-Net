import os
import yaml
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QPushButton, QLabel, QTextEdit, QFileDialog, QComboBox
import requests
# 使用 jmcomic 模块实现下载逻辑
import jmcomic

option_path = os.path.join(os.path.dirname(__file__), '../resources/jmcomic/option.yml')
option = jmcomic.create_option_by_file(option_path)

def load_jmcomic_options():
    """加载 JMComic 的配置文件"""
    option_path = os.path.join(os.path.dirname(__file__), '../resources/jmcomic/option.yml')
    with open(option_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def save_jmcomic_options(options):
    """保存 JMComic 的配置文件"""
    option_path = os.path.join(os.path.dirname(__file__), '../resources/jmcomic/option.yml')
    with open(option_path, 'w', encoding='utf-8') as f:
        yaml.safe_dump(options, f, allow_unicode=True)

class JMComicWidget(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("JMComic 图形化下载")
        layout = QVBoxLayout()

        self.id_edit = QLineEdit()
        self.id_edit.setPlaceholderText("输入本子ID")
        self.format_combo = QComboBox()
        self.format_combo.addItems(["webp", "both"])
        self.download_btn = QPushButton("下载")
        self.change_path_btn = QPushButton("修改保存路径")
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)

        layout.addWidget(QLabel("本子ID:"))
        layout.addWidget(self.id_edit)
        layout.addWidget(QLabel("选择下载格式:"))
        layout.addWidget(self.format_combo)
        layout.addWidget(self.download_btn)
        layout.addWidget(self.change_path_btn)
        layout.addWidget(QLabel("日志:"))
        layout.addWidget(self.log_area)
        self.setLayout(layout)

        self.download_btn.clicked.connect(self.download)
        self.change_path_btn.clicked.connect(self.change_save_path)
        self.format_combo.currentIndexChanged.connect(self.update_download_format)

    def update_download_format(self):
        """根据选择更新 option.yml 文件"""
        selected_format = self.format_combo.currentText()
        options = load_jmcomic_options()

        if selected_format == "webp":
            # 移除 img2pdf 插件配置
            options['plugins']['after_photo'] = [
                plugin for plugin in options['plugins'].get('after_photo', [])
                if plugin.get('plugin') != 'img2pdf'
            ]
        elif selected_format == "both":
            # 添加 img2pdf 插件配置
            if not any(plugin.get('plugin') == 'img2pdf' for plugin in options['plugins'].get('after_photo', [])):
                options['plugins'].setdefault('after_photo', []).append({
                    'plugin': 'img2pdf',
                    'kwargs': {
                        'pdf_dir': '${APP_DIR}/resources/downloads/pdf',
                        'filename_rule': 'Pid'
                    }
                })

        save_jmcomic_options(options)
        self.log_area.append(f"下载格式已更新为: {selected_format}")

    def download(self):
        album_id = self.id_edit.text().strip()
        if not album_id:
            self.log_area.append("请输入本子ID！")
            return

        try:
            self.log_area.append(f"开始下载本子 {album_id} ...")
            jmcomic.download_album(album_id, option)
            self.log_area.append(f"本子 {album_id} 下载完成！")
        except Exception as e:
            self.log_area.append(f"下载失败: {e}")

    def change_save_path(self):
        """修改保存路径"""
        options = load_jmcomic_options()
        current_path = options.get('dir_rule', {}).get('base_dir', '')
        new_path = QFileDialog.getExistingDirectory(self, "选择保存路径", current_path)
        if new_path:
            options['dir_rule']['base_dir'] = new_path
            save_jmcomic_options(options)
            self.log_area.append(f"保存路径已修改为: {new_path}")