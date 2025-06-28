# 📅 Calendar Booking Agent

A conversational AI agent that helps you schedule Google Calendar appointments.  
**Built with FastAPI, LangGraph, and Streamlit.**

---

## 🚀 Live Demo & Source Code

- [🔗 Try the Demo] https://tailortalk-f4pxmsbqkk2amthjan9atn.streamlit.app/
- [📂 GitHub Repo] https://github.com/Nikkhil5/TailorTalk

---

## 💬 Example Conversation

User: Do you have any free time this Friday?
Agent: What time? (e.g., 'morning', 'afternoon' or '2 PM')
User: Friday 3PM
Agent: Booked! Your meeting is scheduled for Friday, June 27 at 3:00 PM.

yaml
Copy
Edit

---

## 🛠 Getting Started

git clone YOUR_GITHUB_REPO_URL_HERE
cd calendar-booking-agent
pip install -r requirements.txt
streamlit run app.py
🔐 Set Up Google Credentials
Create a .streamlit/secrets.toml file:

toml
Copy
Edit
[google_credentials]
type = "service_account"
project_id = "your-project-id"
private_key = """-----BEGIN PRIVATE KEY-----
YOUR_PRIVATE_KEY
-----END PRIVATE KEY-----"""
client_email = "your-service-account@project-id.iam.gserviceaccount.com"

CALENDAR_ID = "your-calendar-id@group.calendar.google.com"
⚠️ Do not commit this file. Use Streamlit Cloud's secrets manager for deployment.

Made with ❤️ by [Your Name]

yaml
Copy
Edit

### ✅ After Pasting:
- Save this as `README.md` in your repo
- Replace placeholders like:
  - `YOUR_STREAMLIT_APP_URL_HERE`
  - `YOUR_GITHUB_REPO_URL_HERE`
  - Secrets and `[Your Name]`

Let me know if you'd like deployment steps or Streamlit sharing instructions added!