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
ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", None)

if not OPENROUTER_API_KEY:
    st.error("⚠️ OPENROUTER_API_KEY not found.")
    st.stop()

# -----------------------------
# Page Config
# -----------------------------
st.set_page_config(
    page_title="CHAT WITH NEXTGEN COACHING CENTER",
    layout="centered"
)

# -----------------------------
# Header
# -----------------------------
st.markdown("""
<style>
.chat-header {
    background: linear-gradient(90deg, #4285f4, #5a95f5);
    padding: 14px;
    color: white;
    font-size: 18px;
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
# Knowledge Setup
# -----------------------------
KNOWLEDGE_DIR = "knowledge_pdfs"
os.makedirs(KNOWLEDGE_DIR, exist_ok=True)
MAX_CONTEXT = 4500

# -----------------------------
# Session State
# -----------------------------
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant",
         "content": "👋 Welcome! Ask about admissions, fees, courses or timings.\nYou can ask in English or Urdu."}
    ]

if "admin_unlocked" not in st.session_state:
    st.session_state.admin_unlocked = False

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# -----------------------------
# Load Knowledge (SAFE)
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
user_input = st.chat_input("Message...")

if user_input:
    # Admin login command
    if user_input.startswith("/admin"):
        entered = user_input.replace("/admin", "").strip()
        if ADMIN_PASSWORD and entered == ADMIN_PASSWORD:
            st.session_state.admin_unlocked = True
            st.session_state.messages.append(
                {"role": "assistant", "content": "🔐 Admin panel unlocked."}
            )
        else:
            st.session_state.messages.append(
                {"role": "assistant", "content": "❌ Invalid admin password."}
            )

    else:
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        if not knowledge.strip():
            bot_reply = "⚠️ Knowledge not uploaded yet."
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
                            "You are a helpful coaching center assistant. "
                            "Answer shortly (1–2 sentences). "
                            "Use English or Urdu based on user language. "
                            "Answer ONLY from the document."
                        )
                    },
                    {
                        "role": "user",
                        "content": f"Document:\n{knowledge}\n\nQuestion:\n{user_input}"
                    }
                ],
                "max_output_tokens": 100,
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
                        "Error generating response"
                    )
                    st.markdown(bot_reply)

        st.session_state.messages.append({"role": "assistant", "content": bot_reply})
        st.session_state.chat_history.append(
            (user_input, bot_reply, datetime.now())
        )

# -----------------------------
# Admin Panel (SAFE)
# -----------------------------
if st.session_state.admin_unlocked:
    st.sidebar.header("🔐 Admin Panel")

    # PDF Upload
    st.sidebar.subheader("Upload Knowledge PDFs")
    uploaded_files = st.sidebar.file_uploader(
        "Select PDF(s)",
        type="pdf",
        accept_multiple_files=True
    )

    pdf_text = ""

    if uploaded_files:
        for file in uploaded_files:
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages:
                pdf_text += page.extract_text() or ""

            with open(os.path.join(KNOWLEDGE_DIR, file.name), "wb") as f:
                f.write(file.getbuffer())

    # Text Upload (SAFE – optional)
    st.sidebar.subheader("Add Text Information (Optional)")
    admin_text = st.sidebar.text_area(
        "Extra info (fees, notices, timings)"
    )

    if st.sidebar.button("Update Knowledge"):
        final_text = knowledge

        if pdf_text.strip():
            final_text = pdf_text[:MAX_CONTEXT]

        if admin_text.strip():
            final_text = (admin_text + "\n\n" + final_text)[:MAX_CONTEXT]

        if final_text.strip():
            with open("knowledge.txt", "w", encoding="utf-8") as f:
                f.write(final_text)
            st.sidebar.success("✅ Knowledge updated safely")

    # Knowledge Preview
    st.sidebar.subheader("Knowledge Preview")
    st.sidebar.write(f"Characters: {len(knowledge)}")
    st.sidebar.text_area("Stored Knowledge", knowledge, height=200)

    # Analytics
    st.sidebar.subheader("Chat Statistics")
    st.sidebar.write(f"Total Questions: {len(st.session_state.chat_history)}")

# -----------------------------
# Footer
# -----------------------------
st.markdown("""
<div class="footer">
Powered by AI | Developed by <b>Bilal AI Studio</b>
</div>
""", unsafe_allow_html=True)
