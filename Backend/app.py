import os
import base64
import requests
import tempfile
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from google import genai
from flask_cors import CORS

load_dotenv()

frontend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Frontend")
if not os.path.isdir(frontend_dir):
    frontend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend")

app = Flask(__name__, static_folder=frontend_dir, static_url_path="")
CORS(app)

@app.route("/")
def index():
    return app.send_static_file("index.html")

MURF_API_KEY = os.environ.get("MURF_API_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

client = genai.Client(api_key=GEMINI_API_KEY)

PROMPTS = {
    "Summary": """
        You are a professional tourist guide.
Provide a high-level overview of "{place}" in {language}.

Focus on:
- The historical significance
- Why the place is famous
- Key architectural or cultural highlights

Keep the explanation concise, engaging, and easy to follow.
Avoid excessive details and dates.
Limit the response to around 200 words.

Respond ONLY in {language}.
    """,
    "Detailed": """
        You are a professional tourist guide.
Provide a detailed and immersive explanation of "{place}" in {language}.

Cover:
- Historical background and timeline
- Architectural design and unique features
- Cultural importance and notable events
- Interesting facts and visitor insights

Explain concepts clearly and in a storytelling manner.
Include relevant details and examples to create a rich experience.
Limit the response to around 400 words.

Respond ONLY in {language}.
    """
}

def generate_description(place, answer_type, language):
    prompt = PROMPTS[answer_type].format(place=place, language=language)
    response = client.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents=prompt
    )
    return response.text

# Step 3 — Generate speech with Murf.AI Falcon
def generate_speech(text, voice_id, locale):
    url = "https://global.api.murf.ai/v1/speech/stream"
    headers = {
        "api-key": MURF_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "text": text,
        "voiceId": voice_id,
        "locale": locale,
        "format": "MP3",
    }
    response = requests.post(url, json=payload, headers=headers)
    # Save audio to a temporary file
    temp_audio = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
    temp_audio.write(response.content)
    temp_audio.close()
    return temp_audio.name

# Step 2 & Step 4 — Backend extracts voice settings and encodes audio as Base64
@app.route("/generate-audio-guide", methods=["POST"])
def generate_audio_guide():
    data = request.json
    place = data["place"]
    answer_type = data["answerType"]
    language = data["language"]
    voice_id = data["voiceId"]
    locale = data["locale"]

    # Step 1: Generate text description
    description = generate_description(place, answer_type, language)

    # Step 2: Convert text to speech
    audio_path = generate_speech(description, voice_id, locale)

    # Step 3: Encode audio as Base64
    with open(audio_path, "rb") as audio_file:
        audio_base64 = base64.b64encode(audio_file.read()).decode("utf-8")

    return jsonify({
        "description": description,
        "audio": audio_base64,
    })

if __name__ == "__main__":
    app.run(debug=True)