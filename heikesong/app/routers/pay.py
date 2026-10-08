"""Vibe Pay 支付占位 + 订阅测试开关。

真实支付接入前，用 /test-activate 一键将当前用户设为订阅，方便本地演示。
后续接 Vibe Pay 时替换 create-order / notify 的真实逻辑并补充验签。
"""
import time

from fastapi import APIRouter, Depends

from ..database import get_conn
from ..deps import get_current_user, get_subscription

router = APIRouter(prefix="/api/pay", tags=["pay"])


@router.post("/test-activate")
def test_activate(user: dict = Depends(get_current_user)):
    """测试开关：将当前用户设为订阅（仅用于本地演示，接真实支付后移除）。"""
    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO subscriptions (user_id, status, plan, started_at) "
            "VALUES (?, 'premium', 'vibe_pay_monthly', datetime('now','localtime')) "
            "ON CONFLICT(user_id) DO UPDATE SET status='premium', plan='vibe_pay_monthly'",
            (user["id"],),
        )
        conn.commit()
    finally:
        conn.close()
    return {"status": "premium"}


@router.post("/create-order")
def create_order(user: dict = Depends(get_current_user)):
    """Vibe Pay 下单占位：参数按文档预留，真实支付后续接入。"""
    order_id = f"demo_{user['id']}_{int(time.time())}"
    return {
        "order_id": order_id,
        "amount": "19.90",          # 示例月费
        "currency": "CNY",
        "pay_url": "",               # 接 Vibe Pay 后返回真实支付链接
        "status": "created",
        "note": "Vibe Pay 占位订单，尚未接入真实收款",
    }


@router.post("/notify")
def notify():
    """Vibe Pay 异步回调占位：真实接入后需验签并更新订阅状态。"""
    return {"code": "SUCCESS"}


@router.get("/status")
def status(sub: dict = Depends(get_subscription)):
    return sub
