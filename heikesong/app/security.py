"""密码哈希与安全会话 token。全部使用标准库，避免原生依赖在 Python 3.14 下的安装问题。"""
import hashlib
import secrets

_ITERATIONS = 200_000


def hash_password(password: str) -> str:
    """使用 PBKDF2-SHA256 加盐哈希密码，返回可持久化的字符串。"""
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), _ITERATIONS)
    return f"pbkdf2_sha256${_ITERATIONS}${salt}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """校验密码与存储哈希是否匹配（常量时间比较）。"""
    try:
        _, iters, salt, hex_dk = stored.split("$")
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), int(iters))
        return secrets.compare_digest(dk.hex(), hex_dk)
    except Exception:
        return False


def new_token() -> str:
    """生成随机会话 token。"""
    return secrets.token_urlsafe(32)
