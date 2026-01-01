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
CHAT WITH NEXTGEN COACHING CENTER
</div>
""", unsafe_allow_html=True)

# -----------------------------
# Constants
# -----------------------------
KNOWLEDGE_DIR = "knowledge_pdfs"
KNOWLEDGE_FILE = "knowledge.txt"
os.makedirs(KNOWLEDGE_DIR, exist_ok=True)
MAX_CONTEXT = 6000

# -----------------------------
# Session State
# -----------------------------
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant",
         "content": "Hi! What can I help you with? You can ask in English or Urdu."}
    ]

if "admin_unlocked" not in st.session_state:
    st.session_state.admin_unlocked = False

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# -----------------------------
# Load Knowledge
# -----------------------------
def load_knowledge():
    if os.path.exists(KNOWLEDGE_FILE):
        with open(KNOWLEDGE_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    return ""

knowledge = load_knowledge()

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
    admin_trigger = st.secrets.get("ADMIN_TRIGGER", "@supersecret")

    # ---- Admin Unlock ----
    if user_input.strip() == admin_trigger:
        st.session_state.admin_unlocked = True
        st.session_state.messages.append(
            {"role": "assistant", "content": "🔐 Admin panel unlocked."}
        )
        with st.chat_message("assistant"):
            st.markdown("🔐 Admin panel unlocked.")

    # ---- Normal Chat ----
    else:
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        knowledge = load_knowledge()

        if not knowledge:
            bot_reply = "⚠️ Knowledge base is empty. Please upload documents."
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
                            "You are a strict document-based assistant. "
                            "Answer ONLY using the provided document. "
                            "If the answer is not found, reply exactly: Information not available."
                        )
                    },
                    {
                        "role": "user",
                        "content": f"{knowledge}\n\nQuestion: {user_input}"
                    }
                ],
                "max_output_tokens": 120,
                "temperature": 0.1
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
                        "Error generating response."
                    )
                    st.markdown(bot_reply)

        st.session_state.messages.append(
            {"role": "assistant", "content": bot_reply}
        )

        st.session_state.chat_history.append(
            (user_input, bot_reply, datetime.now())
        )

# -----------------------------
# Admin Panel
# -----------------------------
if st.session_state.admin_unlocked:
    st.sidebar.header("🔐 Admin Panel")

    # ---- Upload PDFs ----
    pdf_files = st.sidebar.file_uploader(
        "Upload PDF files",
        type="pdf",
        accept_multiple_files=True
    )

    # ---- Upload Text ----
    manual_text = st.sidebar.text_area(
        "Add text information (optional)",
        height=150
    )

    if st.sidebar.button("Update Knowledge"):
        combined_text = ""

        # Process PDFs
        if pdf_files:
            for file in pdf_files:
                reader = PyPDF2.PdfReader(file)
                pdf_content = ""
                for page in reader.pages:
                    pdf_content += page.extract_text() or ""
                if pdf_content.strip() == "":
                    st.sidebar.warning(f"⚠️ {file.name} seems empty or scanned (PyPDF2 cannot read).")
                else:
                    combined_text += pdf_content + "\n"
                # Save PDF to folder
                with open(os.path.join(KNOWLEDGE_DIR, file.name), "wb") as f:
                    f.write(file.getbuffer())

        # Add manual text
        if manual_text.strip():
            combined_text += manual_text.strip() + "\n"

        if combined_text.strip() == "":
            st.sidebar.error("❌ No valid text found to update knowledge.")
        else:
            # Save final knowledge
            combined_text = combined_text[:MAX_CONTEXT]
            with open(KNOWLEDGE_FILE, "w", encoding="utf-8") as f:
                f.write(combined_text)
            st.sidebar.success("✅ Knowledge updated successfully!")

    # -----------------------------
    # Analytics
    # -----------------------------
    st.sidebar.subheader("Chat Analytics")
    total = len(st.session_state.chat_history)
    st.sidebar.write(f"Total Questions: {total}")

    if total:
        questions = [q for q, _, _ in st.session_state.chat_history]
        for q, c in Counter(questions).most_common(5):
            st.sidebar.markdown(f"- {q} ({c})")

        if st.sidebar.button("Export Chat History"):
            df = pd.DataFrame(
                st.session_state.chat_history,
                columns=["Question", "Answer", "Timestamp"]
            )
            df.to_csv("chat_history.csv", index=False)
            st.sidebar.success("✅ chat_history.csv created")

# -----------------------------
# Footer
# -----------------------------
st.markdown("""
<div class="footer">
Powered by AI | Developed by <b>Bilal AI Studio</b>
</div>
""", unsafe_allow_html=True)
