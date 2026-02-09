# Bug Fix Applied: Metadata Serialization Error

## 🐛 Bug Description

**Error**: `can't adapt type 'dict'`

**Cause**: Python dictionaries were being passed directly to PostgreSQL without JSON serialization, causing psycopg2 to fail when inserting metadata into the JSONB column.

## ✅ Fix Applied

### File Changed: `app/api/documents.py`

**Line 5**: Added import
```python
from psycopg2.extras import Json
```

**Line 77**: Wrapped metadata dict with `Json()` adapter
```python
# Before (❌ BROKEN):
{"filename": file.filename, "num_chunks": result['num_chunks']},

# After (✅ FIXED):
Json({"filename": file.filename, "num_chunks": result['num_chunks']}),
```

## 🚀 How to Apply the Fix

### Step 1: Rebuild Docker Container

```bash
cd /Users/ayush/.gemini/antigravity/scratch/enterprise-ai-assistant/docker
docker compose down
docker compose up -d --build
```

### Step 2: Wait for Services to Start

```bash
# Wait ~10 seconds, then check health
curl http://localhost:8000/health
```

### Step 3: Upload Sample Documents

```bash
cd /Users/ayush/.gemini/antigravity/scratch/enterprise-ai-assistant
source .env
./scripts/upload_samples.sh
```

### Expected Success Output:

```json
📄 Uploading vacation_policy.md...
{
  "document_id": 1,
  "title": "Company Vacation Policy",
  "num_chunks": 8,
  "status": "processed"
}

📄 Uploading onboarding_guide.md...
{
  "document_id": 2,
  "title": "Employee Onboarding Guide",
  "num_chunks": 12,
  "status": "processed"
}
```

### Step 4: Test RAG Query

```bash
curl -X POST "http://localhost:8000/api/query/" \
  -H "X-API-Key: f26132af20929f7f182d2b8c982818b0dbc036667ffe9ab42a27832df39b1e20" \
  -H "Content-Type: application/json" \
  -d '{"question": "How many vacation days do employees get?", "top_k": 5}'
```

### Expected Success Output:

```json
{
  "answer": "Based on the company vacation policy, employees are entitled to:\n\n- 15 days of paid vacation per year for employees with 0-3 years of service\n- 20 days of paid vacation per year for employees with 3-5 years of service  \n- 25 days of paid vacation per year for employees with 5+ years of service\n\nThe amount of vacation time depends on your length of service with the company.",
  "sources": [
    {
      "document_id": 1,
      "title": "Company Vacation Policy",
      "similarity": 0.89
    }
  ],
  "query_time": 1.23,
  "model_used": "llama-3.3-70b-versatile"
}
```

## 🔍 Why This Fix Works

- **`Json()` adapter**: Tells psycopg2 to serialize the Python dict as JSON
- **JSONB column**: PostgreSQL can now properly store and query the metadata
- **No data loss**: All metadata is preserved with proper structure
- **Query support**: You can now use PostgreSQL JSON operators on metadata

## 📝 Technical Details

The `psycopg2.extras.Json` class is a wrapper that:
1. Serializes Python objects to JSON strings
2. Tells PostgreSQL to treat the value as JSON/JSONB
3. Enables proper indexing and querying

This is the recommended approach for PostgreSQL JSONB columns in Python.

## ✅ Status

**Fix Applied**: ✅  
**Tested**: Pending (requires Docker rebuild)  
**Ready for Deployment**: Yes
