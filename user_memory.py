import streamlit as st
from mem0 import MemoryClient
from ai_agent import get_openai_client
from datetime import datetime

def get_mem0_client():
    """Securely initializes the Mem0 client."""
    try:
        return MemoryClient(api_key=st.secrets["MEM0_API_KEY"])
    except KeyError:
        st.error("MEM0_API_KEY not found. Please add it to .streamlit/secrets.toml")
        st.stop()

def store_session_data(chat_messages, student_id):
    """Saves raw facts natively, and generates a structured Session Summary."""
    client = get_mem0_client()
    openai_client = get_openai_client()
    
    # Filter out system instructions
    conversation_only = [msg for msg in chat_messages if msg["role"] != "system"]
    
    if len(conversation_only) > 1:
        # 1. NATIVE MEM0: Extract raw factual memory (traits, triggers)
        client.add(messages=conversation_only, user_id=student_id)
        
        # 2. OPENAI: Generate a Session Summary
        summary_instructions = """You are a meticulous note-taking assistant. Summarize the following coaching conversation. 
        You MUST extract and include:
        1) Personal Trivia: Where they are from, hobbies, life events, or family details.
        2) State of Mind: The student's mood or stress levels.
        3) Academic Context: What subjects or goals were discussed.
        4) Action Items: Any decisions made.
        Do not leave out personal facts, no matter how small."""
        summary_messages = [{"role": "system", "content": summary_instructions}] + conversation_only
        
        try:
            response = openai_client.chat.completions.create(
                model="gpt-5.4-mini-2026-03-17", # Fast model for backend summarization
                messages=summary_messages
            )
            session_summary = response.choices[0].message.content
            
            # 3. Save the summary with a specific metadata tag
            date_str = datetime.now().strftime("%B %d, %Y")
            final_summary_text = f"Session on {date_str}: {session_summary}"
            
            client.add(final_summary_text, user_id=student_id, metadata={"type": "session_summary"})
        except Exception as e:
            print(f"Summary generation error: {e}")

def retrieve_past_memories(student_id):
    """Fetches and separates factual traits from chronological session summaries."""
    try:
        client = get_mem0_client()
        memories = client.get_all(filters={"user_id": student_id})
        
        facts = []
        summaries = []
        
        # Handle different Mem0 response formats securely
        if memories and isinstance(memories, list):
            iterable = memories
        elif memories and "results" in memories:
             iterable = memories["results"]
        else:
             iterable = []
             
        for m in iterable:
            memory_text = m.get("memory", str(m))
            metadata = m.get("metadata", {})
            
            # Separate the data based on our custom tag
            if metadata and metadata.get("type") == "session_summary":
                summaries.append(memory_text)
            else:
                facts.append(memory_text)
                
        # Format them beautifully for the AI's prompt
        formatted_facts = "\n".join([f"- {fact}" for fact in facts]) if facts else "No specific facts recorded yet."
        formatted_summaries = "\n\n".join(summaries) if summaries else "No past sessions recorded."
        
        return formatted_facts, formatted_summaries
        
    except Exception as e:
        print(f"Memory retrieval error: {e}")
        return "No past memories found.", "No past sessions found."