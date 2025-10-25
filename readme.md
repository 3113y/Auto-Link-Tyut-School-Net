# TYUT 教学管理服务平台自动登录工具

## 简介

这是一个用于自动连接太原理工大学（TYUT）教学管理服务平台的图形界面工具。它通过内置浏览器自动完成 VPN 登录和内网认证两个阶段，并集成了**基于 ONNX 深度学习模型的验证码自动识别功能**，实现真正的全自动登录。

## ✨ 功能特性

- **图形用户界面 (GUI)**：提供简单易用的操作界面，无需命令行基础。
- **双阶段自动登录**：
  - 自动完成 VPN 登录（vpn.tyut.edu.cn）
  - 自动跳转并登录教学管理服务平台（192.168.200.100）
- **🤖 AI 验证码自动识别** ：
  - 基于CNN导出的ONNX深度学习模型（98.99% 准确率）
  - 自动识别算术验证码（如 "8-6=?"）
  - 自动计算并填入结果
  - 无需手动输入，真正实现全自动登录
- **两种登录模式**：
  - **登录一次**：手动触发单次登录尝试，失败后不自动重试
  - **自动重试**：智能检测登录状态，自动重试直到成功或达到次数上限
- **多服务器轮询**：配置多个 VPN 服务器地址（`vpn1`, `vpn2`, `vpn3`），程序会按顺序逐一尝试。
- **多密码支持**：
  - 支持分别配置 VPN 密码和教学管理服务平台密码
  - 如果两个密码相同，只需填写一次
- **配置管理**：
  - 启动时自动从 `scripts/config.json` 加载账号、密码和服务器地址
  - 点击"保存账号密码"按钮直接保存配置，无需手动选择位置
  - 支持从不同的配置文件中加载（切换账号）
- **🎬 抢课辅助工具**（预览功能）：
  - **保存页面 HTML**：一键保存当前选课页面的完整 HTML 结构，自动生成带注释版本
  - **操作录制**：录制你的点击、输入等操作，自动生成选择器建议
  - 为未来的全自动抢课功能提前做准备，无需手动分析 DOM 结构
- **实时日志**：在界面上实时显示当前的连接状态和操作日志，包括登录失败原因。
- **防止窗口堆积**：禁止创建新窗口，所有操作都在当前页面进行。
- **跨平台**：基于 Python 和 PyQt5，可在 Windows, macOS, Linux 上运行。

## 🚀 快速开始

### 方式一：直接运行可执行文件（推荐）

1. 从 [Releases](https://github.com/3113y/Auto-Link-Tyut-School-Net/releases) 下载最新版本的 `TYUT-AutoLogin.exe`
2. 双击运行即可，**无需安装 Python 环境**
3. 首次使用时填写账号密码并保存，之后即可一键登录

### 方式二：从源码运行

1. 克隆项目：
    ```bash
    git clone https://github.com/3113y/Auto-Link-Tyut-School-Net.git
    cd Auto-Link-Tyut-School-Net
    ```

2. 安装依赖：
    ```bash
    pip install -r requirements.txt
    ```

3. 运行程序：
    ```bash
    python app.py
    ```

## 🔧 打包为可执行文件

如果你想自己打包生成 `.exe` 文件：

```bash
python build_spec.py
```

打包完成后，可执行文件位于 `dist/TYUT-AutoLogin.exe`

## ⚙️ 配置说明

程序启动时会自动读取 `scripts/config.json` 文件。你可以手动创建或修改此文件来预设登录信息。

一个典型的 `config.json` 示例如下：

```json
{
    "username": "你的学号",
    "vpn_password": "VPN密码",
    "local_password": "教学管理服务平台密码",
    "server_url": [
        "https://vpn1.tyut.edu.cn/prx/000/http/localhost/login",
        "https://vpn2.tyut.edu.cn/prx/000/http/localhost/login",
        "https://vpn3.tyut.edu.cn/prx/000/http/localhost/login"
    ],
    "retry_interval_secs": 5,
    "max_retries": 0
}
```

### 配置字段说明

- `username`: 你的学号
- `vpn_password`: VPN 登录密码（vpn.tyut.edu.cn）
- `local_password`: 教学管理服务平台密码（192.168.200.100）。如果与 VPN 密码相同，可以填写相同值
- `server_url`: VPN 服务器地址列表，程序会自动按列表顺序进行尝试
- `retry_interval_secs`: 重试间隔（秒），默认 5 秒
- `max_retries`: 最大重试次数，0 表示无限重试

你也可以在程序运行后，在界面上修改信息，并点击 **"保存账号密码"** 按钮来自动更新 `scripts/config.json` 文件。

## 📖 使用说明

1. **填写账号信息**：
   - 在界面中填写学号、VPN 密码和教学管理服务平台密码
   - 点击"保存账号密码"按钮保存配置

2. **选择登录模式**：
   - **登录一次**：适合测试或手动控制，失败后不会自动重试
   - **开始自动重试**：适合自动化场景，会持续重试直到成功

3. **查看日志**：
   - 右侧日志区域会实时显示登录状态和错误信息
   - 如果登录失败，会显示具体的失败原因

4. **停止重试**：
   - 点击"停止自动重试"按钮可以随时中止自动重试过程

## 🎬 抢课辅助工具使用指南

为了方便后续开发全自动抢课功能，程序内置了两个强大的辅助工具：

### 1. 保存页面 HTML

**用途**：保存当前选课页面的完整 HTML 结构，方便离线分析

**使用步骤**：
1. 手动登录到选课页面
2. 点击 **"💾 保存当前页面HTML"** 按钮
3. 程序会自动生成两个文件：
   - `page_YYYYMMDD_HHMMSS.html` - 原始 HTML
   - `page_YYYYMMDD_HHMMSS_annotated.html` - 带注释的版本（标注了常见选择器）

**生成位置**：`recorded_sessions/` 文件夹

### 2. 操作录制

**用途**：录制你的抢课操作（点击、输入），自动生成选择器建议

**使用步骤**：
1. 点击 **"🎬 开始录制操作"** 按钮
2. 在网页中执行你的抢课操作：
   - 搜索课程
   - 点击"选课"按钮
   - 确认选课对话框
3. 完成操作后，点击 **"⏹ 停止录制"** 按钮
4. 程序会自动生成三个文件：
   - `actions_YYYYMMDD_HHMMSS.json` - 完整操作记录（JSON格式）
   - `actions_YYYYMMDD_HHMMSS_summary.txt` - 可读的操作摘要
   - `selector_suggestions_YYYYMMDD_HHMMSS.txt` - **自动生成的选择器建议**

**示例输出**（`selector_suggestions_*.txt`）：
```text
============================================================
自动生成的选择器建议
============================================================

## 点击操作的建议选择器：

操作 1: 点击 "选课"
  推荐选择器: button.btn-select.course-action
  或使用 ID: #selectBtn123

操作 2: 点击 "确定"
  推荐选择器: div.modal-footer > button.btn-confirm

## 输入操作的建议选择器：

输入 1: INPUT name="courseName"
  推荐选择器: input.form-control.course-search-input

============================================================
复制上述选择器到 js_scripts.py 中替换 TODO 标记！
============================================================
```

### 3. 如何使用录制结果

录制完成后：

1. 打开 `recorded_sessions/selector_suggestions_*.txt` 文件
2. 复制建议的选择器
3. 打开 `autolink_modules/js_scripts.py`
4. 找到带 `TODO` 标记的函数（`get_select_course_js` 等）
5. 将 TODO 选择器替换为实际的选择器
6. 测试抢课功能

**这样就不需要手动分析 HTML 结构了！** 🎉

## 🛠️ 技术栈

- **Python 3.9+**
- **PyQt5**: GUI 框架
- **PyQt5-WebEngine**: 内嵌浏览器支持
- **PIL (Pillow)**: 图像处理

## 📝 项目结构

```
Auto-Link-Tyut-School-Net/
├── app.py                      # 程序入口
├── autolink_modules/           # 模块化代码
│   ├── main_window.py         # 主窗口逻辑
│   ├── captcha_handler.py     # 验证码处理器（ONNX模型）
│   ├── preprocess_helper.py   # 智能预处理
│   ├── config_manager.py      # 配置管理
│   ├── js_scripts.py          # JavaScript注入脚本
│   ├── login_logic.py         # 登录逻辑
│   ├── course_grabber.py      # 抢课模块（预留）
│   └── html_recorder.py       # HTML录制器（抢课辅助）
├── models/                     # ONNX模型文件
│   ├── best_model_digits.onnx # 数字识别模型
│   └── best_model_operators.onnx # 运算符识别模型
├── scripts/                    # 配置文件夹
│   ├── config.json            # 用户配置文件
│   └── course_grabber_config.json # 抢课配置（预留）
├── resources/                  # 资源文件
│   └── icon.ico               # 应用图标
├── recorded_sessions/          # 录制的操作记录（自动生成）
└── readme.md                   # 说明文档
```

## ⚠️ 注意事项

- 本工具仅供太原理工大学在校师生使用
- 请妥善保管你的账号密码，不要将配置文件分享给他人
- 如遇到登录问题，请查看日志区域的错误提示
- 本工具不存储或上传任何个人信息

## 📄 开源协议

本项目遵循 MIT 协议开源。

