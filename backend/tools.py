import os, subprocess, asyncio, tempfile, re

SANDBOX_DIR = os.path.join(tempfile.gettempdir(), "sollertia_workspace")
os.makedirs(SANDBOX_DIR, exist_ok=True)

def _safe_path(path):
    full = os.path.realpath(os.path.join(SANDBOX_DIR, path))
    if not full.startswith(os.path.realpath(SANDBOX_DIR)):
        raise ValueError("Path escapes sandbox")
    return full

async def file_read(path):
    try:
        with open(_safe_path(path), "r", encoding="utf-8", errors="replace") as f:
            c = f.read()
        return {"path": path, "content": c[:5000], "size": len(c)}
    except Exception as e:
        return {"error": str(e)}

async def file_write(path, content):
    try:
        full = _safe_path(path)
        os.makedirs(os.path.dirname(full) or SANDBOX_DIR, exist_ok=True)
        with open(full, "w", encoding="utf-8") as f:
            f.write(content)
        return {"path": path, "written": len(content)}
    except Exception as e:
        return {"error": str(e)}

async def file_list(path="."):
    try:
        full = _safe_path(path)
        entries = []
        for n in sorted(os.listdir(full))[:100]:
            fp = os.path.join(full, n)
            entries.append({"name": n, "type": "dir" if os.path.isdir(fp) else "file",
                            "size": os.path.getsize(fp) if os.path.isfile(fp) else 0})
        return {"path": path, "entries": entries}
    except Exception as e:
        return {"error": str(e)}

async def run_python(code, timeout=30):
    try:
        def _run():
            return subprocess.run(["python", "-c", code], capture_output=True, text=True,
                                  timeout=timeout, cwd=SANDBOX_DIR)
        r = await asyncio.get_event_loop().run_in_executor(None, _run)
        return {"stdout": r.stdout[:3000], "stderr": r.stderr[:3000], "returncode": r.returncode}
    except subprocess.TimeoutExpired:
        return {"error": "Timed out"}
    except Exception as e:
        return {"error": str(e)}

async def run_shell(command, timeout=30):
    try:
        def _run():
            return subprocess.run(command, shell=True, capture_output=True, text=True,
                                  timeout=timeout, cwd=SANDBOX_DIR)
        r = await asyncio.get_event_loop().run_in_executor(None, _run)
        return {"stdout": r.stdout[:3000], "stderr": r.stderr[:3000], "returncode": r.returncode}
    except subprocess.TimeoutExpired:
        return {"error": "Timed out"}
    except Exception as e:
        return {"error": str(e)}

async def web_search(query):
    try:
        import httpx
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as c:
            r = await c.get("https://html.duckduckgo.com/html/", params={"q": query},
                            headers={"User-Agent": "Mozilla/5.0"})
        links = re.findall(r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', r.text)
        results = [{"url": u, "title": re.sub(r"<[^>]+>", "", t)} for u, t in links[:8]]
        return {"query": query, "results": results}
    except Exception as e:
        return {"error": str(e)}

TOOL_SCHEMAS = [
    {"type":"function","function":{"name":"file_read","description":"Read a file in the workspace sandbox","parameters":{"type":"object","properties":{"path":{"type":"string"}},"required":["path"]}}},
    {"type":"function","function":{"name":"file_write","description":"Write a file in the workspace sandbox","parameters":{"type":"object","properties":{"path":{"type":"string"},"content":{"type":"string"}},"required":["path","content"]}}},
    {"type":"function","function":{"name":"file_list","description":"List files in the workspace sandbox","parameters":{"type":"object","properties":{"path":{"type":"string"}},"required":[]}}},
    {"type":"function","function":{"name":"run_python","description":"Run Python code in a sandboxed subprocess","parameters":{"type":"object","properties":{"code":{"type":"string"},"timeout":{"type":"integer"}},"required":["code"]}}},
    {"type":"function","function":{"name":"run_shell","description":"Run a shell command in the sandbox","parameters":{"type":"object","properties":{"command":{"type":"string"},"timeout":{"type":"integer"}},"required":["command"]}}},
    {"type":"function","function":{"name":"web_search","description":"Search the web (DuckDuckGo, no key needed)","parameters":{"type":"object","properties":{"query":{"type":"string"}},"required":["query"]}}},
]

async def execute_tool(name, args):
    h = {"file_read": lambda a: file_read(a.get("path","")),
         "file_write": lambda a: file_write(a.get("path",""), a.get("content","")),
         "file_list": lambda a: file_list(a.get("path",".")),
         "run_python": lambda a: run_python(a.get("code",""), a.get("timeout",30)),
         "run_shell": lambda a: run_shell(a.get("command",""), a.get("timeout",30)),
         "web_search": lambda a: web_search(a.get("query",""))}
    if name in h:
        return await h[name](args)
    return None
