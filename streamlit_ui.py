import streamlit as st
import time
import base64
from pathlib import Path
from typing import Dict, Any, List
from config import config
from rag_engine import create_rag_engine
from logging_config import setup_logging, get_logger

setup_logging(
    log_level=config.get('logging.level', 'INFO'),
    log_file=config.get('logging.file')
)
logger = get_logger(__name__)

st.set_page_config(
    page_title=config.get('app.name', 'RAG Chat'),
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

@st.cache_resource
def init_rag_engine():
    try:
        return create_rag_engine()
    except Exception as e:
        logger.error(f"Failed to initialize RAG engine: {e}")
        return None


def create_pdf_link(pdf_path: str, page_number: int) -> str:
    """Create a file:// link to open PDF at specific page"""
    if pdf_path and Path(pdf_path).exists():
        # Note: page parameter depends on PDF viewer support
        return f"file:///{pdf_path}#page={page_number}"
    return "#"


def display_chat_message(role: str, content: str, sources: List[Dict] = None):
    if role == "user":
        st.markdown(f'''
            <div style="background-color: #000000; padding: 15px; border-radius: 10px; margin: 10px 0;">
                <strong>Sie:</strong><br>{content}
            </div>
        ''', unsafe_allow_html=True)
    else:
        st.markdown(f'''
            <div style="background-color: #000000; padding: 15px; border-radius: 10px; margin: 10px 0;">
                <strong>Assistent:</strong><br>{content}
            </div>
        ''', unsafe_allow_html=True)
        
        if sources:
            with st.expander(f"Verwendete Quellen ({len(sources)})"):
                for i, source in enumerate(sources, 1):
                    filename = source.get('filename', 'Unbekannt')
                    title = source.get('title', 'Unbekannt')
                    page = source.get('page_number', 'N/A')
                    #chunk = source.get('chunk_index', 'N/A')
                    pdf_path = source.get('pdf_path', '')
                    
                    pdf_link = create_pdf_link(pdf_path, page if isinstance(page, int) else 1)
                    
                    st.markdown(f'''
                        **Quelle {i}:**  
                        **Dokument:** {filename}  
                        **Abschnitt:** {title}  
                        **Seite:** {page}  
                        [PDF öffnen]({pdf_link})
                    ''')
                    st.markdown("---")


def main():
    st.title("🎓 Universität Leipzig RAG Chatbot")
    st.markdown("Stellen Sie Fragen zu Studiendokumenten und Prüfungsordnungen.")
    
    # Initialize RAG engine
    rag_engine = init_rag_engine()
    
    if rag_engine is None:
        st.error("❌ RAG System konnte nicht initialisiert werden.")
        return
    
    # Sidebar with system status
    with st.sidebar:
        st.header("⚙️ System Status")
        status = rag_engine.check_system_status()
        
        st.metric("📚 Dokumente", status.get('document_count', 0))
        st.write("✅ ChromaDB" if status.get('chroma_db') else "❌ ChromaDB")
        st.write("✅ spaCy" if status.get('spacy_model') else "❌ spaCy")
        st.write("✅ Ollama" if status.get('ollama') else "❌ Ollama")
    
    # Chat interface
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # Display chat history
    for message in st.session_state.messages:
        display_chat_message(
            message["role"],
            message["content"],
            message.get("sources")
        )
    
    # User input
    if prompt := st.chat_input("Ihre Frage..."):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        display_chat_message("user", prompt)
        
        # Get response
        with st.spinner("Suche nach Antwort..."):
            result = rag_engine.process_query(prompt)
        
        # Add assistant response
        st.session_state.messages.append({
            "role": "assistant",
            "content": result['answer'],
            "sources": result.get('sources', [])
        })
        display_chat_message("assistant", result['answer'], result.get('sources'))
        
        st.rerun()


if __name__ == "__main__":
    main()
