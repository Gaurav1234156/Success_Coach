import chromadb
import streamlit as st
from openai import OpenAI

# 1. Initialize ChromaDB 
# This creates a folder named 'chroma_db' in your project to save data permanently
chroma_client = chromadb.PersistentClient(path="./chroma_db")

def get_embedding(text):
    """Translates plain text into a vector (list of numbers) using OpenAI."""
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    response = client.embeddings.create(
        input=text,
        model="text-embedding-3-small"
    )
    return response.data[0].embedding

def get_collection():
    """Gets or creates the 'folder' inside ChromaDB where we store facts."""
    return chroma_client.get_or_create_collection(name="course_materials")

def add_study_material(text_content, doc_id, student_id="ALL"):
    """Saves a new fact into the database."""
    collection = get_collection()
    embedding = get_embedding(text_content)
    
    # We store the text, the vector, and metadata (like who it belongs to)
    collection.add(
        documents=[text_content],
        embeddings=[embedding],
        ids=[doc_id], # A unique ID for this specific fact
        metadatas=[{"student_id": student_id}] 
    )

def search_course_materials(student_query, student_id, n_results=2):
    """Searches the database for the closest facts to the student's question."""
    try:
        collection = get_collection()
        query_embedding = get_embedding(student_query)
        
        # Search for the top 'n' results. 
        # We use a 'where' filter to only get facts for this specific student (or universal facts labeled 'ALL')
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where={"student_id": {"$in": [student_id, "ALL"]}}
        )
        
        # If we found matching documents, join them into one readable string
        if results['documents'] and len(results['documents'][0]) > 0:
            knowledge_text = "\n\n".join(results['documents'][0])
            return knowledge_text
            
        return "No specific course materials found for this topic."
    
    except Exception as e:
        return f"Error searching knowledge base: {e}"