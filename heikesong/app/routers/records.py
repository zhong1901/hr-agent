"""练习记录与能力成长曲线。"""
import json

from fastapi import APIRouter, Depends

from ..database import get_conn
from ..deps import get_current_user

router = APIRouter(prefix="/api/records", tags=["records"])


@router.get("")
def list_records(user: dict = Depends(get_current_user)):
    """最近的练习记录（含评分卡与薄弱维度）。"""
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM practice_records WHERE user_id=? ORDER BY id DESC LIMIT 50",
            (user["id"],),
        ).fetchall()
    finally:
        conn.close()

    records = []
    for r in rows:
        records.append({
            "id": r["id"],
            "position": r["position"],
            "years_range": r["years_range"],
            "salary_tier": r["salary_tier"],
            "source": r["source"],
            "total_score": r["total_score"],
            "hire_probability": r["hire_probability"],
            "weak_dimension": r["weak_dimension"],
            "created_at": r["created_at"],
            "score": json.loads(r["score_json"]) if r["score_json"] else {},
        })
    return {"records": records}


@router.get("/growth")
def growth(user: dict = Depends(get_current_user)):
    """能力成长曲线：按时间顺序返回每次模拟的总分、录取概率与各维度分。"""
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM practice_records WHERE user_id=? ORDER BY id ASC",
            (user["id"],),
        ).fetchall()
    finally:
        conn.close()

    points = []
    for r in rows:
        sc = json.loads(r["score_json"]) if r["score_json"] else {}
        points.append({
            "created_at": r["created_at"],
            "total_score": r["total_score"],
            "hire_probability": r["hire_probability"],
            "dimensions": sc.get("dimensions", {}),
            "position": r["position"],
        })
    return {"points": points}
