# 📅 Calendar Booking Agent

A conversational AI agent that helps you schedule appointments via **Google Calendar** using natural language.  
**Built with FastAPI, LangGraph, and Streamlit.**

---

## 🚀 Live Demo & Source Code

- 🔗 [Live Demo](https://tailortalk-f4pxmsbqkk2amthjan9atn.streamlit.app/)
- 📂 [GitHub Repository](https://github.com/Nikkhil5/TailorTalk)

---

## 💬 Example Conversation

**User**: Do you have any free time this Friday?  
**Agent**: What time? (e.g., 'morning', 'afternoon' or '2 PM')  
**User**: Friday 3PM  
**Agent**: ✅ Booked! Your meeting is scheduled for Friday, June 27 at 3:00 PM.

---

## 🛠 Getting Started Locally

git clone https://github.com/Nikkhil5/TailorTalk.git
cd TailorTalk
pip install -r requirements.txt
streamlit run app.py

## 🔐 Set Up Google Credentials
Create a file at .streamlit/secrets.toml

.

## 📦 Tech Stack
LangGraph – stateful conversation handling

FastAPI – lightweight backend API

Streamlit – web frontend for interaction

Google Calendar API – calendar booking integration

