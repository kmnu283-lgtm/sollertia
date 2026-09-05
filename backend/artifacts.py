import os, base64, time, json

ART_DIR = os.path.join(os.path.dirname(__file__), "artifacts")
os.makedirs(ART_DIR, exist_ok=True)

class Artifacts:
    def __init__(self):
        self.index = []

    def save_screenshot(self, b64, label="shot"):
        name = f"{label}_{int(time.time()*1000)}.png"
        path = os.path.join(ART_DIR, name)
        with open(path, "wb") as f:
            f.write(base64.b64decode(b64))
        self.index.append({"type":"image","name":name})
        return name

    def save_text(self, text, label="artifact", ext="txt"):
        name = f"{label}_{int(time.time()*1000)}.{ext}"
        path = os.path.join(ART_DIR, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        self.index.append({"type":"text","name":name})
        return name

    def list(self):
        return self.index
