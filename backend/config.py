import os

class Config:
    provider = os.getenv("SOLLERTIA_PROVIDER", "openrouter")
    model = os.getenv("SOLLERTIA_MODEL", "google/gemini-2.5-flash")
    max_steps = int(os.getenv("SOLLERTIA_MAX_STEPS", "30"))
    sandbox_timeout = int(os.getenv("SOLLERTIA_TIMEOUT", "30"))
    require_approval = os.getenv("SOLLERTIA_APPROVAL", "0") == "1"
