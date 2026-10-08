"""FastAPI 依赖：解析当前用户、订阅状态、免费额度扣减。"""
from datetime import date

from fastapi import Depends, Header, HTTPException

from .config import settings
from .database import get_conn


def get_current_user(authorization: str = Header(default="")) -> dict:
    """从 Authorization: Bearer <token> 解析当前登录用户。"""
    token = authorization.removeprefix("Bearer ").strip() if authorization else ""
    if not token:
        raise HTTPException(status_code=401, detail="未登录")
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT u.* FROM sessions s JOIN users u ON u.id = s.user_id WHERE s.token = ?",
            (token,),
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        raise HTTPException(status_code=401, detail="登录已失效")
    return dict(row)


def get_subscription(user: dict = Depends(get_current_user)) -> dict:
    """返回当前用户订阅状态（无记录视为免费用户）。"""
    conn = get_conn()
    try:
        row = conn.execute("SELECT * FROM subscriptions WHERE user_id = ?", (user["id"],)).fetchone()
    finally:
        conn.close()
    if row is None:
        return {"user_id": user["id"], "status": "free", "plan": "free"}
    return dict(row)


def require_premium(sub: dict = Depends(get_subscription)) -> dict:
    """要求订阅用户，否则 403。"""
    if sub.get("status") != "premium":
        raise HTTPException(status_code=403, detail="该功能为订阅内容，请先订阅")
    return sub


def consume_daily_quota(user_id: int) -> bool:
    """免费用户每日额度扣减。返回 True 表示扣减成功（可继续），False 表示已用完。"""
    today = date.today().isoformat()
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT count FROM daily_usage WHERE user_id=? AND date=?",
            (user_id, today),
        ).fetchone()
        if row and row["count"] >= settings.free_daily_limit:
            return False
        conn.execute(
            "INSERT INTO daily_usage (user_id, date, count) VALUES (?, ?, 1) "
            "ON CONFLICT(user_id, date) DO UPDATE SET count = count + 1",
            (user_id, today),
        )
        conn.commit()
        return True
    finally:
        conn.close()
