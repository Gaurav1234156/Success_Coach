import streamlit as st
import pandas as pd
from langchain.tools import tool
from googleapiclient.discovery import build
from google.oauth2 import service_account
import uuid  # <-- NEW IMPORT
from datetime import datetime, timedelta # <-- NEW IMPORT

# Helper function to get Google credentials
def get_google_creds(scopes):
    return service_account.Credentials.from_service_account_info(
        dict(st.secrets["gcp_service_account"]), 
        scopes=scopes
    )

@tool
def get_pending_signals():
    """Fetches all pending (un-actioned) student signals from the Google Sheet. Always use this first to see who needs help."""
    try:
        spreadsheet_id = st.secrets["GOOGLE_SPREADSHEET_ID"]
        creds = get_google_creds(["https://www.googleapis.com/auth/spreadsheets"])
        sheets_service = build('sheets', 'v4', credentials=creds)
        
        # Fetch the data
        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id, 
            range="signal_sheet!A:G"
        ).execute()
        
        values = result.get('values', [])
        if not values or len(values) < 2:
            return "No pending signals found."
        
        # Convert to Pandas DataFrame to easily filter
        headers = values[0]
        data = values[1:]
        
        # Ensure all rows have the same number of columns as headers by padding with empty strings
        padded_data = [row + [''] * (len(headers) - len(row)) for row in data]
        df = pd.DataFrame(padded_data, columns=headers)
        
        # Filter for rows where 'actioned' is not 'Yes'
        if 'actioned' in df.columns:
            pending = df[(df['actioned'] != 'Yes') & (df['actioned'] != 'yes')]
        else:
            return "Error: Could not find 'actioned' column in the sheet."
            
        if pending.empty:
            return "No pending signals found. Everyone is actioned!"
            
        return pending.to_json(orient="records")
        
    except Exception as e:
        return f"Failed to fetch signals: {str(e)}"

@tool
def create_calendar_event(student_id: str, reason: str, start_time: str):
    """
    Creates a simple calendar event for a coaching session.
    start_time MUST be an ISO format string like 'YYYY-MM-DDT10:00:00+05:30'.
    """
    try:
        calendar_id = st.secrets["GOOGLE_CALENDAR_ID"]
        creds = get_google_creds(["https://www.googleapis.com/auth/calendar"])
        cal_service = build('calendar', 'v3', credentials=creds)
        
        # Calculate an end time (assuming 30 minute sessions)
        start_dt = datetime.fromisoformat(start_time)
        end_dt = start_dt + timedelta(minutes=30)
        
        # Create a simple payload with NO video conferencing data
        event_payload = {
            'summary': f"Coach Session: {student_id}",
            'description': f"Reason for session: {reason}",
            'start': {
                'dateTime': start_dt.isoformat(),
                'timeZone': 'Asia/Kolkata',
            },
            'end': {
                'dateTime': end_dt.isoformat(),
                'timeZone': 'Asia/Kolkata',
            }
        }
        
        # Insert the standard event
        event_result = cal_service.events().insert(
            calendarId=calendar_id, 
            body=event_payload
        ).execute()
        
        return f"Successfully created standard calendar block for {student_id} at {start_time}."
        
    except Exception as e:
        return f"Failed to create calendar event: {str(e)}"

@tool
def update_sheet_actioned(student_id: str):
    """Marks a student's signal as 'Yes' in the actioned column of the signal_sheet."""
    try:
        spreadsheet_id = st.secrets["GOOGLE_SPREADSHEET_ID"]
        creds = get_google_creds(["https://www.googleapis.com/auth/spreadsheets"])
        sheets_service = build('sheets', 'v4', credentials=creds)

        # 1. Fetch the sheet to find where this student's row is
        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id, 
            range="signal_sheet" # Fetches the whole sheet
        ).execute()
        
        values = result.get('values', [])
        if not values:
            return "Sheet is empty."
        
        headers = values[0]
        
        # 2. Find which columns contain 'student_id' and 'actioned'
        if 'student_id' not in headers or 'actioned' not in headers:
            return "Error: Could not find 'student_id' or 'actioned' headers in row 1."
            
        student_id_col = headers.index('student_id')
        actioned_col = headers.index('actioned')
        
        # 3. Find the exact row number for this student that ISN'T actioned yet
        row_to_update = -1
        for i, row in enumerate(values):
            # Pad the row just in case the last columns are totally blank
            row_padded = row + [''] * (len(headers) - len(row))
            
            # If it's the right student and they aren't actioned yet
            if i > 0 and row_padded[student_id_col] == student_id and row_padded[actioned_col].lower() != 'yes':
                row_to_update = i + 1  # +1 because Google Sheets rows start at 1, but Python lists start at 0
                break
                
        if row_to_update == -1:
            return f"Could not find a pending signal for student {student_id}."
        
        # 4. Calculate the exact cell coordinate (e.g., Column G, Row 3 -> 'G3')
        col_letter = chr(65 + actioned_col) # Converts 0 to A, 1 to B, etc.
        cell_range = f"signal_sheet!{col_letter}{row_to_update}"
        
        # 5. Push the "Yes" to that specific cell
        body = {'values': [['Yes']]}
        sheets_service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=cell_range,
            valueInputOption="USER_ENTERED",
            body=body
        ).execute()
        
        return f"Successfully marked {student_id} as actioned in cell {cell_range}."
        
    except Exception as e:
        return f"Failed to update sheet: {str(e)}"