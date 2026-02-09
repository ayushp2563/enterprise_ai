# Troubleshooting: RAG Queries Returning No Results

## 🔍 Current Symptoms

- ✅ Documents are uploaded successfully (2 documents visible)
- ❌ RAG queries return: "I don't have enough information to answer this question"
- ❌ `sources: []` (empty sources array)

## 🎯 Root Cause

The **Docker container is still running the OLD code** (before the metadata fix). You need to rebuild the container to apply the code changes.

## ✅ Complete Fix Steps

### Step 1: Stop and Rebuild Docker Containers

```bash
cd /Users/ayush/.gemini/antigravity/scratch/enterprise-ai-assistant/docker

# Stop containers
docker compose down

# Rebuild with new code
docker compose up -d --build

# Wait for services to start (~15 seconds)
sleep 15
```

### Step 2: Verify Services Are Running

```bash
# Check container status
docker compose ps

# Check API health
curl http://localhost:8000/health
# Should return: {"status":"healthy","service":"enterprise-ai-assistant"}
```

### Step 3: Check Database (Optional but Recommended)

```bash
# Connect to database
docker compose exec db psql -U postgres -d enterprise_ai

# Check if tables exist
\dt

# Check if pgvector extension is enabled
\dx

# Count existing documents
SELECT COUNT(*) FROM documents;

# Count existing chunks
SELECT COUNT(*) FROM document_chunks;

# Exit psql
\q
```

### Step 4: Clear Old Data and Re-upload

```bash
cd /Users/ayush/.gemini/antigravity/scratch/enterprise-ai-assistant

# Delete old documents (they were uploaded with the broken code)
curl -X DELETE "http://localhost:8000/api/documents/1" \
  -H "X-API-Key: f26132af20929f7f182d2b8c982818b0dbc036667ffe9ab42a27832df39b1e20"

curl -X DELETE "http://localhost:8000/api/documents/2" \
  -H "X-API-Key: f26132af20929f7f182d2b8c982818b0dbc036667ffe9ab42a27832df39b1e20"

# Upload fresh documents with the fixed code
source .env
./scripts/upload_samples.sh
```

### Step 5: Verify Upload Success

You should see output like:
```json
{
  "document_id": 3,
  "title": "Company Vacation Policy",
  "num_chunks": 8,
  "status": "processed"
}
```

**NOT** like:
```json
{
  "detail": "Error processing document: can't adapt type 'dict'"
}
```

### Step 6: Test RAG Query

```bash
curl -X POST "http://localhost:8000/api/query/" \
  -H "X-API-Key: f26132af20929f7f182d2b8c982818b0dbc036667ffe9ab42a27832df39b1e20" \
  -H "Content-Type: application/json" \
  -d '{"question": "How many vacation days do employees get?", "top_k": 5}'
```

### Expected Success Output:

```json
{
  "answer": "Based on the company vacation policy, employees are entitled to:\n\n- 15 days of paid vacation per year for employees with 0-3 years of service\n- 20 days of paid vacation per year for employees with 3-5 years of service\n- 25 days of paid vacation per year for employees with 5+ years of service",
  "sources": [
    {
      "document_id": 3,
      "title": "Company Vacation Policy",
      "similarity": 0.89,
      "metadata": {"filename": "vacation_policy.md", "num_chunks": 8}
    }
  ],
  "query_time": 1.23,
  "model_used": "llama-3.3-70b-versatile"
}
```

## 🔍 Alternative: Check Logs for Errors

If the above doesn't work, check Docker logs:

```bash
cd /Users/ayush/.gemini/antigravity/scratch/enterprise-ai-assistant/docker

# View app logs
docker compose logs app --tail=100

# Follow logs in real-time
docker compose logs -f app
```

Look for errors related to:
- Database connection
- Embedding generation
- Vector storage
- Groq API calls

## 🚨 Common Issues

### Issue 1: "No sources found" but documents exist

**Cause**: Embeddings weren't stored correctly  
**Fix**: Delete and re-upload documents after rebuild

### Issue 2: "Invalid API key"

**Cause**: API key mismatch between `.env` and script  
**Fix**: Run `source .env` before upload script

### Issue 3: "Connection refused"

**Cause**: Docker containers not running  
**Fix**: Run `docker compose up -d`

### Issue 4: Documents upload but chunks = 0

**Cause**: Text extraction failed  
**Fix**: Check file format and encoding

## 📊 Debugging Queries

### Check if chunks were stored:

```bash
# Via API
curl -X GET "http://localhost:8000/api/documents/" \
  -H "X-API-Key: f26132af20929f7f182d2b8c982818b0dbc036667ffe9ab42a27832df39b1e20"

# Via database
docker compose exec db psql -U postgres -d enterprise_ai -c \
  "SELECT d.id, d.title, COUNT(dc.id) as chunk_count 
   FROM documents d 
   LEFT JOIN document_chunks dc ON d.id = dc.document_id 
   GROUP BY d.id, d.title;"
```

### Check if embeddings exist:

```bash
docker compose exec db psql -U postgres -d enterprise_ai -c \
  "SELECT COUNT(*) FROM document_chunks WHERE embedding IS NOT NULL;"
```

### Test vector similarity manually:

```bash
docker compose exec db psql -U postgres -d enterprise_ai -c \
  "SELECT chunk_text, embedding <=> '[0.1, 0.2, ...]'::vector as distance 
   FROM document_chunks 
   ORDER BY distance 
   LIMIT 5;"
```

## ✅ Success Checklist

- [ ] Docker containers rebuilt with `--build` flag
- [ ] Old documents deleted
- [ ] New documents uploaded successfully (no errors)
- [ ] Document count shows correct number of chunks
- [ ] RAG query returns answer with sources
- [ ] Sources array is not empty
- [ ] Similarity scores are reasonable (> 0.5)

## 🎯 Quick One-Liner Fix

```bash
cd /Users/ayush/.gemini/antigravity/scratch/enterprise-ai-assistant/docker && \
docker compose down && \
docker compose up -d --build && \
sleep 15 && \
cd .. && \
source .env && \
./scripts/upload_samples.sh
```

Then test:
```bash
curl -X POST "http://localhost:8000/api/query/" \
  -H "X-API-Key: f26132af20929f7f182d2b8c982818b0dbc036667ffe9ab42a27832df39b1e20" \
  -H "Content-Type: application/json" \
  -d '{"question": "How many vacation days do employees get?"}'
```

---

**TL;DR**: Rebuild Docker container → Delete old docs → Re-upload → Test query
