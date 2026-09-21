"""
唯一负责与大模型对话的文件（OpenAI 兼容接口）。

V2.07：
- chat_backend = local | cloud
- local：LM Studio（默认 http://localhost:1234/v1）
- cloud：任意 OpenAI 兼容端点（base_url + api_key + model）
- Embedding 仍由调用方使用本地 llm_base_url，不走 cloud 配置

关闭「本地对话模型」= chat 改走 cloud，不关闭 LM Studio（检索仍可能需要 Embedding）。
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional, Tuple

import requests

DEFAULT_BASE_URL = "http://localhost:1234/v1"
DEFAULT_MODEL = "auto"
TIMEOUT_SECONDS = 1800

_SETTINGS_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "settings.json")


def _load_settings() -> Dict[str, Any]:
    try:
        if os.path.isfile(_SETTINGS_PATH):
            with open(_SETTINGS_PATH, "r", encoding="utf-8") as f:
                return json.load(f) or {}
    except Exception:
        pass
    return {}


def get_local_base_url(settings: Optional[Dict[str, Any]] = None) -> str:
    data = settings if settings is not None else _load_settings()
    return (data.get("llm_base_url") or DEFAULT_BASE_URL).rstrip("/")


def _normalize_openai_base(url: str) -> str:
    u = (url or "").strip().rstrip("/")
    if not u:
        return ""
    low = u.lower()
    if "console.groq.com" in low:
        return "https://api.groq.com/openai/v1"
    if u.endswith("/V1"):
        u = u[:-3] + "/v1"
    return u


def resolve_chat_config(settings: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    data = settings if settings is not None else _load_settings()
    local_url = (data.get("llm_base_url") or DEFAULT_BASE_URL).rstrip("/")
    backend = (data.get("chat_backend") or "local").strip().lower()
    local_enabled = data.get("local_chat_enabled", True)
    if isinstance(local_enabled, str):
        local_enabled = local_enabled.strip().lower() not in ("0", "false", "no", "off")

    if not local_enabled:
        backend = "cloud"

    if backend == "cloud":
        cloud_url = _normalize_openai_base(data.get("cloud_base_url") or "")
        cloud_model = (data.get("cloud_model") or "").strip() or "gpt-4o-mini"
        cloud_key = (data.get("cloud_api_key") or "").strip()
        return {
            "backend": "cloud",
            "base_url": cloud_url or local_url,
            "model": cloud_model,
            "api_key": cloud_key,
            "local_chat_enabled": bool(local_enabled),
            "configured": bool(cloud_url),
        }

    return {
        "backend": "local",
        "base_url": local_url,
        "model": data.get("llm_model") or DEFAULT_MODEL,
        "api_key": "",
        "local_chat_enabled": True,
        "configured": True,
    }


def _pick_chat_model(base_url: str) -> Optional[str]:
    try:
        online, models = check_connection(base_url)
        if not online:
            return None
        chat = [m for m in models if "embed" not in m.lower()]
        return chat[0] if chat else None
    except Exception:
        return None


def ask(
    messages,
    base_url=None,
    model=None,
    temperature=0.7,
    max_tokens=2000,
    api_key: Optional[str] = None,
    use_settings: bool = True,
):
    cfg = None
    if use_settings and (base_url is None or model is None):
        cfg = resolve_chat_config()
        if base_url is None:
            base_url = cfg["base_url"]
        if model is None:
            model = cfg["model"]
        if api_key is None:
            api_key = cfg.get("api_key") or ""
    elif api_key is None and use_settings:
        cfg = resolve_chat_config()
        api_key = cfg.get("api_key") or ""

    base_url = (base_url or DEFAULT_BASE_URL).rstrip("/")
    if cfg and cfg.get("backend") == "cloud" and not cfg.get("configured"):
        return (
            False,
            "已关闭本地对话或已选择云端生成，但未配置 cloud_base_url。"
            "请在设置中填写云端 API 地址（OpenAI 兼容），或重新开启本地对话模型。",
        )

    url = f"{base_url}/chat/completions"

    if not model or model in ("auto", "local-model", "default"):
        if not (api_key or "").strip():
            picked = _pick_chat_model(base_url)
            model = picked if picked else "local-model"
        else:
            model = "gpt-4o-mini"

    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    headers = {"Content-Type": "application/json"}
    if (api_key or "").strip():
        headers["Authorization"] = f"Bearer {api_key.strip()}"

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=TIMEOUT_SECONDS)
        if resp.status_code >= 400:
            body = (resp.text or "")[:800]
            try:
                from office.context_budget import learn_n_ctx_from_error
                learn_n_ctx_from_error(body)
            except Exception:
                pass
            hint = ""
            low = body.lower()
            if resp.status_code == 400:
                if "context" in low or "length" in low or "n_ctx" in low or "token" in low:
                    hint = "（多为上下文过长；请降低知识库预算）"
                elif "model" in low:
                    hint = "（请确认对话模型名称正确）"
            if resp.status_code in (401, 403):
                hint = "（鉴权失败：请检查 cloud_api_key）"
            return False, f"大模型 HTTP {resp.status_code}{hint}：{body or resp.reason}"
        data = resp.json()
        choice0 = (data.get("choices") or [{}])[0]
        content = (choice0.get("message") or {}).get("content") or ""
        finish = choice0.get("finish_reason") or choice0.get("finishReason") or ""
        usage = data.get("usage") or {}
        try:
            from office.monitor import log as _log
            _log.info(
                "LLM finish_reason=%s completion_chars=%s usage=%s backend=%s"
                % (finish or "?", len(content or ""), usage, (cfg or {}).get("backend", "?"))
            )
            if str(finish).lower() in ("length", "max_tokens", "length_cutoff"):
                _log.warning(
                    "生成因长度限制结束（finish_reason=%s, chars=%s）；"
                    "可提高 cloud_max_tokens（默认 8192）"
                    % (finish, len(content or ""))
                )
        except Exception:
            pass
        if not str(content).strip():
            return False, "模型返回空内容（请换模型或检查推理设置）"
        return True, content
    except requests.exceptions.ConnectionError:
        if (api_key or "").strip():
            return False, f"无法连接到云端 API：{base_url}。请检查网络与 cloud_base_url。"
        return False, "无法连接到 LM Studio，请确认已启动并开启 Local Server（Embedding/本地对话需要）。"
    except requests.exceptions.Timeout:
        return False, "请求超时，请稍后重试或减少知识库范围。"
    except Exception as e:
        return False, f"调用大模型时出现问题：{e}"


def test_cloud_connection(base_url: str, api_key: str = "", model: str = "") -> tuple:
    """探测 OpenAI 兼容云端：优先 GET /models，失败则试一次最小 chat。返回 (ok, message)。"""
    url = _normalize_openai_base(base_url or "")
    if not url:
        return False, "base_url 为空"
    headers = {"Content-Type": "application/json"}
    if (api_key or "").strip():
        headers["Authorization"] = f"Bearer {api_key.strip()}"
    models_err = ""
    try:
        r = requests.get(f"{url}/models", headers=headers, timeout=20)
        if r.status_code == 200:
            data = r.json() if r.content else {}
            ids = []
            for m in (data.get("data") or [])[:12]:
                mid = m.get("id") if isinstance(m, dict) else str(m)
                if mid:
                    ids.append(mid)
            preview = "、".join(ids[:8]) if ids else "（未列出模型 id）"
            return True, f"GET /models 成功；示例：{preview}"
        if r.status_code in (401, 403):
            return False, f"鉴权失败 HTTP {r.status_code}（请检查 api_key）"
        models_err = f"GET /models → HTTP {r.status_code}"
    except requests.exceptions.Timeout:
        return False, "连接超时（请检查网络或 base_url）"
    except requests.exceptions.ConnectionError as e:
        return False, f"无法连接：{e}"
    except Exception as e:
        models_err = str(e)
    m = (model or "").strip() or "gpt-4o-mini"
    try:
        payload = {
            "model": m,
            "messages": [{"role": "user", "content": "ping"}],
            "max_tokens": 8,
        }
        r = requests.post(f"{url}/chat/completions", headers=headers, json=payload, timeout=45)
        if r.status_code == 200:
            return True, f"chat/completions 成功（model={m}）"
        body = (r.text or "")[:200]
        if r.status_code in (401, 403):
            return False, f"鉴权失败 HTTP {r.status_code}：{body}"
        return False, f"HTTP {r.status_code}：{body}；{models_err}"
    except Exception as e:
        return False, f"chat 探测失败：{e}"


def check_connection(base_url=DEFAULT_BASE_URL) -> Tuple[bool, List[str]]:
    try:
        resp = requests.get(f"{base_url.rstrip('/')}/models", timeout=5)
        resp.raise_for_status()
        data = resp.json()
        model_ids = [m.get("id", "") for m in data.get("data", [])]
        return True, model_ids
    except Exception:
        return False, []
