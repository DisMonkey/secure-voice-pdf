import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
from gtts import gTTS
import io
import base64

# --- PRODUCTION CONFIG ---
st.set_page_config(page_title="SecureVoice PDF", page_icon="🛡️", layout="wide")

# 1. Access the Secrets Vault
if "GOOGLE_API_KEY" not in st.secrets:
    st.error("Missing GOOGLE_API_KEY in Streamlit Secrets!")
    st.stop()

genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-flash-latest')

# --- ARCHITECTED UTILITIES ---
def get_audio_html(text):
    """Generates an in-memory audio player."""
    if not text: return ""
    try:
        tts = gTTS(text=text[:2000], lang='en')
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        audio_b64 = base64.b64encode(fp.getvalue()).decode()
        return f'<audio controls src="data:audio/mp3;base64,{audio_b64}">'
    except Exception as e:
        return f"Audio Error: {e}"

def extract_pdf_text(file):
    """Extracts text from all pages."""
    reader = PdfReader(file)
    return "\n".join([page.extract_text() or "" for page in reader.pages])

# --- SESSION INITIALIZATION ---
if "pdf_text" not in st.session_state: st.session_state.pdf_text = None
if "summary" not in st.session_state: st.session_state.summary = None
if "chat_history" not in st.session_state: st.session_state.chat_history = []

# --- UI LAYOUT ---
st.title("🛡️ SecureVoice PDF")
st.caption("Universal PDF Intelligence | RAM-Only Privacy")

with st.sidebar:
    st.header("1. Upload")
    uploaded_file = st.file_uploader("Upload your PDF", type="pdf")
    
    if st.button("🗑️ Reset All Data"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

# --- CORE LOGIC ---
if uploaded_file:
    # A. Initial Processing
    if st.session_state.pdf_text is None:
        with st.spinner("🔍 AI is reading and summarizing..."):
            raw_text = extract_pdf_text(uploaded_file)
            if not raw_text.strip():
                st.error("This PDF seems to be an image/scan. Please use a text-based PDF.")
                st.stop()
            
            st.session_state.pdf_text = raw_text
            # Automatic Summary
            summary_prompt = f"Summarize this document in 5 key bullet points:\n\n{raw_text[:12000]}"
            st.session_state.summary = model.generate_content(summary_prompt).text

    # B. Display Summary & Voice
    st.subheader("📄 AI Document Summary")
    st.write(st.session_state.summary)
    
    # We use a unique key for the button so it doesn't conflict
    if st.button("🔊 Play Summary", key="play_summary"):
        st.components.v1.html(get_audio_html(st.session_state.summary), height=60)

    st.divider()

    # C. Persistent Chat Interface
    st.subheader("💬 Ask Questions")
    
    # Display the conversation
    for i, chat in enumerate(st.session_state.chat_history):
        with st.chat_message(chat["role"]):
            st.write(chat["content"])
            if chat["role"] == "assistant":
                # Voice button for previous answers
                if st.button(f"🔊 Replay Answer {i}", key=f"replay_{i}"):
                    st.components.v1.html(get_audio_html(chat["content"]), height=60)

    # Chat Input
    if user_query := st.chat_input("What else would you like to know?"):
        # Add user message
        st.session_state.chat_history.append({"role": "user", "content": user_query})
        
        # Get AI Response
        context = f"Context: {st.session_state.pdf_text[:15000]}\n\nQuestion: {user_query}"
        response_text = model.generate_content(context).text
        
        # Add assistant message
        st.session_state.chat_history.append({"role": "assistant", "content": response_text})
        st.rerun() # Refresh to show the new chat message immediately

else:
    st.info("👋 Welcome! Please upload a PDF in the sidebar to generate a summary and start chatting.")
