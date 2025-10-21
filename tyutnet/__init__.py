"""tyutnet: 校园网自动登录核心模块

包含：
- config: 配置加载（config.json + 环境变量覆盖）
"""

__all__ = [
    "config",
]

from . import config as config  # noqa: E402,F401
