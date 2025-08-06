# voice_assistant/optimized_response.py

import logging
from voice_assistant.config import Config

def generate_response_with_cached_groq(groq_client, chat_history):
    """
    Optimized response generation using cached Groq client for faster response.
    """
    try:
        # Use faster model and optimized parameters
        response = groq_client.chat.completions.create(
            model=Config.GROQ_LLM,
            messages=chat_history,
            temperature=0.7,  # Slightly lower for faster response
            max_tokens=150,   # Limit tokens for faster generation
            top_p=0.9,        # Optimize for speed
            stream=False      # Disable streaming for faster response
        )
        return response.choices[0].message.content
    except Exception as e:
        logging.error(f"Optimized Groq response generation error: {e}")
        raise 