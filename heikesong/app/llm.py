"""大模型调用封装（Anthropic 兼容 /v1/messages）与 JSON 容错解析。"""
import json
import re

import httpx

from .config import settings

_TIMEOUT = httpx.Timeout(60.0, connect=10.0)


def _endpoint() -> str:
    """构造 /v1/messages 完整地址，兼容 base_url 是否以 /v1 结尾两种情况。"""
    base = settings.anthropic_base_url.rstrip("/")
    if base.endswith("/v1"):
        return base + "/messages"
    return base + "/v1/messages"


def _headers() -> dict:
    """鉴权头：同时携带 Authorization 与 x-api-key，兼容不同网关。"""
    h = {"Content-Type": "application/json"}
    token = settings.anthropic_auth_token
    if token:
        h["Authorization"] = f"Bearer {token}"
        h["x-api-key"] = token
    return h


def chat(system: str, messages: list, temperature: float = 0.7, max_tokens: int = 2048) -> str:
    """调用大模型，返回文本内容。

    messages: [{"role": "user"/"assistant", "content": str}, ...]
    """
    payload = {
        "model": settings.anthropic_model,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "system": system,
        "messages": messages,
    }
    with httpx.Client(timeout=_TIMEOUT) as client:
        resp = client.post(_endpoint(), headers=_headers(), json=payload)
        resp.raise_for_status()
        data = resp.json()

    # Anthropic 风格返回 content 为数组 [{type:"text", text:"..."}]
    parts = data.get("content", [])
    if isinstance(parts, str):
        return parts.strip()
    text = ""
    for p in parts:
        if isinstance(p, dict) and p.get("type") == "text":
            text += p.get("text", "")
    return text.strip()


def extract_json(text: str):
    """从模型输出中提取 JSON（对象或数组），做容错解析。

    依次尝试：整体解析 -> 去掉 ``` 围栏 -> 花括号/方括号平衡扫描。
    """
    if not text:
        raise ValueError("模型返回为空")

    # 去掉 ```json ... ``` 代码围栏
    fenced = re.search(r"```(?:json)?\s*(\[.*?\]|\{.*?\})\s*```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1)

    # 直接整体解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 分别尝试 { } 与 [ ] 平衡扫描
    for open_ch, close_ch in (("{", "}"), ("[", "]")):
        start = text.find(open_ch)
        if start == -1:
            continue
        depth = 0
        in_str = False
        escape = False
        for i in range(start, len(text)):
            ch = text[i]
            if in_str:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == '"':
                    in_str = False
                continue
            if ch == '"':
                in_str = True
            elif ch == open_ch:
                depth += 1
            elif ch == close_ch:
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start:i + 1])
                    except json.JSONDecodeError:
                        break
    raise ValueError("无法从模型输出解析出 JSON")
