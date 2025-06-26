from fastapi import FastAPI, Request
from agent import run_agent

app = FastAPI()

@app.post("/chat")
async def chat(request: Request):
    """Endpoint for processing chat requests"""
    data = await request.json()
    try:
        response = run_agent(data['user_input'], data.get('state', {}))
        return response
    except Exception as e:
        return {
            "response": f"Agent error: {str(e)}",
            "state": {}
        }
