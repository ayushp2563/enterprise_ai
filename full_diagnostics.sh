#!/bin/bash

echo "🔍 Comprehensive RAG System Diagnostics"
echo "========================================"
echo ""

# 1. Check container status
echo "=== 1. Container Status ==="
docker ps --filter name=enterprise_ai_app --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""

# 2. Check if the code change took effect
echo "=== 2. Checking threshold value in container ==="
docker exec enterprise_ai_app grep -B2 -A2 "def similarity_search" /app/app/services/vector_store.py | grep -A3 "top_k"
echo ""

# 3. Check app logs for errors
echo "=== 3. Recent Application Logs ==="
docker logs enterprise_ai_app --tail 20
echo ""

# 4. Test vector search directly in Python
echo "=== 4. Testing Vector Search Directly ==="
docker exec enterprise_ai_app python3 -c "
import sys
sys.path.insert(0, '/app')

try:
    from app.services.document_ingestion import get_ingestion_service
    from app.services.vector_store import get_vector_store
    
    print('✓ Services imported successfully')
    
    # Generate query embedding
    ingestion = get_ingestion_service()
    query = 'vacation days'
    query_embedding = ingestion.generate_embeddings([query])[0]
    print(f'✓ Query embedding generated: {len(query_embedding)} dimensions')
    
    # Test vector search
    vector_store = get_vector_store()
    results = vector_store.similarity_search(query_embedding, top_k=5, threshold=-1.0)
    
    print(f'✓ Vector search returned {len(results)} results')
    
    if results:
        print('\nTop 3 results:')
        for i, r in enumerate(results[:3], 1):
            print(f'  {i}. {r[\"document_title\"]}: similarity={r[\"similarity\"]:.4f}')
    else:
        print('❌ No results found - this is the problem!')
        
except Exception as e:
    print(f'❌ Error: {e}')
    import traceback
    traceback.print_exc()
"
echo ""

# 5. Check database directly
echo "=== 5. Database Check ==="
docker exec enterprise_ai_db psql -U postgres -d enterprise_ai -c "
SELECT 
    COUNT(*) as total_chunks,
    COUNT(embedding) FILTER (WHERE embedding IS NOT NULL) as with_embeddings
FROM document_chunks;
"
echo ""

# 6. Raw SQL similarity test
echo "=== 6. Testing Raw SQL Similarity Search ==="
docker exec enterprise_ai_app python3 -c "
import sys
sys.path.insert(0, '/app')
import psycopg2
from app.config import get_settings
from app.services.document_ingestion import get_ingestion_service

settings = get_settings()
ingestion = get_ingestion_service()

# Get query embedding
query_embedding = ingestion.generate_embeddings(['vacation days'])[0]

# Test raw SQL
conn = psycopg2.connect(settings.database_url)
cursor = conn.cursor()

cursor.execute('''
    SELECT 
        d.title,
        1 - (dc.embedding <=> %s::vector) as similarity
    FROM document_chunks dc
    JOIN documents d ON dc.document_id = d.id
    ORDER BY similarity DESC
    LIMIT 3
''', (query_embedding,))

print('Raw SQL results:')
for row in cursor.fetchall():
    print(f'  {row[0]}: {row[1]:.4f}')

cursor.close()
conn.close()
"

echo ""
echo "=== Diagnostic Complete ==="