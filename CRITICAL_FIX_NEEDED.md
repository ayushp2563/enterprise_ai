# 🚨 CRITICAL ISSUE IDENTIFIED

## Problem
Documents are showing only **2 chunks** instead of the expected **8-12 chunks**.

```json
{
  "document_id": 5,
  "title": "vacation_policy.md",
  "num_chunks": 2,  // ❌ WRONG - Should be ~8
  "status": "processed"
}
```

## Root Cause
**The Docker container is still running the OLD code** (before the metadata fix).

Even though I fixed the code in `app/api/documents.py`, the running Docker container hasn't been updated with the new code.

## Why This Happens
Docker containers don't automatically reload code changes. You must:
1. Rebuild the container image with `--build` flag
2. Restart the container

## ✅ IMMEDIATE FIX (Run These Commands)

```bash
cd /Users/ayush/.gemini/antigravity/scratch/enterprise-ai-assistant/docker

# Stop containers
docker compose down

# Rebuild with the fixed code
docker compose up -d --build

# Wait for services to start
sleep 15

# Verify API is running
curl http://localhost:8000/health
```

## Then Re-upload Documents

```bash
cd /Users/ayush/.gemini/antigravity/scratch/enterprise-ai-assistant

# Load environment variables
source .env

# Upload documents (will now use the FIXED code)
./scripts/upload_samples.sh
```

## Expected Output After Fix

```json
{
  "document_id": 7,
  "title": "Company Vacation Policy",
  "num_chunks": 8,  // ✅ CORRECT - More chunks!
  "status": "processed"
}
```

## Then Test RAG Query

```bash
curl -X POST "http://localhost:8000/api/query/" \
  -H "X-API-Key: f26132af20929f7f182d2b8c982818b0dbc036667ffe9ab42a27832df39b1e20" \
  -H "Content-Type: application/json" \
  -d '{"question": "How many vacation days do employees get?", "top_k": 5}'
```

## Expected Success Output

```json
{
  "answer": "Based on the company vacation policy, employees are entitled to:\n- 15 days for 0-3 years of service\n- 20 days for 3-5 years of service\n- 25 days for 5+ years of service",
  "sources": [
    {
      "document_id": 7,
      "title": "Company Vacation Policy",
      "similarity": 0.89
    }
  ],
  "query_time": 1.2,
  "model_used": "llama-3.3-70b-versatile"
}
```

## Why Only 2 Chunks?

The old broken code had an error that prevented proper chunking. The fixed code will:
1. Extract full text from documents
2. Split into proper chunks (1000 chars with 200 overlap)
3. Generate embeddings for each chunk
4. Store embeddings in PostgreSQL with pgvector

## Verification Checklist

After rebuilding and re-uploading:

- [ ] Documents show 8-12 chunks (not just 2)
- [ ] RAG queries return actual answers (not "I don't have enough information")
- [ ] Sources array is not empty
- [ ] Similarity scores are reasonable (> 0.5)

---

**TL;DR**: Run `docker compose down && docker compose up -d --build` then re-upload documents!
