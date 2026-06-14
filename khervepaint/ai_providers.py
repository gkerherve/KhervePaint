"""AI provider registry — chat + model listing over plain urllib.

Five back-ends share one interface so the assistant panel can switch
freely and a single Refresh button can list each one's models:

* **Claude** (Anthropic Messages API)
* **ChatGPT** (OpenAI), **Mistral**, and **Local** — OpenAI-compatible
* **Ollama** (local, no key)

Only the standard library is used (urllib + json), so there are no new
dependencies. Network calls are blocking; callers run them off the UI
thread (see ai_assistant.py).

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import json
import urllib.request

ANTHROPIC_VERSION = "2023-06-01"

#: provider -> default base URL.
DEFAULT_BASE = {
    "Claude": "https://api.anthropic.com",
    "ChatGPT": "https://api.openai.com",
    "Mistral": "https://api.mistral.ai",
    "Ollama": "http://localhost:11434",
    "Local": "http://localhost:1234",
}

#: providers that require an API key.
NEEDS_KEY = {"Claude", "ChatGPT", "Mistral"}

#: OpenAI-compatible chat/models providers.
_OPENAI_LIKE = {"ChatGPT", "Mistral", "Local"}

PROVIDERS = list(DEFAULT_BASE)

#: A few sensible defaults so the model box is never empty; use Refresh
#: to pull the live list from the provider.
DEFAULT_MODELS = {
    "Claude": ["claude-opus-4-8", "claude-sonnet-4-6",
               "claude-haiku-4-5-20251001"],
    "ChatGPT": ["gpt-4o", "gpt-4o-mini"],
    "Mistral": ["mistral-large-latest", "mistral-small-latest"],
    "Ollama": [],
    "Local": [],
}


def _base(provider, base_url=""):
    return (base_url or DEFAULT_BASE[provider]).rstrip("/")


def _post(url, body, headers, timeout=90):
    req = urllib.request.Request(
        url, data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers},
        method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _get(url, headers, timeout=30):
    req = urllib.request.Request(url, headers=headers, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def chat(provider, model, messages, api_key="", base_url=""):
    """Send *messages* ([{role, content}, …]) and return the reply text."""
    if provider in _OPENAI_LIKE:
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        data = _post(f"{_base(provider, base_url)}/v1/chat/completions",
                     {"model": model, "messages": messages}, headers)
        return data["choices"][0]["message"]["content"]

    if provider == "Claude":
        system = "\n\n".join(m["content"] for m in messages
                             if m["role"] == "system")
        convo = [m for m in messages if m["role"] != "system"]
        body = {"model": model, "max_tokens": 2048, "messages": convo}
        if system:
            body["system"] = system
        data = _post(f"{_base('Claude', base_url)}/v1/messages", body,
                     {"x-api-key": api_key,
                      "anthropic-version": ANTHROPIC_VERSION})
        return "".join(b.get("text", "") for b in data.get("content", [])
                       if b.get("type") == "text")

    if provider == "Ollama":
        data = _post(f"{_base('Ollama', base_url)}/api/chat",
                     {"model": model, "messages": messages, "stream": False},
                     {})
        return data["message"]["content"]

    raise ValueError(f"unknown provider: {provider}")


def list_models(provider, api_key="", base_url=""):
    """Return the available model ids for *provider* (sorted)."""
    if provider in _OPENAI_LIKE:
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        data = _get(f"{_base(provider, base_url)}/v1/models", headers)
        return sorted(m["id"] for m in data.get("data", []) if m.get("id"))

    if provider == "Claude":
        data = _get(f"{_base('Claude', base_url)}/v1/models",
                    {"x-api-key": api_key,
                     "anthropic-version": ANTHROPIC_VERSION})
        return sorted(m["id"] for m in data.get("data", []) if m.get("id"))

    if provider == "Ollama":
        data = _get(f"{_base('Ollama', base_url)}/api/tags", {})
        return sorted(m["name"] for m in data.get("models", []))

    raise ValueError(f"unknown provider: {provider}")
