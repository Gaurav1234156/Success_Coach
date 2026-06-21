import streamlit as st
from data_handler import load_school_data, build_student_profile
from ai_agent import get_openai_client, generate_system_prompt
from knowledge_base import search_knowledge_base
from user_memory import store_session_data, retrieve_past_memories
from auth import show_login_page
from signal_processor import detect_and_save_signal
from coach_agent import get_coach_agent
from briefing_generator import generate_pre_meeting_brief
from plan_manager import evaluate_and_update_plan, execute_manual_resolution # <--- NEW IMPORT

# --- ADD THIS INITIALIZATION BLOCK ---
if "messages" not in st.session_state:
    st.session_state.messages = []
# --------------------------------------

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
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    show_login_page(roster)
    st.stop() 

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
            # if st.sidebar.button("📅 Generate Today's Plan"):
            #     with st.spinner("Agent is reasoning through signals..."):
            #         try:
            #             agent = get_coach_agent()
            #             input_msg = """
            #             1. Use the get_pending_signals tool to fetch the un-actioned signals.
            #             2. Prioritize the students based on severity/urgency.
            #             3. Use the create_calendar_event tool to schedule them for today. 
            #                IMPORTANT: Ensure the start_time is strictly in ISO format with the IST timezone offset (e.g., 'YYYY-MM-DDT10:00:00+05:30').
            #             4. Use the update_sheet_actioned tool to mark them as done.
            #             Give me a final report of what you did.
            #             """
            #             response = agent.invoke({"messages": [("user", input_msg)]})
            #             plan = response["messages"][-1].content
            #             st.sidebar.success("Plan generated!")
            #             st.write("### Agent's Planning Report:")
            #             st.markdown(plan)
            #         except Exception as e:
            #             st.error(f"Agent failed: {e}")

            if st.sidebar.button("📅 Generate Today's Plan"):
                with st.spinner("Agent is reasoning through signals..."):
                    try:
                        import datetime
                        today_str = datetime.datetime.now().strftime("%Y-%m-%d")
                        
                        agent = get_coach_agent()
                        
                        # UPDATED PROMPT: Strict scheduling and capacity limits
                        input_msg = f"""
                        Today's date is {today_str}.
                        
                        1. Use the get_pending_signals tool to fetch ALL un-actioned signals.
                        2. Prioritize them based on severity and urgency.
                        3. CAPACITY LIMIT: You only have time for a MAXIMUM of 4 students today. Select only the top 4 most urgent cases. Ignore the rest for now.
                        4. Use the create_calendar_event tool to schedule the selected students. 
                           - STRICT TIME RULE: You MUST stagger the sessions. Start at 09:00 AM IST and use 30-minute intervals.
                           - Use exactly these start times for your up to 4 slots: 
                             Slot 1: '{today_str}T09:00:00+05:30'
                             Slot 2: '{today_str}T09:30:00+05:30'
                             Slot 3: '{today_str}T10:00:00+05:30'
                             Slot 4: '{today_str}T10:30:00+05:30'
                           - NEVER schedule two students at the same time.
                        5. Use the update_sheet_actioned tool to mark ONLY the scheduled students as done.
                        
                        Give me a final report of who you scheduled, their times, and who was left un-actioned.
                        """
                        response = agent.invoke({"messages": [("user", input_msg)]})
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
            selected_id = st.session_state.student_id
            id_to_name = {st.session_state.student_id: st.session_state.student_name}

        # --- UNIVERSAL APP LOGIC ---
        if st.sidebar.button("💾 Save & End Session", use_container_width=True):
            if "messages" in st.session_state and len(st.session_state.messages) > 1:
                with st.spinner("Saving session and checking for signals..."):
                    store_session_data(st.session_state.messages, selected_id)
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

        student_context = build_student_profile(selected_id, roster, scores, attendance, schedule, signals)

        # ==========================================
        # 4. REAL-TIME DISRUPTION ENGINE (MILESTONE 9)
        # ==========================================
        if st.session_state.role == "coach":
            # Run background plan health validation instantly on dashboard focus
            plan_status = evaluate_and_update_plan(SPREADSHEET_ID)
            
            if plan_status["status"] in ["auto_inserted", "auto_bumped"]:
                st.info(f"🔄 **Notification Area: System Plan Change**\n\n{plan_status['summary']}")
                
            elif plan_status["status"] == "conflict_deadlock":
                st.warning("🚨 **Immediate Attention Required: Scheduling Tradeoff Deadlock**")
                
                with st.container(border=True):
                    st.markdown(f"### {plan_status['summary']}")
                    st.write("The platform cannot resolve this conflict automatically. Review the cases below:")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown(f"**Option A: Keep {plan_status['student_a']}**")
                        st.caption(f"Reasoning: {plan_status['reason_a']}")
                        if st.button(f"Prioritize {plan_status['student_a']}", use_container_width=True):
                            res = execute_manual_resolution(SPREADSHEET_ID, plan_status['student_a'], plan_status['student_b'])
                            st.success(res)
                            st.rerun()
                            
                    with col2:
                        st.markdown(f"**Option B: Prioritize {plan_status['student_b']}**")
                        st.caption(f"Reasoning: {plan_status['reason_b']}")
                        if st.button(f"Prioritize {plan_status['student_b']}", use_container_width=True):
                            res = execute_manual_resolution(SPREADSHEET_ID, plan_status['student_b'], plan_status['student_a'])
                            st.success(res)
                            st.rerun()
                st.stop() # Halt normal operation until conflict resolution choice is locked in

        # ==========================================
        # 5. MAIN UI & CHAT MANAGEMENT
        # ==========================================
        st.title(f"🎓 Coach for: {id_to_name.get(selected_id)}")

        # Milestone 8: Pre-Meeting Brief UI
        if st.session_state.role == "coach":
            with st.expander("📋 Prepare for Meeting: AI Brief", expanded=False):
                st.write("Get a synthesized brief combining real-time academic stats with past session memories.")
                
                if st.button("🤖 Generate Pre-Meeting Brief", use_container_width=True):
                    with st.spinner(f"Synthesizing data and memories for {id_to_name.get(selected_id)}..."):
                        brief = generate_pre_meeting_brief(
                            student_name=id_to_name.get(selected_id),
                            student_context=student_context,
                            student_facts=st.session_state.get('student_facts', 'No facts yet.'),
                            session_summaries=st.session_state.get('session_summaries', 'No sessions yet.')
                        )
                        st.session_state.current_brief = brief
                
                if "current_brief" in st.session_state:
                    st.markdown(st.session_state.current_brief)

        # The raw memory sidebar for debugging/reference
        with st.sidebar.expander("🧠 Raw Memory Data"):
            st.markdown("**Factual Traits & Triggers:**")
            st.info(st.session_state.get('student_facts', 'No facts yet.'))
            st.markdown("**Past Session Summaries:**")
            st.success(st.session_state.get('session_summaries', 'No sessions yet.'))

        # Display history
        for message in st.session_state.messages:
            if message["role"] != "system":
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

        # ==========================================
        # 6. CHAT INPUT BOX & LOGIC
        # ==========================================
        if user_input := st.chat_input("Type your message here..."):
            with st.chat_message("user"):
                st.markdown(user_input)
            
            st.session_state.messages.append({"role": "user", "content": user_input})

            with st.chat_message("assistant"):
                try:
                    with st.spinner("Checking course materials..."):
                        retrieved_facts = search_knowledge_base(user_input, n_results=2)
                    
                    messages_for_ai = st.session_state.messages.copy()
                    
                    memory_reminder = f"""
                    INTERNAL COACHING REMINDER: 
                    Do not forget this student's past history when replying to their message:
                    - Facts & Traits: {st.session_state.get('student_facts', 'None')}
                    - Past Sessions & Goals: {st.session_state.get('session_summaries', 'None')}
                    """
                    messages_for_ai.append({"role": "system", "content": memory_reminder})
                    
                    if retrieved_facts and "No matching documentation found" not in retrieved_facts:
                        st.toast("📚 Fact retrieved from ChromaDB!") 
                        knowledge_prompt = f"The student asked a question. Use this retrieved data accurately:\n{retrieved_facts}"
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