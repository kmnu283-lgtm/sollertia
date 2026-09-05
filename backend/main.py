from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from agent import Agent
import asyncio
import os

app = FastAPI()
agent_instance = None

@app.get("/", response_class=HTMLResponse)
async def index():
    html_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "index.html")
    with open(html_path) as f:
        return HTMLResponse(content=f.read(), status_code=200)

@app.websocket("/ws")
async def ws(websocket: WebSocket):
    global agent_instance
    await websocket.accept()
    
    try:
        while True:
            data = await websocket.receive_json()
            t = data.get("type")
            
            if t == "task":
                agent_instance = Agent(data["provider"], data["apiKey"], data["model"])
                
                async def runner():
                    try:
                        async for event in agent_instance.run(data["task"]):
                            await websocket.send_json(event)
                    except Exception as e:
                        await websocket.send_json({"type": "error", "content": str(e)})
                
                asyncio.create_task(runner())
            
            elif t == "stop" and agent_instance:
                agent_instance.stop_requested = True
            
            elif t == "approve" and agent_instance:
                agent_instance.approved = data["approved"]
                agent_instance.approval_event.set()
            
            elif t == "approval_mode" and agent_instance:
                agent_instance.require_approval = data["on"]
            
            elif t == "manual" and agent_instance:
                result = await agent_instance.manual_command(data["cmd"])
                if result:
                    await websocket.send_json({"type": "observation", "content": f"Manual: {result}"})
                    if isinstance(result, dict) and "screenshot" in result:
                        await websocket.send_json({"type": "screenshot", "data": result["screenshot"]})
    
    except WebSocketDisconnect:
        if agent_instance:
            await agent_instance.browser.close()
