import json, asyncio
from llm import LLM
from browser_tool import Browser

MAX_STEPS = 15
SYSTEM_PROMPT = """You are Manus-Lite, an autonomous web agent. You browse the web to complete the user's task.
Use the browser tools step by step. After each action you'll see a screenshot + list of interactive elements.
When the task is done, reply with a final summary and stop calling tools. Be concise."""

def tool(name, desc, props, required):
    return {"type": "function", "function": {"name": name, "description": desc, "parameters": {"type": "object", "properties": props, "required": required}}}

TOOLS = [
    tool("browser_navigate", "Open a URL", {"url": {"type": "string"}}, ["url"]),
    tool("browser_click", "Click an element by CSS selector", {"selector": {"type": "string"}}, ["selector"]),
    tool("browser_type", "Type text into an input (CSS selector)", {"selector": {"type": "string"}, "text": {"type": "string"}}, ["selector", "text"]),
    tool("browser_extract", "Read the current page text", {}, []),
]

class Agent:
    def __init__(self, provider, api_key, model):
        self.llm = LLM(provider, api_key, model)
        self.browser = Browser()
        self.stop_requested = False
        self.require_approval = False
        self.approved = True
        self.approval_event = asyncio.Event()

    async def _execute(self, name, args):
        if name == "browser_navigate": return await self.browser.navigate(args["url"])
        if name == "browser_click": return await self.browser.click(args["selector"])
        if name == "browser_type": return await self.browser.type_text(args["selector"], args["text"])
        if name == "browser_extract": return await self.browser.extract()
        return {"error": f"Unknown tool {name}"}

    async def run(self, task):
        await self.browser.start()
        messages = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": task}]
        for step in range(MAX_STEPS):
            if self.stop_requested:
                yield {"type": "stopped"}
                break
            msg = await self.llm.chat(messages, tools=TOOLS)
            messages.append(msg)
            if msg.get("content"): yield {"type": "thought", "content": msg["content"]}
            calls = msg.get("tool_calls")
            if not calls:
                yield {"type": "final", "content": msg.get("content", "")}
                break
            for tc in calls:
                fn = tc["function"]["name"]
                args = json.loads(tc["function"]["arguments"] or "{}")
                if self.require_approval:
                    self.approval_event.clear()
                    yield {"type": "approval_request", "action": fn, "args": args}
                    await self.approval_event.wait()
                    if not self.approved:
                        messages.append({"role": "tool", "tool_call_id": tc["id"], "content": "User rejected this action."})
                        continue
                yield {"type": "action", "action": fn, "args": args}
                result = await self._execute(fn, args)
                if isinstance(result, dict) and "screenshot" in result:
                    yield {"type": "screenshot", "data": result["screenshot"], "elements": result["elements"]}
                    obs = "Done. Visible elements: " + json.dumps(result["elements"])[:800]
                else:
                    obs = str(result)[:1500]
                yield {"type": "observation", "content": obs}
                messages.append({"role": "tool", "tool_call_id": tc["id"], "content": obs})
        await self.browser.close()