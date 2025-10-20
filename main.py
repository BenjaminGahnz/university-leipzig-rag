import argparse
import sys
from pathlib import Path
from config import config
from logging_config import setup_logging, get_logger
from document_processor import create_document_processor
from rag_engine import create_rag_engine

def setup_directories():
    directories = [
        Path("data"),
        Path("data/chroma_db"),
        Path("data/pdfs"),
        Path("logs"),
        Path(config.get('chroma.persist_directory')),
    ]
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
        print(f"✓ Created directory: {directory}")

def process_documents(pdf_directory: str = None):
    logger = get_logger(__name__)
    logger.info("Starting document processing...")
    pdf_path = Path(pdf_directory) if pdf_directory else Path("data/pdfs")
    if not pdf_path.exists():
        logger.error(f"PDF directory not found: {pdf_path}")
        print(f"❌ PDF directory not found: {pdf_path}")
        print("Please create the directory and add PDF files, or specify a different path.")
        return False
    pdf_files = list(pdf_path.rglob("*.pdf"))
    if not pdf_files:
        logger.warning(f"No PDF files found in: {pdf_path}")
        print(f"⚠️  No PDF files found in: {pdf_path}")
        return False
    print(f"📄 Found {len(pdf_files)} PDF files")
    try:
        processor = create_document_processor()
        processed_count = processor.process_directory(pdf_path)
        if processed_count > 0:
            print(f"✅ Successfully processed {processed_count} document segments")
            logger.info(f"Document processing completed: {processed_count} segments")
            return True
        else:
            print("❌ No documents were processed")
            return False
    except Exception as e:
        logger.error(f"Error during document processing: {e}")
        print(f"❌ Error during document processing: {e}")
        return False

def test_system():
    logger = get_logger(__name__)
    logger.info("Starting system test...")
    print("🔧 Testing RAG System Components...")
    print("-" * 40)
    try:
        print("1. Initializing RAG Engine...")
        rag_engine = create_rag_engine()
        print("   ✅ RAG Engine initialized successfully")
        print("\n2. Checking system components...")
        status = rag_engine.check_system_status()
        if status['chroma_db']:
            print(f"   ✅ ChromaDB: Connected ({status['document_count']} documents)")
        else:
            print("   ❌ ChromaDB: Connection failed")
        if status['ollama']:
            print("   ✅ Ollama: Connected")
        else:
            print("   ❌ Ollama: Connection failed")
            print("      Make sure Ollama is running: ollama serve")
        if status['spacy_model']:
            print("   ✅ spaCy Model: Loaded")
        else:
            print("   ❌ spaCy Model: Failed to load")
            print("      Run: python -m spacy download de_core_news_lg")
        if all(status.values()):
            print("\n3. Testing sample query...")
            test_query = "Wie lange dauert das Masterstudium?"
            result = rag_engine.process_query(test_query, n_results=3)
            if result['success']:
                print("   ✅ Query processing successful")
                print(f"   📄 Found {result['context_count']} relevant documents")
                print(f"   📝 Answer preview: {result['answer'][:100]}...")
            else:
                print("   ⚠️  Query processing failed (no relevant documents found)")
        print("\n" + "=" * 40)
        if all(status.values()):
            print("🎉 All systems operational! You can start the chat interface.")
            return True
        else:
            print("⚠️  Some components need attention. Please fix the issues above.")
            return False
    except Exception as e:
        logger.error(f"System test failed: {e}")
        print(f"❌ System test failed: {e}")
        return False

def start_ui():
    import subprocess
    import os
    print("🚀 Starting Streamlit Chat Interface...")
    print("The interface will open in your browser at: http://localhost:8501")
    print("Press Ctrl+C to stop the server")
    try:
        env = os.environ.copy()
        subprocess.run([
            "streamlit", "run", "streamlit_ui.py",
            "--server.port", "8501",
            "--server.headless", "false"
        ], env=env)
    except KeyboardInterrupt:
        print("\n👋 Chat interface stopped")
    except FileNotFoundError:
        print("❌ Streamlit not found. Please install with: pip install streamlit")
    except Exception as e:
        print(f"❌ Error starting UI: {e}")

def main():
    parser = argparse.ArgumentParser(description="University Leipzig RAG System")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    setup_parser = subparsers.add_parser('setup', help='Setup directories and configuration')
    process_parser = subparsers.add_parser('process', help='Process PDF documents')
    process_parser.add_argument('--pdf-dir', type=str, help='Path to PDF directory')
    test_parser = subparsers.add_parser('test', help='Test system components')
    start_parser = subparsers.add_parser('start', help='Start chat interface')
    args = parser.parse_args()
    setup_logging(log_level=config.get('logging.level', 'INFO'), log_file=config.get('logging.file'))
    logger = get_logger(__name__)
    logger.info(f"RAG System started with command: {args.command}")
    if args.command == 'setup':
        print("🏗️  Setting up RAG system...")
        setup_directories()
        print("\n✅ Setup complete!\n")
        print("Next steps:")
        print("1. Add PDF files to data/pdfs/ directory")
        print("2. Run: python main.py process")
        print("3. Run: python main.py test")
        print("4. Run: python main.py start")
    elif args.command == 'process':
        success = process_documents(args.pdf_dir)
        sys.exit(0 if success else 1)
    elif args.command == 'test':
        success = test_system()
        sys.exit(0 if success else 1)
    elif args.command == 'start':
        start_ui()
    else:
        parser.print_help()
        print("\n🎓 University Leipzig RAG System")
        print("Available commands:")
        print("  setup   - Setup directories and configuration")
        print("  process - Process PDF documents")
        print("  test    - Test system components")
        print("  start   - Start chat interface")

if __name__ == "__main__":
    main()
