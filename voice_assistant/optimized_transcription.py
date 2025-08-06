# voice_assistant/optimized_transcription.py

import json
import logging
from deepgram import PrerecordedOptions

def transcribe_with_cached_deepgram(deepgram_client, audio_file_path):
    """
    Optimized transcription using cached Deepgram client for faster response.
    """
    try:
        with open(audio_file_path, "rb") as file:
            buffer_data = file.read()

        payload = {"buffer": buffer_data}
        # Use faster model for better latency
        options = PrerecordedOptions(
            model="nova-2", 
            smart_format=True,
            language="en-US",
            punctuate=True,
            diarize=False,  # Disable diarization for speed
            utterances=False,  # Disable utterances for speed
            paragraphs=False   # Disable paragraphs for speed
        )
        
        response = deepgram_client.listen.prerecorded.v("1").transcribe_file(payload, options)
        data = json.loads(response.to_json())

        transcript = data['results']['channels'][0]['alternatives'][0]['transcript']
        return transcript
    except Exception as e:
        logging.error(f"Optimized Deepgram transcription error: {e}")
        raise 