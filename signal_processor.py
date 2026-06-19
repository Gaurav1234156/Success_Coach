import json
import streamlit as st
from ai_agent import get_openai_client
from datetime import datetime, timezone, timedelta # 1. Added timezone and timedelta

def detect_and_save_signal(chat_messages, student_id, student_name, spreadsheet_id):
    """Analyzes the chat for concerns and appends them to the Google Sheet."""
    client = get_openai_client()
    
    # 1. AI SIGNAL DETECTION
    conversation_only = [msg for msg in chat_messages if msg["role"] != "system"]
    
    if len(conversation_only) < 2:
        return 
        
    prompt = """
    You are a student success analyst. Review the following coaching conversation. 
    Are there any concerning signals? (e.g., severe academic struggle, extreme stress, missing classes, mentioning dropping out).
    
    Respond strictly in JSON format with these exact keys:
    {
        "has_signal": boolean,
        "severity": string,
        "urgency": string,
        "description": string
    }
    """
    
    messages_for_eval = [{"role": "system", "content": prompt}] + conversation_only
    
    try:
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
        try:
            from google.oauth2 import service_account
            from googleapiclient.discovery import build
            
            creds_dict = dict(st.secrets["gcp_service_account"])
            credentials = service_account.Credentials.from_service_account_info(
                creds_dict, scopes=["https://www.googleapis.com/auth/spreadsheets"]
            )
            
            service = build('sheets', 'v4', credentials=credentials)
            
            # 2. FIXED: Construct IST time
            ist_offset = timezone(timedelta(hours=5, minutes=30))
            date_str = datetime.now(ist_offset).strftime("%Y-%m-%d %H:%M:%S")
            
            row_data = [
                student_id,
                "Academic Concern",
                signal_data.get("severity", "Medium"),
                signal_data.get("urgency", "Wait"),
                signal_data.get("description", "No description provided."),
                date_str 
            ]
            
            sheet_range = "signal_sheet!A:F"  
            body = {"values": [row_data]}
            
            service.spreadsheets().values().append(
                spreadsheetId=spreadsheet_id,
                range=sheet_range,
                valueInputOption="USER_ENTERED",
                body=body
            ).execute()
            
            return True 
            
        except Exception as e:
            print(f"Failed to append to Google Sheets: {e}")
            return False
            
    return False