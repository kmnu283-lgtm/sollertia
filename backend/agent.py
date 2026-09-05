import json, asyncio
from llm import LLM
from browser_tool import Browser
from planner import Planner
from cost import CostTracker
from recorder import Recorder
from subagent import run_parallel, DELEGATE_SCHEMA
import tools as ext

MAX_STEPS = 30
SYSTEM_PROMPT = """You are Sollertia, an advanced autonomous agent. You can browse the web AND work with files/code/search.

Capabilities:
- Browser: navigate, click, type, extract, scroll, back, wait
- Files: file_read, file_write, file_list (sandboxed)
- Code: run_python, run_shell (sandboxed, timeout)
- Search: web_search (no key)
- Delegate: spawn parallel research sub-agents

Guidelines:
- For complex tasks, first output a numbered plan (one step per line).
- Prefer web_search to find URLs, then browser_navigate to visit them.
- Use run_python for computation; save artifacts with file_write.
- Use delegate for independent research subtasks to run them in parallel.
- Verify browser actions with screenshots/extract.
- When done, give a clear final summary and stop calling tools."""

def tool(name, desc, props, required):
    return {"type":"function","function":{"name":name,"description":desc,
        "parameters":{"type":"object","properties":props,"required":required}}}

BROWSER_TOOLS = [
    tool("browser_navigate","Open a URL",{"url":{"type":"string"}},["url"]),
    tool("browser_click","Click element (CSS selector)",{"selector":{"type":"string"}},["selector"]),
    tool("browser_type","Type into input (CSS selector)",{"selector":{"type":"string"},"text":{"type":"string"}},["selector","text"]),
    tool("browser_extract","Read page text",{},[]),
    tool("browser_scroll","Scroll up/down",{"direction":{"type":"string","enum":["up","down"]},"pixels":{"type":"integer"}},["direction"]),
    tool("browser_back","Go back",{},[]),
    tool("browser_wait","Wait seconds",{"seconds":{"type":"number"}},[]),
    tool("update_progress","Update plan progress",{"step":{"type":"integer"},"status":{"type":"string","enum":["in_progress","completed"]},"notes":{"type":"string"}},["step","status"]),
]
TOOLS = BROWSER_TOOLS + ext.TOOL_SCHEMAS + [DELEGATE_SCHEMA]

class Agent:
    def __init__(self, provider, api_key, model):
        self.llm = LLM(provider, api_key, model)
        self.browser = Browser()
        self.planner = Planner()
        self.cost = CostTracker(model)
        self.recorder = Recorder()
        self.stop_requested = False
        self.require_approval = False
        self.approved = True
        self.approval_event = asyncio.Event()

    async def _execute(self, name, args):
        r = await ext.execute_tool(name, args)
        if r is not None: return r
        if name == "delegate":
            return {"delegated": await run_parallel(self.llm.provider, self.llm.api_key, self.llm.model, args.get("tasks", []))}
        try:
            if name=="browser_navigate": return await self.browser.navigate(args["url"])
            if name=="browser_click": return await self.browser.click(args["selector"])
            if name=="browser_type": return await self.browser.type_text(args["selector"],args["text"])
            if name=="browser_extract": return await self.browser.extract()
            if name=="browser_scroll": return await self.browser.scroll(args.get("direction","down"),args.get("pixels",500))
            if name=="browser_back": return await self.browser.back()
            if name=="browser_wait":
                await asyncio.sleep(args.get("seconds",2)); return await self.browser.snapshot()
            if name=="update_progress":
                self.planner.update_step(args.get("step",1),args.get("status","in_progress"),args.get("notes",""))
                return {"progress":self.planner.get_progress(),"plan":self.planner.plan}
            return {"error":f"Unknown tool {name}"}
        except Exception as e:
            return {"error":str(e)}

    async def manual_command(self, cmd):
        parts = cmd.strip().split(maxsplit=2)
        if not parts: return None
        a = parts[0].lower()
        try:
            if a=="goto" and len(parts)>1: return await self.browser.navigate(parts[1])
            if a=="click" and len(parts)>1: return await self.browser.click(parts[1])
            if a=="type" and len(parts)>2: return await self.browser.type_text(parts[1],parts[2])
            if a=="shot": return await self.browser.snapshot()
            if a=="back": return await self.browser.back()
            return f"Unknown command: {cmd}"
        except Exception as e:
            return f"Error: {e}"

    def _obs(self, result):
        if not isinstance(result, dict): return str(result)[:1000], {}
        extra = {}
        if "url" in result: extra["url"]=result["url"]
        if "screenshot" in result: extra["screenshot"]=result["screenshot"]
        if "error" in result: return f"Error: {result['error']}", extra
        if "text" in result: return f"Page: {result['text'][:1500]}", extra
        if "stdout" in result or "stderr" in result:
            return f"exit={result.get('returncode')}
STDOUT:{result.get('stdout','')[:1200]}
STDERR:{result.get('stderr','')[:800]}", extra
        if "results" in result: return f"Search: {json.dumps(result['results'])[:1200]}", extra
        if "delegated" in result: return f"Sub-agents: {json.dumps(result['delegated'])[:1500]}", extra
        if "content" in result: return f"File: {result['content'][:1500]}", extra
        if "entries" in result: return f"Files: {json.dumps(result['entries'])[:800]}", extra
        if "progress" in result: return f"Progress {result['progress']:.0f}%", extra
        return str(result)[:1000], extra

    async def _emit(self, event):
        self.recorder.log(event)
        return event

    async def run(self, task):
        self.recorder.start(task)
        await self.browser.start()
        messages=[{"role":"system","content":SYSTEM_PROMPT},
                  {"role":"user","content":f"Task: {task}

First output a numbered plan (one step per line)."}]
        plan_msg = await self.llm.chat(messages, tools=None)
        self.cost.add(getattr(self.llm,"last_usage",{}))
        if plan_msg.get("content"):
            self.planner.create_plan(task, plan_msg["content"])
            if self.planner.plan:
                yield await self._emit({"type":"plan","plan":self.planner.plan})
            messages.append(plan_msg)
            messages.append({"role":"user","content":"Now execute the plan step by step."})
        for _ in range(MAX_STEPS):
            if self.stop_requested:
                yield await self._emit({"type":"stopped"}); break
            msg = await self.llm.chat(messages, tools=TOOLS)
            self.cost.add(getattr(self.llm,"last_usage",{}))
            messages.append(msg)
            if msg.get("content"):
                self.planner.add_to_history("thought",msg["content"])
                yield await self._emit({"type":"thought","content":msg["content"]})
            calls = msg.get("tool_calls")
            if not calls:
                yield await self._emit({"type":"final","content":msg.get("content","Done."),
                                        "plan":self.planner.plan,"cost":self.cost.summary()})
                break
            for tc in calls:
                fn=tc["function"]["name"]; args=json.loads(tc["function"]["arguments"] or "{}")
                if self.require_approval and fn not in ("update_progress",):
                    self.approval_event.clear()
                    yield await self._emit({"type":"approval_request","action":fn,"args":args})
                    await self.approval_event.wait()
                    if not self.approved:
                        messages.append({"role":"tool","tool_call_id":tc["id"],"content":"User rejected this action."}); continue
                yield await self._emit({"type":"action","action":fn,"args":args,"plan":self.planner.plan})
                result = await self._execute(fn,args)
                obs, extra = self._obs(result)
                if "url" in extra: yield await self._emit({"type":"url","url":extra["url"]})
                if "screenshot" in extra: yield await self._emit({"type":"screenshot","data":extra["screenshot"]})
                yield await self._emit({"type":"observation","content":obs})
                messages.append({"role":"tool","tool_call_id":tc["id"],"content":obs})
                self.planner.add_to_history("observation",obs)
        await self.browser.close()
        self.recorder.save()
        yield await self._emit({"type":"report","markdown":self.recorder.to_markdown()})
        yield await self._emit({"type":"cost","usd":self.cost.usd(),"model":self.cost.model,"seconds":self.cost.summary()["seconds"]})
        yield await self._emit({"type":"session_summary","summary":self.planner.to_dict(),"cost":self.cost.summary()})
