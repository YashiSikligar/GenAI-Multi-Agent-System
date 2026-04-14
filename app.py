
import os
import requests
import streamlit as st

API_BASE = os.getenv("API_BASE", "http://localhost:8000")

st.set_page_config(
    page_title="Generative AI Multi-Agent System",
    layout="centered",
)



if "messages" not in st.session_state:
    st.session_state.messages = []
if "pdf_name" not in st.session_state:
    st.session_state.pdf_name = ""




def check_server_health():
    try:
        r = requests.get(f"{API_BASE}/health", timeout=4)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


def send_chat(query: str) -> dict:
    r = requests.post(f"{API_BASE}/chat", json={"query": query}, timeout=60)
    r.raise_for_status()
    return r.json()


def upload_pdf(file_bytes, filename: str) -> dict:
    r = requests.post(
        f"{API_BASE}/upload_pdf",
        files={"file": (filename, file_bytes, "application/pdf")},
        timeout=120,
    )
    r.raise_for_status()
    return r.json()



with st.sidebar:
    st.title("Support Assistant for PDF")
    st.caption("Gen Multi-Agent AI")
    st.divider()

    #Server status
    health = check_server_health()
    if health:
        st.success("Server Online")
        st.write("SQL Agent: Ready")
        st.write("RAG Agent:", "Ready" if health.get("rag_ready") else "No docs uploaded yet")
    else:
        st.error("Server Offline")
        st.info("Run `python server.py` to start the backend.")

    st.divider()

    #PDF Upload
    st.subheader("Upload Policy PDF")
    uploaded_file = st.file_uploader("Choose a PDF file", type=["pdf"])
    if uploaded_file is not None:
        if st.button("Index PDF", use_container_width=True):
            with st.spinner("Indexing document..."):
                try:
                    result = upload_pdf(uploaded_file.read(), uploaded_file.name)
                    st.session_state.pdf_name = uploaded_file.name
                    st.success(f"Indexed {result['chunks_indexed']} chunks from '{uploaded_file.name}'")
                except Exception as e:
                    st.error(f"Upload failed: {e}")

    if st.session_state.pdf_name:
        st.caption(f"Indexed: {st.session_state.pdf_name}")

    st.divider()

    if st.button("Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()



st.title("Customer Support ChatBot")
st.caption("Ask questions about customers and tickets, or about your uploaded policy documents.")
st.divider()


# Chat history
for msg in st.session_state.messages:
    if msg["role"] == "user":
        with st.chat_message("user"):
            st.write(msg["content"])
    else:
        with st.chat_message("assistant"):
            st.write(msg["content"])
            if msg.get("route") == "sql":
                st.caption("Answered by SQL Agent")
            elif msg.get("route") == "rag":
                st.caption("Answered by RAG Agent")

# Chat input
user_input = st.chat_input("Ask a question about customers, tickets, or policies...")

if user_input and user_input.strip():
    if not health:
        st.error("Server is offline. Please start `python server.py` first.")
    else:
        # Save user message to session state
        st.session_state.messages.append({"role": "user", "content": user_input.strip()})

        # Call the backend
        with st.spinner("Thinking..."):
            try:
                result = send_chat(user_input.strip())
                st.session_state.messages.append({
                    "role":    "assistant",
                    "content": result["answer"],
                    "route":   result.get("agent_used", "unknown"),
                })
            except Exception as e:
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": f"Error: {e}",
                    "route": "error",
                })

        # Rerun once — the for loop above will render everything cleanly
        st.rerun()