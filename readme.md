# 简介

这是一个用于全自动挤掉其他人来连上太原理工大学校园网的脚本。
本质就是向校园网认证服务器发送认证请求包，从而实现连接校园网的目的。
由于校园网由motionPro提供服务,所以release包也会顺带安装motionPro。

## 使用方法

以下为基础框架与占位实现，需根据实际门户接口补充字段与 URL。

## 配置

两种方式（二选一，环境变量优先）：

1. 在仓库根目录创建 `config.json`（已提供示例），字段：

- username: 学号
- password: 密码
- server_url: 门户认证地址（示例为占位）
- retry_interval_secs: 重试间隔秒数（默认 5）
- max_retries: 最大重试次数，0 表示无限

1. 使用环境变量（PowerShell 示例）：

```powershell
$env:TYUT_USERNAME = "你的学号"
$env:TYUT_PASSWORD = "你的密码"
$env:TYUT_SERVER_URL = "https://portal.example.tyut.edu.cn/login"
$env:TYUT_RETRY_INTERVAL_SECS = "5"
$env:TYUT_MAX_RETRIES = "0"
```

## 运行

支持两种入口：

- 作为模块运行（直接开始循环重试直到成功）：

```powershell
python -m tyutnet
```

- 通过 CLI（可选择子命令）：

```powershell
python .\app.py run            # 循环重试
python .\app.py login          # 单次登录
python .\app.py logout         # 登出
python .\app.py status         # 查看状态

# 指定配置文件路径（默认 ./config.json）
python .\app.py --config .\config.json run
```

提示：当前 `motionpro_client.py` 为占位实现，真实字段名/URL 需结合 MotionPro 与校园网网关接口调整。

