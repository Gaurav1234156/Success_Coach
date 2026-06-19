import os
import json
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

# 1. Load variables from the .env file
load_dotenv()

# Initialize OpenAI Client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

st.set_page_config(page_title="Success Coach", page_icon="🎓")

# ==========================================
# MILESTONE 2: Live Google Sheet Integration
# ==========================================

# 2. Load the exact variable name you set in .env
SPREADSHEET_ID = os.getenv("GOOGLE_SPREADSHEET_ID")

if not SPREADSHEET_ID:
    st.error("Google Spreadsheet ID not found. Please ensure it is saved as GOOGLE_SPREADSHEET_ID in your .env file.")
    st.stop() # Stops the app from crashing further down

@st.cache_data(ttl=600)  # Caches the data for 10 minutes
def load_school_data(sheet_id):
    """Fetches data directly from the public Google Sheet using the ID."""
    try:
        # Construct the export link using the ID
        export_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=xlsx"
        
        # Read all tabs from the Google Sheet into a dictionary of DataFrames
        # NOTE: This requires 'openpyxl' to be installed.
        tabs = pd.read_excel(export_url, sheet_name=None)
        
        # Extract specific tabs based on expected names
        roster = tabs.get('roster', pd.DataFrame())
        scores = tabs.get('exam_scores', pd.DataFrame())
        attendance = tabs.get('attendance', pd.DataFrame())
        schedule = tabs.get('exam_schedule', pd.DataFrame())
        signals = tabs.get('signal_sheet', pd.DataFrame())
        
        return roster, scores, attendance, schedule, signals, list(tabs.keys())
    except Exception as e:
        st.error(f"Error loading Google Sheet data: {e}")
        return None, None, None, None, None, []

# Fetch the data
roster, scores, attendance, schedule, signals, tab_names = load_school_data(SPREADSHEET_ID)

st.sidebar.title("Student Portal")

# Check if data loaded and roster tab was found
if roster is not None and not roster.empty:
    
    # Identify the column used for Student IDs
    # student_id_column = 'student_id' 
    
    # if student_id_column in roster.columns:
    #     # Create a dropdown in the sidebar
    #     student_ids = roster[student_id_column].astype(str).unique().tolist()
    #     selected_id = st.sidebar.selectbox("Select your Student ID to log in:", student_ids)

    # Identify the columns used for Student IDs and Names
    student_id_column = 'student_id'
    name_column = 'name' 
    
    if student_id_column in roster.columns and name_column in roster.columns:
        # Create a dictionary map linking each ID to its corresponding Name
        id_to_name = dict(zip(roster[student_id_column].astype(str), roster[name_column].astype(str)))
        
        # Create the dropdown list of IDs
        student_ids = list(id_to_name.keys())
        
        # Display the Name in the dropdown, but pass the ID to 'selected_id'
        selected_id = st.sidebar.selectbox(
            "Select a Student to log in:", 
            options=student_ids,
            format_func=lambda x: id_to_name.get(x, "Unknown Student")
        )

        # Helper function to safely filter dataframes
        def get_student_records(df):
            if not df.empty and student_id_column in df.columns:
                return df[df[student_id_column].astype(str) == selected_id].to_dict('records')
            return []

        # Filter all data for the logged-in student
        student_roster = get_student_records(roster)
        student_scores = get_student_records(scores)
        student_attendance = get_student_records(attendance)
        student_signals = get_student_records(signals)
        
        # Schedule usually applies to everyone
        school_schedule = schedule.to_dict('records') if not schedule.empty else []

        # Bundle it all into one master JSON profile
        student_data = {
            "profile": student_roster[0] if student_roster else {},
            "grades": student_scores,
            "attendance_records": student_attendance,
            "alerts_and_signals": student_signals,
            "upcoming_exams": school_schedule
        }
        
        student_context = json.dumps(student_data, indent=2)

        st.title(f"🎓 Coach for Student: {selected_id}")
        st.write("Ask me how you're doing in class or for help planning your week!")

        # System Prompt defining the AI's role and providing the real data
        system_prompt = f"""
        You are a supportive, insightful, and knowledgeable student success coach. 
        You are currently coaching the student whose data is below:
        
        {student_context}

        CRITICAL INSTRUCTIONS:
        1. Base all your advice strictly on the 'grades', 'attendance_records', 'alerts_and_signals', and 'upcoming_exams' provided in the JSON data.
        2. If the student asks how they are doing, you MUST proactively highlight drops in performance, low attendance, or any flags found in 'alerts_and_signals'.
        3. If they need to study, reference their specific 'upcoming_exams'.
        4. Keep your tone encouraging, empathetic, and actionable. Do not just list data; interpret it for them.
        """

        # Initialize chat history (resets if a different student logs in)
        if "messages" not in st.session_state or st.session_state.get("current_student") != selected_id:
            st.session_state.messages = [{"role": "system", "content": system_prompt}]
            st.session_state.current_student = selected_id 

        # Display previous chat messages (hiding the system prompt)
        for message in st.session_state.messages:
            if message["role"] != "system":
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

        # Chat Input Box & Logic
        if user_input := st.chat_input("Type your message here..."):
            with st.chat_message("user"):
                st.markdown(user_input)
            
            st.session_state.messages.append({"role": "user", "content": user_input})

            with st.chat_message("assistant"):
                try:
                    response = client.chat.completions.create(
                        model="gpt-5.4-mini-2026-03-17",
                        messages=st.session_state.messages
                    )
                    reply = response.choices[0].message.content
                    st.markdown(reply)
                    st.session_state.messages.append({"role": "assistant", "content": reply})
                    
                except Exception as e:
                    st.error(f"Error connecting to AI: {e}")
                    
    else:
        st.error(f"Could not find a column named '{student_id_column}' in your roster tab.")
        st.write("Columns found:", roster.columns.tolist())

elif roster is not None and roster.empty:
    st.warning("Connected to the Google Sheet, but the 'roster' tab is empty or couldn't be found.")
    st.write("The code expects tabs named exactly: `roster`, `exam_scores`, `attendance`, `exam_schedule`, `signal_sheet`")
    st.write("**Tabs actually found in your Google Sheet:**", tab_names)