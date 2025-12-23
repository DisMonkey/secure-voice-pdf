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
# Using the most stable model name
model = genai.GenerativeModel('gemini-1.5-flash-latest')

def get_audio_html(text):
    if not text or text == "None": return ""
    try:
        tts = gTTS(text=text[:2000], lang='en')
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        audio_b64 = base64.b64encode(fp.getvalue()).decode()
        return f'<audio controls src="data:audio/mp3;base64,{audio_b64}">'
    except: return "Audio error."

def extract_robust_text(file):
    reader = PdfReader(file)
    text_parts = []
    for page in reader.pages:
        t = page.extract_text()
        if t: text_parts.append(t)
    return "\n".join(text_parts)

# --- STATE INITIALIZATION ---
if "pdf_text" not in st.session_state: st.session_state.pdf_text = None
if "summary" not in st.session_state: st.session_state.summary = None
if "chat_history" not in st.session_state: st.session_state.chat_history = []

st.title("🛡️ SecureVoice PDF")

with st.sidebar:
    st.header("Upload")
    uploaded_file = st.file_uploader("Choose a PDF", type="pdf")
    if st.button("🗑️ Reset App"):
        st.session_state.clear()
        st.rerun()

if uploaded_file:
    # Only process if we haven't already
    if st.session_state.pdf_text is None:
        with st.spinner("🔍 Reading PDF..."):
            extracted = extract_robust_text(uploaded_file)
            
            if not extracted.strip():
                st.error("❌ This PDF appears to be a scanned image or empty. I cannot read text from it.")
                st.session_state.pdf_text = "EMPTY_ERROR"
            else:
                st.session_state.pdf_text = extracted
                # Immediate Summary Generation
                prompt = f"Summarize this PDF in 5 bullet points for a voice summary:\n\n{extracted[:15000]}"
                response = model.generate_content(prompt)
                st.session_state.summary = response.text

    # DISPLAY RESULTS
    if st.session_state.summary and st.session_state.pdf_text != "EMPTY_ERROR":
        st.subheader("📄 AI Summary")
        st.write(st.session_state.summary)
        if st.button("🔊 Play Summary Audio"):
            st.components.v1.html(get_audio_html(st.session_state.summary), height=60)
        
        st.divider()
        st.subheader("💬 Ask Questions")
        for chat in st.session_state.chat_history:
            with st.chat_message(chat["role"]): st.write(chat["content"])

        if user_q := st.chat_input("Ask a question..."):
            st.session_state.chat_history.append({"role": "user", "content": user_q})
            with st.chat_message("user"): st.write(user_q)
            
            context = f"PDF Context: {st.session_state.pdf_text[:15000]}\n\nQuestion: {user_q}"
            ai_ans = model.generate_content(context).text
            
            with st.chat_message("assistant"):
                st.write(ai_ans)
                if st.button("🔊 Play Answer"):
                    st.components.v1.html(get_audio_html(ai_ans), height=60)
            st.session_state.chat_history.append({"role": "assistant", "content": ai_ans})
else:
    st.info("Upload a PDF to start.")
