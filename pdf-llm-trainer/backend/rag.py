"""RAG implementation - loads chunks and queries OpenRouter."""
import json
from pathlib import Path
from typing import List, Dict, Optional
import requests

from backend.config import (
    OPENROUTER_API_KEY, OPENROUTER_BASE_URL, OPENROUTER_MODEL,
    CHUNK_DIR, TOP_K
)
from backend.rate_limiter import wait_for_rate_limit


def load_relevant_chunks(query: str, top_k: int = None) -> List[Dict]:
    """
    Load relevant chunks from database (preferred) or file system (fallback).
    
    Args:
        query: User's question
        top_k: Number of chunks to retrieve
    
    Returns:
        List of relevant chunk dictionaries
    """
    if top_k is None:
        top_k = TOP_K
    
    query_lower = query.lower()
    query_terms = query_lower.split()
    
    all_chunks = []
    
    # Try to load from database first
    try:
        from backend.database.repository import ChunkRepository
        print(f"[RAG] Loading chunks from database...")
        # Search chunks by text content
        db_chunks = ChunkRepository.search_by_text(query, limit=top_k * 3)  # Get more for better scoring
        
        for db_chunk in db_chunks:
            chunk_dict = {
                'text': db_chunk.get('text', ''),
                'source': db_chunk.get('source', 'unknown'),
                'page': db_chunk.get('page', 0)
            }
            all_chunks.append(chunk_dict)
        
        print(f"[RAG] Loaded {len(all_chunks)} chunks from database")
    except Exception as e:
        print(f"[WARNING] Failed to load from database: {e}")
        print(f"[RAG] Falling back to file system...")
        
        # Fallback to file system
        chunk_files = list(CHUNK_DIR.glob("*.jsonl"))
        print(f"[RAG] Loading chunks from {len(chunk_files)} files...")
        
        for chunk_file in chunk_files:
            try:
                with open(chunk_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            chunk = json.loads(line)
                            all_chunks.append(chunk)
            except Exception as file_error:
                print(f"[ERROR] Failed to load chunk file {chunk_file.name}: {file_error}")
                continue
        
        print(f"[RAG] Loaded {len(all_chunks)} total chunks from files")
    
    if not all_chunks:
        print("[WARNING] No chunks found!")
        return []
    
    # Simple relevance scoring: count matching terms
    scored_chunks = []
    for chunk in all_chunks:
        text_lower = chunk.get('text', '').lower()
        score = sum(1 for term in query_terms if term in text_lower)
        if score > 0:
            scored_chunks.append((score, chunk))
    
    # Sort by score and return top_k
    scored_chunks.sort(key=lambda x: x[0], reverse=True)
    result = [chunk for _, chunk in scored_chunks[:top_k]]
    
    if scored_chunks:
        top_scores = [s for s, _ in scored_chunks[:top_k]]
        print(f"[RAG] Found {len(result)} relevant chunks (top scores: {top_scores})")
    else:
        # If no matches, return some chunks anyway
        print(f"[RAG] No exact matches found, returning {min(top_k, len(all_chunks))} random chunks")
        result = all_chunks[:top_k]
    
    return result


def query_openrouter(messages: List[Dict], max_retries: int = 5) -> Optional[str]:
    """
    Query OpenRouter API.
    
    Args:
        messages: List of message dictionaries
        max_retries: Maximum retry attempts
    
    Returns:
        Response text or None
    """
    url = f"{OPENROUTER_BASE_URL}/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/asfc",
        "X-Title": "ASFC Chat"
    }
    
    payload = {
        "model": OPENROUTER_MODEL,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 2000
    }
    
    for attempt in range(max_retries):
        try:
            # Wait before making request to avoid rate limits
            if attempt > 0:
                wait_for_rate_limit()
            else:
                wait_for_rate_limit()  # Always wait before first request too
            
            print(f"[OPENROUTER] Attempt {attempt + 1}/{max_retries} - Calling {OPENROUTER_MODEL}")
            # Increase timeout for large responses
            response = requests.post(url, json=payload, headers=headers, timeout=180)
            
            if response.status_code == 200:
                data = response.json()
                if 'choices' in data and len(data['choices']) > 0:
                    print("[OPENROUTER] Success - Response received")
                    return data['choices'][0]['message']['content']
                print("[ERROR] OpenRouter returned 200 but no choices in response")
                return None
            elif response.status_code == 429:
                import time
                # Get retry-after header if available
                retry_after = response.headers.get('retry-after', None)
                if retry_after:
                    try:
                        wait_time = int(retry_after)
                    except:
                        wait_time = None
                else:
                    wait_time = None
                
                # Exponential backoff: 10s, 20s, 40s, 60s, 90s
                if wait_time is None:
                    wait_time = min(10 * (2 ** attempt), 90)
                
                print(f"[ERROR] Rate limited (429) - Waiting {wait_time}s before retry {attempt + 1}/{max_retries}...")
                print(f"[INFO] Free tier models have strict rate limits. Please wait...")
                
                if attempt < max_retries - 1:
                    # Show countdown
                    for remaining in range(wait_time, 0, -5):
                        if remaining > 5:
                            print(f"   Waiting... {remaining}s remaining", end='\r')
                        time.sleep(min(5, remaining))
                    print("   Retrying now...                    ")
                else:
                    print(f"[ERROR] Exhausted all retry attempts after {max_retries} tries")
                    return None
            elif response.status_code == 404:
                print(f"[ERROR] Model not found (404): {OPENROUTER_MODEL}")
                print(f"[ERROR] Response: {response.text[:500]}")
                return None  # Don't retry if model doesn't exist
            elif response.status_code == 401:
                print(f"[ERROR] Authentication failed (401) - Check API key")
                print(f"[ERROR] Response: {response.text[:500]}")
                return None  # Don't retry if auth failed
            else:
                error_text = response.text[:500] if hasattr(response, 'text') else str(response.content)[:500]
                print(f"[ERROR] OpenRouter API error {response.status_code}: {error_text}")
                if attempt < max_retries - 1:
                    import time
                    time.sleep(2 ** attempt)
        
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Request exception: {type(e).__name__}: {str(e)}")
            if attempt < max_retries - 1:
                import time
                time.sleep(2 ** attempt)
    
    print("[ERROR] All retry attempts failed")
    return None


def ask_with_rag(question: str) -> str:
    """
    Ask a question using RAG - loads relevant chunks and queries OpenRouter.
    
    Args:
        question: User's question
    
    Returns:
        Assistant's response
    """
    if not OPENROUTER_API_KEY:
        print("[ERROR] OPENROUTER_API_KEY not set in .env")
        return "Error: OPENROUTER_API_KEY not set in .env"
    
    print(f"[RAG] Processing question: {question[:80]}...")
    
    # Load relevant chunks
    relevant_chunks = load_relevant_chunks(question, top_k=TOP_K)
    
    messages = []
    
    # System message
    system_prompt = """You are ASFC, a helpful assistant that answers questions based on provided documentation context.

When answering:
- Base your answers STRICTLY on the provided context
- Be accurate and cite specific information when possible
- If the context doesn't contain the answer, say so clearly
- Use technical terminology from the context appropriately

IMPORTANT - Format your response clearly:
- Use clear, concise sentences
- Break up long paragraphs into shorter ones
- Use bullet points or numbered lists when appropriate
- Avoid excessive formatting or markdown unless necessary
- Write in a professional, easy-to-read style
- Cite sources when referencing specific documents (e.g., "According to Bulletin-79...")
- Keep paragraphs to 2-3 sentences maximum"""
    
    messages.append({
        "role": "system",
        "content": system_prompt
    })
    
    # Build context from chunks
    if relevant_chunks:
        context_parts = []
        for chunk in relevant_chunks:
            source = chunk.get('source', 'unknown')
            page = chunk.get('page', '?')
            text = chunk.get('text', '')[:1500]
            context_parts.append(f"[From {source}, Page {page}]\n{text}")
        
        context_text = "\n\n---\n\n".join(context_parts)
        
        user_message = f"""Context from documentation:

{context_text}

---

Question: {question}

Please provide a clear, well-formatted answer based ONLY on the context provided above. 
- Use clear paragraphs and bullet points where helpful
- Cite the source document when referencing specific information
- If the context doesn't contain enough information to answer, say so clearly
- Keep your response concise and easy to read"""
    else:
        user_message = f"""Question: {question}

Note: No relevant context found in the documentation. Please answer based on your general knowledge."""
    
    messages.append({
        "role": "user",
        "content": user_message
    })
    
    # Query OpenRouter
    print(f"[RAG] Sending to OpenRouter with {len(relevant_chunks)} context chunks")
    print(f"[RAG] Using model: {OPENROUTER_MODEL}")
    response = query_openrouter(messages)
    
    if response:
        print("[RAG] Successfully generated response")
        # Clean up the response for better readability
        cleaned_response = clean_response(response)
        return cleaned_response
    else:
        print("[ERROR] Failed to get response from OpenRouter")
        # Check backend logs for specific error
        error_msg = """I'm having trouble processing your question right now.

This is likely due to rate limiting on the free tier model. 

**What you can do:**
1. Wait 30-60 seconds and try again
2. The free tier has strict rate limits - multiple requests in quick succession may be blocked
3. Check the backend server console for detailed error messages

**If this persists:**
- Consider upgrading your OpenRouter account for higher rate limits
- Or try again after waiting a few minutes

Sorry for the inconvenience!"""
        return error_msg


def clean_response(text: str) -> str:
    """
    Clean and format the response for better readability.
    
    Args:
        text: Raw response text
    
    Returns:
        Cleaned and formatted text
    """
    if not text:
        return text
    
    import re
    
    # Remove excessive whitespace and newlines
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Remove leading/trailing whitespace from each line
    lines = [line.strip() for line in text.split('\n')]
    
    # Remove empty lines at start and end
    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()
    
    # Join lines back
    cleaned = '\n'.join(lines)
    
    # Fix spacing around punctuation
    cleaned = re.sub(r'\s+([,.!?;:])', r'\1', cleaned)
    cleaned = re.sub(r'([,.!?;:])\s*([A-Z])', r'\1 \2', cleaned)
    
    # Ensure proper spacing after periods
    cleaned = re.sub(r'\.([A-Z])', r'. \1', cleaned)
    
    return cleaned.strip()

