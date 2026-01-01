import streamlit as st
import os
import requests
import PyPDF2
from dotenv import load_dotenv
import pandas as pd
from collections import Counter
from datetime import datetime

# -----------------------------
# Load Environment Variables
# -----------------------------
load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

if not OPENROUTER_API_KEY:
    st.error("⚠️ OPENROUTER_API_KEY not found.")
    st.stop()

# -----------------------------
# Page Config
# -----------------------------
st.set_page_config(
    page_title="NextGen Coaching Center AI Assistant",
    layout="centered"
)

# -----------------------------
# Branding Header
# -----------------------------
st.markdown("""
<style>
.chat-header {
    background: linear-gradient(90deg, #4285f4, #5a95f5);
    padding: 16px;
    color: white;
    font-size: 20px;
    font-weight: bold;
    border-radius: 10px;
    text-align: center;
}
.footer {
    text-align: center;
    font-size: 12px;
    color: gray;
    margin-top: 20px;
}
</style>

<div class="chat-header">
Official AI Assistant – NextGen Coaching Center
</div>
""", unsafe_allow_html=True)

# -----------------------------
# Knowledge Directory
# -----------------------------
KNOWLEDGE_DIR = "knowledge_pdfs"
os.makedirs(KNOWLEDGE_DIR, exist_ok=True)
MAX_CONTEXT = 4500

# -----------------------------
# Session State
# -----------------------------
if "messages" not in st.session_state:
    st.session_state.messages = [{
        "role": "assistant",
        "content": (
            "👋 Welcome!\n\n"
            "I can help you with:\n"
            "- Admissions\n- Fee Structure\n- Courses\n- Timings & Policies\n\n"
            "You can ask in **English or Urdu**."
        )
    }]

if "admin_unlocked" not in st.session_state:
    st.session_state.admin_unlocked = False

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# -----------------------------
# Load Knowledge
# -----------------------------
knowledge = ""
if os.path.exists("knowledge.txt"):
    with open("knowledge.txt", "r", encoding="utf-8") as f:
        knowledge = f.read()

# -----------------------------
# Display Chat
# -----------------------------
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# -----------------------------
# Chat Input
# -----------------------------
user_input = st.chat_input("Type your question...")

if user_input:
    admin_trigger = st.secrets.get("ADMIN_TRIGGER", "@admin")

    if user_input.strip() == admin_trigger:
        st.session_state.admin_unlocked = True
        st.session_state.messages.append({
            "role": "assistant",
            "content": "🔐 Admin panel unlocked."
        })
        with st.chat_message("assistant"):
            st.markdown("🔐 Admin panel unlocked.")

    else:
        st.session_state.messages.append({
            "role": "user",
            "content": user_input
        })
        with st.chat_message("user"):
            st.markdown(user_input)

        if not knowledge:
            bot_reply = (
                "⚠️ Information not available.\n\n"
                "Please contact the office directly for assistance."
            )
        else:
            headers = {
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": "nvidia/nemotron-3-nano-30b-a3b:free",
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are an official AI assistant of a coaching center. "
                            "Answer briefly (1–2 sentences). "
                            "Use English or Urdu based on user language. "
                            "ONLY use the provided document. "
                            "If the answer is missing, reply exactly: "
                            "'Information not available. Please contact the office.'"
                        )
                    },
                    {
                        "role": "user",
                        "content": f"Document:\n{knowledge}\n\nQuestion:\n{user_input}"
                    }
                ],
                "max_output_tokens": 120,
                "temperature": 0.2
            }

            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    response = requests.post(
                        "https://openrouter.ai/api/v1/chat/completions",
                        headers=headers,
                        json=payload,
                        timeout=30
                    )
                    data = response.json()
                    bot_reply = (
                        data["choices"][0]["message"]["content"]
                        if "choices" in data else
                        "⚠️ Error generating response."
                    )
                    st.markdown(bot_reply)

        st.session_state.messages.append({
            "role": "assistant",
            "content": bot_reply
        })

        st.session_state.chat_history.append(
            (user_input, bot_reply, datetime.now())
        )

# -----------------------------
# Admin Panel
# -----------------------------
if st.session_state.admin_unlocked:
    st.sidebar.header("🔐 Admin Panel")

    # PDF Upload
    st.sidebar.subheader("Upload Knowledge PDFs")
    uploaded_files = st.sidebar.file_uploader(
        "Upload PDF files",
        type="pdf",
        accept_multiple_files=True
    )

    combined_text = ""

    if uploaded_files:
        for file in uploaded_files:
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages:
                combined_text += page.extract_text() or ""

            with open(os.path.join(KNOWLEDGE_DIR, file.name), "wb") as f:
                f.write(file.getbuffer())

    # Text Information Upload
    st.sidebar.subheader("Add Text Information")
    admin_text = st.sidebar.text_area(
        "Add or update text information (announcements, fees, notices)"
    )

    if st.sidebar.button("Update Knowledge"):
        final_knowledge = (combined_text + "\n\n" + admin_text)[:MAX_CONTEXT]
        with open("knowledge.txt", "w", encoding="utf-8") as f:
            f.write(final_knowledge)

        st.sidebar.success("✅ Knowledge updated successfully")

    # -----------------------------
    # Analytics
    # -----------------------------
    st.sidebar.subheader("Chat Analytics")

    total_q = len(st.session_state.chat_history)
    st.sidebar.markdown(f"**Total Questions:** {total_q}")

    if total_q > 0:
        questions = [q for q, _, _ in st.session_state.chat_history]
        freq = Counter(questions).most_common(5)

        st.sidebar.markdown("**Top 5 Questions:**")
        for q, c in freq:
            st.sidebar.markdown(f"- {q} ({c})")

        last_active = st.session_state.chat_history[-1][2].strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        st.sidebar.markdown(f"**Last Active:** {last_active}")

        if st.sidebar.button("Export Chat History"):
            df = pd.DataFrame(
                st.session_state.chat_history,
                columns=["Question", "Answer", "Timestamp"]
            )
            df.to_csv("chat_history.csv", index=False)
            st.sidebar.success("✅ Chat history exported")

# -----------------------------
# Footer
# -----------------------------
st.markdown("""
<div class="footer">
Powered by AI | Developed by <b>Bilal AI Studio</b><br>
This chatbot provides informational responses only.
</div>
""", unsafe_allow_html=True)
