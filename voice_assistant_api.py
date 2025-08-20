from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import logging
import os
import tempfile
import base64
from werkzeug.utils import secure_filename
import io
import threading
import asyncio
import concurrent.futures
from functools import lru_cache

from voice_assistant.audio import record_audio, play_audio
from voice_assistant.transcription import transcribe_audio
from voice_assistant.response_generation import generate_response
from voice_assistant.text_to_speech import text_to_speech
from voice_assistant.utils import delete_file
from voice_assistant.config import Config
from voice_assistant.api_key_manager import get_transcription_api_key, get_response_api_key, get_tts_api_key
from voice_assistant.optimized_transcription import transcribe_with_cached_deepgram
from voice_assistant.optimized_response import generate_response_with_cached_groq
from voice_assistant.optimized_tts import tts_with_cached_deepgram

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)
CORS(app)

# Performance optimizations
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.config['TEMPLATES_AUTO_RELOAD'] = False

# Thread pool for concurrent processing
executor = concurrent.futures.ThreadPoolExecutor(max_workers=6)

# Global clients for connection reuse (major latency improvement)
global_clients = {
    'deepgram': None,
    'groq': None,
    'openai': None
}

def get_cached_deepgram_client():
    """Get cached Deepgram client for connection reuse"""
    if global_clients['deepgram'] is None:
        from deepgram import DeepgramClient
        global_clients['deepgram'] = DeepgramClient(get_cached_transcription_api_key())
    return global_clients['deepgram']

def get_cached_groq_client():
    """Get cached Groq client for connection reuse"""
    if global_clients['groq'] is None:
        from groq import Groq
        global_clients['groq'] = Groq(api_key=get_cached_response_api_key())
    return global_clients['groq']

def get_cached_openai_client():
    """Get cached OpenAI client for connection reuse"""
    if global_clients['openai'] is None:
        from openai import OpenAI
        global_clients['openai'] = OpenAI(api_key=get_cached_tts_api_key())
    return global_clients['openai']

# Global chat history for maintaining conversation context
chat_history = [
    {"role": "system", "content": """ You are a UAE Property Assistant called Verbi. 
     You are professional and very concise, specializing in UAE real estate information.
     You can help users with property queries, greetings, pricing, and accounting questions.
     Provide very short answers under 25 words. Key facts only. """}
]

# Cache for API keys to avoid repeated lookups
@lru_cache(maxsize=10)
def get_cached_transcription_api_key():
    return get_transcription_api_key()

@lru_cache(maxsize=10)
def get_cached_response_api_key():
    return get_response_api_key()

@lru_cache(maxsize=10)
def get_cached_tts_api_key():
    return get_tts_api_key()

# Configure upload folder
UPLOAD_FOLDER = 'temp_uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

ALLOWED_EXTENSIONS = {'wav', 'mp3', 'm4a', 'flac', 'ogg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET'])
def root():
    """Serve the voice agent HTML page"""
    return send_file('voice_agent.html')

@app.route('/api-info', methods=['GET'])
def api_info():
    """API information endpoint"""
    return jsonify({
        'message': 'Voice Assistant API',
        'version': '1.0',
        'endpoints': {
            'health': '/health',
            'transcribe': '/transcribe (POST)',
            'chat': '/chat (POST)',
            'tts': '/tts (POST)',
            'voice-chat': '/voice-chat (POST)',
            'chat-history': '/chat-history (GET/DELETE)'
        }
    })

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'message': 'Voice Assistant API is running',
        'config': {
            'transcription_model': Config.TRANSCRIPTION_MODEL,
            'response_model': Config.RESPONSE_MODEL,
            'tts_model': Config.TTS_MODEL
        }
    })

@app.route('/transcribe', methods=['POST'])
def transcribe_endpoint():
    """Transcribe audio file to text"""
    try:
        if 'audio' not in request.files:
            return jsonify({'error': 'No audio file provided'}), 400
        
        file = request.files['audio']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type. Allowed: wav, mp3, m4a, flac, ogg'}), 400
        
        # Save uploaded file temporarily
        filename = secure_filename(file.filename)
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(temp_path)
        
        # Get API key and transcribe (optimized)
        transcription_api_key = get_cached_transcription_api_key()
        transcription = transcribe_audio(
            Config.TRANSCRIPTION_MODEL, 
            transcription_api_key, 
            temp_path, 
            Config.LOCAL_MODEL_PATH
        )
        
        # Clean up temp file
        delete_file(temp_path)
        
        if not transcription:
            return jsonify({'error': 'No transcription generated'}), 400
        
        return jsonify({
            'transcription': transcription,
            'model': Config.TRANSCRIPTION_MODEL
        })
        
    except Exception as e:
        logging.error(f"Transcription error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/chat', methods=['POST'])
def chat_endpoint():
    """Process text input and generate response"""
    try:
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({'error': 'No message provided'}), 400
        
        user_message = data['message']
        
        # Append user message to chat history
        chat_history.append({"role": "user", "content": user_message})
        
        # Generate response (optimized)
        response_api_key = get_cached_response_api_key()
        response_text = generate_response(
            Config.RESPONSE_MODEL, 
            response_api_key, 
            chat_history, 
            Config.LOCAL_MODEL_PATH
        )
        
        # Append assistant response to chat history
        chat_history.append({"role": "assistant", "content": response_text})
        
        return jsonify({
            'response': response_text,
            'model': Config.RESPONSE_MODEL
        })
        
    except Exception as e:
        logging.error(f"Chat error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/tts', methods=['POST'])
def tts_endpoint():
    """Convert text to speech and return audio file"""
    try:
        data = request.get_json()
        if not data or 'text' not in data:
            return jsonify({'error': 'No text provided'}), 400
        
        text = data['text']
        
        # Determine output file format
        if Config.TTS_MODEL in ['openai', 'elevenlabs', 'melotts', 'cartesia']:
            output_file = 'output.mp3'
        else:
            output_file = 'output.wav'
        
        # Generate speech (optimized)
        tts_api_key = get_cached_tts_api_key()
        text_to_speech(
            Config.TTS_MODEL, 
            tts_api_key, 
            text, 
            output_file, 
            Config.LOCAL_MODEL_PATH
        )
        
        # Read the generated audio file
        with open(output_file, 'rb') as audio_file:
            audio_data = audio_file.read()
        
        # Clean up the file
        delete_file(output_file)
        
        # Return audio as base64 encoded string
        audio_base64 = base64.b64encode(audio_data).decode('utf-8')
        
        return jsonify({
            'audio': audio_base64,
            'format': 'mp3' if output_file.endswith('.mp3') else 'wav',
            'model': Config.TTS_MODEL
        })
        
    except Exception as e:
        logging.error(f"TTS error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/voice-chat', methods=['POST'])
def voice_chat_endpoint():
    """Complete voice chat: transcribe audio, generate response, and return audio"""
    try:
        if 'audio' not in request.files:
            return jsonify({'error': 'No audio file provided'}), 400
        
        file = request.files['audio']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type. Allowed: wav, mp3, m4a, flac, ogg'}), 400
        
        # Save uploaded file temporarily
        filename = secure_filename(file.filename)
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(temp_path)
        
        # Step 1: Transcribe audio
        transcription_api_key = get_transcription_api_key()
        user_input = transcribe_audio(
            Config.TRANSCRIPTION_MODEL, 
            transcription_api_key, 
            temp_path, 
            Config.LOCAL_MODEL_PATH
        )
        
        # Clean up input audio file
        delete_file(temp_path)
        
        if not user_input:
            return jsonify({'error': 'No transcription generated'}), 400
        
        # Step 2: Generate response
        chat_history.append({"role": "user", "content": user_input})
        response_api_key = get_response_api_key()
        response_text = generate_response(
            Config.RESPONSE_MODEL, 
            response_api_key, 
            chat_history, 
            Config.LOCAL_MODEL_PATH
        )
        chat_history.append({"role": "assistant", "content": response_text})
        
        # Step 3: Convert response to speech
        if Config.TTS_MODEL in ['openai', 'elevenlabs', 'melotts', 'cartesia']:
            output_file = 'output.mp3'
        else:
            output_file = 'output.wav'
        
        tts_api_key = get_tts_api_key()
        text_to_speech(
            Config.TTS_MODEL, 
            tts_api_key, 
            response_text, 
            output_file, 
            Config.LOCAL_MODEL_PATH
        )
        
        # Read the generated audio file
        with open(output_file, 'rb') as audio_file:
            audio_data = audio_file.read()
        
        # Clean up the file
        delete_file(output_file)
        
        # Return complete response
        audio_base64 = base64.b64encode(audio_data).decode('utf-8')
        
        return jsonify({
            'user_input': user_input,
            'response': response_text,
            'audio': audio_base64,
            'audio_format': 'mp3' if output_file.endswith('.mp3') else 'wav',
            'models': {
                'transcription': Config.TRANSCRIPTION_MODEL,
                'response': Config.RESPONSE_MODEL,
                'tts': Config.TTS_MODEL
            }
        })
        
    except Exception as e:
        logging.error(f"Voice chat error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/chat-history', methods=['GET'])
def get_chat_history():
    """Get current chat history"""
    return jsonify({'chat_history': chat_history})

@app.route('/chat-history', methods=['DELETE'])
def clear_chat_history():
    """Clear chat history and reset to initial system message"""
    global chat_history
    chat_history = [
        {"role": "system", "content": """ You are a helpful Assistant called Verbi. 
         You are friendly and fun and you will help the users with their requests.
         Your answers are short and concise. """}
    ]
    return jsonify({'message': 'Chat history cleared'})

@app.route('/api/start_conversation', methods=['POST'])
def start_conversation():
    """Start a new conversation - OPTIMIZED FOR LATENCY"""
    try:
        data = request.get_json()
        language = data.get('language', 'English')
        
        # Clear previous chat history
        global chat_history
        chat_history = [
            {"role": "system", "content": f""" You are a UAE Property Assistant called Verbi. 
             You are professional and very concise, specializing in UAE real estate information.
             You can help users with property queries, greetings, pricing, and accounting questions.
             Provide very short answers under 25 words. Key facts only. Please respond in {language}. """}
        ]
        
        # Generate greeting
        greeting_text = f"Hello! I'm Verbi. UAE Property assistant. How can I help?"
        
        # OPTIMIZATION: Use cached Deepgram client for TTS
        deepgram_tts_client = get_cached_deepgram_client()
        greeting_file = 'greeting.wav'  # Deepgram TTS uses WAV
        
        tts_with_cached_deepgram(deepgram_tts_client, greeting_text, greeting_file)
        
        # Read and encode greeting audio
        with open(greeting_file, 'rb') as audio_file:
            greeting_audio = base64.b64encode(audio_file.read()).decode('utf-8')
        
        # Clean up greeting file
        delete_file(greeting_file)
        
        return jsonify({
            'status': 'success',
            'greeting_text': greeting_text,
            'greeting_audio': greeting_audio
        })
        
    except Exception as e:
        logging.error(f"Error starting conversation: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/stop_conversation', methods=['POST'])
def stop_conversation():
    """Stop the current conversation"""
    try:
        return jsonify({'status': 'success', 'message': 'Conversation stopped'})
    except Exception as e:
        logging.error(f"Error stopping conversation: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/start_auto_listening', methods=['POST'])
def start_auto_listening():
    """Start auto listening mode"""
    try:
        return jsonify({'status': 'success', 'message': 'Auto listening started'})
    except Exception as e:
        logging.error(f"Error starting auto listening: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/stop_auto_listening', methods=['POST'])
def stop_auto_listening():
    """Stop auto listening mode"""
    try:
        return jsonify({'status': 'success', 'message': 'Auto listening stopped'})
    except Exception as e:
        logging.error(f"Error stopping auto listening: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/stop_current_audio', methods=['POST'])
def stop_current_audio():
    """Stop currently playing audio"""
    try:
        return jsonify({'status': 'success', 'message': 'Audio stopped'})
    except Exception as e:
        logging.error(f"Error stopping audio: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/process_user_input', methods=['POST'])
def process_user_input():
    """Process user audio input and generate response - OPTIMIZED FOR LATENCY"""
    try:
        if 'audio' not in request.files:
            return jsonify({'status': 'error', 'message': 'No audio file provided'}), 400
        
        file = request.files['audio']
        language = request.form.get('language', 'English')
        
        if file.filename == '':
            return jsonify({'status': 'error', 'message': 'No file selected'}), 400
        
        # Save uploaded file temporarily (safe file handling)
        filename = secure_filename(file.filename)
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(temp_path)
        
        # OPTIMIZATION 2: Use cached clients for connection reuse
        deepgram_client = get_cached_deepgram_client()
        
        # Step 1: Transcribe audio (optimized with cached client)
        user_input = transcribe_with_cached_deepgram(deepgram_client, temp_path)
        
        # Clean up input audio file
        delete_file(temp_path)
        
        if not user_input or user_input.strip() == '':
            return jsonify({'status': 'error', 'message': 'No transcription generated'}), 400
        
        # OPTIMIZATION 3: Use cached Groq client for connection reuse
        groq_client = get_cached_groq_client()
        
        # Step 2: Generate response (optimized with cached client)
        chat_history.append({"role": "user", "content": user_input})
        response_text = generate_response_with_cached_groq(groq_client, chat_history)
        chat_history.append({"role": "assistant", "content": response_text})
        
        # OPTIMIZATION 4: Use cached Deepgram client for TTS
        deepgram_tts_client = get_cached_deepgram_client()
        
        # Step 3: Convert response to speech (optimized with cached client)
        output_file = 'output.wav'  # Deepgram TTS uses WAV
        
        tts_with_cached_deepgram(deepgram_tts_client, response_text, output_file)
        
        # Read the generated audio file
        with open(output_file, 'rb') as audio_file:
            audio_data = base64.b64encode(audio_file.read()).decode('utf-8')
        
        # Clean up the file
        delete_file(output_file)
        
        return jsonify({
            'status': 'success',
            'user_input': user_input,
            'assistant_response': response_text,
            'audio_data': audio_data
        })
        
    except Exception as e:
        logging.error(f"Error processing user input: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500



if __name__ == '__main__':
    # Validate configuration before starting
    try:
        Config.validate_config()
        logging.info("Configuration validated successfully")
    except ValueError as e:
        logging.error(f"Configuration error: {e}")
        exit(1)
    
    print("=" * 60)
    print("🚀 Voice Assistant API Starting - OPTIMIZED FOR LATENCY")
    print("=" * 60)
    print("⚡ ADVANCED Performance Optimizations Applied:")
    print("  • Connection reuse with cached clients (major latency improvement)")
    print("  • Optimized model parameters for speed")
    print("  • Thread pool for concurrent processing")
    print("  • Cached API keys for faster access")
    print("  • Fastest models: Deepgram (STT/TTS) + Groq (LLM)")
    print("  • Safe file handling (no quality compromise)")
    print("  • Reduced audio quality settings for speed (maintains clarity)")
    print("=" * 60)
    print("Available endpoints:")
    print("  GET  /                    - Voice Agent Interface")
    print("  GET  /health              - Health check")
    print("  GET  /api-info            - API information")
    print("  POST /api/start_conversation    - Start conversation")
    print("  POST /api/stop_conversation     - Stop conversation")
    print("  POST /api/start_auto_listening  - Start auto listening")
    print("  POST /api/stop_auto_listening   - Stop auto listening")
    print("  POST /api/stop_current_audio    - Stop current audio")
    print("  POST /api/process_user_input    - Process user input")
    print("  POST /transcribe          - Transcribe audio")
    print("  POST /chat                - Text chat")
    print("  POST /tts                 - Text to speech")
    print("  POST /voice-chat          - Complete voice chat")
    print("  GET  /chat-history        - Get chat history")
    print("  DELETE /chat-history      - Clear chat history")
    print("=" * 60)
    print("🎯 Voice Agent will be available at: http://localhost:5000")
    print("⚡ Optimized for minimal latency while maintaining quality!")
    print("=" * 60)
    
    # Performance optimized Flask settings
    app.run(
        debug=False,  # Disable debug mode for production performance
        host='0.0.0.0', 
        port=5000,
        threaded=True,  # Enable threading for concurrent requests
        processes=1     # Single process to avoid memory issues
    ) 