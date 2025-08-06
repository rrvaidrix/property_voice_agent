# voice_assistant/audio.py

import speech_recognition as sr
import pygame
import time
import logging
import pydub
from io import BytesIO
from pydub import AudioSegment
from functools import lru_cache
import os
import wave

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

@lru_cache(maxsize=None)
def get_recognizer():
    """
    Return a cached speech recognizer instance
    """
    return sr.Recognizer()

def record_audio(file_path, timeout=10, phrase_time_limit=None, retries=3, energy_threshold=2000, 
                 pause_threshold=1, phrase_threshold=0.1, dynamic_energy_threshold=True, 
                 calibration_duration=1):
    """
    Record audio from the microphone and save it as an MP3 file.
    
    Args:
    file_path (str): The path to save the recorded audio file.
    timeout (int): Maximum time to wait for a phrase to start (in seconds).
    phrase_time_limit (int): Maximum time for the phrase to be recorded (in seconds).
    retries (int): Number of retries if recording fails.
    energy_threshold (int): Energy threshold for considering whether a given chunk of audio is speech or not.
    pause_threshold (float): How much silence the recognizer interprets as the end of a phrase (in seconds).
    phrase_threshold (float): Minimum length of a phrase to consider for recording (in seconds).
    dynamic_energy_threshold (bool): Whether to enable dynamic energy threshold adjustment.
    calibration_duration (float): Duration of the ambient noise calibration (in seconds).
    """
    recognizer = get_recognizer()
    recognizer.energy_threshold = energy_threshold
    recognizer.pause_threshold = pause_threshold
    recognizer.phrase_threshold = phrase_threshold
    recognizer.dynamic_energy_threshold = dynamic_energy_threshold
    
    for attempt in range(retries):
        try:
            with sr.Microphone() as source:
                logging.info("Calibrating for ambient noise...")
                recognizer.adjust_for_ambient_noise(source, duration=calibration_duration)
                logging.info("Recording started")
                # Listen for the first phrase and extract it into audio data
                audio_data = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
                logging.info("Recording complete")

                # Convert the recorded audio data to a file
                wav_data = audio_data.get_wav_data()
                
                # Ensure the directory exists
                os.makedirs(os.path.dirname(file_path) if os.path.dirname(file_path) else '.', exist_ok=True)
                
                # Determine file format based on extension
                if file_path.lower().endswith('.mp3'):
                    # Try to save as MP3, fallback to WAV if FFmpeg not available
                    try:
                        audio_segment = pydub.AudioSegment.from_wav(BytesIO(wav_data))
                        audio_segment.export(file_path, format="mp3", bitrate="128k")
                        logging.info(f"Audio saved as MP3: {file_path}")
                    except Exception as mp3_error:
                        logging.warning(f"Failed to save as MP3: {mp3_error}")
                        # Fallback to WAV
                        wav_path = file_path.replace('.mp3', '.wav')
                        with open(wav_path, 'wb') as f:
                            f.write(wav_data)
                        logging.info(f"Audio saved as WAV: {wav_path}")
                        # Update the file path for the rest of the process
                        file_path = wav_path
                else:
                    # Save as WAV directly
                    with open(file_path, 'wb') as f:
                        f.write(wav_data)
                    logging.info(f"Audio saved as WAV: {file_path}")
                
                return
                    
        except sr.WaitTimeoutError:
            logging.warning(f"Listening timed out, retrying... ({attempt + 1}/{retries})")
        except Exception as e:
            logging.error(f"Failed to record audio: {e}")
            if attempt == retries - 1:
                raise
        
    logging.error("Recording failed after all retries")

def play_audio(file_path):
    """
    Play an audio file using pygame.
    
    Args:
    file_path (str): The path to the audio file to play.
    """
    try:
        pygame.mixer.init()
        pygame.mixer.music.load(file_path)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pygame.time.wait(100)
    except pygame.error as e:
        logging.error(f"Failed to play audio: {e}")
    except Exception as e:
        logging.error(f"An unexpected error occurred while playing audio: {e}")
    finally:
        pygame.mixer.quit()