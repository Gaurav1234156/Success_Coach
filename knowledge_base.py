import chromadb
import streamlit as st
from openai import OpenAI
import os
import re

# Initialize the local persistent ChromaDB client
chroma_client = chromadb.PersistentClient(path="./chroma_db")

def get_embedding(text):
    """Generates vector embeddings for a given text snippet using OpenAI."""
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    response = client.embeddings.create(
        input=text,
        model="text-embedding-3-small"
    )
    return response.data[0].embedding

def get_collection():
    """Retrieves or creates the collection inside ChromaDB."""
    return chroma_client.get_or_create_collection(name="portal_documentation")

def initialize_database():
    """
    Checks if the database is empty. If it is, it automatically opens 
    SETUP_GUIDE 3.md, splits it into sections, and saves it to ChromaDB.
    """
    collection = get_collection()
    
    # If we already have data saved, skip this step to save time and API costs!
    if collection.count() > 0:
        return

    file_path = "SETUP_GUIDE 3.md"
    
    # Check if the file exists before trying to read it
    if not os.path.exists(file_path):
        print(f"Warning: Could not find {file_path}. Make sure it is in the same folder as this script.")
        return

    print(f"Database empty. Reading {file_path} and generating embeddings. This may take a moment...")
    
    # Read the markdown file
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Split the document by markdown headers (# Header)
    sections = re.split(r'\n(?=#+\s)', content)
    
    for index, section in enumerate(sections):
        section = section.strip()
        if not section:
            continue
            
        # Extract title and create a unique ID
        lines = section.split("\n")
        title = lines[0].replace("#", "").strip()
        clean_id = f"chunk_{index}"
        
        # Turn the text into a vector and save it to the database
        embedding = get_embedding(section)
        collection.add(
            documents=[section],
            embeddings=[embedding],
            ids=[clean_id],
            metadatas=[{"title": title, "source": file_path}]
        )
    print("Successfully read SETUP_GUIDE 3.md and populated ChromaDB!")

def search_knowledge_base(user_query, n_results=2):
    """Searches ChromaDB for the most contextually relevant documentation chunks."""
    try:
        # 1. Always ensure the database is initialized before searching
        initialize_database()
        
        # 2. Run the search query against the database
        collection = get_collection()
        query_embedding = get_embedding(user_query)
        
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )
        
        # 3. Format and return the results
        if results['documents'] and len(results['documents'][0]) > 0:
            return "\n\n---\n\n".join(results['documents'][0])
            
        return "No matching documentation found."
    except Exception as e:
        return f"Error searching knowledge base: {e}"