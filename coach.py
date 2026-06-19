import streamlit as st
from data_handler import load_school_data, build_student_profile
from ai_agent import get_openai_client, generate_system_prompt
from knowledge_base import search_knowledge_base
from user_memory import store_session_data, retrieve_past_memories

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

        # Add a Save & End Session Button to the sidebar
        st.sidebar.divider()
        if st.sidebar.button("💾 Save & End Session", use_container_width=True):
            if "messages" in st.session_state and len(st.session_state.messages) > 1:
                with st.spinner("Extracting and saving session memories..."):
                    store_session_data(st.session_state.messages, selected_id)
                st.toast("✅ Session saved to memory!")
                # Clear the chat history to start fresh next time
                st.session_state.messages = []
                st.rerun()
            else:
                st.sidebar.warning("No conversation to save yet.")
                
        # Optional: Button to clear chat without saving to Mem0
        if st.sidebar.button("🗑️ Start New Chat (Don't Save)", use_container_width=True):
            st.session_state.messages = []
            st.rerun()

        # Process the student's data using our imported function
        student_context = build_student_profile(selected_id, roster, scores, attendance, schedule, signals)

        # Build Main UI
        st.title(f"🎓 Coach for: {id_to_name.get(selected_id)}")
        st.write("Ask me how you're doing in class or for help planning your week!")

        # 4. Chat Management & Initialization
        system_prompt = generate_system_prompt(student_context)

        # Reset chat if a new student is selected or chat is empty
        if "messages" not in st.session_state or st.session_state.get("current_student") != selected_id or not st.session_state.messages:
            
            # Fetch BOTH types of memory
            with st.spinner("Recalling past sessions and student facts..."):
                student_facts, session_summaries = retrieve_past_memories(selected_id)
                
                # Save them to session state so we can display them in the sidebar
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

        # ==========================================
        # MILESTONE 5: THE COACH'S BRIEFING SIDEBAR
        # ==========================================
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

#         # Chat Input Box & Logic
#         if user_input := st.chat_input("Type your message here..."):
#             with st.chat_message("user"):
#                 st.markdown(user_input)
            
#             st.session_state.messages.append({"role": "user", "content": user_input})

#             with st.chat_message("assistant"):
#                 try:
#                     # ==========================================
#                     # MILESTONE 3: CHROMADB SEARCH (RAG)
#                     # ==========================================
#                     with st.spinner("Checking course materials..."):
#                         retrieved_facts = search_knowledge_base(user_input, n_results=2)
                    
#                     # # Copy the chat history for this specific API call
#                     # messages_for_ai = st.session_state.messages.copy()

#                     # Copy the chat history for this specific API call
#                     messages_for_ai = st.session_state.messages.copy()
                    
#                     # ==========================================
#                     # DYNAMIC MEMORY INJECTION
#                     # Whisper the memory to the AI right before it responds!
#                     # ==========================================
#                     memory_reminder = f"""
#                     INTERNAL COACHING REMINDER: 
#                     Do not forget this student's past history when replying to their message:
#                     - Facts & Traits: {st.session_state.get('student_facts', 'None')}
#                     - Past Sessions & Goals: {st.session_state.get('session_summaries', 'None')}
                    
#                     CRITICAL INSTRUCTION: Explicitly tailor your advice to align with their past goals and history.
#                     """
#                     messages_for_ai.append({"role": "system", "content": memory_reminder})
#                     # ==========================================
                    
#                     # If ChromaDB found something, inject it into the prompt!
#                     if retrieved_facts and "No matching documentation found" not in retrieved_facts:
                    
#                     # If ChromaDB found something, inject it into the prompt!
#                     if retrieved_facts and "No matching documentation found" not in retrieved_facts:
#                         st.toast("📚 Fact retrieved from ChromaDB!") 
#                         knowledge_prompt = f"""
#                         The student just asked a question. Here is accurate information retrieved from your course database:
                        
#                         {retrieved_facts}
                        
#                         CRITICAL INSTRUCTION: Use the information above to answer the student's question accurately. Do not contradict the database.
#                         """
#                         messages_for_ai.append({"role": "system", "content": knowledge_prompt})
#                     # ==========================================

#                     response = client.chat.completions.create(
#                         model="gpt-5.4-mini-2026-03-17",
#                         messages=messages_for_ai
#                     )
#                     reply = response.choices[0].message.content
#                     st.markdown(reply)
#                     st.session_state.messages.append({"role": "assistant", "content": reply})
                    
#                 except Exception as e:
#                     st.error(f"Error connecting to AI: {e}")
                    
#     else:
#         st.error(f"Could not find columns named '{student_id_column}' or '{name_column}' in your roster tab.")
        
# elif roster is not None and roster.empty:
#     st.warning("Connected to the Google Sheet, but the 'roster' tab is empty or couldn't be found.")
# Chat Input Box & Logic
        if user_input := st.chat_input("Type your message here..."):
            with st.chat_message("user"):
                st.markdown(user_input)
            
            st.session_state.messages.append({"role": "user", "content": user_input})

            with st.chat_message("assistant"):
                try:
                    # ==========================================
                    # MILESTONE 3: CHROMADB SEARCH (RAG)
                    # ==========================================
                    with st.spinner("Checking course materials..."):
                        retrieved_facts = search_knowledge_base(user_input, n_results=2)
                    
                    # Copy the chat history for this specific API call
                    messages_for_ai = st.session_state.messages.copy()
                    
                    # ==========================================
                    # DYNAMIC MEMORY INJECTION
                    # Whisper the memory to the AI right before it responds!
                    # ==========================================
                    memory_reminder = f"""
                    INTERNAL COACHING REMINDER: 
                    Do not forget this student's past history when replying to their message:
                    - Facts & Traits: {st.session_state.get('student_facts', 'None')}
                    - Past Sessions & Goals: {st.session_state.get('session_summaries', 'None')}
                    
                    CRITICAL INSTRUCTION: Explicitly tailor your advice to align with their past goals and history.
                    """
                    messages_for_ai.append({"role": "system", "content": memory_reminder})
                    # ==========================================
                    
                    # If ChromaDB found something, inject it into the prompt!
                    if retrieved_facts and "No matching documentation found" not in retrieved_facts:
                        st.toast("📚 Fact retrieved from ChromaDB!") 
                        knowledge_prompt = f"""
                        The student just asked a question. Here is accurate information retrieved from your course database:
                        
                        {retrieved_facts}
                        
                        CRITICAL INSTRUCTION: Use the information above to answer the student's question accurately. Do not contradict the database.
                        """
                        messages_for_ai.append({"role": "system", "content": knowledge_prompt})
                    # ==========================================

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