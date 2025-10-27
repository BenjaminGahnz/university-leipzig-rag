#  University Leipzig RAG Chat System

Ein lokales RAG (Retrieval-Augmented Generation) System für die Studiendokumente der Universität Leipzig. Das System ermöglicht es, Fragen zu Studien- und Prüfungsordnungen zu stellen und erhält Antworten basierend auf den offiziellen Dokumenten.

## Features

- **Lokale Ausführung**: Vollständig lokal mit Ollama LLMs
- **Deutsche Sprachunterstützung**:
- **Intelligente Dokumentenverarbeitung**: Automatische PDF-Verarbeitung und Chunking
- **Web-basierte Chat-Oberfläche**: Moderne Streamlit-UI
- **Quellenangaben**: Transparente Nachverfolgung der Antwortquellen
- **Automatisches Web Scraping**: Download von Universitätsdokumenten der Uni Leipzig
- **Modulare Architektur**: Erweiterbar und wartbar

##  Installation

### Schritt 1: Repository klonen
```bash
git clone <repository-url>
cd university-leipzig-rag
```

### Schritt 2: Virtual Environment erstellen
```bash
python -m venv venv

source venv/bin/activate
```

### Schritt 3: Dependencies installieren
```bash
pip install -r requirements.txt
```

### Schritt 4: spaCy Modell herunterladen
```bash
python -m spacy download de_core_news_lg
```

### Schritt 5: Ollama installieren und einrichten

#### Ollama Installation:
```bash
brew install ollama

```

#### Ollama Modell herunterladen:
```bash
# Ollama starten (in separatem Terminal)
ollama serve

# Modell herunterladen (in neuem Terminal)
ollama pull llama3.1:8b
# oder für weniger RAM:
ollama pull llama3.1:3b
```

### Schritt 6: System einrichten
```bash
python main.py setup
```

## Verwendung

### 1. Dokumente hinzufügen

#### Option A: Manuelle PDF-Dateien
1. PDF-Dateien in `data/pdfs/` ablegen
2. Hierarchische Ordnerstruktur wird unterstützt

#### Option B: Automatisches Web Scraping
```bash
# Mit dem integrierten Scraper
python web_scraper.py --output-dir data/pdfs

# Oder für spezifische URLs
python web_scraper.py --urls https://amb.uni-leipzig.de/startseite-bekanntmachungen.html?kat_id=2001 --output-dir data/pdfs
```

### 2. Dokumente verarbeiten
```bash
python main.py process
```
Dies extrahiert Text aus den PDFs und erstellt Vektorembeddings in ChromaDB.

### 3. System testen
```bash
python main.py test
```
Überprüft alle Komponenten und führt eine Testabfrage durch.

### 4. Chat-Interface starten
```bash
python main.py start
```
Öffnet die Streamlit-Oberfläche unter `http://localhost:8501`

## Konfiguration

Die Konfiguration erfolgt über `config.yaml`:

```yaml
# Ollama Einstellungen
ollama:
  base_url: "http://localhost:11434"
  model: "llama2:7b"  # Anpassen je nach verfügbarem Modell
  temperature: 0.1

# ChromaDB Einstellungen  
chroma:
  persist_directory: "./data/chroma_db"
  collection_name: "university_regulations"

# Dokumentverarbeitung
documents:
  processing:
    chunk_size: 500
    chunk_overlap: 50
```


## Verwendungsbeispiele

### Beispielfragen an das System:
- "Wie lange dauert das Masterstudium Ethnologie?"
- "Welche Prüfungsvorleistungen sind im Bachelorstudium Wirtschaftsinformatik erforderlich?"


### CLI-Kommandos:
```bash
# System-Setup
python main.py setup

# PDFs verarbeiten (mit spezifischem Verzeichnis)
python main.py process --pdf-dir /path/to/pdfs

# System-Status prüfen
python main.py test

# UI starten
python main.py start

# Web Scraping (eigenständig)
python web_scraper.py --max-depth 4 --output-dir data/new_pdfs
```


### Tests ausführen
```bash
# System-Integrationstests
python main.py test

# Einzelkomponenten testen
python -c "from rag_engine import create_rag_engine; engine = create_rag_engine(); print(engine.check_system_status())"
```


### Performance-Optimierung
- **Kleinere Modelle**: Verwenden Sie `llama3.1:3b` für weniger RAM-Verbrauch
- **Chunk-Größe anpassen**: Größere Chunks in `config.yaml` für weniger, aber längere Kontexte
- **GPU-Beschleunigung**: Ollama unterstützt GPU-Beschleunigung automatisch wenn verfügbar


**Entwickelt für Studierende der Universität Leipzig** 
