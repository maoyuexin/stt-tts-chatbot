import streamlit as st
from st_audiorec import st_audiorec
import requests
import io

# --- UI Setup ---
st.set_page_config(page_title="Voice Assistant", layout="centered")

# --- Configuration ---
BACKEND_URL = "http://127.0.0.1:8000/api/chat"

# --- Custom CSS to hide unwanted buttons ---
# This CSS is more specific and forceful to ensure the buttons are hidden.
st.markdown("""
<style>
/* Target the 3rd and 4th buttons within the audio recorder component */
div[data-testid="stAudioRecMic"] button:nth-of-type(3),
div[data-testid="stAudioRecMic"] button:nth-of-type(4) {
    display: none !important;
}

/* Also hide the small audio player that appears after recording */
div[data-testid="stAudioRecMic"] > audio {
    display: none !important;
}
</style>
""", unsafe_allow_html=True)

st.title("🎙️ Voice Assistant")
st.markdown("Click 'Start Recording' to begin.")

# --- Session State Initialization ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "last_audio" not in st.session_state:
    st.session_state.last_audio = None
if "audio_to_play" not in st.session_state:
    st.session_state.audio_to_play = None

# --- Display Chat History ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.audio(message["audio"], format="audio/wav")

# --- Autoplay Handler ---
if st.session_state.audio_to_play:
    st.audio(st.session_state.audio_to_play, format="audio/wav", autoplay=True)
    st.session_state.audio_to_play = None

# --- Audio Recorder UI ---
wav_audio_data = st_audiorec()

# --- Main Logic ---
if wav_audio_data is not None and wav_audio_data != st.session_state.last_audio:
    st.session_state.last_audio = wav_audio_data
    
    with st.chat_message("user"):
        st.audio(wav_audio_data, format="audio/wav")
    st.session_state.messages.append({"role": "user", "audio": wav_audio_data})

    try:
        with st.spinner("Thinking..."):
            files = {'file': ('audio.wav', io.BytesIO(wav_audio_data), 'audio/wav')}
            response = requests.post(BACKEND_URL, files=files, timeout=60)

        if response.status_code == 200:
            assistant_audio_bytes = response.content
            with st.chat_message("assistant"):
                st.audio(assistant_audio_bytes, format="audio/wav")
            st.session_state.messages.append({"role": "assistant", "audio": assistant_audio_bytes})
            st.session_state.audio_to_play = assistant_audio_bytes
            
        else:
            st.error(f"Error from server: {response.status_code} - {response.text}")

    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")

# The sidebar code has been completely removed.