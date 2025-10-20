import chromadb
import spacy

# Lade das gleiche Embedding-Model
def get_chunks_from_query(query_text): 
    nlp = spacy.load("de_core_news_lg") 
    
    # Use the same path as in transformData.py
    client = chromadb.PersistentClient(path="./chroma_db")
    
    # Use the collection name from transformData.py
    collection = client.get_collection(name="university_regulations")
    
    query_embedding = nlp(query_text).vector.tolist()

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=5,  # Top 3 most relevant chunks
        where={"category": "pruefungsordnungen"}  # Filter for Prüfungsordnungen
    )

    # Collect document text and metadata
    context_docs = results['documents'][0]
    source_files = results['metadatas'][0]

    return context_docs, source_files

def generate_prompt(context_docs, query_text):
    prompt = f"""
    Antworte auf die folgende Frage basierend nur auf dem untenstehenden Kontext.
    Wenn der Kontext keine ausreichenden Informationen enthält, antworte, dass du die Frage nicht beantworten kannst.
    Stelle sicher, dass du die Antwort direkt aus dem Kontext ableitest und keine zusätzlichen Informationen hinzufügst.
    Verwende die Quellenangaben, um deine Antwort zu belegen. Sollten Informationen fehlen, spezifieziere diese und bitte um weitere Details.
    Gib am Ende deiner Antwort die Quelle(n) an, aus der die Information stammt.

    ---
    Kontext:
    {context_docs[0]}
    {context_docs[1]}
    ...
    ---

    Frage: {query_text}

    Antwort:
    """
    return prompt

def main():
    query_text = "Wie lange dauert das Studium für den Bachelor Wirtschaftsinformatik?"
    
    # Get relevant chunks and metadata
    context_docs, source_files = get_chunks_from_query(query_text)
    
    # Generate the prompt
    prompt = generate_prompt(context_docs, query_text)
    
    # Print the results
    print("\nGenerated Prompt:")
    print(prompt)
    
    print("\nSource Files:")
    for source in source_files:
        print(f"- {source.get('file', 'Unknown file')}")
        print(f"  Category: {source.get('category_display', 'Unknown category')}")
        if 'path_level_1' in source:
            print(f"  Path: {source.get('path_level_1', '')}")

if __name__ == "__main__":
    main()


