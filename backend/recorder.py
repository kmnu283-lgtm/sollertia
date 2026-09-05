import json, os, time

class Recorder:
    def __init__(self, out_dir="sessions"):
        self.out_dir = out_dir
        os.makedirs(out_dir, exist_ok=True)
        self.events = []
        self.task = None
        self.t0 = time.time()

    def start(self, task):
        self.task = task
        self.t0 = time.time()
        self.events = [{"t": 0.0, "type": "task", "content": task}]

    def log(self, event):
        e = dict(event)
        e["t"] = round(time.time() - self.t0, 2)
        if e.get("type") == "screenshot":
            e["has_shot"] = True
            e.pop("data", None)
        self.events.append(e)

    def save(self):
        path = os.path.join(self.out_dir, "session_%d.json" % int(self.t0))
        with open(path, "w") as f:
            json.dump({"task": self.task, "events": self.events}, f)
        return path

    def to_markdown(self):
        lines = ["# Sollertia Session Report", "", "**Task:** %s" % self.task, ""]
        for e in self.events:
            t = e.get("type")
            if t == "thought": lines.append("> 🧠 %s" % e.get("content",""))
            elif t == "action": lines.append("- 🛠 `%s` %s" % (e.get("action"), json.dumps(e.get("args",{}))))
            elif t == "observation": lines.append("  - 👁 %s" % str(e.get("content",""))[:200])
            elif t == "final": lines.append("\n## ✅ Result\n%s" % e.get("content",""))
            elif t == "error": lines.append("- ⚠ %s" % e.get("content",""))
        return "\n".join(lines)
