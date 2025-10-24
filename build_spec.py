"""
自动生成 PyInstaller spec 文件并打包
"""
import PyInstaller.__main__
import os
from pathlib import Path

# 获取当前目录
root_dir = Path(__file__).parent

# PyInstaller 参数
PyInstaller.__main__.run([
    'app.py',                                      # 主程序入口
    '--name=TYUT-AutoLogin',                       # 应用名称
    '--windowed',                                   # 窗口模式（不显示控制台）
    '--onefile',                                    # 打包成单个exe
    '--icon=resources/icon.ico',                    # 图标
    '--add-data=autolink_modules;autolink_modules', # 添加模块文件夹
    '--add-data=models;models',                     # 添加模型文件夹
    '--add-data=resources;resources',               # 添加资源文件夹
    '--hidden-import=PyQt5',
    '--hidden-import=PyQt5.QtCore',
    '--hidden-import=PyQt5.QtGui',
    '--hidden-import=PyQt5.QtWidgets',
    '--hidden-import=PyQt5.QtWebEngineWidgets',
    '--hidden-import=onnxruntime',
    '--hidden-import=cv2',
    '--hidden-import=PIL',
    '--hidden-import=numpy',
    '--hidden-import=scipy',
    '--collect-all=onnxruntime',
    '--collect-all=PyQt5',
    '--noconfirm',                                  # 不确认覆盖
    '--clean',                                      # 清理临时文件
])

print("\n✅ 打包完成！")
print(f"📦 可执行文件位于: {root_dir / 'dist' / 'TYUT-AutoLogin.exe'}")
