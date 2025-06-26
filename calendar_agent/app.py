import streamlit as st
import requests
from fastapi import FastAPI, Request
from agent import run_agent

# Create FastAPI instance
app = FastAPI()

# Define API endpoint
@app.post("/chat")
async def chat(request: Request):
    """API endpoint for chat requests"""
    data = await request.json()
    response = run_agent(data['user_input'], data.get('state', {}))
    return response

# Streamlit client code
if __name__ == "__main__":
    st.title("Calendar Booking Agent")

    # Get API URL from secrets
    try:
        api_base_url = st.secrets["DEPLOYED_API_BASE_URL"]
    except KeyError:
        st.error("API base URL not configured in secrets. Please check your secrets.toml file.")
        st.stop()

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
               f"{api_base_url}/chat",
                json={
                    "user_input": prompt,
                    "state": st.session_state.agent_state
                },
                timeout=60
            )
            
            # Check for HTTP errors
            response.raise_for_status()
            data = response.json()
            
            # Update state and display response
            st.session_state.agent_state = data['state']
            st.session_state.messages.append({
                "role": "assistant",
                "content": data['response']
            })
        except requests.exceptions.RequestException as e:
            st.session_state.messages.append({
                "role": "assistant",
                "content": f"Network error: {str(e)}"
            })
        except ValueError as e:
            st.session_state.messages.append({
                "role": "assistant",
                "content": f"Invalid response from API: {str(e)}"
            })
        except Exception as e:
            st.session_state.messages.append({
                "role": "assistant",
                "content": f"Error: {str(e)}"
            })
        
        st.rerun()
