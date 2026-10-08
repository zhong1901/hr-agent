"""模拟面试：出题 / 追问 / 评分。"""
import json

from fastapi import APIRouter, Depends, HTTPException

from .. import question_bank, scoring
from ..config import settings
from ..database import get_conn
from ..deps import consume_daily_quota, get_current_user, get_subscription
from ..models import FollowupRequest, GenerateRequest, ScoreRequest

router = APIRouter(prefix="/api/interview", tags=["interview"])


@router.post("/generate")
def generate(
    req: GenerateRequest,
    user: dict = Depends(get_current_user),
    sub: dict = Depends(get_subscription),
):
    """开始一次模拟面试：题库优先 + AI 兜底出题。免费用户每次调用扣减额度。"""
    position = req.position.strip()
    if not position:
        raise HTTPException(status_code=400, detail="请填写目标岗位")

    count = max(1, min(req.count, 5))
    if sub.get("status") != "premium":
        if not consume_daily_quota(user["id"]):
            raise HTTPException(
                status_code=429,
                detail=f"今日免费模拟次数已用完（{settings.free_daily_limit} 次），订阅后可无限次使用",
            )

    return question_bank.generate_questions(position, req.years_range, req.salary_tier, req.job_desc, count)


@router.post("/followup")
def followup(req: FollowupRequest, user: dict = Depends(get_current_user)):
    """追问式多轮问答：基于回答生成一道追问。"""
    question = question_bank.generate_followup(
        req.position.strip(), req.question, req.answer, req.years_range, req.salary_tier
    )
    return {"question": question}


@router.post("/score")
def score(
    req: ScoreRequest,
    user: dict = Depends(get_current_user),
    sub: dict = Depends(get_subscription),
):
    """评分判定：四维度评分卡 + 总分 + 录取概率，并落库练习记录。"""
    if not req.qa:
        raise HTTPException(status_code=400, detail="请先作答")

    scorecard = scoring.score_interview(req.position.strip(), req.years_range, req.salary_tier, req.qa)
    weak = scoring.weak_dimension(scorecard)
    source = scoring.classify_source(req.qa)

    conn = get_conn()
    try:
        cur = conn.execute(
            "INSERT INTO practice_records "
            "(user_id, position, years_range, salary_tier, source, qa_json, score_json, "
            " total_score, hire_probability, weak_dimension) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                user["id"],
                req.position.strip(),
                req.years_range,
                req.salary_tier,
                source,
                json.dumps(req.qa, ensure_ascii=False),
                json.dumps(scorecard, ensure_ascii=False),
                scorecard["total_score"],
                scorecard["hire_probability"],
                weak,
            ),
        )
        record_id = cur.lastrowid
        conn.commit()
    finally:
        conn.close()

    is_premium = sub.get("status") == "premium"
    if not is_premium:
        scorecard = scoring.simplify(scorecard)

    return {"record_id": record_id, "scorecard": scorecard, "is_premium": is_premium}
