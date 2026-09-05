import asyncio, pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
import tools

def test_sandbox_escape_blocked():
    with pytest.raises(ValueError):
        tools._safe_path("../../etc/passwd")

def test_file_write_read_roundtrip():
    async def run():
        w = await tools.file_write("test_hello.txt", "world")
        r = await tools.file_read("test_hello.txt")
        return r["content"] == "world"
    assert asyncio.get_event_loop().run_until_complete(run())

def test_run_python():
    async def run():
        r = await tools.run_python("print(1+1)")
        return r["stdout"].strip() == "2"
    assert asyncio.get_event_loop().run_until_complete(run())

def test_web_search():
    async def run():
        r = await tools.web_search("python programming")
        return "results" in r and len(r["results"]) > 0
    assert asyncio.get_event_loop().run_until_complete(run())
