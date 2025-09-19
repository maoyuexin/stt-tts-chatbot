# Voice-Enabled AI Assistant with Azure AI

This project is a proof-of-concept for a voice-enabled chatbot. It features a web-based user interface built with Streamlit that accepts voice input and provides spoken responses. The backend, built with FastAPI, orchestrates Azure AI services for speech-to-text, text-to-speech, and intelligent response generation via a custom Azure AI Agent.

## Features

-   **Voice-First Interface**: Interact with the assistant using your voice.
-   **Real-time Transcription & Synthesis**: Leverages Azure AI Speech for fast and accurate STT and TTS.
-   **Intelligent Responses**: Connects to a custom Azure AI Agent to answer complex queries and perform actions.
-   **Web-Based UI**: A clean and modern chat interface built with Streamlit.
-   **Asynchronous Backend**: Built with FastAPI for efficient handling of requests.

## Architecture

The application consists of two main components: a frontend web application and a backend API.

1.  **Streamlit Frontend (`app.py`)**:
    -   Captures audio from the user's microphone using `streamlit-webrtc`.
    -   Displays the conversation history.
    -   Sends the recorded audio to the backend and plays the returned audio response.

2.  **FastAPI Backend (`main.py`)**:
    -   Exposes a `/api/chat` endpoint that accepts audio files.
    -   **Speech-to-Text**: Uses the Azure AI Speech SDK to transcribe the user's audio into text.
    -   **Agent Logic**: Sends the transcribed text to a pre-configured Azure AI Agent to generate a response.
    -   **Text-to-Speech**: Uses the Azure AI Speech SDK to convert the agent's text response back into high-quality audio.
    -   Returns the synthesized audio to the frontend.

## Prerequisites

Before you begin, ensure you have the following installed and configured:

-   Python 3.9+
-   An Azure Subscription.
-   **Azure AI Speech Service**: A deployed Speech resource in your Azure subscription.
-   **Azure AI Agent**: An existing agent in an Azure AI Studio project.
-   **FFmpeg**: This is required by the `pydub` library for audio processing.
    -   Download from [ffmpeg.org](https://ffmpeg.org/download.html).
    -   Install it and ensure the `bin` directory is added to your system's PATH.
-   **Azure CLI**: Make sure you are logged in with `az login`.

## Setup Instructions

1.  **Clone the Repository**
    ```bash
    # This project is not yet in a repo, so you can start by initializing one.
    git init
    ```

2.  **Create a Virtual Environment**
    It's highly recommended to use a virtual environment to manage dependencies.
    ```bash
    # On Windows
    python -m venv .venv
    .venv\Scripts\activate

    # On macOS/Linux
    python -m venv .venv
    source .venv/bin/activate
    ```

3.  **Install Dependencies**
    Install all required Python packages from the `requirements.txt` file.
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment Variables**
    Create a file named `.env` in the `STT-TTS-chatbot` directory by copying the example below. Fill in the values from your Azure resources.

    ```env
    # .env file

    # Azure AI Speech Service Configuration
    SPEECH_KEY="YOUR_AZURE_SPEECH_KEY"
    SPEECH_REGION="YOUR_AZURE_SPEECH_REGION"

    # Azure AI Agent Configuration
    AI_PROJECT_ENDPOINT="YOUR_AZURE_AI_PROJECT_ENDPOINT" # e.g., https://your-resource.services.ai.azure.com
    AGENT_ID="YOUR_AGENT_ID" # e.g., asst_xxxxxxxxxxxxxxxx
    ```

## Running the Application

You need to run the backend and frontend in two separate terminals.

1.  **Start the Backend Server**
    In your first terminal, make sure your virtual environment is active and run:
    ```bash
    uvicorn main:app --reload
    ```
    The backend will be available at `http://127.0.0.1:8000`.

2.  **Start the Frontend Application**
    In a second terminal, activate the same virtual environment and run:
    ```bash
    streamlit run app.py
    ```
    Your web browser should open with the voice assistant interface.

---

I also highly recommend creating a `.gitignore` file to prevent sensitive information and unnecessary files from being committed to your repository.

````text
// filepath: c:\Users\yuexinmao\Documents\Code\multi-agent-accelerator\customer_workshop\STT-TTS-chatbot\.gitignore
# Environment variables
.env

# Python cache
__pycache__/
*.pyc

# VS Code settings
.vscode/

# Virtual environment
.venv/
venv/