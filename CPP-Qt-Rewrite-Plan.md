# 使用 C++ & Qt 重写 `Auto-Link-Tyut-School-Net` 的方案

下面是将当前基于 Python/PyQt 的项目重写为原生 C++/Qt 应用的完整计划与技术建议，适用于 Windows（首选）以及 macOS/Linux 的后续移植。

## 概要（1句）

将现有 Python/PyQt 程序用 C++ 与 Qt 重写以获得更小的可执行体积、更低的运行时依赖和更高的性能，同时保留现有功能（双阶段自动登录、ONNX 验证码识别、内嵌浏览器 JS 注入、抢课辅助框架）。

## 开始前的要点（决策项）

- 使用 Qt Widgets + Qt WebEngine（与现项目 UI 相似、稳定）。
- 使用 CMake 构建系统（跨平台且与 Qt 官方推荐一致）。
- 使用 ONNX Runtime C++ API（轻量，推理速度快）。
- 使用 OpenCV C++ 进行图像预处理（与现有 Python/OpenCV 对应）。
- 打包方式：Windows 推荐 MSVC + 静态 Qt（或使用 Qt Installer Framework / windeployqt 进行动态部署）；若追求最小体积考虑使用静态并剥离不必要模块或使用 Qt for Device/Embedded。

## 目标（验收条件）

- 功能等价：VPN 登录自动化、教学平台自动登录、ONNX 验证码识别、JS 注入模块、抢课录制/选择器框架。
- 可执行文件体积显著减少（目标：比 Python+PyInstaller 版本减小 70%+，实际依赖 Qt 构建方式）
- 稳定性与响应速度优于 Python 版本
- 代码结构清晰，便于维护与扩展

## 高层架构映射（Python -> C++）

- GUI: `autolink_modules/main_window.py` -> `src/main_window.cpp/.h`（Qt Widgets + Designer 可选）
- WebEngine 与 JS 注入: `QWebEngineView` / `QWebEnginePage`（C++ API）
- 验证码识别: `autolink_modules/captcha_handler.py` -> `src/captcha/` 中使用 ONNX Runtime C++ + OpenCV
- 预处理: `preprocess_helper.py` -> `src/captcha/preprocess.cpp/.h`（OpenCV 实现 rgb_to_binary_smart）
- 抢课 JS: `autolink_modules/js_scripts.py` -> `resources/js/*.js`（内置为资源或外部文件）
- 抢课框架: `course_grabber.py` -> `src/course_grabber/`（使用 QThread 或 Qt Concurrent）
- 配置管理: `scripts/config.json` -> `src/config/ConfigManager`（读取/写入 JSON，使用 nlohmann/json）
- 日志：使用 Qt 日志或 spdlog（可选）

## 详细模块设计

### 1) 应用入口与主窗口

- `main.cpp`：初始化 Qt、日志、加载资源、检查模型文件路径
- `MainWindow`（`main_window.h/.cpp`）
  - Layout 与行为与现有 Python 版本一致
  - 按钮和信号槽替换 Python 回调
  - 提供 API：`startAutoLogin()`, `stopAutoLogin()`, `saveHTML()`, `startRecording()`, `stopRecording()`

### 2) Web 层与 JS 注入

- 使用 `QWebEngineView` 与自定义 `QWebEnginePage`（禁止新窗口）
- JS 注入通过 `page()->runJavaScript()`（回调 C++ lambda 捕获结果）
- 将 `js_scripts.py` 中的 JS 函数转为 `.js` 文件并作为 Qt 资源：`:/js/get_select_course.js`

### 3) 验证码识别（核心）

- ONNX Runtime C++:
  - 创建 `InferenceSession`（注意：onnxruntime-cpp 库）
  - 加载 `best_model_digits.onnx` 与 `best_model_operators.onnx`
- 预处理：使用 OpenCV 实现 `rgb_to_binary_smart()` 的逻辑
- 动画 GIF 处理：
  - 选项 A：使用 Qt 的 `QMovie` 读取各帧并转换为 `QImage` → 转 OpenCV Mat
  - 选项 B：用第三方库（stb_image 动态 GIF 支持或 giflib）
- 接口：提供同步/异步两种调用方式（主线程不可阻塞）
- 返回格式：结构体 { success: bool, text: std::string, confidence: float }

### 4) 抢课录制器（HTML 录制与操作回放）

- 借助 `QWebEnginePage::runJavaScript` 注入录制脚本
- 将录制结果写为 JSON（使用 nlohmann/json）并保存在 `recorded_sessions/`
- 生成选择器建议并写入文本文件
- 回放（可选）：将 JSON 转换为 JS 并依次执行以模拟用户交互（小心权限/时间间隔）

### 5) 配置与持久化

- 使用 `nlohmann/json` 或 Qt 自带 `QJsonDocument` 进行配置读写
- 模型文件和资源路径通过 `QStandardPaths::writableLocation()` / 应用目录处理

### 6) 打包与部署

- Windows（推荐）：MSVC + CMake + Qt 静态/动态
  - 动态部署：使用 `windeployqt` 收集依赖（更简单）
  - 静态部署：需取得 Qt 商业授权（静态链接许可证问题）或使用社区构建并自行承担兼容性
- 减小体积技巧：
  - 在 Release 模式下剥离符号
  - 使用 `Qt Lite` 或仅编译需要的模块（widgets, webengine, network）
  - 精简资源，外部加载大模型文件

## 构建工具与第三方依赖

- CMake >= 3.16
- Qt 5.15+ / Qt 6.x（确保 `Qt WebEngine` 可用）
- ONNX Runtime C++ API（Windows x64 预编译二进制或源码）
- OpenCV（使用官方预编译包或自己编译）
- nlohmann/json（单文件头）
- spdlog（可选，用于日志）

## 示例 CMake 片段（草案）

```cmake
cmake_minimum_required(VERSION 3.16)
project(tyut_auto_login)
set(CMAKE_CXX_STANDARD 17)

find_package(Qt5 COMPONENTS Widgets WebEngineWidgets Network REQUIRED)
find_package(OpenCV REQUIRED)
# onnxruntime: 设置 ONNXRUNTIME_DIR 或 find_package 自定义

add_executable(tyut_auto_login
  src/main.cpp
  src/main_window.cpp
  src/captcha/captcha_handler.cpp
  src/captcha/preprocess.cpp
  ...
)

target_include_directories(tyut_auto_login PRIVATE ${OpenCV_INCLUDE_DIRS} ${ONNXRUNTIME_INCLUDE_DIRS})
target_link_libraries(tyut_auto_login PRIVATE Qt5::Widgets Qt5::WebEngineWidgets ${OpenCV_LIBS} ${ONNXRUNTIME_LIBS})
```

## 迁移注意事项与实现细节

1. Python 的方便之处：动态、开发快；C++ 需要明确内存与线程管理。建议在早期先实现最小可运行版本（MVP）：
   - 只实现登录+内嵌浏览器+验证码离线推理（同步）
   - 验证工作流后再做抢课框架与录制回放

2. QWebEngine 中 `runJavaScript` 回调均在 UI 线程，长时间 JS 处理需异步设计与超时控制。

3. ONNX Runtime: 输入数据格式需严格匹配训练时（float32 / NHWC 或 NCHW）；将 Python preprocess 转换为 OpenCV C++ 函数并严格校验输出。

4. GIF 帧处理：`QMovie` 在 GUI 线程工作，可能需要把帧提取移到后台线程或先将 GIF 保存为单独文件并用 OpenCV/第三方库读取。

5. 字体/本地化：保留中文界面，使用 Qt 的国际化（`.ts` / `lupdate` / `linguist`）以便日后扩展。

## 性能与体积预估（经验值）

- 可执行文件体积：
  - 使用 `windeployqt`（动态）: 约 40–120 MB，依赖于 Qt WebEngine 与运行时
  - 使用静态构建并剥离模块：理论上可降到 20–50 MB（需要定制构建）
- 开发周期（单人经验估计）：
  - MVP（核心功能）: 1–2 周
  - 完整替换（UI、打包、测试、文档）: 3–5 周

## 测试计划

- 单元测试：对 `preprocess`、ONNX 推理封装、配置读写添加单元测试（使用 GoogleTest）
- 集成测试：在受控环境中跑完整登录流程（含验证码）
- 回归测试：记录成功的抓取与失败日志，建立用例

## 风险与缓解

- 风险：Qt WebEngine 的二进制体积大 → 缓解：只在必要平台使用，或使用轻量浏览器内核（代价大）
- 风险：静态链接 Qt 可能违反许可证或困难 → 缓解：使用动态部署并优化资源
- 风险：ONNX 模型输入/输出不一致导致识别失败 → 缓解：在开发早期加入详细的输入/输出断言并对齐预处理

## 开发里程碑（建议）

1. **阶段 1：项目初始化**（2 天）
   - CMake 配置 + Qt 快速 UI 原型
   - 验证开发环境与依赖库
   
2. **阶段 2：Web 层与登录**（3–5 天）
   - WebEngine 嵌入 + 登录工作流（VPN + local）
   - JS 注入基础框架
   
3. **阶段 3：验证码识别**（3–5 天）
   - ONNX + OpenCV 预处理
   - 本地验证码识别与测试
   
4. **阶段 4：抢课录制**（2 天）
   - 抢课录制脚本迁移
   - 文件读写与选择器生成
   
5. **阶段 5：抢课框架**（3–5 天）
   - CourseGrabber 框架
   - UI 集成与配置管理
   
6. **阶段 6：打包与测试**（2–4 天）
   - 打包脚本与文档
   - 完整测试与优化

**总计：15–25 工作日（3–5 周）**

## 交付产物清单

- `src/` 完整 C++ 源代码
- `resources/js/` 迁移的 JS 脚本
- CMake 构建脚本与 `README-build.md`
- 打包脚本（`windeployqt` 流程文档）
- 单元测试与集成测试用例

## 其他建议与可选优化

- 如果目标仅是减小体积且不想花大量开发成本，可考虑：
  - 使用 PySide2 的独立打包并裁剪（改良 PyInstaller 选项）
  - 或者用 C++ 仅编写性能关键模块（如验证码识别），其余保留 Python，实现混合架构

---

如果你想，我可以：

1. 基于这个计划生成 CMake 工程骨架（`CMakeLists.txt` + 最小 `main.cpp` + `main_window` stub）到仓库；
2. 生成 `captcha` 子模块的 C++ 实现骨架（ONNX Runtime 封装 + OpenCV 预处理函数）；
3. 给出 Windows 下用 MSVC + `windeployqt` 的详细打包步骤和脚本。

告诉我你想先要哪一个，我会直接把对应代码/脚本写入仓库。
