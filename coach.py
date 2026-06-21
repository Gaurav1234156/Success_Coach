import streamlit as st
from data_handler import load_school_data, build_student_profile
from ai_agent import get_openai_client, generate_system_prompt
from knowledge_base import search_knowledge_base
from user_memory import store_session_data, retrieve_past_memories
from auth import show_login_page
from signal_processor import detect_and_save_signal
from coach_agent import get_coach_agent

# ==========================================
# 1. PAGE CONFIGURATION & SETUP
# ==========================================
st.set_page_config(page_title="Success Coach", page_icon="🎓")
client = get_openai_client()

try:
    SPREADSHEET_ID = st.secrets["GOOGLE_SPREADSHEET_ID"]
except KeyError:
    st.error("Google Spreadsheet ID not found. Please ensure it is saved in .streamlit/secrets.toml")
    st.stop()

# Load Data 
roster, scores, attendance, schedule, signals, tab_names = load_school_data(SPREADSHEET_ID)

# ==========================================
# 2. AUTHENTICATION ROUTING LOGIC
# ==========================================
# Initialize login state if it doesn't exist yet
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# If not logged in, show the login page and STOP the script from running further
if not st.session_state.logged_in:
    show_login_page(roster)
    st.stop() 

# Add a universal Logout button to the sidebar
if st.sidebar.button("🚪 Logout", use_container_width=True):
    st.session_state.clear()
    st.rerun()

st.sidebar.divider()

# ==========================================
# 3. MAIN INTERFACE LOGIC
# ==========================================
if roster is not None and not roster.empty:
    student_id_column = 'student_id'
    name_column = 'name' 
    
    if student_id_column in roster.columns and name_column in roster.columns:
        
        # --- VIEW 1: COACH DASHBOARD ---
        if st.session_state.role == "coach":
            st.sidebar.title("Coach Portal")
            
            # Build Sidebar Dropdown for Coach to select any student
            id_to_name = dict(zip(roster[student_id_column].astype(str), roster[name_column].astype(str)))
            student_ids = list(id_to_name.keys())
            
            selected_id = st.sidebar.selectbox(
                "Select a Student to view:", 
                options=student_ids,
                format_func=lambda x: id_to_name.get(x, "Unknown Student")
            )
            
            # Autonomous Planning Block (LangChain Agent)
            st.sidebar.divider()
            st.sidebar.subheader("Autonomous Planning")
            if st.sidebar.button("📅 Generate Today's Plan"):
                with st.spinner("Agent is reasoning through signals..."):
                    try:
                        agent = get_coach_agent()
                        
                        # Modern agents use .invoke()
                        # The agent expects a list of messages
                        # input_msg = "Analyze the signal_sheet, prioritize students, create calendar events, and mark them as actioned."
                        # Inside the Generate Today's Plan button block...
                        input_msg = """
                        1. Use the get_pending_signals tool to fetch the un-actioned signals.
                        2. Prioritize the students based on severity/urgency.
                        3. Use the create_calendar_event tool to schedule them for today.
                        4. Use the update_sheet_actioned tool to mark them as done.
                        Give me a final report of what you did.
                        """
                        response = agent.invoke({"messages": [("user", input_msg)]})
                        
                        # Extract the final answer from the message history
                        plan = response["messages"][-1].content
                        
                        st.sidebar.success("Plan generated!")
                        st.write("### Agent's Planning Report:")
                        st.markdown(plan)
                    except Exception as e:
                        st.error(f"Agent failed: {e}")
            
        # --- VIEW 2: STUDENT DASHBOARD ---
        elif st.session_state.role == "student":
            st.sidebar.title("Student Portal")
            st.sidebar.success(f"Logged in as:\n{st.session_state.student_name}")
            
            # Lock the selected ID to the logged-in student (no dropdown!)
            selected_id = st.session_state.student_id
            
            # Build a dictionary just to get their name for the title
            id_to_name = {st.session_state.student_id: st.session_state.student_name}

        # --- UNIVERSAL APP LOGIC (Runs for both Coach and Student) ---
        if st.sidebar.button("💾 Save & End Session", use_container_width=True):
            if "messages" in st.session_state and len(st.session_state.messages) > 1:
                with st.spinner("Saving session and checking for signals..."):
                    
                    # 1. Save memories to Mem0
                    store_session_data(st.session_state.messages, selected_id)
                    
                    # 2. Check for Signals and append to Google Sheets
                    student_name = id_to_name.get(selected_id, "Unknown Student")
                    signal_triggered = detect_and_save_signal(
                        st.session_state.messages, 
                        selected_id, 
                        student_name, 
                        SPREADSHEET_ID
                    )
                    
                    if signal_triggered:
                        st.sidebar.error("⚠️ An alert signal was generated for this session.")
                
                st.toast("✅ Session saved to memory!")
                st.session_state.messages = []
                st.rerun()
            else:
                st.sidebar.warning("No conversation to save yet.")
                
        if st.sidebar.button("🗑️ Start New Chat (Don't Save)", use_container_width=True):
            st.session_state.messages = []
            st.rerun()

        # Process the specific student's data
        student_context = build_student_profile(selected_id, roster, scores, attendance, schedule, signals)

        # Build Main UI
        st.title(f"🎓 Coach for: {id_to_name.get(selected_id)}")
        st.write("Ask me how you're doing in class or for help planning your week!")

        # ==========================================
        # 4. CHAT MANAGEMENT & INITIALIZATION
        # ==========================================
        system_prompt = generate_system_prompt(student_context)

        # Reset chat if a new student is selected or chat is empty
        if "messages" not in st.session_state or st.session_state.get("current_student") != selected_id or not st.session_state.messages:
            
            # Fetch BOTH types of memory
            with st.spinner("Recalling past sessions and student facts..."):
                student_facts, session_summaries = retrieve_past_memories(selected_id)
                
                st.session_state.student_facts = student_facts
                st.session_state.session_summaries = session_summaries
            
            # Inject deep context into the AI
            memory_injection = f"""
            
            === FACTUAL MEMORY ===
            (Student traits, stressors, and recurring patterns):
            {student_facts}
            
            === CHRONOLOGICAL SESSION SUMMARIES ===
            (What was discussed and decided in past meetings):
            {session_summaries}
            
            CRITICAL INSTRUCTION: You are a long-term mentor. Use the chronological session summaries above to understand the student's journey. If they have had multiple sessions, acknowledge their ongoing progress and reference past decisions naturally.
            """
            final_system_prompt = system_prompt + memory_injection
            
            st.session_state.messages = [{"role": "system", "content": final_system_prompt}]
            st.session_state.current_student = selected_id

        # The Coach's Briefing Sidebar
        with st.sidebar.expander("📋 Request Coach's Briefing"):
            st.markdown("**🧠 Factual Traits & Triggers:**")
            st.info(st.session_state.get('student_facts', 'No facts yet.'))
            st.markdown("**📅 Past Session Summaries:**")
            st.success(st.session_state.get('session_summaries', 'No sessions yet.'))

        # Display history
        for message in st.session_state.messages:
            if message["role"] != "system":
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

        # ==========================================
        # 5. CHAT INPUT BOX & LOGIC
        # ==========================================
        if user_input := st.chat_input("Type your message here..."):
            with st.chat_message("user"):
                st.markdown(user_input)
            
            st.session_state.messages.append({"role": "user", "content": user_input})

            with st.chat_message("assistant"):
                try:
                    # ChromaDB Search (RAG)
                    with st.spinner("Checking course materials..."):
                        retrieved_facts = search_knowledge_base(user_input, n_results=2)
                    
                    messages_for_ai = st.session_state.messages.copy()
                    
                    # Dynamic Memory Injection Whisper
                    memory_reminder = f"""
                    INTERNAL COACHING REMINDER: 
                    Do not forget this student's past history when replying to their message:
                    - Facts & Traits: {st.session_state.get('student_facts', 'None')}
                    - Past Sessions & Goals: {st.session_state.get('session_summaries', 'None')}
                    
                    CRITICAL INSTRUCTION: Explicitly tailor your advice to align with their past goals and history.
                    """
                    messages_for_ai.append({"role": "system", "content": memory_reminder})
                    
                    # ChromaDB Injection
                    if retrieved_facts and "No matching documentation found" not in retrieved_facts:
                        st.toast("📚 Fact retrieved from ChromaDB!") 
                        knowledge_prompt = f"""
                        The student just asked a question. Here is accurate information retrieved from your course database:
                        
                        {retrieved_facts}
                        
                        CRITICAL INSTRUCTION: Use the information above to answer the student's question accurately. Do not contradict the database.
                        """
                        messages_for_ai.append({"role": "system", "content": knowledge_prompt})

                    response = client.chat.completions.create(
                        model="gpt-5.4-mini-2026-03-17",
                        messages=messages_for_ai
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