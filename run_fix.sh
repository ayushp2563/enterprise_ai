#!/bin/bash

# Run the fix script inside the Docker container where all dependencies are installed

echo "🔧 Running embedding fix inside Docker container..."
echo ""

# Check if Docker container is running
if ! docker ps | grep -q enterprise_ai_app; then
    echo "❌ Docker container 'enterprise_ai_app' is not running."
    echo "Please start it first with:"
    echo "  cd docker && docker-compose up -d"
    exit 1
fi

echo "✅ Docker container is running"
echo ""

# Copy the fix script to the container
echo "📋 Copying fix script to container..."
docker cp fix_embeddings.py enterprise_ai_app:/app/fix_embeddings.py

echo "🚀 Running fix script..."
echo ""
docker exec enterprise_ai_app python3 fix_embeddings.py

echo ""
echo "✅ Fix complete!"
echo ""
echo "🧪 Now test your query:"
echo ""
echo 'curl -X POST "http://localhost:8000/api/query/" \'
echo '  -H "X-API-Key:f26132af20929f7f182d2b8c982818b0dbc036667ffe9ab42a27832df39b1e20" \'
echo '  -H "Content-Type: application/json" \'
echo '  -d '"'"'{"question": "How many vacation days do employees get?", "top_k": 5}'"'"
echo ""