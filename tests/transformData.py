import os
import spacy
import chromadb
from chromadb.config import Settings
from pypdf import PdfReader
import re
from typing import List, Tuple, Dict

def clean_text(text: str) -> str:
    """Cleanes text"""
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def segment_study_regulations(text: str, nlp) -> List[Dict]:
    """
    Chunks an PDF 
    """
    # Pattern for sections like "§ 1", "Artikel 2", "Kapitel 3"
    pattern = re.compile(r'(?m)^(\s*(§|Kapitel|Artikel)\s*\d+.*)', re.IGNORECASE)
    
    segments = []
    
    # Split the text by the pattern to get logical chunks
    split_text = re.split(pattern, text)
    
    # The first element is usually preamble, subsequent elements are title/content pairs
    preamble = split_text[0].strip()
    if preamble:
        doc = nlp(preamble)
        if doc.vector_norm:
            segments.append({
                'text': preamble,
                'metadata': {'title': 'Präambel'},
                'vector': doc.vector.tolist()
            })
    
    # Process the rest of the splits
    for i in range(1, len(split_text), 4): # 
        title = split_text[i].strip()
        content = split_text[i+3].strip()

        if not content:
            continue
            
        doc = nlp(content)
        # Split content into smaller, context-rich chunks 
        sentences = [sent.text.strip() for sent in doc.sents]
        
        current_chunk = ""
        for sentence in sentences:
            if len(current_chunk.split()) + len(sentence.split()) <= 100: # chunk size limit
                current_chunk += " " + sentence
            else:
                if current_chunk:
                    chunk_doc = nlp(current_chunk)
                    if chunk_doc.vector_norm:
                        segments.append({
                            'text': current_chunk.strip(),
                            'metadata': {'title': title},
                            'vector': chunk_doc.vector.tolist()
                        })
                current_chunk = sentence
        
        if current_chunk:
            chunk_doc = nlp(current_chunk)
            if chunk_doc.vector_norm:
                segments.append({
                    'text': current_chunk.strip(),
                    'metadata': {'title': title},
                    'vector': chunk_doc.vector.tolist()
                })
    
    return segments

def sanitize_collection_name(name: str) -> str:
    """Convert a string to a valid ChromaDB collection name"""
    # Replace umlauts
    name = name.replace('ä', 'ae').replace('ö', 'oe').replace('ü', 'ue')
    name = name.replace('Ä', 'Ae').replace('Ö', 'Oe').replace('Ü', 'Ue')
    name = name.replace('ß', 'ss')
    
    # Replace spaces and other special characters
    name = re.sub(r'[^a-zA-Z0-9._-]', '_', name)
    
    # Ensure it starts and ends with alphanumeric
    name = re.sub(r'^[._-]+', '', name)
    name = re.sub(r'[._-]+$', '', name)
    
    return name

def process_pdf_directory(base_dir: str):
    """Process all PDFs in directory structure with persistent storage"""
    try:
        nlp = spacy.load("de_core_news_lg")
    except OSError:
        print("Installing German language model...")
        os.system("python -m spacy download de_core_news_lg")
        nlp = spacy.load("de_core_news_lg")

    # Create persistent client with specified path
    persist_directory = os.path.join(os.path.dirname(__file__), "chroma_db")
    client = chromadb.PersistentClient(path=persist_directory)
    
    # Create or get collection with sanitized name
    collection_name = sanitize_collection_name("Prüfungsordnungen")
    collection = client.get_or_create_collection(
        name=collection_name,
        metadata={
            "description": "Processed study regulations",
            "original_name": "Prüfungsordnungen"
        }
    )
    
    doc_id = collection.count()  # Start from existing count
    
    for root, _, files in os.walk(base_dir):
        for file in files:
            if not file.lower().endswith('.pdf'):
                continue
                
            pdf_path = os.path.join(root, file)
            relative_path = os.path.relpath(root, base_dir)
            path_components = relative_path.split(os.sep)
            
            print(f"Processing: {pdf_path}")
            
            try:
                reader = PdfReader(pdf_path)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() + "\n"
                
                clean_text_content = clean_text(text)
                segments = segment_study_regulations(clean_text_content, nlp)
                
                for segment in segments:
                    # Enrich metadata with path information
                    metadata = segment['metadata']
                    metadata['file'] = file
                    metadata['full_path'] = pdf_path
                    
                    # Add path components as separate metadata fields
                    for i, component in enumerate(path_components):
                        if component:  # Skip empty components
                            metadata[f'path_level_{i+1}'] = component
                    
                    collection.add(
                        documents=[segment['text']],
                        embeddings=[segment['vector']],
                        metadatas=[metadata],
                        ids=[f"doc_{doc_id}"]
                    )
                    doc_id += 1
                    
            except Exception as e:
                print(f"Error processing {pdf_path}: {e}")
                continue               

    # Ensure changes are persisted
    client.persist()
    print(f"\nData persisted to: {persist_directory}")

def process_multiple_directories():
    """Process both regulation types with their specific categories"""
    
    # Define directory configurations
    directories = [
        {
            'path': "Prüfungs-, Studien- und Eignungsfeststellungsordnungen",
            'category': "pruefungsordnungen",
            'display_name': "Prüfungsordnungen"
        },
        {
            'path': "Ordnungen der Fakultäten und Einrichtungen",
            'category': "fakultaetsordnungen",
            'display_name': "Fakultätsordnungen"
        }
    ]
    
    
    nlp = spacy.load("de_core_news_lg")
    

    # Create persistent client
    persist_directory = os.path.join(os.path.dirname(__file__), "chroma_db")
    client = chromadb.PersistentClient(path=persist_directory)
    
    # Create or get collection for all regulations
    collection = client.get_or_create_collection(
        name="university_regulations",
        metadata={"description": "Combined university regulations"}
    )
    
    doc_id = collection.count()
    
    # Process each directory
    for dir_config in directories:
        base_dir = dir_config['path']
        if not os.path.exists(base_dir):
            print(f"\nSkipping {dir_config['display_name']}: Directory not found")
            continue
            
        print(f"\nProcessing {dir_config['display_name']} from: {base_dir}")
        
        for root, _, files in os.walk(base_dir):
            for file in files:
                if not file.lower().endswith('.pdf'):
                    continue
                    
                pdf_path = os.path.join(root, file)
                relative_path = os.path.relpath(root, base_dir)
                path_components = relative_path.split(os.sep)
                
                print(f"Processing: {pdf_path}")
                
                try:
                    reader = PdfReader(pdf_path)
                    text = ""
                    for page in reader.pages:
                        text += page.extract_text() + "\n"
                    
                    clean_text_content = clean_text(text)
                    segments = segment_study_regulations(clean_text_content, nlp)
                    
                    for segment in segments:
                        # Enrich metadata
                        metadata = segment['metadata']
                        metadata.update({
                            'file': file,
                            'full_path': pdf_path,
                            'category': dir_config['category'],
                            'category_display': dir_config['display_name']
                        })
                        
                        # Add path components as metadata
                        for i, component in enumerate(path_components):
                            if component:
                                metadata[f'path_level_{i+1}'] = component
                        
                        collection.add(
                            documents=[segment['text']],
                            embeddings=[segment['vector']],
                            metadatas=[metadata],
                            ids=[f"doc_{doc_id}"]
                        )
                        doc_id += 1
                        
                except Exception as e:
                    print(f"Error processing {pdf_path}: {e}")
                    continue

    print(f"\nAll data persisted to: {persist_directory}")

if __name__ == "__main__":
    process_multiple_directories()