from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from agent import Agent
import asyncio

app = FastAPI()

@app.get("/")
def index():
    return FileResponse("../frontend/index.html")

@app.websocket("/ws")
async def ws(websocket: WebSocket):
    await websocket.accept()
    state = {"agent": None}

    async def runner(task, provider, api_key, model):
        agent = Agent(provider, api_key, model)
        state["agent"] = agent
        try:
            async for event in agent.run(task):
                await websocket.send_json(event)
        except Exception as e:
            await websocket.send_json({"type": "error", "content": str(e)})

    try:
        while True:
            data = await websocket.receive_json()
            t = data.get("type")
            if t == "task":
                asyncio.create_task(runner(data["task"], data["provider"], data["apiKey"], data["model"]))
            elif t == "stop" and state["agent"]:
                state["agent"].stop_requested = True
            elif t == "approve" and state["agent"]:
                state["agent"].approved = data["approved"]
                state["agent"].approval_event.set()
            elif t == "approval_mode" and state["agent"]:
                state["agent"].require_approval = data["on"]
    except WebSocketDisconnect:
        if state["agent"]:
            await state["agent"].browser.close()