"""Pydantic 请求模型（响应大多直接返回 dict，不单独建模）。"""
from typing import List, Optional

from pydantic import BaseModel


class RegisterRequest(BaseModel):
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class GenerateRequest(BaseModel):
    """出题请求。years_range: 0-1 / 1-3 / 3-5；salary_tier: low / mid / high。"""
    position: str
    years_range: str = "0-1"
    salary_tier: str = "mid"
    job_desc: Optional[str] = None
    count: int = 3


class FollowupRequest(BaseModel):
    """追问请求（追问式多轮问答）。"""
    position: str
    years_range: str = "0-1"
    salary_tier: str = "mid"
    question: str
    answer: str


class ScoreRequest(BaseModel):
    """评分请求。qa 为 [{question, answer, source}]。"""
    position: str
    years_range: str = "0-1"
    salary_tier: str = "mid"
    qa: List[dict]
