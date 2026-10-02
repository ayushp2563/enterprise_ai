#!/bin/bash

# Upload sample documents to the API
# Make sure the API is running before executing this script

set -e

API_URL="http://localhost:8000"
: "${ACCESS_TOKEN:?Set ACCESS_TOKEN to an owner or admin access token}"

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
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -F "file=@sample_docs/vacation_policy.md" \
  -F "title=Company Vacation Policy" \
  -s | python3 -m json.tool

echo ""

# Upload onboarding guide
echo "📄 Uploading onboarding_guide.md..."
curl -X POST "${API_URL}/api/documents/upload" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
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
echo '  -H "Authorization: Bearer ${ACCESS_TOKEN}" \'
echo "  -H \"Content-Type: application/json\" \\"
echo '  -d '"'"'{"question": "What is the vacation policy?", "top_k": 5}'"'"
echo ""
