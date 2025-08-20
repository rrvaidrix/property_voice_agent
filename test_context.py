#!/usr/bin/env python3
# test_context.py

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from voice_assistant.optimized_response import generate_response_with_cached_groq, _is_follow_up_about_properties
from voice_assistant.property_kb_handler import PropertyKBHandler

def test_context_handling():
    """Test the context handling improvements"""
    
    # Initialize property KB handler
    property_kb = PropertyKBHandler()
    
    # Test chat history with property conversation
    chat_history = [
        {"role": "system", "content": "You are a UAE Property Assistant called Verbi. You are professional and very concise."},
        {"role": "user", "content": "Please give me the pricing of the all of the property."},
        {"role": "assistant", "content": "Downtown Dubai: 3.8M AED for a 2BR apartment with Burj Khalifa view and luxury amenities."},
        {"role": "user", "content": "Are you the only one of them?"}
    ]
    
    print("Testing context handling...")
    print("=" * 50)
    
    # Test the follow-up detection
    user_message = "Are you the only one of them?"
    is_follow_up = _is_follow_up_about_properties(user_message, chat_history)
    print(f"User message: '{user_message}'")
    print(f"Is follow-up about properties: {is_follow_up}")
    print()
    
    # Test property search for "all properties"
    all_properties = property_kb.search_properties("all properties")
    print(f"Number of all properties found: {len(all_properties)}")
    print()
    
    # Test property-related query detection
    is_property_related = property_kb.is_property_related_query(user_message)
    print(f"Is property related query: {is_property_related}")
    print()
    
    # Test response formatting
    if all_properties:
        response = property_kb.format_property_response(all_properties)
        print("Formatted response:")
        print(response)
        print()
    
    print("Context handling test completed!")

if __name__ == "__main__":
    test_context_handling() 