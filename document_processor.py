import re
import spacy
from pathlib import Path
from typing import List, Dict, Any
from pypdf import PdfReader
import chromadb
from tqdm import tqdm
from config import config
from logging_config import get_logger
import uuid

logger = get_logger(__name__)


class DocumentProcessor:
    def __init__(self):
        self.config = config
        self.chroma_client = chromadb.PersistentClient(
            path=self.config.get_chroma_config()['persist_directory']
        )
        self.collection = self.chroma_client.get_or_create_collection(
            name=self.config.get_chroma_config()['collection_name']
        )
        self.nlp = spacy.load(self.config.get_spacy_config()['model'])
        logger.info(f"Using spaCy model: {self.config.get_spacy_config()['model']}")

    def clean_text(self, text: str) -> str:
        """Remove unnecessary whitespace and broken line breaks"""
        text = re.sub(r'\s+', ' ', text)
        text = text.replace('\n', ' ')
        return text.strip()

    def extract_text_from_pdf_with_pages(self, pdf_path: Path) -> List[Dict[str, Any]]:
        """Extract text from PDF with page number tracking"""
        try:
            reader = PdfReader(pdf_path)
            pages_data = []
            for page_num, page in enumerate(reader.pages, start=1):
                text = page.extract_text()
                if text:
                    pages_data.append({
                        'text': text,
                        'page_number': page_num
                    })
            return pages_data
        except Exception as e:
            logger.error(f"Failed to read {pdf_path}: {e}")
            return []

    def segment_document(self, pages_data: List[Dict], filename: str, pdf_path: Path) -> List[Dict[str, Any]]:
        """Segment document into logical parts with page tracking"""
        doc_config = self.config.get_document_config()
        chunk_size = doc_config['processing']['chunk_size']
        overlap = doc_config['processing']['chunk_overlap']

        section_pattern = re.compile(
            r'(?m)^(?:\s*(Modul|Modulname|Inhalt|Ziele|Leistungspunkte|Dauer|Voraussetzungen|Studienleistungen|Empfohlene Literatur|Prüfungen|Lehrformen)[^:]*:)',
            re.IGNORECASE
        )

        all_segments = []
        
        for page_data in pages_data:
            text = page_data['text']
            page_num = page_data['page_number']
            cleaned = self.clean_text(text)
            
            pieces = re.split(section_pattern, cleaned)
            
            if len(pieces) < 2:
                # No section headers found, treat as single segment
                if len(cleaned.split()) > 10:
                    all_segments.append({
                        "title": "Gesamtdokument",
                        "text": cleaned,
                        "page_number": page_num
                    })
            else:
                current_title = ""
                for part in pieces:
                    if re.match(section_pattern, part):
                        current_title = part.strip()
                    else:
                        cleaned_part = self.clean_text(part)
                        if len(cleaned_part.split()) > 10:
                            all_segments.append({
                                "title": current_title or "Abschnitt",
                                "text": cleaned_part,
                                "page_number": page_num
                            })

        # Split long sections into smaller chunks with indexing
        final_segments = []
        chunk_counter = 0
        
        for seg in all_segments:
            words = seg["text"].split()
            for i in range(0, len(words), chunk_size - overlap):
                chunk = " ".join(words[i:i + chunk_size])
                chunk_counter += 1
                final_segments.append({
                    "text": chunk,
                    "metadata": {
                        "title": seg["title"],
                        "filename": filename,
                        "page_number": seg["page_number"],
                        "chunk_index": chunk_counter,
                        "pdf_path": str(pdf_path.absolute())
                    }
                })
        return final_segments

    def vectorize_and_store(self, segments: List[Dict[str, Any]]):
        """Embed document text using spaCy and store in ChromaDB"""
        for segment in tqdm(segments, desc="Vectorizing segments"):
            try:
                doc = self.nlp(segment['text'])
                if doc.vector_norm > 0:
                    unique_id = str(uuid.uuid4())
                    self.collection.add(
                        ids=[unique_id],
                        documents=[segment['text']],
                        embeddings=[doc.vector.tolist()],
                        metadatas=[segment['metadata']]
                    )
            except Exception as e:
                logger.error(f"Vectorizing segment failed: {e}")

    def process_pdf(self, pdf_path: Path):
        """Full processing pipeline for one PDF"""
        logger.info(f"Processing: {pdf_path}")
        pages_data = self.extract_text_from_pdf_with_pages(pdf_path)
        if not pages_data:
            logger.warning(f"No text extracted from {pdf_path}")
            return 0
        
        segments = self.segment_document(pages_data, pdf_path.name, pdf_path)
        self.vectorize_and_store(segments)
        logger.info(f"Processed {len(segments)} segments from {pdf_path}")
        return len(segments)

    def process_directory(self, directory: Path):
        """Process all PDFs within a directory"""
        pdf_files = list(directory.rglob("*.pdf"))
        total_segments = 0
        for pdf_path in tqdm(pdf_files, desc="Processing PDFs"):
            total_segments += self.process_pdf(pdf_path)
        logger.info(f"Total processed segments: {total_segments}")
        return total_segments


def create_document_processor() -> DocumentProcessor:
    return DocumentProcessor()


if __name__ == "__main__":
    processor = create_document_processor()
    processor.process_directory(Path("data/pdfs"))


