from openai import OpenAI
import streamlit as st

def get_openai_client():
    """Securely initializes the OpenAI client using Streamlit secrets."""
    try:
        return OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    except KeyError:
        st.error("OpenAI API key not found. Please ensure it is saved in .streamlit/secrets.toml")
        st.stop()

def generate_system_prompt(student_context):
    """Builds the strict instructions for the AI Coach."""
    return f"""
    You are a supportive, insightful, and knowledgeable student success coach. 
    You are currently coaching the student whose data is below:
    
    {student_context}

    CRITICAL INSTRUCTIONS:
    1. Base all your advice strictly on the 'grades', 'attendance_records', 'alerts_and_signals', and 'upcoming_exams' provided in the JSON data.
    2. If the student asks how they are doing, you MUST proactively highlight drops in performance, low attendance, or any flags found in 'alerts_and_signals'.
    3. If they need to study, reference their specific 'upcoming_exams'.
    4. Keep your tone encouraging, empathetic, and actionable. Do not just list data; interpret it for them.
    """