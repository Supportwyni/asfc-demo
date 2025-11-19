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


def detect_bulletin_query(query: str) -> Optional[str]:
    """
    Detect if query is asking about a specific bulletin.
    Returns the bulletin identifier (e.g., "Bulletin-113", "bulletin 113", "113") or None.
    """
    import re
    query_lower = query.lower()
    
    # Patterns to detect bulletin queries:
    # - "tell me about bulletin 113"
    # - "what is bulletin 113"
    # - "bulletin 113"
    # - "about bulletin-113"
    # - "analyze bulletin 113"
    
    # Match patterns like "bulletin 113", "bulletin-113", "bulletin113"
    patterns = [
        r'bulletin[\s\-]?(\d+)',  # "bulletin 113", "bulletin-113", "bulletin113"
        r'bulletin[\s\-]?(\d+\.\d+)',  # "bulletin 113.5"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, query_lower)
        if match:
            bulletin_num = match.group(1)
            # Return in format that matches source filenames (e.g., "Bulletin-113")
            return f"Bulletin-{bulletin_num}"
    
    # Also check if query mentions "bulletin" and contains a number
    if 'bulletin' in query_lower:
        # Extract any number in the query
        numbers = re.findall(r'\d+', query)
        if numbers:
            return f"Bulletin-{numbers[0]}"
    
    return None


def load_relevant_chunks(query: str, top_k: int = None) -> List[Dict]:
    """
    Load relevant chunks from database (preferred) or file system (fallback).
    If query is about a specific bulletin, loads ALL chunks from that bulletin.
    
    Args:
        query: User's question
        top_k: Number of chunks to retrieve (ignored if bulletin query detected)
    
    Returns:
        List of relevant chunk dictionaries
    """
    if top_k is None:
        top_k = TOP_K
    
    query_lower = query.lower()
    query_terms = query_lower.split()
    
    # Check if this is a bulletin query
    bulletin_source = detect_bulletin_query(query)
    
    all_chunks = []
    
    # Try to load from database first
    try:
        from backend.database.repository import ChunkRepository
        print(f"[RAG] Loading chunks from database...")
        
        if bulletin_source:
            # Load ALL chunks from the specific bulletin
            print(f"[RAG] Detected bulletin query - Loading ALL chunks from {bulletin_source}")
            db_chunks = ChunkRepository.get_by_source(bulletin_source)
            print(f"[RAG] Found {len(db_chunks)} chunks from {bulletin_source}")
            
            # Sort by page number for better organization
            db_chunks.sort(key=lambda x: x.get('page', 0))
        else:
            # Regular text search
            db_chunks = ChunkRepository.search_by_text(query, limit=top_k * 2)
        
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
        if bulletin_source:
            # Try to find chunks from the bulletin file
            bulletin_filename = f"{bulletin_source.lower()}.jsonl"
            chunk_file = CHUNK_DIR / bulletin_filename
            if chunk_file.exists():
                print(f"[RAG] Loading chunks from {bulletin_filename}")
                try:
                    with open(chunk_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            if line.strip():
                                chunk = json.loads(line)
                                all_chunks.append(chunk)
                except Exception as file_error:
                    print(f"[ERROR] Failed to load chunk file {chunk_file.name}: {file_error}")
        else:
            # Load from all files
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
    
    # If bulletin query, return all chunks (already sorted by page)
    if bulletin_source:
        print(f"[RAG] Returning all {len(all_chunks)} chunks from {bulletin_source} for comprehensive analysis")
        return all_chunks
    
    # Otherwise, use relevance scoring for regular queries
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


def query_openrouter(messages: List[Dict], max_retries: int = 3) -> Optional[str]:
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
        "max_tokens": 4000  # Increased for more comprehensive responses
    }
    
    for attempt in range(max_retries):
        try:
            # Send request immediately - no wait
            print(f"[OPENROUTER] Attempt {attempt + 1}/{max_retries} - Calling {OPENROUTER_MODEL}")
            response = requests.post(url, json=payload, headers=headers, timeout=60)
            
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
                
                # Quick retry with minimal wait
                if wait_time is None:
                    wait_time = 2  # Just 2 seconds between retries
                
                print(f"[ERROR] Rate limited (429) - Waiting {wait_time}s before retry {attempt + 1}/{max_retries}...")
                
                if attempt < max_retries - 1:
                    time.sleep(wait_time)
                    print("   Retrying now...")
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
    system_prompt = """You are ASFC, an expert aviation and technical documentation assistant. Your role is to provide comprehensive, in-depth analysis based on the provided documentation context.

ANALYSIS REQUIREMENTS - Provide DEEP, THOROUGH answers:
- Analyze the question from multiple angles and perspectives
- Extract ALL relevant information from the context, not just surface-level facts
- Connect related concepts, procedures, and regulations together
- Explain the "why" behind procedures, not just the "what"
- Identify relationships between different pieces of information
- Consider implications, requirements, and dependencies
- Break down complex topics into clear, detailed explanations
- Provide comprehensive coverage of the topic, including edge cases when relevant

RESPONSE STRUCTURE:
- Start with a brief summary or direct answer
- Then provide detailed analysis with multiple supporting points
- Include specific examples, procedures, or regulations from the context
- Explain technical terms and concepts clearly
- Discuss related considerations or important caveats
- End with a concise summary if the answer is lengthy

CITATION AND ACCURACY:
- Base your answers STRICTLY on the provided context
- Cite specific sources (e.g., "According to Bulletin-79, page 12...")
- Quote exact text when referencing critical procedures or regulations
- If information is incomplete in the context, acknowledge what's missing
- Use technical terminology accurately from the context
- Distinguish between requirements, recommendations, and best practices

FORMATTING:
- Use clear paragraphs (2-4 sentences each)
- Use bullet points or numbered lists for procedures, requirements, or multiple points
- Use headings or bold text for key sections when helpful
- Write in a professional, authoritative style
- Ensure logical flow from general to specific information"""
    
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
        
        # Check if this is a bulletin analysis query
        is_bulletin_query = detect_bulletin_query(question) is not None
        
        if is_bulletin_query:
            # Special prompt for bulletin analysis
            user_message = f"""Complete Bulletin Documentation:

{context_text}

---

Question: {question}

BULLETIN ANALYSIS INSTRUCTIONS:
You are analyzing an ENTIRE bulletin document. Provide a COMPREHENSIVE, DETAILED analysis covering all aspects of this bulletin.

1. OVERVIEW & PURPOSE:
   - Provide a clear summary of what this bulletin is about
   - Explain its purpose, scope, and objectives
   - Identify the main topics and subject areas covered

2. COMPREHENSIVE CONTENT ANALYSIS:
   - Go through ALL sections and topics in the bulletin systematically
   - Extract and explain key information, procedures, regulations, and guidelines
   - Cover all major points, not just surface-level facts
   - Include technical details, specifications, and requirements

3. STRUCTURE & ORGANIZATION:
   - Describe how the bulletin is organized (sections, chapters, etc.)
   - Explain the flow and logical structure
   - Identify key sections and their purposes

4. DETAILED PROCEDURES & REQUIREMENTS:
   - Extract all procedures, step-by-step instructions, and workflows
   - List all requirements, regulations, and compliance items
   - Include specific numbers, measurements, thresholds, and technical specifications
   - Mention any forms, checklists, or documentation requirements

5. IMPORTANT CONSIDERATIONS:
   - Highlight critical safety information, warnings, or cautions
   - Note any exceptions, special cases, or edge cases
   - Identify dependencies on other documents or procedures
   - Mention any updates, revisions, or superseded information

6. PRACTICAL APPLICATIONS:
   - Explain how this bulletin applies in real-world scenarios
   - Provide context for when and why this information is needed
   - Connect related concepts and procedures

7. CITE SPECIFICALLY:
   - Reference specific page numbers when citing information
   - Quote exact text for critical procedures or regulations
   - Organize information by page/section for easy reference

STRUCTURE YOUR RESPONSE:
- Start with a comprehensive overview of the bulletin
- Then provide detailed analysis organized by major topics/sections
- Use clear headings, bullet points, and formatting
- Include page references throughout
- End with a summary of key points and takeaways

Provide the MOST COMPREHENSIVE analysis possible - analyze EVERYTHING in this bulletin, not just a summary."""
        else:
            # Regular query prompt
            user_message = f"""Context from documentation:

{context_text}

---

Question: {question}

ANALYSIS INSTRUCTIONS:
Please provide a COMPREHENSIVE, IN-DEPTH answer based on the context provided above. 

1. ANALYZE DEEPLY:
   - Extract all relevant information from the context
   - Consider multiple aspects and perspectives of the question
   - Connect related concepts, procedures, and regulations
   - Explain underlying principles and reasoning, not just facts

2. BE THOROUGH:
   - Provide detailed explanations with supporting details
   - Include step-by-step procedures when applicable
   - Mention important considerations, requirements, and dependencies
   - Discuss related topics that are relevant to fully understanding the answer

3. CITE SOURCES:
   - Reference specific documents and page numbers when citing information
   - Quote exact text for critical procedures or regulations
   - Distinguish between different sources when multiple documents are referenced

4. STRUCTURE WELL:
   - Start with a direct answer or summary
   - Then provide comprehensive analysis with multiple supporting points
   - Use clear paragraphs, bullet points, and formatting for readability
   - End with key takeaways if the answer is lengthy

If the context doesn't contain enough information to fully answer the question, acknowledge what information is available and what is missing. Provide the most comprehensive answer possible based on what is available."""
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
        # Return a shorter, more helpful message
        return "I'm currently unable to process your question due to rate limiting. Please wait 30 seconds and try again. The system is automatically managing request timing to avoid errors."


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

