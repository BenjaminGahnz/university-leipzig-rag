import chromadb
import spacy
from typing import List, Dict, Any, Tuple
from pathlib import Path
import requests

from config import config
from logging_config import get_logger

logger = get_logger(__name__)

class RAGEngine:
    def __init__(self):
        self.config = config
        self.nlp = self._load_spacy_model()
        self.chroma_client = self._initialize_chroma()
        self.collection = self._get_collection()
        self.ollama_config = self.config.get_ollama_config()

    def _load_spacy_model(self) -> spacy.Language:
        spacy_config = self.config.get_spacy_config()
        model_name = spacy_config['model']
        try:
            nlp = spacy.load(model_name)
            logger.info(f"Loaded spaCy model: {model_name}")
            return nlp
        except OSError:
            logger.error(f"spaCy model {model_name} not found. Run: python -m spacy download {model_name}")
            raise

    def _initialize_chroma(self) -> chromadb.PersistentClient:
        chroma_config = self.config.get_chroma_config()
        persist_dir = Path(chroma_config['persist_directory'])
        if not persist_dir.exists():
            logger.error(f"ChromaDB directory not found: {persist_dir}")
            raise FileNotFoundError(f"ChromaDB directory not found: {persist_dir}")
        client = chromadb.PersistentClient(path=str(persist_dir))
        logger.info(f"Connected to ChromaDB at: {persist_dir}")
        return client

    def _get_collection(self) -> chromadb.Collection:
        chroma_config = self.config.get_chroma_config()
        try:
            collection = self.chroma_client.get_collection(name=chroma_config['collection_name'])
            doc_count = collection.count()
            logger.info(f"Connected to collection '{chroma_config['collection_name']}' with {doc_count} documents")
            if doc_count == 0:
                logger.warning("Collection is empty. Please process documents first.")
            return collection
        except Exception as e:
            logger.error(f"Error accessing collection '{chroma_config['collection_name']}': {e}")
            raise

    def _query_ollama(self, prompt: str) -> str:
        url = f"{self.ollama_config['base_url']}/api/generate"
        payload = {
            "model": self.ollama_config['model'],
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self.ollama_config.get('temperature', 0.1),
                "num_predict": self.ollama_config.get('max_tokens', 2048),
            }
        }
        try:
            response = requests.post(url, json=payload, timeout=60)
            response.raise_for_status()
            result = response.json()
            return result.get('response', 'Keine Antwort erhalten.')
        except requests.exceptions.ConnectionError:
            logger.error("Cannot connect to Ollama. Make sure Ollama is running.")
            return "Fehler: Verbindung zu Ollama fehlgeschlagen. Stellen Sie sicher, dass Ollama läuft."
        except requests.exceptions.Timeout:
            logger.error("Ollama request timed out")
            return "Fehler: Zeitüberschreitung bei der Anfrage an Ollama."
        except Exception as e:
            logger.error(f"Error querying Ollama: {e}")
            return f"Fehler bei der Anfrage: {str(e)}"

    def retrieve_documents(self, query_text: str, n_results: int = 5) -> Tuple[List[str], List[Dict]]:
        try:
            query_doc = self.nlp(query_text)
            if query_doc.vector_norm == 0:
                logger.warning(f"Query has no vector representation: {query_text}")
                return [], []
            query_embedding = query_doc.vector.tolist()
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
            )
            if not results['documents'] or not results['documents'][0]:
                logger.info(f"No documents found for query: {query_text}")
                return [], []
            documents = results['documents'][0]
            metadatas = results['metadatas'][0]
            return documents, metadatas
        except Exception as e:
            logger.error(f"Error retrieving documents: {e}")
            return [], []

    def generate_prompt(self, query_text: str, context_docs: List[str], metadatas: List[Dict]) -> str:
        context_parts = []
        for i, (doc, meta) in enumerate(zip(context_docs, metadatas), 1):
            filename = meta.get('filename', 'Unbekanntes Dokument')
            title = meta.get('title', 'Unbekannter Abschnitt')
            context_parts.append(f"[Quelle {i}: {filename} - {title}]\n{doc}\n")
        context = "\n".join(context_parts)
        prompt = f"""Du bist ein hilfreicher Assistent für Studierende der Universität Leipzig. 
Beantworte die folgende Frage basierend ausschließlich auf dem gegebenen Kontext aus den Universitätsdokumenten.

WICHTIGE REGELN:
1. Beantworte nur Fragen, die sich aus dem Kontext beantworten lassen
2. Wenn der Kontext keine ausreichenden Informationen enthält, sage ehrlich "Ich kann diese Frage nicht basierend auf den verfügbaren Dokumenten beantworten"
3. Gib am Ende deiner Antwort die verwendeten Quellen an
4. Antworte auf Deutsch und sei präzise

KONTEXT:
{context}

FRAGE: {query_text}

ANTWORT:"""
        return prompt

    """
    #! BAD
    def process_query(self, query_text: str, n_results: int = 5) -> Dict[str, Any]:
        logger.info(f"Processing query: {query_text}")
        context_docs, metadatas = self.retrieve_documents(query_text, n_results)
        if not context_docs:
            return {
                'answer': "Entschuldigung, ich konnte keine relevanten Dokumente zu Ihrer Frage finden. Bitte versuchen Sie eine andere Formulierung oder ein anderes Thema.",
                'sources': [],
                'query': query_text,
                'success': False
            }
        prompt = self.generate_prompt(query_text, context_docs, metadatas)
        answer = self._query_ollama(prompt)
        sources = []
        for meta in metadatas:
            source_info = {
                'filename': meta.get('filename', 'Unbekannt'),
                'title': meta.get('title', 'Unbekannt'),
                'path': meta.get('relative_path', 'Unbekannt')
            }
            if source_info not in sources:
                sources.append(source_info)
        return {
            'answer': answer,
            'sources': sources,
            'query': query_text,
            'success': True,
            'context_count': len(context_docs)
        } """

    def check_system_status(self) -> Dict[str, Any]:
        status = {'chroma_db': False, 'spacy_model': False, 'ollama': False, 'document_count': 0}
        try:
            count = self.collection.count()
            status['chroma_db'] = True
            status['document_count'] = count
        except Exception as e:
            logger.error(f"ChromaDB check failed: {e}")
        try:
            test_doc = self.nlp("Test")
            status['spacy_model'] = test_doc.vector_norm > 0
        except Exception as e:
            logger.error(f"spaCy check failed: {e}")
        try:
            response = requests.get(f"{self.ollama_config['base_url']}/api/version", timeout=5)
            status['ollama'] = response.status_code == 200
        except Exception as e:
            logger.error(f"Ollama check failed: {e}")
        return status
    
    def process_query(self, query_text: str, n_results: int = 5) -> Dict[str, Any]:
        logger.info(f"Processing query: {query_text}")
        context_docs, metadatas = self.retrieve_documents(query_text, n_results)
        
        if not context_docs:
            return {
                'answer': "Entschuldigung, ich konnte keine relevanten Dokumente zu Ihrer Frage finden.",
                'sources': [],
                'query': query_text,
                'success': False
            }
        
        prompt = self.generate_prompt(query_text, context_docs, metadatas)
        answer = self._query_ollama(prompt)
        
        sources = []
        for meta in metadatas:
            source_info = {
                'filename': meta.get('filename', 'Unbekannt'),
                'title': meta.get('title', 'Unbekannt'),
                'page_number': meta.get('page_number', 'N/A'),
                'chunk_index': meta.get('chunk_index', 'N/A'),
                'pdf_path': meta.get('pdf_path', '')
            }
            if source_info not in sources:
                sources.append(source_info)
        
        return {
            'answer': answer,
            'sources': sources,
            'query': query_text,
            'success': True,
            'context_count': len(context_docs)
        }


def create_rag_engine() -> RAGEngine:
    return RAGEngine()
