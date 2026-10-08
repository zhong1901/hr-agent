"""出题：题库优先 + AI 兜底两级策略。"""
import random

from . import llm
from .database import get_conn

YEARS_LABELS = {"0-1": "0-1 年", "1-3": "1-3 年", "3-5": "3-5 年"}
SALARY_LABELS = {"low": "基础/初级", "mid": "中级", "high": "高级/资深"}


def generate_questions(position: str, years_range: str, salary_tier: str, job_desc, count: int) -> dict:
    """两级策略出题，返回 {questions, notice, source}。

    题库命中优先；题库不足则 AI 补齐；完全没有则 AI 生成并返回显眼提示语。
    """
    bank_qs = _pick_from_bank(position, years_range, salary_tier, count)
    if len(bank_qs) >= count:
        return {"questions": bank_qs[:count], "notice": None, "source": "题库"}

    ai_qs = _generate_by_ai(position, years_range, salary_tier, job_desc, count - len(bank_qs))
    questions = bank_qs + ai_qs

    if not bank_qs:
        notice = "该岗位暂无预设题库，以下题目由 AI 为您即时生成"
        source = "AI"
    else:
        notice = "部分题目来自预设题库，其余由 AI 即时补充"
        source = "混合"
    return {"questions": questions, "notice": notice, "source": source}


def _pick_from_bank(position: str, years_range: str, salary_tier: str, count: int) -> list:
    """按岗位 + 年限 + 薪资检索题库；放宽到仅岗位匹配。"""
    conn = get_conn()
    try:
        rows = _query_bank(conn, position, years_range, salary_tier)
        if not rows:
            rows = _query_bank(conn, position, None, None)
    finally:
        conn.close()

    rows = list(rows)
    picked = random.sample(rows, min(count, len(rows))) if rows else []
    return [
        {"id": r["id"], "question": r["question"], "source": "题库", "analysis": r["analysis"]}
        for r in picked
    ]


def _query_bank(conn, position: str, years_range, salary_tier):
    sql = "SELECT * FROM question_bank WHERE position = ?"
    args = [position]
    if years_range:
        sql += " AND (years_range = ? OR years_range = 'all')"
        args.append(years_range)
    if salary_tier:
        sql += " AND (salary_tier = ? OR salary_tier = 'all')"
        args.append(salary_tier)
    sql += " ORDER BY difficulty ASC, id ASC"
    return conn.execute(sql, args).fetchall()


def _generate_by_ai(position: str, years_range: str, salary_tier: str, job_desc, count: int) -> list:
    """大模型即时生成题目，返回 source='AI' 的题目列表。"""
    system = "你是一名资深 HR 面试官，擅长为不同岗位设计专业、有区分度的面试题。"
    desc = f"岗位职责：{job_desc}" if job_desc else "无额外职责描述，请按通用岗位要求出题。"
    user = f"""请为「{position}」岗位生成 {count} 道面试题。
候选人工作年限：{YEARS_LABELS.get(years_range, years_range)}
期望薪资档：{SALARY_LABELS.get(salary_tier, salary_tier)}
{desc}

要求：
1. 题目贴合该岗位实际，难度与年限匹配，避免假大空。
2. 每道题附带一句简短的考察点说明。

严格返回 JSON 数组，不要输出多余文字：
[{{"question": "...", "focus": "..."}}, ...]
"""
    raw = llm.chat(system, [{"role": "user", "content": user}], temperature=0.8)
    data = llm.extract_json(raw)
    if isinstance(data, dict):
        data = data.get("questions") or data.get("data") or []
    if not isinstance(data, list):
        data = []

    result = []
    for item in data:
        q = item.get("question") if isinstance(item, dict) else str(item)
        if q:
            result.append({"id": None, "question": q, "source": "AI", "analysis": None})
    return result[:count]


def generate_followup(position: str, question: str, answer: str, years_range: str, salary_tier: str) -> str:
    """基于候选人回答生成一道追问（追问式多轮问答）。"""
    system = "你是一名资深面试官，会根据候选人回答进行追问式提问，考察其真实水平。"
    user = f"""岗位：{position}（年限：{years_range}，薪资档：{salary_tier}）
面试题：{question}
候选人回答：{answer}

请基于该回答追问一道更深入的面试题，只返回问题本身，不要多余文字。"""
    return llm.chat(system, [{"role": "user", "content": user}], temperature=0.8, max_tokens=512)
