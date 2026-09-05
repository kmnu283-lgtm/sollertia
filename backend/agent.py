import json, asyncio
from llm import LLM
from browser_tool import Browser
from planner import Planner

MAX_STEPS = 30
SYSTEM_PROMPT = """You are Sollertia, an advanced autonomous web agent. You browse the web and complete the user's task with precision.

You have access to browser tools that let you navigate, click, type, extract content, scroll, and more. After each action you'll see a screenshot and list of interactive elements.

Guidelines:
- Think step by step before acting
- When you receive a complex task, first create a numbered plan with clear steps
- Use screenshots to verify your actions
- When the task is complete, reply with a clear final summary and stop calling tools
- If you encounter an error or can't proceed, explain the situation
- Be efficient but thorough
- Update your progress as you complete each step

Tool calling:
- Use tools by calling them with the appropriate arguments
- After each tool call, you'll receive feedback including screenshots and page content
- Use this feedback to decide your next action"""

def tool(name, desc, props, required):
    return {"type": "function", "function": {"name": name, "description": desc, "parameters": {"type": "object", "properties": props, "required": required}}}

TOOLS = [
    tool("browser_navigate", "Open a URL in the browser", {"url": {"type": "string"}}, ["url"]),
    tool("browser_click", "Click an element by CSS selector", {"selector": {"type": "string"}}, ["selector"]),
    tool("browser_type", "Type text into an input field (CSS selector)", {"selector": {"type": "string"}, "text": {"type": "string"}}, ["selector", "text"]),
    tool("browser_extract", "Read the current page text content", {}, []),
    tool("browser_scroll", "Scroll the page up or down", {"direction": {"type": "string", "enum": ["up", "down"]}, "pixels": {"type": "integer", "default": 500}}, ["direction"]),
    tool("browser_back", "Go back to the previous page", {}, []),
    tool("browser_wait", "Wait for a number of seconds (useful for loading)", {"seconds": {"type": "number", "default": 2}}, []),
    tool("update_progress", "Update your current progress on the plan", {"step": {"type": "integer", "description": "Current step number (1-based)"}, "status": {"type": "string", "enum": ["in_progress", "completed"]}, "notes": {"type": "string", "description": "Optional notes about what was accomplished"}}, ["step", "status"]),
]

class Agent:
    def __init__(self, provider, api_key, model):
        self.llm = LLM(provider, api_key, model)
        self.browser = Browser()
        self.planner = Planner()
        self.stop_requested = False
        self.require_approval = False
        self.approved = True
        self.approval_event = asyncio.Event()
        self.step_count = 0

    async def _execute(self, name, args):
        try:
            if name == "browser_navigate":
                return await self.browser.navigate(args["url"])
            if name == "browser_click":
                return await self.browser.click(args["selector"])
            if name == "browser_type":
                return await self.browser.type_text(args["selector"], args["text"])
            if name == "browser_extract":
                return await self.browser.extract()
            if name == "browser_scroll":
                direction = args.get("direction", "down")
                pixels = args.get("pixels", 500)
                return await self.browser.scroll(direction, pixels)
            if name == "browser_back":
                return await self.browser.back()
            if name == "browser_wait":
                seconds = args.get("seconds", 2)
                await asyncio.sleep(seconds)
                return await self.browser.snapshot()
            if name == "update_progress":
                step = args.get("step", self.step_count)
                status = args.get("status", "in_progress")
                notes = args.get("notes", "")
                self.planner.update_step(step, status, notes)
                self.step_count = step
                return {"progress": self.planner.get_progress(), "plan": self.planner.plan}
            return {"error": f"Unknown tool {name}"}
        except Exception as e:
            return {"error": str(e)}

    async def manual_command(self, cmd):
        """Handle manual commands from the takeover console"""
        parts = cmd.strip().split(maxsplit=2)
        if not parts:
            return None
        action = parts[0].lower()
        try:
            if action == "goto" and len(parts) >= 2:
                return await self.browser.navigate(parts[1])
            if action == "click" and len(parts) >= 2:
                return await self.browser.click(parts[1])
            if action == "type" and len(parts) >= 3:
                return await self.browser.type_text(parts[1], parts[2])
            if action == "shot":
                return await self.browser.snapshot()
            if action == "back":
                return await self.browser.back()
            return f"Unknown command: {cmd}"
        except Exception as e:
            return f"Error: {e}"

    async def run(self, task):
        await self.browser.start()
        messages = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": task}]
        
        # Initial planning phase
        planning_msg = f"Task: {task}\n\nFirst, create a numbered plan with clear steps to complete this task. List each step on a new line starting with a number."
        messages.append({"role": "user", "content": planning_msg})
        
        plan_response = await self.llm.chat(messages, tools=None)
        if plan_response.get("content"):
            # Try to extract plan from response
            self.planner.create_plan(task, plan_response["content"])
            if self.planner.plan:
                yield {"type": "plan", "plan": self.planner.plan, "content": plan_response["content"]}
                messages.append(plan_response)
                # Now proceed with execution
                messages.append({"role": "user", "content": "Great plan! Now execute it step by step. Start with step 1."})
        
        for step in range(MAX_STEPS):
            if self.stop_requested:
                yield {"type": "stopped"}
                break
            
            msg = await self.llm.chat(messages, tools=TOOLS)
            messages.append(msg)
            
            if msg.get("content"):
                yield {"type": "thought", "content": msg["content"]}
                self.planner.add_to_history("thought", msg["content"])
            
            calls = msg.get("tool_calls")
            if not calls:
                yield {"type": "final", "content": msg.get("content", "Task complete."), "plan": self.planner.plan}
                break
            
            for tc in calls:
                fn = tc["function"]["name"]
                args = json.loads(tc["function"]["arguments"] or "{}")
                
                if self.require_approval and fn != "update_progress":
                    self.approval_event.clear()
                    yield {"type": "approval_request", "action": fn, "args": args}
                    await self.approval_event.wait()
                    if not self.approved:
                        messages.append({"role": "tool", "tool_call_id": tc["id"], "content": "User rejected this action."})
                        continue
                
                yield {"type": "action", "action": fn, "args": args, "plan": self.planner.plan}
                result = await self._execute(fn, args)
                
                if isinstance(result, dict):
                    if "url" in result:
                        yield {"type": "url", "url": result["url"]}
                    if "screenshot" in result:
                        yield {"type": "screenshot", "data": result["screenshot"]}
                        obs = f"Action completed. URL: {result.get('url', 'N/A')}"
                        if "elements" in result:
                            obs += f"\nVisible elements: {json.dumps(result['elements'])[:600]}"
                    elif "text" in result:
                        obs = f"Page content (first 1500 chars): {result['text'][:1500]}"
                    elif "error" in result:
                        obs = f"Error: {result['error']}"
                    elif "progress" in result:
                        obs = f"Progress updated: {result['progress']:.1f}% complete"
                        yield {"type": "plan_update", "plan": self.planner.plan, "progress": result['progress']}
                    else:
                        obs = str(result)[:1000]
                else:
                    obs = str(result)[:1000]
                
                yield {"type": "observation", "content": obs}
                messages.append({"role": "tool", "tool_call_id": tc["id"], "content": obs})
                self.planner.add_to_history("observation", obs)
        
        await self.browser.close()
        yield {"type": "session_summary", "summary": self.planner.to_dict()}
