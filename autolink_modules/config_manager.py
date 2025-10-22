# 配置管理相关
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class AppConfig:
    """应用配置数据类"""
    username: str
    password: str
    server_url: list[str]
    retry_interval_secs: int = 5
    max_retries: int = 0  # 0 表示无限重试
    vpn_password: str = ""  # VPN密码（如果与主密码不同）
    local_password: str = ""  # 内网认证密码（如果与主密码不同）


def _read_json_config(path: Path) -> dict:
    """读取JSON配置文件"""
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        # 容忍坏的 json，返回空
        return {}


def load_config(base_dir: Optional[Path] = None) -> AppConfig:
    """加载配置，优先级：环境变量 > config.json > 默认值。

    环境变量：
    - TYUT_USERNAME
    - TYUT_PASSWORD
    - TYUT_VPN_PASSWORD
    - TYUT_LOCAL_PASSWORD
    - TYUT_SERVER_URL
    - TYUT_RETRY_INTERVAL_SECS
    - TYUT_MAX_RETRIES
    """

    # 强制设置 base_dir 为 scripts 文件夹
    base_dir = Path.cwd() / "scripts"
    print(f"强制更新后的 base_dir: {base_dir}")

    json_cfg = _read_json_config(base_dir / "config.json")

    # 添加调试信息以打印加载路径和内容
    print(f"加载配置文件路径: {base_dir / 'config.json'}")
    print(f"配置文件内容: {json_cfg}")

    def getenv_str(name: str, default: str) -> str:
        val = os.getenv(name)
        return val if val not in (None, "") else default

    username = os.getenv("TYUT_USERNAME") or str(json_cfg.get("username", ""))
    password = os.getenv("TYUT_PASSWORD") or str(json_cfg.get("password", ""))
    vpn_password = os.getenv("TYUT_VPN_PASSWORD") or str(json_cfg.get("vpn_password", password))
    local_password = os.getenv("TYUT_LOCAL_PASSWORD") or str(json_cfg.get("local_password", password))

    # 支持环境变量和 config.json 均可为单个或多个 server_url
    env_server_url = os.getenv("TYUT_SERVER_URL")
    if env_server_url:
        # 逗号分隔或直接列表
        if "," in env_server_url:
            server_url = [u.strip() for u in env_server_url.split(",") if u.strip()]
        else:
            server_url = [env_server_url.strip()]
    else:
        url_val = json_cfg.get("server_url", [])
        if isinstance(url_val, str):
            server_url = [url_val]
        elif isinstance(url_val, list):
            server_url = [str(u) for u in url_val if u]
        else:
            server_url = []

    retry_interval_secs = int(
        getenv_str("TYUT_RETRY_INTERVAL_SECS", str(json_cfg.get("retry_interval_secs", 5)))
    )
    max_retries = int(
        getenv_str("TYUT_MAX_RETRIES", str(json_cfg.get("max_retries", 0)))
    )

    missing = [k for k, v in {
        "username": username,
        "password": password,
        "server_url": server_url,
    }.items() if not v or (isinstance(v, list) and not v)]

    if missing:
        raise ValueError(
            f"缺少必要配置: {', '.join(missing)}。请在 config.json 中填写，或通过环境变量设置。"
        )

    return AppConfig(
        username=username,
        password=password,
        server_url=server_url,
        retry_interval_secs=retry_interval_secs,
        max_retries=max_retries,
        vpn_password=vpn_password,
        local_password=local_password,
    )


def save_config(path: Path, config_data: dict):
    """保存配置文件"""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(config_data, f, ensure_ascii=False, indent=4)


def example_config() -> dict:
    """返回示例配置"""
    return {
        "username": "你的学号",
        "password": "你的密码",
        "vpn_password": "VPN密码（可选，默认同主密码）",
        "local_password": "内网认证密码（可选，默认同主密码）",
        "server_url": [
            "https://vpn1.tyut.edu.cn/prx/000/http/localhost/login",
            "https://vpn2.tyut.edu.cn/prx/000/http/localhost/login",
            "https://vpn3.tyut.edu.cn/prx/000/http/localhost/login"
        ],
        "retry_interval_secs": 5,
        "max_retries": 0,
    }
