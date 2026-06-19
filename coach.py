import streamlit as st
from data_handler import load_school_data, build_student_profile
from ai_agent import get_openai_client, generate_system_prompt

# 1. Page Configuration & Setup
st.set_page_config(page_title="Success Coach", page_icon="🎓")
client = get_openai_client()

try:
    SPREADSHEET_ID = st.secrets["GOOGLE_SPREADSHEET_ID"]
except KeyError:
    st.error("Google Spreadsheet ID not found. Please ensure it is saved in .streamlit/secrets.toml")
    st.stop()

# 2. Load Data using our imported function
roster, scores, attendance, schedule, signals, tab_names = load_school_data(SPREADSHEET_ID)

st.sidebar.title("Student Portal")

# 3. Main Interface Logic
if roster is not None and not roster.empty:
    student_id_column = 'student_id'
    name_column = 'name' 
    
    if student_id_column in roster.columns and name_column in roster.columns:
        # Build Sidebar Dropdown
        id_to_name = dict(zip(roster[student_id_column].astype(str), roster[name_column].astype(str)))
        student_ids = list(id_to_name.keys())
        
        selected_id = st.sidebar.selectbox(
            "Select a Student to log in:", 
            options=student_ids,
            format_func=lambda x: id_to_name.get(x, "Unknown Student")
        )

        # Process the student's data using our imported function
        student_context = build_student_profile(selected_id, roster, scores, attendance, schedule, signals)

        # Build Main UI
        st.title(f"🎓 Coach for: {id_to_name.get(selected_id)}")
        st.write("Ask me how you're doing in class or for help planning your week!")

        # 4. Chat Management
        system_prompt = generate_system_prompt(student_context)

        # Reset chat if a new student is selected
        if "messages" not in st.session_state or st.session_state.get("current_student") != selected_id:
            st.session_state.messages = [{"role": "system", "content": system_prompt}]
            st.session_state.current_student = selected_id 

        # Display history
        for message in st.session_state.messages:
            if message["role"] != "system":
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

        # Input Box
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
        st.error(f"Could not find columns named '{student_id_column}' or '{name_column}' in your roster tab.")
        
elif roster is not None and roster.empty:
    st.warning("Connected to the Google Sheet, but the 'roster' tab is empty or couldn't be found.")