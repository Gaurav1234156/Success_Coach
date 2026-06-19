import os
import re
from knowledge_base import add_document_chunk

def chunk_markdown_file(file_path):
    """
    Reads a markdown file and splits it into sections based on main headers (# or ##).
    Returns a list of dictionaries containing the chunk ID, title, and content text.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Could not find the file: {file_path}. Please check the filename.")

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Split the document by markdown headers (# Header or ## Header)
    # This regex keeps the header titles intact while splitting the sections
    sections = re.split(r'\n(?=#+\s)', content)
    
    chunks = []
    for index, section in enumerate(sections):
        section = section.strip()
        if not section:
            continue
            
        # Extract the first line to use as the title/clean name
        lines = section.split("\n")
        title = lines[0].replace("#", "").strip()
        
        # Create a unique database ID from the index and title
        clean_id = f"chunk_{index}_{re.sub(r'[^a-zA-Z0-9]', '_', title.lower())}"[:50]
        
        chunks.append({
            "id": clean_id,
            "title": title,
            "text": section
        })
        
    return chunks

# ==========================================
# EXECUTION PIPELINE
# ==========================================
FILE_NAME = "SETUP_GUIDE 3.md"

try:
    print(f"Opening and reading '{FILE_NAME}' directly from workspace...")
    documentation_chunks = chunk_markdown_file(FILE_NAME)
    
    print(f"Found {len(documentation_chunks)} distinct sections to process.")
    print("Starting vectorization and database ingestion into ChromaDB...")

    for chunk in documentation_chunks:
        print(f" -> Ingesting section: '{chunk['title']}'")
        add_document_chunk(
            text_content=chunk['text'],
            doc_id=chunk['id'],
            metadata={"title": chunk['title'], "source": FILE_NAME}
        )

    print("\nSuccess! Your ChromaDB local folder is fully populated directly from the file.")

except Exception as e:
    print(f"\nAn error occurred during ingestion: {e}")