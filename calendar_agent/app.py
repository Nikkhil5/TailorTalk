import streamlit as st
import threading
import time
from fastapi import FastAPI, Request
import uvicorn
from agent import run_agent

# FastAPI app
app = FastAPI()

@app.post("/chat")
async def chat(request: Request):
    data = await request.json()
    response = run_agent(data['user_input'], data.get('state', {}))
    return response

# Start FastAPI in background thread
def start_fastapi():
    uvicorn.run(app, host="127.0.0.1", port=8000)

# Start FastAPI server
if "fastapi_started" not in st.session_state:
    st.session_state.fastapi_started = True
    fastapi_thread = threading.Thread(target=start_fastapi, daemon=True)
    fastapi_thread.start()
    time.sleep(2)  # Give FastAPI time to start

# Streamlit UI
st.title("Calendar Booking Agent")

if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.agent_state = {}

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

if prompt := st.chat_input("Book an appointment"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    try:
        import requests
        response = requests.post(
            "http://127.0.0.1:8000/chat",
            json={
                "user_input": prompt,
                "state": st.session_state.agent_state
            },
            timeout=60
        ).json()
        
        st.session_state.agent_state = response['state']
        st.session_state.messages.append({
            "role": "assistant",
            "content": response['response']
        })
    except Exception as e:
        st.session_state.messages.append({
            "role": "assistant", 
            "content": f"Error: {str(e)}"
        })
    
    st.rerun()
