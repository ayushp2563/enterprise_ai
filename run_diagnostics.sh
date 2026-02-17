#!/bin/bash

# Diagnostic script - runs inside Docker to check database state

echo "🔍 RAG System Diagnostics"
echo "=========================="
echo ""

# Check if Docker container is running
if ! docker ps | grep -q enterprise_ai_db; then
    echo "❌ Database container 'enterprise_ai_db' is not running."
    echo "Please start it first with:"
    echo "  cd docker && docker-compose up -d"
    exit 1
fi

echo "Running database diagnostics..."
echo ""

# Run diagnostic queries
docker exec -i enterprise_ai_db psql -U postgres -d enterprise_ai << 'EOF'
\echo '=== 1. Documents ==='
SELECT id, title, metadata->>'num_chunks' as chunks, created_at FROM documents ORDER BY created_at DESC;

\echo ''
\echo '=== 2. Chunk Count ==='
SELECT COUNT(*) as total_chunks FROM document_chunks;

\echo ''
\echo '=== 3. Embedding Status ==='
SELECT 
    COUNT(*) as total,
    COUNT(*) FILTER (WHERE embedding IS NOT NULL) as with_embeddings,
    COUNT(*) FILTER (WHERE embedding IS NULL) as without_embeddings
FROM document_chunks;

\echo ''
\echo '=== 4. Sample Chunks ==='
SELECT 
    dc.id,
    d.title,
    LEFT(dc.chunk_text, 80) as preview,
    CASE WHEN dc.embedding IS NULL THEN 'NO' ELSE 'YES' END as has_embedding
FROM document_chunks dc
JOIN documents d ON dc.document_id = d.id
LIMIT 5;
EOF

echo ""
echo "=== Diagnostic complete ==="
echo ""
echo "Next steps:"
echo "1. If chunks show 'NO' for embeddings, run: ./run_fix.sh"
echo "2. If embeddings exist, check similarity threshold in code"
echo "3. Try the test query again"
echo ""