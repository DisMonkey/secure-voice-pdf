import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
from gtts import gTTS
import io
import base64

# --- PRODUCTION CONFIGURATION ---
st.set_page_config(page_title="SecureVoice PDF", page_icon="🛡️", layout="wide")

# Link to the Secrets Vault
if "GOOGLE_API_KEY" not in st.secrets:
    st.error("⚠️ API Key Missing! Please add GOOGLE_API_KEY to your Streamlit Secrets.")
    st.stop()

genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-flash-latest')

# --- ARCHITECTED UTILITIES ---
def get_audio_html(text):
    """Converts text to speech in RAM and returns an HTML audio player."""
    if not text: return ""
    try:
        tts = gTTS(text=text[:2500], lang='en') # Optimized length for speed
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        audio_b64 = base64.b64encode(fp.getvalue()).decode()
        return f'<audio controls src="data:audio/mp3;base64,{audio_b64}">'
    except Exception as e:
        return f"Error generating audio: {e}"

def extract_pdf_text(file):
    """Robustly extracts text from all pages of the PDF."""
    reader = PdfReader(file)
    text = ""
    for page in reader.pages:
        extracted = page.extract_text()
        if extracted:
            text += extracted + "\n"
    return text

# --- SESSION STORAGE ---
if "pdf_text" not in st.session_state: st.session_state.pdf_text = None
if "summary" not in st.session_state: st.session_state.summary = None
if "chat_history" not in st.session_state: st.session_state.chat_history = []

# --- UI INTERFACE ---
st.title("🛡️ SecureVoice PDF")
st.caption("Production-Ready • Private RAM Processing • AI Voice Summary")

with st.sidebar:
    st.header("1. Upload Document")
    uploaded_file = st.file_uploader("Drop any PDF here", type="pdf")
    
    if st.button("🗑️ Clear All Data"):
        for key in st.session_state.keys(): del st.session_state[key]
        st.rerun()
    
    st.markdown("---")
    st.markdown("### Privacy Shield")
    st.info("Files are processed in memory and never written to disk.")

# --- CORE LOGIC ---
if uploaded_file:
    # STEP 1: Process and Auto-Summarize
    if st.session_state.pdf_text is None:
        with st.spinner("AI is analyzing your document..."):
            extracted_text = extract_pdf_text(uploaded_file)
            st.session_state.pdf_text = extracted_text
            
            # AI Summary Generation
            summary_prompt = f"Summarize this document clearly for a mobile user. Use bullet points:\n\n{extracted_text[:15000]}"
            summary_res = model.generate_content(summary_prompt)
            st.session_state.summary = summary_res.text

    # STEP 2: Display Summary & TTS Button
    st.subheader("📄 AI Summary")
    st.write(st.session_state.summary)
    
    if st.button("🔊 Play Summary Audio"):
        audio_player = get_audio_html(st.session_state.summary)
        st.components.v1.html(audio_player, height=60)

    st.divider()

    # STEP 3: Interactive Chat
    st.subheader("💬 Ask Questions")
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if user_input := st.chat_input("Ask a question about this PDF..."):
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            context = f"Context: {st.session_state.pdf_text[:15000]}\n\nQuestion: {user_input}"
            response = model.generate_content(context).text
            st.markdown(response)
            
            # TTS for the Chat Response
            if st.button("🔊 Play Answer"):
                audio_player = get_audio_html(response)
                st.components.v1.html(audio_player, height=60)
                
        st.session_state.chat_history.append({"role": "assistant", "content": response})
else:
    st.info("👋 Upload a PDF to see the AI Summary and use the Voice features.")
