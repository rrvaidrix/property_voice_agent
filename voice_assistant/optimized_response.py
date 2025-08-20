# voice_assistant/optimized_response.py

import logging
from voice_assistant.config import Config
from voice_assistant.property_kb_handler import PropertyKBHandler

# Initialize property KB handler
property_kb = PropertyKBHandler()

def generate_response_with_cached_groq(groq_client, chat_history):
    """
    Optimized response generation using cached Groq client with property KB integration.
    """
    try:
        # Get the latest user message
        user_message = ""
        for message in reversed(chat_history):
            if message.get('role') == 'user':
                user_message = message.get('content', '')
                break
        
        # Check if this is a follow-up question about previously mentioned properties
        is_follow_up_question = _is_follow_up_about_properties(user_message, chat_history)
        
        # Check if it's a property-related query
        if property_kb.is_property_related_query(user_message) or is_follow_up_question:
            # Check if this is a follow-up request for details
            detail_keywords = ['yes', 'want', 'details', 'more', 'information', 'tell me', 'show me', 'provide']
            is_detail_request = any(keyword in user_message.lower() for keyword in detail_keywords)
            
            # If it's a follow-up question, search for all properties to provide context
            if is_follow_up_question:
                matching_properties = property_kb.search_properties("all properties")
            else:
                # Search properties based on user query
                matching_properties = property_kb.search_properties(user_message)
            
            if is_detail_request and matching_properties:
                # Provide detailed response
                return property_kb.format_detailed_property_response(matching_properties)
            else:
                # Provide concise response
                property_response = property_kb.format_property_response(matching_properties)
                
                # Create enhanced response with property info
                enhanced_prompt = f"""
                User: {user_message}
                Property data: {property_response}
                
                Provide a very short response. Maximum 25 words. Key facts only.
                """
                
                # Add the enhanced prompt to chat history
                enhanced_chat_history = chat_history.copy()
                enhanced_chat_history.append({
                    "role": "system", 
                    "content": "You are a UAE property assistant. Provide very short, direct responses. Maximum 25 words. Use key facts only."
                })
                enhanced_chat_history.append({
                    "role": "user", 
                    "content": enhanced_prompt
                })
            
        elif property_kb.is_greeting_or_general_query(user_message):
            # Handle greetings and general queries
            enhanced_chat_history = chat_history.copy()
            enhanced_chat_history.append({
                "role": "system", 
                "content": "You are a UAE property assistant. Provide very short responses. Maximum 20 words for greetings. For emotional responses like 'that\'s nice', respond naturally and professionally."
            })
            
        else:
            # Non-property query - provide default response
            return property_kb.get_default_response()
        
        # Generate response with optimized parameters for very concise answers
        response = groq_client.chat.completions.create(
            model=Config.GROQ_LLM,
            messages=enhanced_chat_history,
            temperature=0.3,  # Very low temperature for focused responses
            max_tokens=50,    # Very short responses
            top_p=0.7,        # More focused generation
            stream=False      # Disable streaming for faster response
        )
        return response.choices[0].message.content
        
    except Exception as e:
        logging.error(f"Optimized Groq response generation error: {e}")
        raise

def _is_follow_up_about_properties(user_message: str, chat_history: list) -> bool:
    """
    Check if the user message is a follow-up question about previously mentioned properties.
    """
    user_message_lower = user_message.lower()
    
    # Keywords that indicate follow-up questions about properties
    follow_up_keywords = [
        'are you the only one', 'only one', 'just that', 'only that',
        'is that all', 'that\'s it', 'nothing else', 'any others',
        'more options', 'other properties', 'different ones',
        'what else', 'anything else', 'other locations', 'other areas'
    ]
    
    # Check if the message contains follow-up keywords
    if any(keyword in user_message_lower for keyword in follow_up_keywords):
        # Check if the previous assistant message mentioned properties
        for message in reversed(chat_history):
            if message.get('role') == 'assistant':
                assistant_message = message.get('content', '').lower()
                # Check if the assistant message contains property-related terms
                property_indicators = ['property', 'properties', 'dubai', 'aed', 'bedroom', 'bhk', 'location']
                if any(indicator in assistant_message for indicator in property_indicators):
                    return True
                break
    
    # Check for pronouns that refer to properties
    pronoun_keywords = ['them', 'those', 'that', 'this', 'it']
    if any(pronoun in user_message_lower for pronoun in pronoun_keywords):
        # Check recent context for property mentions
        recent_messages = chat_history[-4:]  # Check last 4 messages
        for message in recent_messages:
            if message.get('role') == 'assistant':
                assistant_message = message.get('content', '').lower()
                if any(term in assistant_message for term in ['property', 'properties', 'dubai', 'aed', 'bedroom']):
                    return True
    
    return False 