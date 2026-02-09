#!/bin/bash

# Upload sample documents to the API
# Make sure the API is running before executing this script

set -e

API_URL="http://localhost:8000"
API_KEY="f26132af20929f7f182d2b8c982818b0dbc036667ffe9ab42a27832df39b1e20"

echo "📤 Uploading sample documents to Enterprise AI Assistant"
echo "========================================================="
echo ""

# Check if API is running
if ! curl -s "${API_URL}/health" > /dev/null; then
    echo "❌ API is not running. Please start it first with:"
    echo "   cd docker && docker-compose up -d"
    exit 1
fi

echo "✅ API is running"
echo ""

# Upload vacation policy
echo "📄 Uploading vacation_policy.md..."
curl -X POST "${API_URL}/api/documents/upload" \
  -H "X-API-Key: ${API_KEY}" \
  -F "file=@sample_docs/vacation_policy.md" \
  -F "title=Company Vacation Policy" \
  -s | python3 -m json.tool

echo ""

# Upload onboarding guide
echo "📄 Uploading onboarding_guide.md..."
curl -X POST "${API_URL}/api/documents/upload" \
  -H "X-API-Key: ${API_KEY}" \
  -F "file=@sample_docs/onboarding_guide.md" \
  -F "title=Employee Onboarding Guide" \
  -s | python3 -m json.tool

echo ""
echo "✅ Sample documents uploaded successfully!"
echo ""
echo "🔍 Try querying the documents:"
echo ""
echo "Example query:"
echo 'curl -X POST "http://localhost:8000/api/query/" \'
echo '  -H "X-API-Key: '"${API_KEY}"'" \'
echo "  -H \"Content-Type: application/json\" \\"
echo '  -d '"'"'{"question": "What is the vacation policy?", "top_k": 5}'"'"
echo ""
