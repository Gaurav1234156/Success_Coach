import json
import streamlit as st
from ai_agent import get_openai_client
from datetime import datetime

def detect_and_save_signal(chat_messages, student_id, student_name, spreadsheet_id):
    """Analyzes the chat for concerns and appends them to the Google Sheet."""
    client = get_openai_client()
    
    # 1. AI SIGNAL DETECTION
    # Filter out system instructions to only read the actual conversation
    conversation_only = [msg for msg in chat_messages if msg["role"] != "system"]
    
    if len(conversation_only) < 2:
        return # Not enough conversation to analyze
        
    prompt = """
    You are a student success analyst. Review the following coaching conversation. 
    Are there any concerning signals? (e.g., severe academic struggle, extreme stress, missing classes, mentioning dropping out).
    
    Respond strictly in JSON format with these exact keys:
    {
        "has_signal": boolean (true if there is a concern, false if fine),
        "severity": string ("Low", "Medium", or "High" - how serious the issue is),
        "urgency": string ("Act Today" or "Wait" - whether the human coach needs to intervene immediately),
        "description": string (A concise 1-sentence summary of the exact concern)
    }
    """
    
    messages_for_eval = [{"role": "system", "content": prompt}] + conversation_only
    
    try:
        # We force the AI to return a perfect JSON object
        response = client.chat.completions.create(
            model="gpt-5.4-mini-2026-03-17",
            response_format={ "type": "json_object" },
            messages=messages_for_eval
        )
        
        signal_data = json.loads(response.choices[0].message.content)
        
    except Exception as e:
        print(f"Signal extraction failed: {e}")
        return

    # 2. SAVE TO GOOGLE SHEETS
    if signal_data.get("has_signal"):
        print(f"🚨 SIGNAL DETECTED: {signal_data['description']}")
        
        try:
            # Import the required Google libraries
            from google.oauth2 import service_account
            from googleapiclient.discovery import build
            
            # Authenticate using your Streamlit secrets
            # Note: Your Google Cloud Service Account MUST have "Editor" access to your spreadsheet
            creds_dict = dict(st.secrets["gcp_service_account"])
            credentials = service_account.Credentials.from_service_account_info(
                creds_dict, scopes=["https://www.googleapis.com/auth/spreadsheets"]
            )
            
            service = build('sheets', 'v4', credentials=credentials)
            
            date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            row_data = [
                student_id,           # A: student_id
                "Academic Concern",   # B: signal_type (Added a default label)
                signal_data.get("severity", "Medium"), # C: severity
                signal_data.get("urgency", "Wait"),    # D: urgency
                signal_data.get("description", "No description provided."), # E: reason
                date_str              # F: timestamp
            ]
            
            # Target the 'signal_sheet' tab (assuming columns A through F)
            sheet_range = "signal_sheet!A:F"  
            body = {"values": [row_data]}
            
            # Execute the append command
            service.spreadsheets().values().append(
                spreadsheetId=spreadsheet_id,
                range=sheet_range,
                valueInputOption="USER_ENTERED",
                body=body
            ).execute()
            
            # Return true so the UI can flash a warning
            return True 
            
        except Exception as e:
            print(f"Failed to append to Google Sheets. Check your credentials and permissions: {e}")
            return False
            
    return False