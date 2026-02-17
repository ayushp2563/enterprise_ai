#!/usr/bin/env python3
"""
Fix script to rebuild document embeddings
This will re-process existing documents and regenerate embeddings
"""

import psycopg2
from sentence_transformers import SentenceTransformer
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/enterprise_ai')

def fix_embeddings():
    """Rebuild embeddings for all document chunks"""
    
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    print("=== Fixing Vector Embeddings ===\n")
    
    # Initialize embedding model
    print("Loading embedding model...")
    model = SentenceTransformer('all-MiniLM-L6-v2')
    
    # Get all chunks without embeddings or with null embeddings
    cursor.execute("""
        SELECT id, chunk_text 
        FROM document_chunks 
        ORDER BY id
    """)
    
    chunks = cursor.fetchall()
    print(f"Found {len(chunks)} chunks to process\n")
    
    if len(chunks) == 0:
        print("No chunks found. Please upload documents first.")
        return
    
    # Process in batches
    batch_size = 10
    updated = 0
    
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i+batch_size]
        chunk_ids = [c[0] for c in batch]
        chunk_texts = [c[1] for c in batch]
        
        # Generate embeddings
        print(f"Processing batch {i//batch_size + 1} ({len(batch)} chunks)...")
        embeddings = model.encode(chunk_texts, show_progress_bar=False)
        
        # Update database
        for chunk_id, embedding in zip(chunk_ids, embeddings):
            cursor.execute(
                "UPDATE document_chunks SET embedding = %s::vector WHERE id = %s",
                (embedding.tolist(), chunk_id)
            )
            updated += 1
        
        conn.commit()
    
    print(f"\n✅ Successfully updated {updated} chunk embeddings!")
    
    # Verify
    cursor.execute("SELECT COUNT(*) FROM document_chunks WHERE embedding IS NOT NULL")
    count = cursor.fetchone()[0]
    print(f"✓ Total chunks with embeddings: {count}")
    
    # Test a sample query
    print("\n=== Testing Sample Query ===\n")
    query = "vacation days"
    query_embedding = model.encode([query])[0].tolist()
    
    cursor.execute("""
        SELECT 
            d.title,
            LEFT(dc.chunk_text, 150) as preview,
            1 - (dc.embedding <=> %s::vector) as similarity
        FROM document_chunks dc
        JOIN documents d ON dc.document_id = d.id
        ORDER BY dc.embedding <=> %s::vector
        LIMIT 3
    """, (query_embedding, query_embedding))
    
    print(f"Query: '{query}'\n")
    for i, row in enumerate(cursor.fetchall(), 1):
        print(f"{i}. {row[0]} (similarity: {row[2]:.4f})")
        print(f"   {row[1]}...\n")
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    try:
        fix_embeddings()
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()