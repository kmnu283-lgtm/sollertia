import httpx
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

class LLM:
    def __init__(self, provider, api_key, model):
        self.provider = provider.lower()
        self.api_key = api_key
        self.model = model
        self.last_usage = {}

    async def chat(self, messages, tools=None):
        if self.provider == "openrouter":
            return await self._openrouter(messages, tools)
        if self.provider == "gemini":
            return await self._gemini(messages)
        raise ValueError(f"Unknown provider: {self.provider}")

    async def _openrouter(self, messages, tools=None):
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:8000",
            "X-Title": "Sollertia",
        }
        payload = {"model": self.model, "messages": messages}
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        async with httpx.AsyncClient(timeout=180) as c:
            r = await c.post(OPENROUTER_URL, headers=headers, json=payload)
            r.raise_for_status()
            data = r.json()
            self.last_usage = data.get("usage", {})
            return data["choices"][0]["message"]

    async def _gemini(self, messages):
        url = GEMINI_URL.format(model=self.model)
        contents = []
        for m in messages:
            role = "user" if m["role"] in ("user", "tool") else "model"
            contents.append({"role": role, "parts": [{"text": str(m.get("content", ""))}]})
        async with httpx.AsyncClient(timeout=180) as c:
            r = await c.post(url, headers={"x-goog-api-key": self.api_key}, json={"contents": contents})
            r.raise_for_status()
            text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
            return {"role": "assistant", "content": text}
