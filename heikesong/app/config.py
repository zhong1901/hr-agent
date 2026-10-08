"""应用配置：所有敏感信息从环境变量 / .env 文件读取，绝不硬编码。"""
import os
from pathlib import Path

# 项目根目录（app/ 的上一级）
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"


def _load_dotenv(path: Path) -> None:
    """极简 .env 解析：KEY=VALUE 每行，支持 # 注释与引号。不覆盖已存在的环境变量。"""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


_load_dotenv(ENV_FILE)


class Settings:
    """集中管理配置项，全部来自环境变量，便于替换与部署。"""

    # 大模型（Anthropic 兼容 /v1/messages 接口）
    anthropic_base_url: str = os.getenv("ANTHROPIC_BASE_URL", "https://api.deepseek.com/anthropic")
    anthropic_auth_token: str = os.getenv("ANTHROPIC_AUTH_TOKEN", "")
    anthropic_model: str = os.getenv("ANTHROPIC_MODEL", "deepseek-v4-pro")

    # SQLite 数据库路径
    database_path: str = os.getenv("DATABASE_PATH", str(BASE_DIR / "data" / "app.db"))

    # 免费用户每日模拟面试次数
    free_daily_limit: int = int(os.getenv("FREE_DAILY_LIMIT", "3"))


settings = Settings()
