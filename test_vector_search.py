#!/usr/bin/env python3
"""
Diagnostic script to test vector similarity search
"""

import psycopg2
from sentence_transformers import SentenceTransformer
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/enterprise_ai')

def test_vector_search():
    """Test vector similarity search"""
    
    # Connect to database
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    print("=== Database Diagnostics ===\n")
    
    # 1. Check if documents exist
    cursor.execute("SELECT COUNT(*) FROM documents")
    doc_count = cursor.fetchone()[0]
    print(f"✓ Total documents: {doc_count}")
    
    # 2. Check if chunks exist
    cursor.execute("SELECT COUNT(*) FROM document_chunks")
    chunk_count = cursor.fetchone()[0]
    print(f"✓ Total chunks: {chunk_count}")
    
    # 3. Check if embeddings exist (not null)
    cursor.execute("SELECT COUNT(*) FROM document_chunks WHERE embedding IS NOT NULL")
    embedding_count = cursor.fetchone()[0]
    print(f"✓ Chunks with embeddings: {embedding_count}")
    
    # 4. Sample some chunk texts
    print("\n=== Sample Chunk Texts ===\n")
    cursor.execute("SELECT id, document_id, LEFT(chunk_text, 100) FROM document_chunks LIMIT 3")
    for row in cursor.fetchall():
        print(f"Chunk {row[0]} (Doc {row[1]}): {row[2]}...")
    
    # 5. Test embedding generation for query
    print("\n=== Testing Query Embedding ===\n")
    model = SentenceTransformer('all-MiniLM-L6-v2')
    query = "How many vacation days do employees get?"
    query_embedding = model.encode([query])[0].tolist()
    print(f"✓ Query embedding generated: {len(query_embedding)} dimensions")
    print(f"✓ Query: '{query}'")
    
    # 6. Test similarity search with different thresholds
    print("\n=== Testing Similarity Search ===\n")
    
    for threshold in [0.0, 0.1, 0.2, 0.3]:
        cursor.execute(
            """
            SELECT 
                dc.id,
                dc.document_id,
                d.title,
                LEFT(dc.chunk_text, 100) as preview,
                1 - (dc.embedding <=> %s::vector) as similarity
            FROM document_chunks dc
            JOIN documents d ON dc.document_id = d.id
            WHERE 1 - (dc.embedding <=> %s::vector) > %s
            ORDER BY dc.embedding <=> %s::vector
            LIMIT 5
            """,
            (query_embedding, query_embedding, threshold, query_embedding)
        )
        
        results = cursor.fetchall()
        print(f"\nThreshold {threshold}: Found {len(results)} results")
        
        for i, row in enumerate(results, 1):
            print(f"  {i}. Doc: {row[2]}, Similarity: {row[4]:.4f}")
            print(f"     Preview: {row[3]}...")
    
    # 7. Check embedding dimensions
    print("\n=== Checking Embedding Dimensions ===\n")
    cursor.execute("SELECT vector_dims(embedding) FROM document_chunks LIMIT 1")
    result = cursor.fetchone()
    if result:
        print(f"✓ Embedding dimensions in DB: {result[0]}")
    else:
        print("✗ No embeddings found in database!")
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    try:
        test_vector_search()
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()