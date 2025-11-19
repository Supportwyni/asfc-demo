"""Script to backfill embeddings for existing chunks that don't have them."""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.database.client import get_client
from backend.database.repository import ChunkRepository
from backend.embeddings import generate_embeddings_batch
from backend.database.models import Chunk


def backfill_embeddings(batch_size: int = 50, limit: int = None):
    """
    Backfill embeddings for chunks that don't have them.
    
    Args:
        batch_size: Number of chunks to process in each batch
        limit: Maximum number of chunks to process (None for all)
    """
    client = get_client()
    
    # Get chunks without embeddings
    query = client.table("chunks").select("*").is_("embedding", "null")
    if limit:
        query = query.limit(limit)
    
    result = query.execute()
    
    if not result.data:
        print("[INFO] No chunks without embeddings found.")
        return
    
    chunks_without_embeddings = result.data
    total = len(chunks_without_embeddings)
    print(f"[INFO] Found {total} chunks without embeddings. Processing in batches of {batch_size}...")
    
    processed = 0
    failed = 0
    
    for i in range(0, total, batch_size):
        batch = chunks_without_embeddings[i:i + batch_size]
        print(f"[INFO] Processing batch {i // batch_size + 1} ({i + 1}-{min(i + batch_size, total)} of {total})...")
        
        # Extract texts
        texts = [chunk.get('text', '') for chunk in batch]
        chunk_ids = [chunk.get('id') for chunk in batch]
        
        # Generate embeddings
        embeddings = generate_embeddings_batch(texts, batch_size=batch_size)
        
        # Update chunks with embeddings
        for chunk_id, embedding in zip(chunk_ids, embeddings):
            if embedding:
                try:
                    client.table("chunks").update({
                        "embedding": embedding
                    }).eq("id", chunk_id).execute()
                    processed += 1
                except Exception as e:
                    print(f"[ERROR] Failed to update chunk {chunk_id}: {e}")
                    failed += 1
            else:
                failed += 1
        
        print(f"[INFO] Batch complete. Processed: {processed}, Failed: {failed}")
    
    print(f"[INFO] Backfill complete! Processed: {processed}, Failed: {failed}, Total: {total}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Backfill embeddings for existing chunks")
    parser.add_argument("--batch-size", type=int, default=50, help="Batch size for processing")
    parser.add_argument("--limit", type=int, default=None, help="Maximum number of chunks to process")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("Backfilling Embeddings for Existing Chunks")
    print("=" * 60)
    
    backfill_embeddings(batch_size=args.batch_size, limit=args.limit)
    
    print("=" * 60)
    print("Done!")
    print("=" * 60)


