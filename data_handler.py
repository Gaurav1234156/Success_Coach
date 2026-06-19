import pandas as pd
import streamlit as st
import json

@st.cache_data(ttl=600)
def load_school_data(sheet_id):
    """Fetches data directly from the public Google Sheet using the ID."""
    try:
        export_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=xlsx"
        tabs = pd.read_excel(export_url, sheet_name=None)
        
        roster = tabs.get('roster', pd.DataFrame())
        scores = tabs.get('exam_scores', pd.DataFrame())
        attendance = tabs.get('attendance', pd.DataFrame())
        schedule = tabs.get('exam_schedule', pd.DataFrame())
        signals = tabs.get('signal_sheet', pd.DataFrame())
        
        return roster, scores, attendance, schedule, signals, list(tabs.keys())
    except Exception as e:
        st.error(f"Error loading Google Sheet data: {e}")
        return None, None, None, None, None, []

def build_student_profile(selected_id, roster, scores, attendance, schedule, signals):
    """Filters all dataframes for the specific student and bundles into JSON."""
    student_id_column = 'student_id'
    
    def get_student_records(df):
        if not df.empty and student_id_column in df.columns:
            return df[df[student_id_column].astype(str) == selected_id].to_dict('records')
        return []

    student_data = {
        "profile": get_student_records(roster)[0] if get_student_records(roster) else {},
        "grades": get_student_records(scores),
        "attendance_records": get_student_records(attendance),
        "alerts_and_signals": get_student_records(signals),
        "upcoming_exams": schedule.to_dict('records') if not schedule.empty else []
    }
    
    return json.dumps(student_data, indent=2)