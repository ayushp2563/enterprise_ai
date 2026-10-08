# Resume Section

## Enterprise AI Platform

**Next.js, React, TypeScript, FastAPI, PostgreSQL, pgvector, Docker, GitHub Actions**

- Designed a multi-tenant knowledge platform with FastAPI and PostgreSQL, isolating documents, embeddings, conversations, and administration through membership checks and composite foreign keys.
- Built an asynchronous ingestion pipeline that validates uploads, stores originals privately, tracks pending-to-failed job state, and generates SentenceTransformer embeddings through a PostgreSQL-backed worker.
- Implemented tenant-filtered RAG with source-chunk citations, explicit abstention when retrieval is insufficient, untrusted-document prompt boundaries, and a version-controlled evaluation set.
- Delivered JWT membership authentication, rotating hashed refresh sessions, role-based authorization, Docker Compose services, and CI coverage for migrations, backend tests, and frontend builds.
