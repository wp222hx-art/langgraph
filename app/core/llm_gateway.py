"""
LLM Gateway —— 多平台统一调用网关
把 TokenHost.cn / DeepSeek / Claude 等平台抽象成一致接口:
  - verify_key()  验证 Key 是否有效(并顺带能拉到模型)
  - list_models() 拉取平台支持的模型列表
  - chat()        统一聊天调用(自动适配 OpenAI 兼容 / Anthropic 协议)

协议适配:
  - kind == "openai_compatible": TokenHost / DeepSeek / OpenAI / 通义 / Kimi 等
        Authorization: Bearer <key>
        POST {base}/chat/completions     GET {base}/models
  - kind == "anthropic": Claude 官方
        x-api-key: <key> + anthropic-version
        POST {base}/v1/messages          (模型列表用内置已知清单)

无 Key / 调用失败 → 抛 GatewayError,上层 Agent 自动回退到规则引擎。
"""
from __future__ import annotations

import json
from typing import Any

import httpx

# ── 内置平台预设(前端"基础配置"下拉直接选) ──
PROVIDER_PRESETS = {
    "tokenhost": {
        "name": "TokenHost.cn", "kind": "openai_compatible",
        "base_url": "https://api.tokenhost.cn/v1",
        "name_en": "TokenHost.cn",
    },
    "deepseek": {
        "name": "DeepSeek", "kind": "openai_compatible",
        "base_url": "https://api.deepseek.com/v1",
        "name_en": "DeepSeek",
    },
    "claude": {
        "name": "Claude (Anthropic)", "kind": "anthropic",
        "base_url": "https://api.anthropic.com",
        "name_en": "Claude (Anthropic)",
    },
    "openai": {
        "name": "OpenAI", "kind": "openai_compatible",
        "base_url": "https://api.openai.com/v1",
        "name_en": "OpenAI",
    },
}

# Anthropic 没有公开 list models 接口,用已知清单
_ANTHROPIC_MODELS = [
    {"model_id": "claude-3-5-sonnet-20241022", "label": "Claude 3.5 Sonnet", "capability": "chat,vision,reasoning"},
    {"model_id": "claude-3-5-haiku-20241022", "label": "Claude 3.5 Haiku", "capability": "chat"},
    {"model_id": "claude-3-opus-20240229", "label": "Claude 3 Opus", "capability": "chat,vision,reasoning"},
]

_TIMEOUT = 30.0


class GatewayError(Exception):
    pass


def _norm_base(base_url: str) -> str:
    return base_url.rstrip("/")


# ═══════════════════════════════════════════════
# 1) 验证 Key
# ═══════════════════════════════════════════════
def verify_key(kind: str, base_url: str, api_key: str) -> dict:
    """返回 {ok, msg, models_count}。验证方式:尝试拉模型/发最小请求。"""
    if not api_key:
        return {"ok": False, "msg": "未提供 API Key", "models_count": 0}
    try:
        if kind == "anthropic":
            # 发一个极小的 messages 请求验证
            r = httpx.post(
                f"{_norm_base(base_url)}/v1/messages",
                headers={"x-api-key": api_key, "anthropic-version": "2023-06-01",
                         "content-type": "application/json"},
                json={"model": _ANTHROPIC_MODELS[0]["model_id"], "max_tokens": 1,
                      "messages": [{"role": "user", "content": "hi"}]},
                timeout=_TIMEOUT,
            )
            if r.status_code in (200, 201):
                return {"ok": True, "msg": "验证通过", "models_count": len(_ANTHROPIC_MODELS)}
            if r.status_code == 401:
                return {"ok": False, "msg": "Key 无效(401)", "models_count": 0}
            # 400 但能到达鉴权(部分模型不可用)也算 Key 有效
            if r.status_code == 400 and "authentication" not in r.text.lower():
                return {"ok": True, "msg": "验证通过(鉴权有效)", "models_count": len(_ANTHROPIC_MODELS)}
            return {"ok": False, "msg": f"验证失败 HTTP {r.status_code}: {r.text[:120]}", "models_count": 0}
        else:
            r = httpx.get(
                f"{_norm_base(base_url)}/models",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=_TIMEOUT,
            )
            if r.status_code == 200:
                data = r.json()
                models = data.get("data", data) if isinstance(data, dict) else data
                cnt = len(models) if isinstance(models, list) else 0
                return {"ok": True, "msg": "验证通过", "models_count": cnt}
            if r.status_code == 401:
                return {"ok": False, "msg": "Key 无效(401)", "models_count": 0}
            return {"ok": False, "msg": f"验证失败 HTTP {r.status_code}: {r.text[:120]}", "models_count": 0}
    except httpx.ConnectError:
        return {"ok": False, "msg": f"无法连接 {base_url}(网络/地址错误)", "models_count": 0}
    except Exception as e:
        return {"ok": False, "msg": f"验证异常: {e}", "models_count": 0}


# ═══════════════════════════════════════════════
# 2) 拉取模型列表
# ═══════════════════════════════════════════════
def list_models(kind: str, base_url: str, api_key: str) -> list[dict]:
    """返回 [{model_id, label, capability}, ...]"""
    if kind == "anthropic":
        return list(_ANTHROPIC_MODELS)
    try:
        r = httpx.get(
            f"{_norm_base(base_url)}/models",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=_TIMEOUT,
        )
        if r.status_code != 200:
            raise GatewayError(f"拉取模型失败 HTTP {r.status_code}: {r.text[:120]}")
        data = r.json()
        raw = data.get("data", data) if isinstance(data, dict) else data
        out = []
        for m in raw:
            mid = m.get("id") if isinstance(m, dict) else str(m)
            if not mid:
                continue
            cap = "chat"
            low = mid.lower()
            if any(k in low for k in ("vision", "-v", "vl", "4o", "gpt-4")):
                cap = "chat,vision"
            if any(k in low for k in ("reason", "o1", "r1", "think")):
                cap = "chat,reasoning"
            out.append({"model_id": mid, "label": mid, "capability": cap})
        return out
    except GatewayError:
        raise
    except Exception as e:
        raise GatewayError(f"拉取模型异常: {e}")


# ═══════════════════════════════════════════════
# 3) 统一聊天调用
# ═══════════════════════════════════════════════
def chat(cfg: dict, messages: list[dict], temperature: float = 0.3,
         max_tokens: int = 1024, json_mode: bool = False) -> str:
    """
    cfg 来自 db.resolve_binding():{kind, base_url, api_key, model_id}
    返回模型生成的纯文本。失败抛 GatewayError(上层回退规则)。
    """
    kind = cfg.get("kind", "openai_compatible")
    base_url = _norm_base(cfg.get("base_url", ""))
    api_key = cfg.get("api_key", "")
    model = cfg.get("model_id")
    if not api_key or not model:
        raise GatewayError("未配置可用的 Key 或模型")

    try:
        if kind == "anthropic":
            sys_txt = "".join(m["content"] for m in messages if m["role"] == "system")
            conv = [m for m in messages if m["role"] != "system"]
            payload: dict[str, Any] = {
                "model": model, "max_tokens": max_tokens,
                "messages": conv or [{"role": "user", "content": " "}],
            }
            if sys_txt:
                payload["system"] = sys_txt
            r = httpx.post(
                f"{base_url}/v1/messages",
                headers={"x-api-key": api_key, "anthropic-version": "2023-06-01",
                         "content-type": "application/json"},
                json=payload, timeout=_TIMEOUT,
            )
            if r.status_code not in (200, 201):
                raise GatewayError(f"Claude 调用失败 HTTP {r.status_code}: {r.text[:160]}")
            data = r.json()
            parts = data.get("content", [])
            return "".join(p.get("text", "") for p in parts if p.get("type") == "text")
        else:
            payload = {"model": model, "messages": messages,
                       "temperature": temperature, "max_tokens": max_tokens}
            if json_mode:
                payload["response_format"] = {"type": "json_object"}
            r = httpx.post(
                f"{base_url}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}",
                         "Content-Type": "application/json"},
                json=payload, timeout=_TIMEOUT,
            )
            if r.status_code != 200:
                raise GatewayError(f"调用失败 HTTP {r.status_code}: {r.text[:160]}")
            data = r.json()
            return data["choices"][0]["message"]["content"]
    except GatewayError:
        raise
    except Exception as e:
        raise GatewayError(f"调用异常: {e}")


def chat_json(cfg: dict, system: str, user: str, temperature: float = 0.1) -> dict:
    """要求模型返回 JSON 并解析。失败抛 GatewayError。"""
    msgs = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    txt = chat(cfg, msgs, temperature=temperature, json_mode=True, max_tokens=512)
    return _parse_json(txt)


def _parse_json(txt: str) -> dict:
    """从模型回复中稳健解析 JSON(去 ```json 包裹 / 截取第一个 {...})。"""
    txt = (txt or "").strip()
    if txt.startswith("```"):
        txt = txt.split("```")[1] if "```" in txt[3:] else txt.strip("`")
        txt = txt.replace("json", "", 1).strip() if txt.lower().startswith("json") else txt
    try:
        return json.loads(txt)
    except Exception:
        import re
        m = re.search(r"\{.*\}", txt, re.S)
        if m:
            return json.loads(m.group(0))
        raise GatewayError(f"返回非合法 JSON: {txt[:120]}")


# ═══════════════════════════════════════════════
# 4) 多模态发票识别(Vision OCR)
# ═══════════════════════════════════════════════
_OCR_SYS = (
    "你是专业的发票/票据 OCR 识别引擎。仔细阅读图片中的发票或收据,"
    "提取关键字段并只输出 JSON,不要任何解释文字。\n"
    'JSON 格式:{"merchant":"商户名称","category":"费用类别(餐饮/交通/住宿/办公/差旅/其他)",'
    '"amount":数字金额,"currency":"币种代码如CNY/SGD/USD","date":"YYYY-MM-DD",'
    '"tax_no":"发票号或税号(无则空字符串)"}\n'
    "金额只填数字(不带符号);识别不到的字段填空字符串或0。"
)


def vision_ocr(cfg: dict, image_b64: str, mime: str = "image/jpeg") -> dict:
    """
    多模态识票:传入 base64 图片(不含 data: 前缀),返回结构化票据 dict。
    cfg 来自 db.resolve_binding():{kind, base_url, api_key, model_id}
    失败抛 GatewayError(上层回退到 NL 抽取 / 示例 OCR)。
    """
    kind = cfg.get("kind", "openai_compatible")
    base_url = _norm_base(cfg.get("base_url", ""))
    api_key = cfg.get("api_key", "")
    model = cfg.get("model_id")
    if not api_key or not model:
        raise GatewayError("未配置可用的 Key 或模型")
    # 去掉可能携带的 data:image/...;base64, 前缀
    if "," in image_b64 and image_b64.strip().startswith("data:"):
        image_b64 = image_b64.split(",", 1)[1]

    try:
        if kind == "anthropic":
            payload = {
                "model": model, "max_tokens": 512,
                "system": _OCR_SYS,
                "messages": [{"role": "user", "content": [
                    {"type": "image", "source": {"type": "base64",
                                                  "media_type": mime, "data": image_b64}},
                    {"type": "text", "text": "识别这张票据,只输出 JSON。"},
                ]}],
            }
            r = httpx.post(
                f"{base_url}/v1/messages",
                headers={"x-api-key": api_key, "anthropic-version": "2023-06-01",
                         "content-type": "application/json"},
                json=payload, timeout=_TIMEOUT,
            )
            if r.status_code not in (200, 201):
                raise GatewayError(f"Claude Vision 失败 HTTP {r.status_code}: {r.text[:160]}")
            data = r.json()
            parts = data.get("content", [])
            txt = "".join(p.get("text", "") for p in parts if p.get("type") == "text")
        else:
            payload = {
                "model": model, "max_tokens": 512, "temperature": 0.1,
                "messages": [
                    {"role": "system", "content": _OCR_SYS},
                    {"role": "user", "content": [
                        {"type": "text", "text": "识别这张票据,只输出 JSON。"},
                        {"type": "image_url",
                         "image_url": {"url": f"data:{mime};base64,{image_b64}"}},
                    ]},
                ],
            }
            r = httpx.post(
                f"{base_url}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}",
                         "Content-Type": "application/json"},
                json=payload, timeout=_TIMEOUT,
            )
            if r.status_code != 200:
                raise GatewayError(f"Vision 调用失败 HTTP {r.status_code}: {r.text[:160]}")
            data = r.json()
            txt = data["choices"][0]["message"]["content"]
        return _parse_json(txt)
    except GatewayError:
        raise
    except Exception as e:
        raise GatewayError(f"Vision OCR 异常: {e}")
