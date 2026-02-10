# Enterprise AI Assistant

AI-Powered Enterprise Assistant with RAG (Retrieval-Augmented Generation) and Workflow Automation built with FastAPI, Groq Cloud, and PostgreSQL.

## 🎯 Features

- **RAG-Powered Q&A**: Answer questions using internal documents with source citations
- **Document Ingestion**: Support for PDF, DOCX, TXT, and Markdown files
- **Vector Search**: Fast similarity search using PostgreSQL with pgvector
- **LLM Integration**: Powered by Groq Cloud's llama-3.3-70b-versatile model
- **Workflow Automation**: 
  - Automated ticket creation
  - Report summarization
- **REST API**: FastAPI-based API with authentication
- **Security**: API key authentication and input sanitization

## 🛠️ Tech Stack

- **Backend**: Python 3.11, FastAPI
- **LLM**: Groq Cloud (llama-3.3-70b-versatile)
- **Database**: PostgreSQL 16 with pgvector extension
- **Embeddings**: SentenceTransformers (all-MiniLM-L6-v2)
- **Deployment**: Docker & Docker Compose

## 📋 Prerequisites

- Docker and Docker Compose
- Groq API key ([Get one here](https://console.groq.com))

## 🚀 Quick Start

### 1. Clone and Setup

```bash
cd /Users/ayush/.gemini/antigravity/scratch/enterprise-ai-assistant
```

### 2. Configure Environment

Copy the example environment file and add your Groq API key:

```bash
cp .env.example .env
```

Edit `.env` and set your Groq API key:
```
GROQ_API_KEY=your_groq_api_key_here
API_KEY=your_secure_api_key_here
SECRET_KEY=your_secret_key_here
```

### 3. Start Services

```bash
cd docker
docker-compose up -d
```

This will start:
- PostgreSQL with pgvector on port 5432
- FastAPI application on port 8000

### 4. Initialize Database

Wait for services to be healthy, then initialize the database:

```bash
docker-compose exec app python scripts/init_db.py
```

### 5. Verify Installation

```bash
curl http://localhost:8000/health
```

You should see: `{"status":"healthy","service":"enterprise-ai-assistant"}`

## 📚 API Documentation

Once running, visit:
- **Interactive API Docs**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc

### Authentication

All API endpoints (except `/health` and `/`) require an API key in the header:

```bash
X-API-Key: your_api_key_here
```

### Key Endpoints

#### 1. Upload Document

```bash
curl -X POST "http://localhost:8000/api/documents/upload" \
  -H "X-API-Key: your_api_key_here" \
  -F "file=@document.pdf" \
  -F "title=Company Policy"
```

#### 2. Query Documents (RAG)

```bash
curl -X POST "http://localhost:8000/api/query/" \
  -H "X-API-Key: your_api_key_here" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is our vacation policy?",
    "top_k": 5
  }'
```

#### 3. Create Ticket (Workflow)

```bash
curl -X POST "http://localhost:8000/api/workflows/execute" \
  -H "X-API-Key: your_api_key_here" \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_type": "ticket_creation",
    "parameters": {
      "title": "Bug in login page",
      "description": "Users cannot log in with SSO",
      "priority": "high",
      "category": "bug"
    }
  }'
```

#### 4. Summarize Report (Workflow)

```bash
curl -X POST "http://localhost:8000/api/workflows/execute" \
  -H "X-API-Key: your_api_key_here" \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_type": "report_summary",
    "parameters": {
      "report_text": "Your long report text here...",
      "max_length": 500
    }
  }'
```

#### 5. List Documents

```bash
curl -X GET "http://localhost:8000/api/documents/" \
  -H "X-API-Key: your_api_key_here"
```

## 🏗️ Project Structure

```
enterprise-ai-assistant/
├── app/
│   ├── main.py                    # FastAPI application
│   ├── config.py                  # Configuration management
│   ├── models/                    # Pydantic models
│   │   ├── documents.py
│   │   └── workflows.py
│   ├── services/                  # Business logic
│   │   ├── document_ingestion.py  # Text extraction & chunking
│   │   ├── vector_store.py        # PostgreSQL pgvector
│   │   ├── llm_service.py         # Groq Cloud integration
│   │   ├── rag_engine.py          # RAG orchestration
│   │   └── workflow_automation.py # Workflow execution
│   ├── api/                       # API routes
│   │   ├── query.py
│   │   ├── documents.py
│   │   └── workflows.py
│   └── security/                  # Authentication
│       └── auth.py
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
├── scripts/
│   └── init_db.py                 # Database initialization
├── tests/                         # Test files
├── requirements.txt
├── .env.example
└── README.md
```

## 🧪 Development

### Install Dependencies Locally

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Run Tests

```bash
pytest tests/ -v --cov=app
```

### View Logs

```bash
docker-compose logs -f app
```

### Stop Services

```bash
docker-compose down
```

### Reset Database

```bash
docker-compose down -v
docker-compose up -d
docker-compose exec app python scripts/init_db.py
```

## 🔒 Security Notes

This implementation includes **basic security**:
- API key authentication
- Input sanitization
- Rate limiting (configured, not enforced in code)

For production use, consider adding:
- JWT tokens with expiration
- Role-based access control (RBAC)
- HTTPS/TLS encryption
- Database connection pooling
- Advanced rate limiting middleware
- Audit logging

## 🎓 Why This Project?

This project demonstrates key skills for an **IBM Entry-Level AI Engineer**:

✅ **Full-stack AI fundamentals** - RAG, LLM integration, vector search  
✅ **Cloud-ready architecture** - Docker, microservices, REST APIs  
✅ **Production practices** - Logging, error handling, security  
✅ **Collaboration-ready** - Clean code, documentation, testing  

## 📝 License

MIT License - feel free to use this for your portfolio!

## 🤝 Contributing

This is a portfolio project, but suggestions are welcome! Open an issue or submit a pull request.

## 📧 Contact

Built as a resume project for AI/ML engineering roles.
# enterprise_ai
# enterprise_ai
