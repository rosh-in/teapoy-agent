#!/usr/bin/env python3
"""
PI2PRINTER Utilities
Shared functions for Gmail and Gemini API operations
"""

import os
import base64
import logging
from typing import Dict, Any, Optional
from dotenv import load_dotenv
import requests
import json

# Google APIs
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Gemini API
import warnings
with warnings.catch_warnings():
    warnings.simplefilter('ignore', FutureWarning)
    import google.generativeai as genai

# Load environment variables
load_dotenv()

# Gmail permissions
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

logger = logging.getLogger(__name__)

# Ollama configuration
OLLAMA_HOST = os.getenv('OLLAMA_HOST', 'http://192.168.1.43:11434')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'gemma2:2b')
USE_OLLAMA = os.getenv('USE_OLLAMA', 'true').lower() == 'true'

# Gemini configuration
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash-lite')


def setup_gmail_service():
    """Setup Gmail API service with credential handling"""
    logger.debug("Setting up Gmail API service...")
    
    if not os.path.exists('token.json'):
        raise FileNotFoundError("Gmail credentials not found. Run: python3 -c \"from utils import *; setup_gmail_auth()\"")
    
    try:
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        
        # Refresh if expired
        if creds and creds.expired and creds.refresh_token:
            logger.info("Refreshing expired Gmail token...")
            creds.refresh(Request())
            with open('token.json', 'w') as token:
                token.write(creds.to_json())
        
        if creds and creds.valid:
            service = build('gmail', 'v1', credentials=creds)
            logger.debug("Gmail API service ready")
            return service
        else:
            raise ValueError("Invalid Gmail credentials")
            
    except Exception as e:
        logger.error(f"Failed to setup Gmail service: {e}")
        raise



def setup_ollama_model() -> Dict[str, Any]:
    """Setup Ollama model connection - returns config dict"""
    logger.debug(f"Setting up Ollama connection to {OLLAMA_HOST}...")
    
    try:
        # Test connection
        response = requests.get(f"{OLLAMA_HOST}/api/version", timeout=5)
        response.raise_for_status()
        
        version = response.json()
        logger.info(f"✅ Ollama connected - version: {version.get('version', 'unknown')}")
        logger.info(f"✅ Using model: {OLLAMA_MODEL}")
        
        return {
            'host': OLLAMA_HOST,
            'model': OLLAMA_MODEL,
            'available': True
        }
    except requests.exceptions.RequestException as e:
        logger.warning(f"⚠️  Ollama connection failed: {e}")
        return {'available': False}



def generate_content_ollama(prompt: str) -> str:
    """Generate content using Ollama API"""
    url = f"{OLLAMA_HOST}/api/generate"
    
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "keep_alive": "30m",
        "options": {
            "temperature": 0.7,
            "top_p": 0.9
        }
    }
    
    try:
        response = requests.post(url, json=payload, timeout=200)
        response.raise_for_status()
        
        result = response.json()
        return result.get('response', '').strip()
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Ollama generation failed: {e}")
        raise RuntimeError(f"LLM generation failed - is Ollama running at {OLLAMA_HOST}?") from e


class OllamaModel:
    """Simplified model interface - Ollama only (gemma3:4b)"""
    
    def __init__(self):
        self.using_ollama = True
        self.ollama_config = {"host": OLLAMA_HOST, "model": OLLAMA_MODEL}
        logger.info(f"Initializing Ollama model: {OLLAMA_MODEL} at {OLLAMA_HOST}")
        
        # Test connection
        try:
            response = requests.get(f"{OLLAMA_HOST}/api/version", timeout=5)
            response.raise_for_status()
            version = response.json()
            logger.info(f"✅ Ollama connected - version: {version.get('version', 'unknown')}")
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Cannot connect to Ollama at {OLLAMA_HOST}")
            raise RuntimeError(f"Ollama connection failed. Is it running at {OLLAMA_HOST}?") from e
    
    def generate_content(self, prompt: str):
        """Generate content - returns object with .text attribute for compatibility"""
        text = generate_content_ollama(prompt)
        
        # Return object with .text attribute (for compatibility with existing code)
        class Response:
            def __init__(self, text):
                self.text = text
        
        return Response(text)




class GeminiModel:
    """Gemini API model interface"""

    def __init__(self):
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not set in environment")
        genai.configure(api_key=GEMINI_API_KEY)
        self.model = genai.GenerativeModel(GEMINI_MODEL)
        logger.info(f"✅ Gemini model initialized: {GEMINI_MODEL}")

    def generate_content(self, prompt: str):
        """Generate content - returns response with .text attribute"""
        try:
            response = self.model.generate_content(prompt)
            return response
        except Exception as e:
            logger.error(f"Gemini generation failed: {e}")
            raise


# Use Gemini as the primary LLM
UnifiedLLMModel = GeminiModel




def decode_base64_email_data(data: str) -> str:
    """Decode base64url encoded email data"""
    try:
        return base64.urlsafe_b64decode(data + '===').decode('utf-8', errors='ignore')
    except Exception as e:
        logger.warning(f"Failed to decode base64 data: {e}")
        return ""


def extract_email_body(payload: Dict) -> str:
    """Extract text body from Gmail message payload"""
    body = ""
    
    try:
        if 'parts' in payload:
            # Multi-part message
            for part in payload['parts']:
                if part.get('mimeType') == 'text/plain' and 'data' in part.get('body', {}):
                    body = decode_base64_email_data(part['body']['data'])
                    break
                # Also check nested parts
                elif 'parts' in part:
                    for nested_part in part['parts']:
                        if (nested_part.get('mimeType') == 'text/plain' and 
                            'data' in nested_part.get('body', {})):
                            body = decode_base64_email_data(nested_part['body']['data'])
                            break
                    if body:
                        break
        else:
            # Single part message
            if (payload.get('mimeType') == 'text/plain' and 
                'data' in payload.get('body', {})):
                body = decode_base64_email_data(payload['body']['data'])
        
        return body or "No text content found"
        
    except Exception as e:
        logger.error(f"Failed to extract email body: {e}")
        return "Could not extract email content"


def create_task_analysis_prompt(email_data: Dict[str, Any]) -> str:
    """Create standardized prompt for email task analysis"""
    return f"""
    Analyze the following email and determine if it is a "Mission" (task/request) or a "Personal Message" (banter, compliment, chat).

    Email Subject: {email_data.get('subject')}
    From: {email_data.get('from')}
    Body: {email_data.get('body')}

    Return ONLY a JSON object with this structure:
    {{
        "type": "MISSION" | "MESSAGE" | "IGNORE",
        "has_task": boolean, (true if type is MISSION)
        "confidence": float (0-1),
        "reasoning": "explanation",
        
        // If type is MISSION:
        "mission_briefing": {{
            "title": "Short title",
            "urgency": "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "INFO",
            "deadline": "YYYY-MM-DD" or null,
            "action_required": "What needs to be done",
            "context": "Why it matters",
            "people_involved": ["List of names"],
            "mission_id": "MI-{email_data['id'][:8]}"
        }},

        // If type is MESSAGE (Personal/Banter):
        "receipt_data": {{
            "customer_name": "Sender name (extract from From field, just name)",
            "items": [
                {{ "name": "The full message text" }}
            ]
        }}
    }}
    
    Rules:
    1. If it requires action/work -> MISSION
    2. If it's just chatting/compliments/fun -> MESSAGE  
    3. If it's newsletters/automated spam -> IGNORE
    4. For MESSAGE: Put entire message in items[0].name. Extract sender name for customer_name.
    """



def parse_gmail_message(message: Dict) -> Optional[Dict[str, Any]]:
    """Parse Gmail message into structured email data"""
    try:
        headers = {h['name']: h['value'] for h in message['payload']['headers']}
        
        # Extract body
        body = extract_email_body(message['payload'])
        
        # Get timestamp
        from datetime import datetime, timezone
        timestamp = int(message['internalDate']) / 1000
        email_date = datetime.fromtimestamp(timestamp, timezone.utc)
        
        email_data = {
            'id': message['id'],
            'subject': headers.get('Subject', 'No Subject'),
            'from': headers.get('From', 'Unknown'),
            'to': headers.get('To', ''),
            'date': email_date.isoformat(),
            'body': body[:3000],  # Limit for AI processing
            'labels': message.get('labelIds', []),
            'thread_id': message.get('threadId', ''),
            'raw_message': message
        }
        
        return email_data
        
    except Exception as e:
        logger.error(f"Failed to parse Gmail message: {e}")
        return None


def setup_gmail_auth():
    """Interactive Gmail authentication setup (for initial setup only)"""
    from google_auth_oauthlib.flow import InstalledAppFlow
    
    print("🔐 Setting up Gmail authentication...")
    
    if not os.path.exists('credentials.json'):
        print("❌ Error: credentials.json not found!")
        print("\nTo fix this:")
        print("1. Go to https://console.cloud.google.com/")
        print("2. Create a new project (or select existing)")
        print("3. Enable the Gmail API")
        print("4. Create OAuth 2.0 credentials")
        print("5. Download as 'credentials.json' and put it in this folder")
        return False
    
    print("   🔐 Starting login process...")
    flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
    
    # Use manual flow for WSL/headless environments
    print("\n📋 Please follow these steps:")
    print("1. Copy this URL and open it in your browser:")
    
    flow.redirect_uri = 'urn:ietf:wg:oauth:2.0:oob'
    auth_url, _ = flow.authorization_url(prompt='consent')
    print(f"\n{auth_url}\n")
    
    print("2. After authorizing, Google will show you an authorization code")
    print("3. Copy that authorization code and paste it below:")
    
    auth_code = input("\nPaste the authorization code here: ").strip()
    
    if not auth_code:
        print("❌ No authorization code provided")
        return False
    
    # Exchange the authorization code for credentials
    flow.fetch_token(code=auth_code)
    creds = flow.credentials
    
    # Save the credentials for future use
    print("   💾 Saving credentials for future use")
    with open('token.json', 'w') as token:
        token.write(creds.to_json())
    
    print("✅ Gmail authentication setup complete!")
    return True


# Test functions
def test_gmail_connection():
    """Test Gmail API connection"""
    try:
        service = setup_gmail_service()
        
        # Try to list 1 message
        results = service.users().messages().list(userId='me', maxResults=1).execute()
        messages = results.get('messages', [])
        
        if messages:
            print(f"✅ Gmail connection working - found {len(messages)} message(s)")
            return True
        else:
            print("📭 Gmail connection working but no messages found")
            return True
            
    except Exception as e:
        print(f"❌ Gmail connection failed: {e}")
        return False


def test_gemini_connection():
    """Test Gemini API connection"""
    try:
        model = GeminiModel()
        
        # Simple test query
        response = model.generate_content("Say 'Hello from Gemini!' in JSON format: {\"message\": \"...\"}}")
        print(f"✅ Gemini connection working - response: {response.text[:100]}...")
        return True
        
    except Exception as e:
        print(f"❌ Gemini connection failed: {e}")
        return False


if __name__ == '__main__':
    """Quick connection tests"""
    print("🧪 Testing API connections...")
    print("-" * 40)
    
    gmail_ok = test_gmail_connection()
    gemini_ok = test_gemini_connection()
    
    print("-" * 40)
    if gmail_ok and gemini_ok:
        print("🎉 All API connections working!")
    else:
        print("⚠️  Some connections failed - check configuration")

def clean_json_response(text: str) -> str:
    """Clean LLM-generated JSON to handle common formatting issues"""
    import re
    
    # Remove markdown code blocks
    if text.startswith('```json'):
        text = text[7:]
    elif text.startswith('```'):
        text = text[3:]
    if text.endswith('```'):
        text = text[:-3]
    
    text = text.strip()
    
    # Extract just the JSON object if there is narrative text around it
    first_brace = text.find('{')
    if first_brace != -1:
        # Find matching closing brace
        brace_count = 0
        last_brace = -1
        for i in range(first_brace, len(text)):
            if text[i] == '{':
                brace_count += 1
            elif text[i] == '}':
                brace_count -= 1
                if brace_count == 0:
                    last_brace = i
                    break
        
        if last_brace != -1:
            text = text[first_brace:last_brace+1]
    
    # Remove single-line comments (// ...)
    # Must preserve strings, so only remove comments outside quotes
    lines = []
    for line in text.split('\n'):
        if '//' in line:
            # Check if it's outside a string
            in_string = False
            cleaned_line = []
            i = 0
            while i < len(line):
                if line[i] == '"' and (i == 0 or line[i-1] != '\\'):
                    in_string = not in_string
                    cleaned_line.append(line[i])
                elif line[i:i+2] == '//' and not in_string:
                    # Found comment outside string, stop here
                    break
                else:
                    cleaned_line.append(line[i])
                i += 1
            lines.append(''.join(cleaned_line))
        else:
            lines.append(line)
    
    text = '\n'.join(lines)
    
    # Remove multi-line comments (/* ... */)
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
    
    # Remove trailing commas before closing braces/brackets
    text = re.sub(r',(\s*[}\]])', r'\1', text)
    
    # Remove multiple trailing commas
    text = re.sub(r',+', ',', text)
    
    # Fix property names that are missing opening quote: word": -> "word":
    text = re.sub(r'([{\[,\s])([a-zA-Z_][a-zA-Z0-9_]*)"(\s*):', r'\1"\2"\3:', text)
    
    # Fix unquoted property names: word: -> "word":
    text = re.sub(r'([{\[,]\s*)([a-zA-Z_][a-zA-Z0-9_]*)(\s*):', r'\1"\2"\3:', text)
    
    # Fix unquoted string values after colons
    def quote_unquoted_values(match):
        prefix = match.group(1)
        value = match.group(2).strip()
        suffix = match.group(3)
        
        # Don't quote if it's already quoted, or if it's a number, boolean, null, or object/array start
        if value.startswith('"') or value in ['true', 'false', 'null'] or \
           re.match(r'^-?\d+\.?\d*$', value) or value.startswith('{') or value.startswith('['):
            return match.group(0)
        
        # Quote the value
        return f'{prefix}"{value}"{suffix}'
    
    # Match: colon, optional whitespace, value, then comma/brace/bracket
    text = re.sub(r'(:\s*)([^,}\]\s][^,}\]]*?)(\s*[,}\]])', quote_unquoted_values, text)
    
    # Remove narrative text that appears mid-JSON (e.g., after a comma before next property)
    # Pattern: comma, whitespace, then non-JSON-like text (sentences), then valid JSON resumes
    text = re.sub(r',\s*[^{"\[\]},:\s][^{"\[\]]*?(?=[{":])', ',', text)
    
    return text.strip()


