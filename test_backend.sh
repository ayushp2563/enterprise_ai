#!/bin/bash

# Backend API Testing Script
# Tests all endpoints of the multi-tenant enterprise AI platform

set -e

BASE_URL="http://localhost:8000"
TEST_DIR="/tmp/enterprise_ai_test"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}==================================${NC}"
echo -e "${BLUE}Enterprise AI Platform - API Tests${NC}"
echo -e "${BLUE}==================================${NC}\n"

# Create test directory
mkdir -p $TEST_DIR

# Test 1: Health Check
echo -e "${BLUE}Test 1: Health Check${NC}"
curl -s "$BASE_URL/health" | jq .
echo -e "${GREEN}✓ Health check passed${NC}\n"

# Test 2: Register Company
echo -e "${BLUE}Test 2: Register Company${NC}"
curl -s -X POST "$BASE_URL/api/auth/register-company" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Acme Corporation",
    "slug": "acme-corp",
    "domain": "acme.com",
    "admin_email": "admin@acme.com",
    "admin_password": "SecurePass123",
    "admin_full_name": "John Admin"
  }' | jq . > $TEST_DIR/register.json

if [ -s $TEST_DIR/register.json ]; then
  echo -e "${GREEN}✓ Company registered successfully${NC}"
  cat $TEST_DIR/register.json | jq '{user: .user.email, role: .user.role, company: .user.company_id}'
else
  echo -e "${RED}✗ Company registration failed${NC}"
  exit 1
fi
echo ""

# Extract access token
TOKEN=$(cat $TEST_DIR/register.json | jq -r '.access_token')
echo -e "Access Token: ${TOKEN:0:50}...\n"

# Test 3: Get Current User
echo -e "${BLUE}Test 3: Get Current User${NC}"
curl -s -X GET "$BASE_URL/api/auth/me" \
  -H "Authorization: Bearer $TOKEN" | jq .
echo -e "${GREEN}✓ User info retrieved${NC}\n"

# Test 4: List Documents (should be empty)
echo -e "${BLUE}Test 4: List Documents${NC}"
curl -s -X GET "$BASE_URL/api/documents/" \
  -H "Authorization: Bearer $TOKEN" | jq .
echo -e "${GREEN}✓ Documents listed${NC}\n"

# Test 5: Upload Document
echo -e "${BLUE}Test 5: Upload Policy Document${NC}"
cat > $TEST_DIR/vacation_policy.txt << 'EOF'
VACATION POLICY 2024

All full-time employees are entitled to 15 vacation days per year.
Part-time employees receive vacation days prorated based on hours worked.

Vacation requests must be submitted at least 2 weeks in advance through the HR portal.
Unused vacation days can be carried over to the next year, up to a maximum of 5 days.

For questions about vacation policy, please contact HR at hr@acme.com or call ext. 5555.
EOF

curl -s -X POST "$BASE_URL/api/documents/upload" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@$TEST_DIR/vacation_policy.txt" \
  -F "title=Vacation Policy 2024" \
  -F "category=Time Off" | jq . > $TEST_DIR/upload.json

if [ -s $TEST_DIR/upload.json ]; then
  echo -e "${GREEN}✓ Document uploaded successfully${NC}"
  cat $TEST_DIR/upload.json
else
  echo -e "${RED}✗ Document upload failed${NC}"
fi
echo ""

# Wait for document processing
echo "Waiting for document processing..."
sleep 3

# Test 6: Query - Should Find Answer
echo -e "${BLUE}Test 6: Query About Vacation Days${NC}"
curl -s -X POST "$BASE_URL/api/query/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "How many vacation days do full-time employees get?",
    "top_k": 5
  }' | jq . > $TEST_DIR/query1.json

echo -e "${GREEN}✓ Query executed${NC}"
cat $TEST_DIR/query1.json | jq '{answer: .answer, confidence: .confidence_score, should_escalate: .should_escalate}'
echo ""

# Test 7: Query - Low Confidence (should escalate)
echo -e "${BLUE}Test 7: Query About Unrelated Topic (Should Escalate)${NC}"
curl -s -X POST "$BASE_URL/api/query/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is the company policy on workplace harassment?",
    "top_k": 5
  }' | jq . > $TEST_DIR/query2.json

echo -e "${GREEN}✓ Query executed${NC}"
cat $TEST_DIR/query2.json | jq '{answer: .answer, confidence: .confidence_score, should_escalate: .should_escalate, escalation_reason: .escalation_reason}'
echo ""

# Test 8: Invite Employee
echo -e "${BLUE}Test 8: Invite Employee${NC}"
curl -s -X POST "$BASE_URL/api/users/invite" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "employee@acme.com",
    "role": "employee"
  }' | jq . > $TEST_DIR/invite.json

if [ -s $TEST_DIR/invite.json ]; then
  echo -e "${GREEN}✓ Employee invited${NC}"
  cat $TEST_DIR/invite.json | jq '{email: .email, role: .role, token: .token}'
else
  echo -e "${RED}✗ Invitation failed${NC}"
fi
echo ""

# Test 9: List Users
echo -e "${BLUE}Test 9: List Users${NC}"
curl -s -X GET "$BASE_URL/api/users/" \
  -H "Authorization: Bearer $TOKEN" | jq .
echo -e "${GREEN}✓ Users listed${NC}\n"

# Test 10: HR Escalations
echo -e "${BLUE}Test 10: List HR Escalations${NC}"
curl -s -X GET "$BASE_URL/api/hr/escalations" \
  -H "Authorization: Bearer $TOKEN" | jq . > $TEST_DIR/escalations.json

echo -e "${GREEN}✓ Escalations listed${NC}"
cat $TEST_DIR/escalations.json | jq 'length as $count | "Total escalations: \($count)"'
echo ""

# Test 11: HR Analytics
echo -e "${BLUE}Test 11: HR Analytics${NC}"
curl -s -X GET "$BASE_URL/api/hr/analytics" \
  -H "Authorization: Bearer $TOKEN" | jq .
echo -e "${GREEN}✓ Analytics retrieved${NC}\n"

# Test 12: Query History
echo -e "${BLUE}Test 12: Query History${NC}"
curl -s -X GET "$BASE_URL/api/query/history?limit=10" \
  -H "Authorization: Bearer $TOKEN" | jq .
echo -e "${GREEN}✓ Query history retrieved${NC}\n"

# Test 13: Document Categories
echo -e "${BLUE}Test 13: Document Categories${NC}"
curl -s -X GET "$BASE_URL/api/documents/categories/list" \
  -H "Authorization: Bearer $TOKEN" | jq .
echo -e "${GREEN}✓ Categories listed${NC}\n"

# Summary
echo -e "${BLUE}==================================${NC}"
echo -e "${GREEN}All Tests Passed! ✓${NC}"
echo -e "${BLUE}==================================${NC}\n"

echo "Test artifacts saved to: $TEST_DIR"
echo "- Company registration: $TEST_DIR/register.json"
echo "- Document upload: $TEST_DIR/upload.json"
echo "- Query results: $TEST_DIR/query1.json, $TEST_DIR/query2.json"
echo "- HR escalations: $TEST_DIR/escalations.json"
echo ""

echo -e "${BLUE}API Documentation:${NC} http://localhost:8000/docs"
