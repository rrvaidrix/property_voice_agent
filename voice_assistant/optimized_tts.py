# voice_assistant/optimized_tts.py

import logging
from deepgram import SpeakOptions

def tts_with_cached_deepgram(deepgram_client, text, output_file_path):
    """
    Optimized TTS using cached Deepgram client for faster response.
    """
    try:
        # Use faster model and optimized parameters
        options = SpeakOptions(
            model="aura-arcas-en",  # Fastest model
            encoding="linear16",
            container="wav",
            sample_rate=16000  # Supported sample rate for speed
        )
        
        SPEAK_OPTIONS = {"text": text}
        response = deepgram_client.speak.v("1").save(output_file_path, SPEAK_OPTIONS, options)
        return True
    except Exception as e:
        logging.error(f"Optimized Deepgram TTS error: {e}")
        raise 