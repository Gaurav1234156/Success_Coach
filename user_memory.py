import streamlit as st
from mem0 import MemoryClient

def get_mem0_client():
    """Securely initializes the Mem0 client."""
    try:
        return MemoryClient(api_key=st.secrets["MEM0_API_KEY"])
    except KeyError:
        st.error("MEM0_API_KEY not found. Please add it to .streamlit/secrets.toml")
        st.stop()

def store_session_data(chat_messages, student_id):
    """Sends the chat history to Mem0 to extract and permanently store user facts."""
    client = get_mem0_client()
    
    # Filter out system prompts/documentation so Mem0 only memorizes the actual conversation
    conversation_only = [msg for msg in chat_messages if msg["role"] != "system"]
    
    if len(conversation_only) > 0:
        # Mem0's AI will automatically read the chat and extract important facts!
        client.add(conversation_only, user_id=student_id)

def retrieve_past_memories(student_id):
    """Fetches previously stored facts about the student from past sessions."""
    try:
        client = get_mem0_client()
        # Retrieve all memories associated with this student
        # memories = client.get_all(user_id=student_id)
        # Retrieve all memories associated with this student using the new filters syntax
        memories = client.get_all(filters={"user_id": student_id})
        
        # Format the memories into a readable list for the AI Coach
        if memories and isinstance(memories, list):
            # Mem0 sometimes returns a list directly or a dict with 'results' depending on version
            facts = [m["memory"] if "memory" in m else str(m) for m in memories]
            return "\n".join([f"- {fact}" for fact in facts])
        elif memories and "results" in memories:
             facts = [m["memory"] for m in memories["results"]]
             return "\n".join([f"- {fact}" for fact in facts])
             
        return "No past memories found."
    except Exception as e:
        print(f"Memory retrieval error: {e}")
        return "No past memories found."