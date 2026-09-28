"""Minimal Claude API helper used by the weekly automation."""
import json, os, re, time
import requests

API = "https://api.anthropic.com/v1/messages"
MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5")


def call(system, content, tools=None, max_tokens=6000, max_rounds=4):
    """Send one request; follow `pause_turn` continuations of server tools.
    Returns the list of all content blocks produced by the assistant."""
    key = os.environ["ANTHROPIC_API_KEY"]
    headers = {"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"}
    messages = [{"role": "user", "content": content}]
    blocks = []
    for _ in range(max_rounds):
        body = {"model": MODEL, "max_tokens": max_tokens, "system": system, "messages": messages}
        if tools:
            body["tools"] = tools
        for attempt in range(3):
            r = requests.post(API, headers=headers, json=body, timeout=300)
            if r.status_code in (429, 500, 502, 503, 529):
                time.sleep(20 * (attempt + 1))
                continue
            break
        r.raise_for_status()
        data = r.json()
        blocks += data.get("content", [])
        if data.get("stop_reason") != "pause_turn":
            return blocks
        messages = messages + [{"role": "assistant", "content": data["content"]}]
    return blocks


def final_json(blocks):
    """Return the JSON object contained in the last text blocks."""
    text = "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
    text = re.sub(r"```(?:json)?", "", text)
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < 0:
        raise ValueError("no JSON in the model reply")
    return json.loads(text[start:end + 1])


def searched_urls(blocks):
    """All URLs actually returned by the web search tool."""
    urls = set()
    for b in blocks:
        if b.get("type") == "web_search_tool_result" and isinstance(b.get("content"), list):
            for item in b["content"]:
                if item.get("url"):
                    urls.add(item["url"])
    return urls


def norm(url):
    return re.sub(r"^https?://(www\.)?", "", (url or "").split("#")[0]).rstrip("/").lower()
