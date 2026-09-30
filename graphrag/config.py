import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class Settings:
    uri: str = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
    user: str = os.getenv('NEO4J_USER', 'neo4j')
    password: str = os.getenv('NEO4J_PASSWORD', '')
    database: str = os.getenv('NEO4J_DATABASE', 'neo4j')
    ollama: str = os.getenv('OLLAMA_URL', 'http://localhost:11434')
    chat_model: str = os.getenv('CHAT_MODEL', 'mistral:latest')
    embed_model: str = os.getenv('EMBED_MODEL', 'nomic-embed-text:latest')
    data: Path = Path(os.getenv('DATA_DIR', 'data'))
