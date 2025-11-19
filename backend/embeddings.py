"""Embedding service for generating vector embeddings."""
import os
import requests
from typing import List, Optional
from backend.config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL


# Default embedding model (OpenAI compatible)
# Using OpenAI's text-embedding-3-small (1536 dimensions) via OpenRouter
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "openai/text-embedding-3-small")
EMBEDDING_DIMENSIONS = 1536


def generate_embedding(text: str) -> Optional[List[float]]:
    """
    Generate embedding for a single text.
    
    Args:
        text: Text to embed
    
    Returns:
        Embedding vector (list of floats) or None if failed
    """
    if not text or not text.strip():
        return None
    
    if not OPENROUTER_API_KEY:
        print("[WARNING] OPENROUTER_API_KEY not set - cannot generate embeddings")
        return None
    
    url = f"{OPENROUTER_BASE_URL}/embeddings"
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/asfc",
        "X-Title": "ASFC Embeddings"
    }
    
    payload = {
        "model": EMBEDDING_MODEL,
        "input": text
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            if 'data' in data and len(data['data']) > 0:
                return data['data'][0]['embedding']
            else:
                print(f"[ERROR] Invalid embedding response structure: {data}")
                return None
        else:
            print(f"[ERROR] Embedding API error {response.status_code}: {response.text[:200]}")
            return None
    
    except Exception as e:
        print(f"[ERROR] Failed to generate embedding: {e}")
        return None


def generate_embeddings_batch(texts: List[str], batch_size: int = 10) -> List[Optional[List[float]]]:
    """
    Generate embeddings for multiple texts in batches.
    
    Args:
        texts: List of texts to embed
        batch_size: Number of texts to process in each batch
    
    Returns:
        List of embedding vectors (same order as input texts)
    """
    if not OPENROUTER_API_KEY:
        print("[WARNING] OPENROUTER_API_KEY not set - cannot generate embeddings")
        return [None] * len(texts)
    
    url = f"{OPENROUTER_BASE_URL}/embeddings"
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/asfc",
        "X-Title": "ASFC Embeddings"
    }
    
    results = []
    
    # Process in batches
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        
        # Filter out empty texts
        valid_texts = []
        valid_indices = []
        for idx, text in enumerate(batch):
            if text and text.strip():
                valid_texts.append(text)
                valid_indices.append(i + idx)
        
        if not valid_texts:
            # Add None for empty texts in this batch
            results.extend([None] * len(batch))
            continue
        
        payload = {
            "model": EMBEDDING_MODEL,
            "input": valid_texts
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=60)
            
            if response.status_code == 200:
                data = response.json()
                if 'data' in data:
                    # Map embeddings back to original positions
                    batch_results = [None] * len(batch)
                    for j, embedding_data in enumerate(data['data']):
                        if j < len(valid_indices):
                            orig_idx = valid_indices[j] - i
                            batch_results[orig_idx] = embedding_data['embedding']
                    results.extend(batch_results)
                else:
                    print(f"[ERROR] Invalid batch embedding response structure")
                    results.extend([None] * len(batch))
            else:
                print(f"[ERROR] Batch embedding API error {response.status_code}: {response.text[:200]}")
                results.extend([None] * len(batch))
        
        except Exception as e:
            print(f"[ERROR] Failed to generate batch embeddings: {e}")
            results.extend([None] * len(batch))
    
    return results


