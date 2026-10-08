"""评分卡：调用大模型做四维度评分，并做字段规范化与薄弱维度识别。"""
import json

from . import llm

DIMENSION_NAMES = {
    "communication": "沟通表达",
    "professional_fit": "岗位专业匹配",
    "experience_fit": "经验匹配",
    "adaptability": "应变能力",
}

SYSTEM_PROMPT = (
    "你是一名资深面试官，负责对求职者的模拟面试作答进行客观、专业的评分。"
    "请严格按用户要求的结构返回 JSON，不要输出任何多余文字。"
)


def score_interview(position: str, years_range: str, salary_tier: str, qa: list) -> dict:
    """调用大模型输出评分卡并规范化。"""
    qa_text = "\n\n".join(f"【问题】{q['question']}\n【回答】{q.get('answer', '')}" for q in qa)
    user_msg = f"""目标岗位：{position}
工作年限档：{years_range}
期望薪资档：{salary_tier}

以下是候选人的模拟面试问答：
{qa_text}

请给出评分卡，严格返回如下 JSON（不要有多余文字）：
{{
  "dimensions": {{
    "communication": {{"score": 1-5, "comment": "评语"}},
    "professional_fit": {{"score": 1-5, "comment": "评语"}},
    "experience_fit": {{"score": 1-5, "comment": "评语"}},
    "adaptability": {{"score": 1-5, "comment": "评语"}}
  }},
  "total_score": 1-20,
  "hire_probability": 0-100,
  "summary": "总评",
  "suggestions": ["改进建议1", "改进建议2"]
}}
"""
    raw = llm.chat(SYSTEM_PROMPT, [{"role": "user", "content": user_msg}], temperature=0.4)
    data = llm.extract_json(raw)
    return normalize_scorecard(data)


def normalize_scorecard(data: dict) -> dict:
    """规范化评分卡字段：补齐缺省、约束取值范围，保证前端稳定可用。"""
    dims_raw = data.get("dimensions") or {}
    dims = {}
    for key in DIMENSION_NAMES:
        d = dims_raw.get(key) or {}
        score = _clamp(int(d.get("score", 3)), 1, 5)
        dims[key] = {"score": score, "comment": str(d.get("comment", ""))}

    total = _clamp(int(data.get("total_score", sum(x["score"] for x in dims.values()))), 1, 20)
    hire = _clamp(int(data.get("hire_probability", 50)), 0, 100)
    summary = str(data.get("summary", ""))

    suggestions = data.get("suggestions") or []
    if not isinstance(suggestions, list):
        suggestions = [str(suggestions)]
    suggestions = [str(s) for s in suggestions if str(s).strip()][:5]

    return {
        "dimensions": dims,
        "total_score": total,
        "hire_probability": hire,
        "summary": summary,
        "suggestions": suggestions,
    }


def weak_dimension(scorecard: dict) -> str:
    """识别薄弱维度（四维中分数最低者）。"""
    dims = scorecard.get("dimensions") or {}
    if not dims:
        return ""
    lowest = min(dims.items(), key=lambda kv: kv[1]["score"])
    return DIMENSION_NAMES.get(lowest[0], lowest[0])


def classify_source(qa: list) -> str:
    """汇总题目来源：题库 / AI / 混合。"""
    sources = {q.get("source") for q in qa if q.get("source")}
    if len(sources) <= 1:
        return (sources or {"AI"}).pop()
    return "混合"


def simplify(scorecard: dict) -> dict:
    """免费用户简化版评分卡：保留分数与总评，隐藏详细建议与深度解析。"""
    sc = json.loads(json.dumps(scorecard, ensure_ascii=False))
    sc["suggestions"] = []
    sc["locked"] = "订阅后解锁详细改进建议与 AI 深度解析"
    return sc


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))
