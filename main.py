import os
import azure.cognitiveservices.speech as speechsdk
# Import Response instead of StreamingResponse
from fastapi import FastAPI, File, UploadFile, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
import io
from dotenv import load_dotenv
import wave

# ... (imports for AI Agent are correct) ...
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from azure.ai.agents.models import ListSortOrder

# ... (Configuration section is correct, no changes needed) ...
# --- 1. Configuration ---
load_dotenv()

# Speech Service Config
SPEECH_KEY = os.environ.get('SPEECH_KEY')
SPEECH_REGION = os.environ.get('SPEECH_REGION')
SPEECH_ENDPOINT = os.environ.get('SPEECH_ENDPOINT')

if not SPEECH_KEY or not SPEECH_REGION:
    raise RuntimeError("SPEECH_KEY and SPEECH_REGION environment variables are required.")

if SPEECH_ENDPOINT:
    speech_config = speechsdk.SpeechConfig(endpoint=SPEECH_ENDPOINT, subscription=SPEECH_KEY)
else:
    speech_config = speechsdk.SpeechConfig(subscription=SPEECH_KEY, region=SPEECH_REGION)

speech_config.set_speech_synthesis_output_format(speechsdk.SpeechSynthesisOutputFormat.Riff24Khz16BitMonoPcm)

# --- New Azure AI Agent Config ---
AI_PROJECT_ENDPOINT = os.environ.get("AI_PROJECT_ENDPOINT")
AGENT_ID = os.environ.get("AGENT_ID")

if not AI_PROJECT_ENDPOINT or not AGENT_ID:
    raise RuntimeError("AI_PROJECT_ENDPOINT and AGENT_ID environment variables are required.")

# Initialize the AI Project Client. It will use your logged-in Azure credentials.
try:
    project_client = AIProjectClient(
        credential=DefaultAzureCredential(),
        endpoint=AI_PROJECT_ENDPOINT
    )
except Exception as e:
    print(f"Failed to initialize AIProjectClient. Ensure you are logged into Azure CLI. Error: {e}")
    project_client = None


# --- 2. FastAPI Application Setup ---
app = FastAPI(
    title="Speech-to-Text and Text-to-Speech API",
    description="An API that uses Azure services to transcribe user audio, get a mock response, and synthesize it back to audio.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- 3. Core Service Functions ---
# ... (speech_to_text_from_audio_data and text_to_speech_to_stream are correct, no changes needed) ...
async def speech_to_text_from_audio_data(audio_data: bytes) -> str:
    """
    Converts speech from in-memory audio data (in WAV format) to text using Azure Speech Service.
    This version dynamically configures the audio stream format based on the WAV file's properties.
    """
    
    # Use the 'wave' module to read the WAV file's properties and raw audio data.
    with wave.open(io.BytesIO(audio_data), 'rb') as wave_file:
        frame_rate = wave_file.getframerate()
        sample_width = wave_file.getsampwidth()
        n_channels = wave_file.getnchannels()
        bits_per_sample = sample_width * 8
        
        # Read the raw audio frames (the actual sound data)
        frames = wave_file.readframes(wave_file.getnframes())

    # --- Create an AudioStreamFormat object to describe the raw audio ---
    # This is the crucial step. We are telling the SDK exactly what kind of audio to expect.
    stream_format = speechsdk.audio.AudioStreamFormat(
        samples_per_second=frame_rate,
        bits_per_sample=bits_per_sample,
        channels=n_channels
    )

    # --- Use a PushAudioInputStream with the specified format ---
    push_stream = speechsdk.audio.PushAudioInputStream(stream_format)
    audio_config = speechsdk.audio.AudioConfig(stream=push_stream)
    
    speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)
    
    # Write the raw audio frames (without the header) to the push stream.
    push_stream.write(frames)
    # Close the stream to signal that we have sent all the audio data.
    push_stream.close()
    
    # Perform a single, non-blocking recognition.
    result = speech_recognizer.recognize_once_async().get()
    
    # Check the result
    if result.reason == speechsdk.ResultReason.RecognizedSpeech:
        print(f"Recognized: {result.text}") # Added for debugging
        return result.text
    elif result.reason == speechsdk.ResultReason.NoMatch:
        print("No speech could be recognized.") # Added for debugging
        raise HTTPException(status_code=400, detail="No speech could be recognized.")
    elif result.reason == speechsdk.ResultReason.Canceled:
        cancellation_details = result.cancellation_details
        error_details = cancellation_details.error_details
        print(f"Speech Recognition canceled: {cancellation_details.reason}. Error: {error_details}") # Added for debugging
        raise HTTPException(status_code=500, detail=f"Speech Recognition canceled: {cancellation_details.reason}. Error: {error_details}")
    
    return ""

def text_to_speech_to_stream(text: str) -> io.BytesIO:
    """
    Converts text to speech and returns it as an in-memory audio stream (BytesIO).
    This version uses the recommended method for in-memory synthesis.
    """
    # By setting audio_config to None, the SpeechSynthesizer will return the
    # synthesized audio in memory on the result object.
    speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)
    
    result = speech_synthesizer.speak_text_async(text).get()
    
    # Check the result
    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        # The synthesized audio is available in result.audio_data as a bytes object.
        return io.BytesIO(result.audio_data)
    elif result.reason == speechsdk.ResultReason.Canceled:
        cancellation_details = result.cancellation_details
        raise HTTPException(status_code=500, detail=f"Text-to-Speech canceled: {cancellation_details.reason}. Error: {cancellation_details.error_details}")
        
    return None

def get_agent_response(user_text: str) -> str:
    """
    Calls the Azure AI Agent, sends the user's text, and returns the agent's response.
    """
    if not project_client:
        return "Error: AI Project Client is not initialized. Check server logs."

    print(f"User said: '{user_text}'")
    
    try:
        # 1. Create a new thread for this interaction
        thread = project_client.agents.threads.create()
        print(f"Created thread, ID: {thread.id}")

        # 2. Add the user's message to the thread
        project_client.agents.messages.create(
            thread_id=thread.id,
            role="user",
            content=user_text
        )

        # 3. Run the agent and wait for it to process the message
        run = project_client.agents.runs.create_and_process(
            thread_id=thread.id,
            agent_id=AGENT_ID
        )

        if run.status == "failed":
            print(f"Run failed: {run.last_error}")
            return f"The agent encountered an error: {run.last_error}"
        
        # 4. Get all messages from the thread in DESCENDING order (newest first)
        messages = project_client.agents.messages.list(thread_id=thread.id, order=ListSortOrder.DESCENDING)
        
        # Find the first message from the assistant, which will be the latest one.
        assistant_response = "Sorry, I couldn't get a response."
        for message in messages:
            if message.role == "assistant" and message.text_messages:
                assistant_response = message.text_messages[-1].text.value
                break # Found the latest response, no need to continue
        
        print(f"Agent responded: '{assistant_response}'")
        return assistant_response

    except Exception as e:
        print(f"An error occurred while interacting with the AI Agent: {e}")
        return "I'm sorry, but I encountered an error while trying to process your request."

# --- 4. API Endpoint ---

@app.post("/api/chat")
async def chat_endpoint(request: Request, file: UploadFile = File(...)):
    """
    The main endpoint to handle the chat workflow.
    """
    try:
        audio_data = await file.read()
        user_text = await speech_to_text_from_audio_data(audio_data)
        if not user_text:
            raise HTTPException(status_code=400, detail="Could not understand the audio.")

        agent_response_text = get_agent_response(user_text)
        audio_response_stream = text_to_speech_to_stream(agent_response_text)
        
        # --- THE FIX ---
        # Get the complete audio data as bytes
        audio_bytes = audio_response_stream.getvalue()
        # Return a regular Response with the full content and length, not a stream.
        return Response(content=audio_bytes, media_type="audio/wav")

    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        raise HTTPException(status_code=500, detail=f"An internal server error occurred. Details: {str(e)}")

@app.get("/")
def read_root():
    return {"message": "Welcome to the STT-TTS API. Use the /api/chat endpoint to interact."}