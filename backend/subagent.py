import asyncio
from llm import LLM

class SubAgent:
    def __init__(self, provider, api_key, model):
        self.llm = LLM(provider, api_key, model)

    async def run(self, instruction):
        msgs = [{"role":"system","content":"You are a focused research sub-agent. Answer concisely with facts only."},
                {"role":"user","content":instruction}]
        try:
            r = await self.llm.chat(msgs, tools=None)
            return {"subtask": instruction, "result": r.get("content","")[:1500]}
        except Exception as e:
            return {"subtask": instruction, "error": str(e)}

async def run_parallel(provider, api_key, model, tasks):
    workers = [SubAgent(provider, api_key, model).run(t) for t in tasks]
    return await asyncio.gather(*workers)

DELEGATE_SCHEMA = {"type":"function","function":{
    "name":"delegate","description":"Delegate one or more research subtasks to parallel sub-agents",
    "parameters":{"type":"object","properties":{"tasks":{"type":"array","items":{"type":"string"}}},
    "required":["tasks"]}}}
