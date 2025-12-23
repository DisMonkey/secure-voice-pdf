import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
from gtts import gTTS
import io
import base64

# --- PRODUCTION CONFIG ---
st.set_page_config(page_title="SecureVoice PDF", page_icon="🛡️", layout="wide")

# 1. API Security
if "GOOGLE_API_KEY" not in st.secrets:
    st.error("Missing API Key! Please go to Settings > Secrets in Streamlit.")
    st.stop()

genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
model = genai.GenerativeModel('gemini-2.5-flash')

# --- ARCHITECTED UTILITIES ---
def get_audio_html(text):
    """Generates an in-memory audio player without touching disk."""
    if not text: return ""
    try:
        # Optimization: Limit TTS to 1500 chars for mobile speed
        tts = gTTS(text=text[:1500], lang='en')
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        audio_b64 = base64.b64encode(fp.getvalue()).decode()
        return f'<audio controls autoplay src="data:audio/mp3;base64,{audio_b64}">'
    except Exception as e:
        return f"Audio Error: {e}"

def extract_pdf_text(file):
    """Extracts text from all available PDF pages."""
    try:
        reader = PdfReader(file)
        text = ""
        for page in reader.pages:
            content = page.extract_text()
            if content: text += content + "\n"
        return text
    except Exception as e:
        st.error(f"Error reading PDF: {e}")
        return None

# --- SESSION INITIALIZATION ---
if "pdf_text" not in st.session_state: st.session_state.pdf_text = None
if "summary" not in st.session_state: st.session_state.summary = None
if "chat_history" not in st.session_state: st.session_state.chat_history = []

# --- UI LAYOUT ---
st.title("🛡️ SecureVoice PDF")
st.caption("Universal PDF Intelligence | RAM-Only Privacy | Voice Enabled")

with st.sidebar:
    st.header("1. Upload")
    uploaded_file = st.file_uploader("Upload your PDF (Multi-page)", type="pdf")
    
    if st.button("🗑️ Reset Application"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
    
    st.divider()
    st.info("🔒 Files are processed in memory and never stored.")

# --- CORE LOGIC ---
if uploaded_file:
    # A. PDF Digestion & Automatic Summary
    if st.session_state.pdf_text is None:
        with st.spinner("🔍 Reading and Summarizing..."):
            raw_text = extract_pdf_text(uploaded_file)
            if not raw_text or not raw_text.strip():
                st.error("Could not extract text. This might be a scanned image.")
                st.stop()
            
            st.session_state.pdf_text = raw_text
            # Automatic Summary Generation
            prompt = f"Summarize this document in 5 key bullet points for a quick read:\n\n{raw_text[:10000]}"
            st.session_state.summary = model.generate_content(prompt).text
            st.toast("Document Analyzed!", icon="✅")

    # B. Document Summary Section
    st.subheader("📄 AI Document Summary")
    st.markdown(st.session_state.summary)
    
    if st.button("🔊 Play Summary"):
        st.components.v1.html(get_audio_html(st.session_state.summary), height=60)

    st.divider()

    # C. Question & Answer Interface
    st.subheader("💬 Ask Questions")
    
    # Display historical chat
    for i, chat in enumerate(st.session_state.chat_history):
        with st.chat_message(chat["role"]):
            st.write(chat["content"])
            if chat["role"] == "assistant":
                if st.button(f"🔊 Play Answer {i}", key=f"ans_{i}"):
                    st.components.v1.html(get_audio_html(chat["content"]), height=60)

    # Chat Interaction
    if user_query := st.chat_input("Ask a question about this document..."):
        st.session_state.chat_history.append({"role": "user", "content": user_query})
        
        # Build context-aware query
        context_prompt = f"Using the following context, answer the user's question:\n\nCONTEXT: {st.session_state.pdf_text[:15000]}\n\nQUESTION: {user_query}"
        
        with st.spinner("AI is thinking..."):
            response = model.generate_content(context_prompt)
            st.session_state.chat_history.append({"role": "assistant", "content": response.text})
            st.rerun()

else:
    st.info("👋 Welcome! Please upload a PDF in the sidebar to generate a summary and start chatting.")
