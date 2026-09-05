import time

PRICING = {
    "google/gemini-2.5-flash": (0.30, 2.50),
    "anthropic/claude-3.5-sonnet": (3.00, 15.00),
    "openai/gpt-4o": (2.50, 10.00),
    "openai/gpt-4o-mini": (0.15, 0.60),
}

class CostTracker:
    def __init__(self, model):
        self.model = model
        self.in_tok = 0
        self.out_tok = 0
        self.start = time.time()

    def add(self, usage):
        self.in_tok += usage.get("prompt_tokens", 0)
        self.out_tok += usage.get("completion_tokens", 0)

    def usd(self):
        pi, po = PRICING.get(self.model, (1.0, 3.0))
        return self.in_tok / 1e6 * pi + self.out_tok / 1e6 * po

    def summary(self):
        return {"model": self.model, "input_tokens": self.in_tok, "output_tokens": self.out_tok, "usd": round(self.usd(), 4), "seconds": round(time.time() - self.start, 1)}
