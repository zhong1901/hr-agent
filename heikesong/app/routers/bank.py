"""题库与 AI 解析（订阅内容）。"""
from fastapi import APIRouter, Depends, HTTPException

from .. import llm
from ..database import get_conn
from ..deps import get_current_user, get_subscription, require_premium

router = APIRouter(prefix="/api/bank", tags=["bank"])


@router.get("/positions")
def list_positions(user: dict = Depends(get_current_user)):
    """列出已有预设题库的岗位。"""
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT position, COUNT(*) AS c FROM question_bank GROUP BY position ORDER BY c DESC"
        ).fetchall()
    finally:
        conn.close()
    return {"positions": [{"position": r["position"], "count": r["c"]} for r in rows]}


@router.get("")
def browse_bank(position: str, user: dict = Depends(get_current_user), sub: dict = Depends(get_subscription)):
    """浏览某岗位题库；解析内容为订阅专属。"""
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT id, position, years_range, salary_tier, difficulty, question, analysis "
            "FROM question_bank WHERE position=? ORDER BY difficulty, id",
            (position,),
        ).fetchall()
    finally:
        conn.close()

    is_premium = sub.get("status") == "premium"
    questions = []
    for r in rows:
        item = {
            "id": r["id"],
            "position": r["position"],
            "years_range": r["years_range"],
            "salary_tier": r["salary_tier"],
            "difficulty": r["difficulty"],
            "question": r["question"],
        }
        if is_premium:
            item["analysis"] = r["analysis"]
        else:
            item["analysis"] = None
            item["locked"] = True
        questions.append(item)
    return {"questions": questions, "is_premium": is_premium}


@router.post("/analysis")
def ai_analysis(body: dict, sub: dict = Depends(require_premium)):
    """按需生成 AI 深度解析与答题思路（订阅专属）。"""
    question = (body or {}).get("question", "")
    if not question:
        raise HTTPException(status_code=400, detail="缺少题目")
    system = "你是一名资深面试官，给出专业、实用的答题思路与解析。"
    user = f"请对以下面试题给出深度解析与答题思路（分点、简洁、实用）：\n{question}"
    text = llm.chat(system, [{"role": "user", "content": user}], temperature=0.4, max_tokens=1024)
    return {"analysis": text}
