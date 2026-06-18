import os
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

# Load the API key from your .env file
load_dotenv()

# Initialize the OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Set up the visual header for the web app
st.set_page_config(page_title="Success Coach", page_icon="🎓")
st.title("🎓 Your Success Coach")
st.write("Ask me anything about your academic, personal, or career goals!")

# Initialize chat history in Streamlit's session state (memory)
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "system", 
            "content": "You are a supportive, insightful, and knowledgeable student success coach. Your goal is to help students navigate their academic, personal, and career challenges. Keep your answers concise, encouraging, and actionable."
        }
    ]

# Display previous chat messages (skipping the hidden system prompt)
for message in st.session_state.messages:
    if message["role"] != "system":
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

# Create the input box for the user
if user_input := st.chat_input("Type your message here..."):
    
    # 1. Display user's message on the screen
    with st.chat_message("user"):
        st.markdown(user_input)
    
    # 2. Add user's message to memory
    st.session_state.messages.append({"role": "user", "content": user_input})

    # 3. Get the AI's response and display it
    with st.chat_message("assistant"):
        try:
            # Send the whole conversation history to OpenAI
            response = client.chat.completions.create(
                model="gpt-5.4-mini-2026-03-17",
                messages=st.session_state.messages
            )
            
            # Extract and show the reply
            reply = response.choices[0].message.content
            st.markdown(reply)
            
            # Add the reply to memory
            st.session_state.messages.append({"role": "assistant", "content": reply})
            
        except Exception as e:
            st.error(f"Error connecting to AI: {e}")