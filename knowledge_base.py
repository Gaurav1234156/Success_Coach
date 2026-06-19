import chromadb
import streamlit as st
from openai import OpenAI

# Initialize the local persistent ChromaDB client
# This creates a folder named 'chroma_db' in your project directory
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

def add_document_chunk(text_content, doc_id, metadata):
    """Saves a specific chunk of documentation along with its vector embedding."""
    collection = get_collection()
    embedding = get_embedding(text_content)
    
    collection.add(
        documents=[text_content],
        embeddings=[embedding],
        ids=[doc_id],
        metadatas=[metadata]
    )

def search_knowledge_base(user_query, n_results=2):
    """Searches ChromaDB for the most contextually relevant documentation chunks."""
    try:
        collection = get_collection()
        query_embedding = get_embedding(user_query)
        
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )
        
        if results['documents'] and len(results['documents'][0]) > 0:
            # Combine the matching document chunks into a single reference block
            return "\n\n---\n\n".join(results['documents'][0])
            
        return "No matching documentation found."
    except Exception as e:
        return f"Error searching knowledge base: {e}"