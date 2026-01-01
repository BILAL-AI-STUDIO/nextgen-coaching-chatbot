import streamlit as st
import os
import requests
import PyPDF2
from dotenv import load_dotenv
import pandas as pd
from collections import Counter
from datetime import datetime

# -----------------------------
# Load environment variables
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
    page_title="CHAT WITH NEXTGEN COACHING CENTER",
    layout="centered"
)

# -----------------------------
# Custom Header
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
}
</style>
<div class="chat-header">
    "CHAT WITH NEXTGEN COACHING CENTER
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
    st.session_state.messages = [
        {"role": "assistant", "content": "Hi! What can I help you with?"}
    ]
if "admin_unlocked" not in st.session_state:
    st.session_state.admin_unlocked = False
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []  # Stores (question, answer, timestamp)

# -----------------------------
# Load Knowledge
# -----------------------------
knowledge = ""
if os.path.exists("knowledge.txt"):
    with open("knowledge.txt", "r", encoding="utf-8") as f:
        knowledge = f.read()

# -----------------------------
# Display Chat Messages
# -----------------------------
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# -----------------------------
# Chat Input
# -----------------------------
user_input = st.chat_input("Message...")

if user_input:
    # Check for admin trigger
    admin_trigger = st.secrets.get("ADMIN_TRIGGER", "@admin")
    if user_input.strip() == admin_trigger:
        st.session_state.admin_unlocked = True
        st.session_state.messages.append(
            {"role": "assistant", "content": "🔐 Admin panel unlocked."}
        )
        with st.chat_message("assistant"):
            st.markdown("🔐 Admin panel unlocked.")
    else:
        # Normal user message
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        # Call AI
        if not knowledge:
            bot_reply = "⚠️ No knowledge uploaded yet. Admin must upload PDFs or add text first."
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
                            "You are a helpful AI assistant. "
                            "Answer SHORT (1-2 sentences) and ONLY using the content provided in the document. "
                            "If the answer is not in the document, reply exactly: 'Information not available.'"
                        )
                    },
                    {
                        "role": "user",
                        "content": f"Document:\n{knowledge}\n\nQuestion:\n{user_input}"
                    }
                ],
                "max_output_tokens": 80,
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

        # Save to chat history for analytics
        st.session_state.chat_history.append((user_input, bot_reply, datetime.now()))

# -----------------------------
# Admin Panel
# -----------------------------
if st.session_state.admin_unlocked:
    st.sidebar.header("🔐 Admin Panel")

    # PDF / Knowledge Upload
    st.sidebar.subheader("Upload Knowledge PDF(s)")
    uploaded_files = st.sidebar.file_uploader(
        "Select PDF(s) to upload",
        type="pdf",
        accept_multiple_files=True
    )

    if uploaded_files:
        combined_text = ""
        for file in uploaded_files:
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages:
                combined_text += page.extract_text() or ""
            with open(os.path.join(KNOWLEDGE_DIR, file.name), "wb") as f:
                f.write(file.getbuffer())

        combined_text = combined_text[:MAX_CONTEXT]
        # Append to knowledge.txt
        with open("knowledge.txt", "a", encoding="utf-8") as f:
            f.write("\n" + combined_text)
        st.sidebar.success("✅ Knowledge updated successfully from PDFs")

    # -----------------------------
    # Text Input for Knowledge
    st.sidebar.subheader("Add Knowledge Text")
    text_input = st.sidebar.text_area(
        "Enter text to add to knowledge base",
        height=150
    )

    if st.sidebar.button("Add Text to Knowledge"):
        if text_input.strip():
            text_to_add = text_input.strip()[:MAX_CONTEXT]
            with open("knowledge.txt", "a", encoding="utf-8") as f:
                f.write("\n" + text_to_add)
            st.sidebar.success("✅ Text added to knowledge successfully")
            # Update in-memory knowledge immediately
            knowledge += "\n" + text_to_add
        else:
            st.sidebar.warning("⚠️ Enter some text first.")

    # -----------------------------
    # Analytics
    st.sidebar.subheader("Chat Statistics")
    total_questions = len(st.session_state.chat_history)
    st.sidebar.markdown(f"**Total Questions:** {total_questions}")

    if total_questions > 0:
        questions = [q for q, _, _ in st.session_state.chat_history]
        freq = Counter(questions).most_common(5)
        st.sidebar.markdown("**Top 5 Questions:**")
        for q, count in freq:
            st.sidebar.markdown(f"- {q} ({count} times)")

        last_active = st.session_state.chat_history[-1][2].strftime("%Y-%m-%d %H:%M:%S")
        st.sidebar.markdown(f"**Last Active:** {last_active}")

        # Export chat history
        if st.sidebar.button("Export Chat History"):
            df = pd.DataFrame(
                st.session_state.chat_history, 
                columns=["Question", "Answer", "Timestamp"]
            )
            df.to_csv("chat_history.csv", index=False)
            st.sidebar.success("✅ Chat history saved as chat_history.csv")
