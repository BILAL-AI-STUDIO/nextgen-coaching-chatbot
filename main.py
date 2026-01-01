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
# Knowledge Setup
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
            "I can help you with admissions, fees, courses, and timings.\n"
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
        knowledge = f.read().strip()

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
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        if len(knowledge) < 200:
            bot_reply = (
                "⚠️ Knowledge base is empty or unreadable.\n"
                "Please contact the office."
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
                            "You are the official AI assistant of a coaching center.\n"
                            "Rules:\n"
                            "- Use ONLY the provided document\n"
                            "- Answer briefly (1–3 sentences)\n"
                            "- Match user language (English/Urdu)\n"
                            "- If exact answer not found, give closest relevant info\n"
                            "- If nothing is relevant, reply:\n"
                            "'Information not available. Please contact the office.'"
                        )
                    },
                    {
                        "role": "user",
                        "content": f"DOCUMENT:\n{knowledge}\n\nQUESTION:\n{user_input}"
                    }
                ],
                "max_output_tokens": 150,
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

        st.session_state.messages.append({"role": "assistant", "content": bot_reply})
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

    pdf_text = ""
    unreadable_pdfs = []

    if uploaded_files:
        for file in uploaded_files:
            reader = PyPDF2.PdfReader(file)
            extracted = ""
            for page in reader.pages:
                extracted += page.extract_text() or ""

            if len(extracted.strip()) < 50:
                unreadable_pdfs.append(file.name)
            else:
                pdf_text += extracted

            with open(os.path.join(KNOWLEDGE_DIR, file.name), "wb") as f:
                f.write(file.getbuffer())

    # Text Upload (PRIORITY)
    st.sidebar.subheader("Add Text Information (High Priority)")
    admin_text = st.sidebar.text_area(
        "Fees, courses, admissions, notices"
    )

    if st.sidebar.button("Update Knowledge"):
        final_knowledge = (admin_text + "\n\n" + pdf_text)[:MAX_CONTEXT]
        with open("knowledge.txt", "w", encoding="utf-8") as f:
            f.write(final_knowledge)

        st.sidebar.success("✅ Knowledge updated successfully")

        if unreadable_pdfs:
            st.sidebar.warning(
                "⚠️ Scanned PDFs detected:\n" + ", ".join(unreadable_pdfs)
            )

    # Knowledge Preview
    st.sidebar.subheader("Knowledge Preview")
    st.sidebar.write(f"Characters loaded: {len(knowledge)}")
    st.sidebar.text_area("Stored Knowledge", knowledge, height=200)

    # Analytics
    st.sidebar.subheader("Chat Analytics")
    total_q = len(st.session_state.chat_history)
    st.sidebar.write(f"Total Questions: {total_q}")

# -----------------------------
# Footer
# -----------------------------
st.markdown("""
<div class="footer">
Powered by AI | Developed by <b>Bilal AI Studio</b><br>
Informational responses only.
</div>
""", unsafe_allow_html=True)
