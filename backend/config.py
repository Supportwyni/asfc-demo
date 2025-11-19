"""Configuration for backend."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Get project root (parent of backend folder)
PROJECT_ROOT = Path(__file__).parent.parent

# Load environment variables from project root
env_path = PROJECT_ROOT / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=str(env_path), override=True)
else:
    # Fallback: try current directory
    load_dotenv(override=True)

# OpenRouter configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "qwen/qwen-2.5-72b-instruct:free")

# Paths
CHUNK_DIR = PROJECT_ROOT / "data" / "chunks"
TOP_K = int(os.getenv("TOP_K", "3"))

# Embedding configuration
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "openai/text-embedding-3-small")
EMBEDDING_DIMENSIONS = 1536
USE_SEMANTIC_SEARCH = os.getenv("USE_SEMANTIC_SEARCH", "true").lower() == "true"

