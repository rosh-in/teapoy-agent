#!/usr/bin/env python3
"""
Simple Gmail API Test
Just connect to Gmail and fetch 1 recent email
"""

import os
import json
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Gmail permissions we need
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def test_gmail():
    """Test Gmail API connection and fetch 1 recent email"""
    print("🔧 Testing Gmail API connection...")
    
    # Step 1: Set up authentication
    creds = None
    
    # Check if we already have saved credentials
    if os.path.exists('token.json'):
        print("   📋 Found existing credentials")
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    # If no valid credentials are available, let the user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("   🔄 Refreshing expired credentials")
            creds.refresh(Request())
        else:
            # Check if credentials.json exists
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
            
            # Set up the authorization URL with proper redirect URI
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
        
        # Save the credentials for the next run
        print("   💾 Saving credentials for next time")
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    
    # Step 2: Connect to Gmail
    try:
        service = build('gmail', 'v1', credentials=creds)
        print("✅ Connected to Gmail successfully!")
        
        # Step 3: Fetch 1 recent email
        print("   📧 Fetching 1 recent email...")
        
        # Get list of messages (just 1)
        results = service.users().messages().list(userId='me', maxResults=1).execute()
        messages = results.get('messages', [])
        
        if not messages:
            print("   📭 No messages found")
            return True
        
        # Get the first message details
        message_id = messages[0]['id']
        message = service.users().messages().get(userId='me', id=message_id).execute()
        
        # Extract basic info
        headers = message['payload']['headers']
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
        sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
        
        print("   📬 Found email:")
        print(f"      Subject: {subject}")
        print(f"      From: {sender}")
        print(f"      Message ID: {message_id}")
        
        print("✅ Gmail API test completed successfully!")
        return True
        
    except HttpError as error:
        print(f"❌ Gmail API error: {error}")
        return False
    except Exception as error:
        print(f"❌ Unexpected error: {error}")
        return False

if __name__ == '__main__':
    print("🚀 Starting Gmail API Test")
    print("=" * 40)
    
    success = test_gmail()
    
    print("=" * 40)
    if success:
        print("🎉 Test completed successfully!")
        print("   Gmail API is working and ready to use")
    else:
        print("💥 Test failed - check the error messages above")