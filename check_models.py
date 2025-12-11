#!/usr/bin/env python3
"""
Check available Gemini models
"""

import google.generativeai as genai
from dotenv import load_dotenv
import os

load_dotenv()

# Configure Gemini
api_key = os.getenv('GEMINI_API_KEY')
genai.configure(api_key=api_key)

print("Available Gemini models:")
print("="*40)

try:
    for model in genai.list_models():
        if 'generateContent' in model.supported_generation_methods:
            print(f"✅ {model.name}")
        else:
            print(f"❌ {model.name} (doesn't support generateContent)")
except Exception as e:
    print(f"Error listing models: {e}")