import streamlit as st
import requests
from fastapi import FastAPI, Request
import uvicorn
from agent import run_agent
import threading
import time

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

# Initialize Streamlit app
st.title("📅 Calendar Booking Agent")
st.caption("A conversational AI that helps you book appointments on Google Calendar")

# Start FastAPI server
if "fastapi_started" not in st.session_state:
    st.session_state.fastapi_started = True
    fastapi_thread = threading.Thread(target=start_fastapi, daemon=True)
    fastapi_thread.start()
    time.sleep(2)  # Give FastAPI time to start

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = [{
        "role": "assistant",
        "content": "Hello! I'm your calendar assistant. I can help you:\n"
                   "- Check availability\n"
                   "- Book appointments\n\n"
                   "💡 **Tip**: Always include date AND time in your requests like:\n"
                   "   - 'Friday 2 PM'\n"
                   "   - 'Tomorrow morning'\n"
                   "   - 'Tomorrow at afternoon at 2 PM'"
    }]
    st.session_state.agent_state = {}

# Display message history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Process user input
if prompt := st.chat_input("Type your request..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    with st.spinner("Checking calendar..."):
        try:
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
        except requests.exceptions.ConnectionError:
            error_msg = "🔌 Connection error: Backend service unavailable"
            st.session_state.messages.append({
                "role": "assistant",
                "content": error_msg
            })
        except Exception as e:
            error_msg = f"⚠️ Error: {str(e)}"
            st.session_state.messages.append({
                "role": "assistant",
                "content": error_msg
            })
    
    st.rerun()
