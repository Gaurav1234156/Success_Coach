import pandas as pd
import streamlit as st
import json
import numpy as np
from datetime import datetime, date

# class CustomJSONEncoder(json.JSONEncoder):
#     """Custom encoder to handle pandas/numpy/datetime types automatically."""
#     def default(self, obj):
#         if isinstance(obj, (pd.Timestamp, datetime, date)):
#             return obj.isoformat()
#         if isinstance(obj, (np.integer, np.floating)):
#             return float(obj)
#         if isinstance(obj, np.ndarray):
#             return obj.tolist()
#         if pd.isna(obj):
#             return None
#         return str(obj) # Final safety fallback

# def build_student_profile(selected_id, roster, scores, attendance, schedule, signals):
#     # ... (all your existing logic to build 'student_data' dictionary) ...
    
#     # Use the cls parameter to force the use of our custom encoder
#     return json.dumps(student_data, indent=2, cls=CustomJSONEncoder)

# Add this helper function at the top of your data_handler.py
def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, (pd.Timestamp, pd.DatetimeIndex)):
        return obj.strftime('%Y-%m-%d %H:%M:%S')
    if hasattr(obj, 'isoformat'): # Handles datetime.date and datetime.datetime
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

# def build_student_profile(selected_id, roster, scores, attendance, schedule, signals):
#     # ... your existing logic to build the student_data dictionary ...
    
#     # Define a 'universal' serializer that forces EVERYTHING to string if it fails
#     def default_converter(o):
#         if isinstance(o, (pd.Timestamp, pd.DatetimeIndex, pd.Period)):
#             return o.strftime('%Y-%m-%d %H:%M:%S')
#         if isinstance(o, (np.integer, np.floating)):
#             return float(o)
#         if isinstance(o, np.ndarray):
#             return o.tolist()
#         # The ultimate fallback: turn any unknown object into a string
#         return str(o)

#     # Use the 'default' parameter to run the converter on every object
#     return json.dumps(
#     student_data,
#     indent=2,
#     default=str
# )

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
    
    return json.dumps(
    student_data,
    indent=2,
    default=str
)