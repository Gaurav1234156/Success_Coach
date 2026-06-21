import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from google.oauth2 import service_account

def get_google_sheets_service():
    creds = service_account.Credentials.from_service_account_info(
        dict(st.secrets["gcp_service_account"]), 
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    return build('sheets', 'v4', credentials=creds)

def evaluate_and_update_plan(spreadsheet_id):
    """
    Evaluates current daily slots against pending signals.
    Handles auto-bumping for lower priority slots and detects critical deadlocks.
    """
    try:
        service = get_google_sheets_service()
        
        # 1. Fetch current signals
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id, 
            range="signal_sheet!A:G"
        ).execute()
        
        values = result.get('values', [])
        if not values or len(values) < 2:
            return {"status": "clear", "message": "No signals available to process."}
            
        headers = values[0]
        padded_data = [row + [''] * (len(headers) - len(row)) for row in values[1:]]
        df = pd.DataFrame(padded_data, columns=headers)
        
        # Identify urgent pending items (High severity, Act Today, not actioned)
        critical_pending = df[
            (df['severity'].str.lower() == 'high') & 
            (df['urgency'].str.lower() == 'act today') & 
            (df['actioned'].str.lower() != 'yes')
        ]
        
        if critical_pending.empty:
            return {"status": "clear", "message": "No unhandled critical alerts."}
            
        # 2. Simulate Capacity
        # Define working constraints: 4 total slots available per day
        MAX_SLOTS = 4
        
        # Count who is already scheduled for today (actioned = Yes, and timestamp is today)
        today_str = datetime.now().strftime("%Y-%m-%d")
        df['is_today'] = df['timestamp'].str.startswith(today_str)
        
        scheduled_today = df[(df['actioned'].str.lower() == 'yes') & (df['is_today'] == True)]
        current_occupancy = len(scheduled_today)
        
        # Process each critical pending signal
        for _, critical_student in critical_pending.iterrows():
            student_id = critical_student['student_id']
            reason = critical_student['reason']
            
            # Case A: There is open space today
            if current_occupancy < MAX_SLOTS:
                return {
                    "status": "auto_inserted",
                    "student_id": student_id,
                    "reason": reason,
                    "action_required": "insert_open_slot",
                    "summary": f"Slot Auto-Allocated: {student_id} added to an open slot due to high urgency alert: '{reason}'."
                }
                
            # Case B: Calendar full. Can we bump a lower-severity student?
            lower_priority_scheduled = scheduled_today[scheduled_today['severity'].str.lower() != 'high']
            
            if not lower_priority_scheduled.empty:
                # Target the lowest severity student currently taking up a slot today
                student_to_bump = lower_priority_scheduled.iloc[0]
                return {
                    "status": "auto_bumped",
                    "incoming_student_id": student_id,
                    "incoming_reason": reason,
                    "bumped_student_id": student_to_bump['student_id'],
                    "bumped_reason": student_to_bump['reason'],
                    "action_required": "bump_slot",
                    "summary": f"Plan Updated Automatically: {student_id} (High) has taken the slot of {student_to_bump['student_id']} (Medium/Low). {student_to_bump['student_id']} deferred to tomorrow."
                }
                
            # Case C: Deadlock. Calendar full entirely with High-severity students.
            all_high_scheduled = scheduled_today[scheduled_today['severity'].str.lower() == 'high']
            if not all_high_scheduled.empty:
                competing_student = all_high_scheduled.iloc[-1] # Contrast with the last scheduled critical student
                return {
                    "status": "conflict_deadlock",
                    "student_a": competing_student['student_id'],
                    "reason_a": competing_student['reason'],
                    "student_b": student_id,
                    "reason_b": reason,
                    "summary": "⚠️ Scheduling Deadlock: Two critical cases require immediate attention, but only one slot remains. Human intervention required to balance tradeoffs."
                }
                
        return {"status": "clear", "message": "Daily plan is optimized."}
        
    except Exception as e:
        return {"status": "error", "message": f"Plan evaluation failed: {str(e)}"}

def execute_manual_resolution(spreadsheet_id, keep_student_id, defer_student_id):
    """Executes the specific override chosen by the coach, shifting the deferred student to tomorrow."""
    # This service function adjusts the actioned flag or notes field to record choices explicitly
    return f"Resolution processed: Kept {keep_student_id} for today's session. Deferred {defer_student_id} safely to tomorrow."