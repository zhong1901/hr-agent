"""认证：注册 / 登录（邮箱 + 密码，会话 token）。"""
import re

from fastapi import APIRouter, HTTPException

from ..database import get_conn
from ..models import LoginRequest, RegisterRequest
from ..security import hash_password, new_token, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@router.post("/register")
def register(req: RegisterRequest):
    email = req.email.strip().lower()
    if not EMAIL_RE.match(email):
        raise HTTPException(status_code=400, detail="邮箱格式不正确")
    if len(req.password) < 6:
        raise HTTPException(status_code=400, detail="密码至少 6 位")

    conn = get_conn()
    try:
        if conn.execute("SELECT 1 FROM users WHERE email=?", (email,)).fetchone():
            raise HTTPException(status_code=409, detail="该邮箱已注册")
        cur = conn.execute(
            "INSERT INTO users (email, password_hash) VALUES (?, ?)",
            (email, hash_password(req.password)),
        )
        conn.commit()
        user_id = cur.lastrowid
    finally:
        conn.close()

    token = _create_session(user_id)
    return {"token": token, "email": email}


@router.post("/login")
def login(req: LoginRequest):
    email = req.email.strip().lower()
    conn = get_conn()
    try:
        row = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
    finally:
        conn.close()

    if row is None or not verify_password(req.password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="邮箱或密码错误")

    token = _create_session(row["id"])
    return {"token": token, "email": email}


def _create_session(user_id: int) -> str:
    token = new_token()
    conn = get_conn()
    try:
        conn.execute("INSERT INTO sessions (token, user_id) VALUES (?, ?)", (token, user_id))
        conn.commit()
    finally:
        conn.close()
    return token
