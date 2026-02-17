#!/bin/bash

echo "🔍 Testing vector similarity search directly..."
echo ""

# Run a test query inside the Docker container
docker exec enterprise_ai_app python3 << 'PYTHON_SCRIPT'
import sys
sys.path.insert(0, '/app')

from app.services.document_ingestion import get_ingestion_service
from app.services.vector_store import get_vector_store

print("=== Testing Vector Similarity Search ===\n")

# Generate query embedding
ingestion = get_ingestion_service()
query = "How many vacation days do employees get?"
print(f"Query: '{query}'")

query_embedding = ingestion.generate_embeddings([query])[0]
print(f"✓ Query embedding generated: {len(query_embedding)} dimensions\n")

# Search with different thresholds
vector_store = get_vector_store()

print("Testing with threshold = -1.0:")
results = vector_store.similarity_search(query_embedding, top_k=5, threshold=-1.0)
print(f"Found {len(results)} results\n")

if results:
    for i, result in enumerate(results, 1):
        print(f"{i}. Document: {result['document_title']}")
        print(f"   Similarity: {result['similarity']:.4f}")
        print(f"   Preview: {result['chunk_text'][:100]}...")
        print()
else:
    print("❌ No results found even with threshold -1.0!")
    print("\nLet's check the database directly...\n")
    
    import psycopg2
    from app.config import get_settings
    settings = get_settings()
    
    conn = psycopg2.connect(settings.database_url)
    cursor = conn.cursor()
    
    # Test raw query
    cursor.execute("""
        SELECT 
            d.title,
            LEFT(dc.chunk_text, 100),
            1 - (dc.embedding <=> %s::vector) as similarity
        FROM document_chunks dc
        JOIN documents d ON dc.document_id = d.id
        ORDER BY dc.embedding <=> %s::vector
        LIMIT 5
    """, (query_embedding, query_embedding))
    
    print("Raw database query results:")
    for row in cursor.fetchall():
        print(f"- {row[0]}: similarity={row[2]:.4f}")
        print(f"  {row[1]}...\n")
    
    cursor.close()
    conn.close()

PYTHON_SCRIPT

echo ""
echo "=== Debug complete ==="