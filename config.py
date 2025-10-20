
import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)

class Config:
    """Configuration management class"""
    
    def __init__(self, config_path: str = "config.yaml"):
        load_dotenv()  # Load .env file
        self.config_path = Path(config_path)
        self._config = self._load_config()
        self._validate_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        try:
            if not self.config_path.exists():
                logger.warning(f"Config file {self.config_path} not found, using defaults")
                return self._get_default_config()
                
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                
            # Override with environment variables
            self._override_with_env(config)
            return config
            
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return self._get_default_config()
    
    def _override_with_env(self, config: Dict[str, Any]) -> None:
        if os.getenv('OLLAMA_HOST'):
            config['ollama']['base_url'] = f"http://{os.getenv('OLLAMA_HOST')}:{os.getenv('OLLAMA_PORT', '11434')}"
            
        if os.getenv('LOG_LEVEL'):
            config['logging']['level'] = os.getenv('LOG_LEVEL')
            
        if os.getenv('CHROMA_PERSIST_DIRECTORY'):
            config['chroma']['persist_directory'] = os.getenv('CHROMA_PERSIST_DIRECTORY')
    
    def _get_default_config(self) -> Dict[str, Any]:
        return {
            'app': {
                'name': 'University Leipzig RAG Chat',
                'version': '1.0.0',
                'debug': False
            },
            'chroma': {
                'persist_directory': './data/chroma_db',
                'collection_name': 'university_regulations'
            },
            'ollama': {
                'base_url': 'http://localhost:11434',
                'model': 'llama3.1:8b',
                'temperature': 0.1,
                'max_tokens': 2048
            },
            'documents': {
                'processing': {
                    'chunk_size': 500,
                    'chunk_overlap': 50,
                    'max_file_size_mb': 50
                }
            },
            'spacy': {
                'model': 'de_core_news_lg',
                'auto_download': True
            },
            'logging': {
                'level': 'INFO',
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                'file': './logs/rag_system.log'
            }
        }
    
    def _validate_config(self) -> None:
        required_keys = ['app', 'chroma', 'ollama', 'documents', 'spacy', 'logging']
        for key in required_keys:
            if key not in self._config:
                raise ValueError(f"Missing required configuration key: {key}")
    
    def get(self, key_path: str, default: Any = None) -> Any:
        keys = key_path.split('.')
        value = self._config
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def get_ollama_config(self) -> Dict[str, Any]:
        return self._config['ollama']
    
    def get_chroma_config(self) -> Dict[str, Any]:
        return self._config['chroma']
    
    def get_spacy_config(self) -> Dict[str, Any]:
        return self._config['spacy']
    
    def get_document_config(self) -> Dict[str, Any]:
        return self._config['documents']

# Global config instance
config = Config()