import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
from gtts import gTTS
import io
import base64

# --- PRODUCTION CONFIG ---
st.set_page_config(page_title="SecureVoice PDF", page_icon="🛡️", layout="wide")

if "GOOGLE_API_KEY" not in st.secrets:
    st.error("Missing API Key! Please add it to Streamlit Secrets.")
    st.stop()

genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
model = genai.GenerativeModel('gemini-2.5-flash') # Using the latest 2025 model

# --- UPDATED VOICE UTILITY ---
def get_audio_html(text, lang_code):
    """Generates audio with correct language accent."""
    if not text: return ""
    try:
        tts = gTTS(text=text[:1500], lang=lang_code)
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        audio_b64 = base64.b64encode(fp.getvalue()).decode()
        return f'<audio controls autoplay src="data:audio/mp3;base64,{audio_b64}">'
    except Exception as e:
        return f"Audio Error: {e}"

def extract_pdf_text(file):
    reader = PdfReader(file)
    return "\n".join([page.extract_text() or "" for page in reader.pages])

# --- SESSION INITIALIZATION ---
if "pdf_text" not in st.session_state: st.session_state.pdf_text = None
if "summary" not in st.session_state: st.session_state.summary = None
if "chat_history" not in st.session_state: st.session_state.chat_history = []

# --- UI LAYOUT ---
st.title("🛡️ SecureVoice PDF")

with st.sidebar:
    st.header("1. Settings")
    # NEW: Language Selector
    app_lang = st.selectbox("Preferred Language / Idioma", ["English", "Spanish"])
    lang_code = 'en' if app_lang == "English" else 'es'
    
    uploaded_file = st.file_uploader("Upload PDF", type="pdf")
    
    if st.button("🗑️ Reset Application"):
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()

# --- CORE LOGIC ---
if uploaded_file:
    if st.session_state.pdf_text is None:
        with st.spinner("🔍 Analyzing..."):
            raw_text = extract_pdf_text(uploaded_file)
            if not raw_text.strip():
                st.error("Could not read text. Is this a scan?")
                st.stop()
            st.session_state.pdf_text = raw_text
            
            # Smart Prompt: Telling AI which language to use
            prompt = f"Summarize this in 5 bullets. IMPORTANT: Provide the summary in {app_lang}:\n\n{raw_text[:10000]}"
            st.session_state.summary = model.generate_content(prompt).text

    # Display Summary
    st.subheader(f"📄 {'AI Summary' if lang_code == 'en' else 'Resumen de IA'}")
    st.write(st.session_state.summary)
    if st.button(f"🔊 {'Play Summary' if lang_code == 'en' else 'Reproducir Resumen'}"):
        st.components.v1.html(get_audio_html(st.session_state.summary, lang_code), height=60)

    st.divider()

    # Chat Interface
    st.subheader(f"💬 {'Ask Questions' if lang_code == 'en' else 'Hacer Preguntas'}")
    for i, chat in enumerate(st.session_state.chat_history):
        with st.chat_message(chat["role"]):
            st.write(chat["content"])
            if chat["role"] == "assistant":
                if st.button(f"🔊 Replay {i}", key=f"v_{i}"):
                    st.components.v1.html(get_audio_html(chat["content"], lang_code), height=60)

    if user_query := st.chat_input("Ask a question..."):
        st.session_state.chat_history.append({"role": "user", "content": user_query})
        
        # Smart Context: AI responds in the selected language
        context_prompt = f"Context: {st.session_state.pdf_text[:12000]}\nQuestion: {user_query}\nIMPORTANT: Respond in {app_lang}."
        
        response = model.generate_content(context_prompt).text
        st.session_state.chat_history.append({"role": "assistant", "content": response})
        st.rerun()
else:
    st.info("👋 Please upload a PDF to begin.")
