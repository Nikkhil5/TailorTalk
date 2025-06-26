import streamlit as st
import requests
from fastapi import FastAPI, Request
from agent import run_agent

app = FastAPI()

@app.post("/chat")
async def chat(request: Request):
    """API endpoint for chat requests"""
    data = await request.json()
    response = run_agent(data['user_input'], data.get('state', {}))
    return response

if __name__ == "__main__":
    st.title("Calendar Booking Agent")
    
    # Initialize session state
    if "messages" not in st.session_state:
        st.session_state.messages = []
        st.session_state.agent_state = {}
    
    # Display message history
    for msg in st.session_state.messages:
        st.chat_message(msg["role"]).write(msg["content"])
    
    # Process user input
    if prompt := st.chat_input("Book an appointment"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        try:
            response = requests.post(
                "http://127.0.0.1:8000/chat",
                json={
                    "user_input": prompt,
                    "state": st.session_state.agent_state
                },
                timeout=60
            ).json()
            
            # Update state and display response
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
