# Interview Guide

These answers describe the implementation in this repository. They do not
describe planned infrastructure as if it already exists.

## Architecture

### Why React?

The interface is a Next.js application using React and TypeScript. React fits
the dashboard because authentication state, document lists, ingestion polling,
and chat updates are interactive client concerns. Next.js supplies routing and
a production build without replacing the FastAPI API.

### Why FastAPI?

FastAPI provides typed request validation through Pydantic, explicit dependency
injection for authentication, and generated OpenAPI documentation. Those
features make the API contract testable and visible at `/docs`.

### Why PostgreSQL?

PostgreSQL stores users, memberships, documents, jobs, conversations, messages,
and audit records in one transactional database. Ingestion state and chat
history need foreign keys and transactions, not just a vector index.

### Why pgvector?

Document embeddings are 384-dimensional vectors created by
`all-MiniLM-L6-v2`. Storing them in `document_chunks.embedding` lets retrieval
and tenant filtering happen in the same query as document metadata. A separate
vector database would add an operational system without a demonstrated need.

### Why RAG?

Company policies change by uploading documents. RAG retrieves the current
tenant's chunks and asks the LLM to answer from that context. The documents do
not need to be baked into model weights.

### Why not fine-tuning?

There is no labeled training corpus, and updating a policy should not require
retraining. Fine-tuning also would not provide the per-request tenant filter
or chunk citations implemented here. The evaluation set is too small to support
a responsible fine-tuning claim.

### Why Docker?

Docker Compose runs PostgreSQL with pgvector, migrations, the API, the worker,
and the frontend from the same configuration. The production Compose file runs
the same API and worker image with different commands.

## Backend

### How does authentication work?

Registration creates a user and an owner membership. Login verifies the Argon2
password hash, selects an active membership, and returns a short-lived JWT plus
an opaque refresh token. The JWT contains `sub` and `mid`; its signature,
issuer, audience, expiry, and token type are validated. The refresh token is
stored only as a SHA-256 hash and rotated on every refresh. Logout revokes the
caller's refresh session.

### How does authorization work?

Every protected request loads the user, membership, and organization from
PostgreSQL. A request proceeds only when all three are active. The database
role—not a role claim—is checked against owner, admin, or member permissions.
For example, admins may invite members, while only owners may change roles or
deactivate memberships. The last active owner cannot be removed.

### How are API errors handled?

Validation errors use FastAPI/Pydantic responses. Authentication failures
return 401, permission failures return 403, and cross-tenant resources return
404. Duplicate uploads return 409 and oversized uploads return 413. Unexpected
failures are logged and returned with a generic message rather than a stack
trace or document contents.

### How would you scale the backend?

The API is stateless apart from its in-memory rate limiter, so replicas can
share one database. Workers already coordinate through locked job rows. The
first real limits are PostgreSQL connections, embedding CPU, LLM latency, and
local file storage. Connection pooling and object storage would come before any
move to microservices.

## Database

### Explain the schema.

`companies` is the tenant root. `users` are global identities, and `memberships`
assign each user a role in an organization. Documents belong to one company and
have one ingestion job. Chunks belong to both the document and company and
store embeddings, page numbers, and model identity. Conversations belong to a
company and user; messages snapshot citations. Refresh sessions, invitations,
query logs, HR escalations, and audit events are separate tables. Existing
tables retain integer internal keys, while new aggregate tables use UUIDs.

### Which indexes did you create, and why?

The important indexes support actual access paths: active membership lookup,
public UUID lookup, tenant document pagination and status filtering, checksum
deduplication, unique chunk positions, tenant-and-document chunk access,
pending-job claims, conversation history, and audit/event investigation. The
pgvector index supports cosine nearest-neighbor search. Indexes were not added
to every column.

### How does tenant isolation work?

The API derives `company_id` from the authenticated membership. Document,
conversation, and vector queries include that value. Chunk queries filter both
`document_chunks.company_id` and `documents.company_id`. Composite foreign keys
ensure referenced users and documents belong to the same company. Another
tenant's resource returns 404. PostgreSQL row-level security is not yet
enabled, so application queries remain part of the enforcement path.

## RAG

### Explain the complete RAG pipeline.

The worker extracts text, preserves PDF page numbers, cleans text, splits it
into chunks, and stores embeddings. A question is embedded with the same model,
filtered to the caller's tenant and a similarity threshold, and sent to Groq
inside delimited source blocks. The response and citation snapshot are stored
on the conversation.

### How do embeddings work?

`all-MiniLM-L6-v2` converts text into a 384-float vector. pgvector ranks chunks
by cosine distance. Similarity is converted to `1 - distance` so higher values
represent closer text. The embedding model name is stored so vectors can be
rebuilt deliberately after a model change.

### How did you choose chunk size?

The current splitter uses 1,000 characters with 200 characters of overlap,
carried forward from the existing configuration. It is not the result of a
completed chunk-size experiment. Page boundaries are preserved so citations can
name a page when extraction provides one.

### What happens if retrieval returns irrelevant chunks?

Results below the configured similarity threshold are excluded. If no chunk
remains, the system returns an insufficient-information response instead of
calling the model for a factual answer. This behavior is tested and included in
the evaluation cases.

### How do you reduce hallucination?

The prompt limits answers to supplied context, tells the model to abstain when
evidence is insufficient, and forbids invented source IDs. The application then
removes citation markers that do not match retrieved chunks. This reduces
unsupported citations; it does not prove the wording is always correct.

### How do citations work?

Each retrieved chunk receives a `citation_id`, document title, chunk position,
similarity score, excerpt, and page number when available. The model cites
`[Source N]`. The API returns the corresponding chunk metadata and stores that
list on the assistant message, preserving the evidence even if the document
later changes.

### How did you evaluate retrieval quality?

`evaluation/rag_cases.jsonl` defines expected documents, expected answer terms,
and one abstention case. `evaluation/run_evaluation.py` calculates retrieval,
term presence, citation validity, abstention, and measured latency. These are
deterministic checks, not an LLM-judge score or a general accuracy percentage.
The dataset contains six cases.

## Security

### How do you prevent cross-tenant access?

Tenant identity comes from the membership record, and repository queries
include it. Database foreign keys reject mismatched company references.
Integration tests create two tenants and verify that vector search, chunk
reads, chunk deletes, and document reads do not cross that boundary.

### How do you handle prompt injection?

Retrieved text is placed inside `<source>` elements and labeled untrusted. The
system prompt says document text cannot override instructions, request secrets,
or create citations. The application independently checks citation markers.
This is a boundary and validation layer, not a claim that all model manipulation
is impossible.

### How are secrets stored?

Passwords use Argon2. Refresh and invitation secrets are random and stored as
SHA-256 hashes. `SECRET_KEY` and `GROQ_API_KEY` come from the environment.
Compose fails closed when the signing key or database password is absent. The
repository's `.env.example` contains placeholders rather than usable secrets.

### What happens if a malicious document is uploaded?

Uploads must have an allowed extension and matching media type, cannot be
empty, and are limited to 10 MB. Duplicate active content in the same tenant is
rejected by checksum. The original file is stored outside the response body.
Its text can still enter prompts, but it is treated as untrusted content.
There is no malware scanner.

## Performance

### What is the biggest bottleneck?

For a user request, the external LLM call dominates once embeddings exist. For
ingestion, loading the embedding model and encoding chunks is the expensive
work. That work was moved out of the upload request and into a worker, but it
remains CPU-bound.

### How would you reduce latency?

Keep the embedding model warm in the worker, batch chunk encoding, enforce the
retrieval limit and threshold, and avoid sending more context than necessary.
Database latency is addressed with tenant-first indexes and a vector index.
These are design choices; this repository does not publish a measured latency
number.

### How would you scale to 100,000 users?

Start with horizontal API replicas, multiple workers, a managed PostgreSQL
instance, connection pooling, and shared object storage. Add a shared rate
limiter because the current limiter is per process. Measure query latency and
database load before partitioning data or introducing new infrastructure.
100,000 users is a capacity target, not a tested result.

## Tradeoffs

### What would you change if you rebuilt it?

I would make memberships the only identity relationship from the first
migration, use public UUIDs in routes, and add a small database connection pool
before the service layer grew. I would also put tenant context into database
sessions so row-level security could be tested alongside application filters.

### What did you intentionally not implement?

Kubernetes, microservices, Redis, Kafka, fine-tuning, autonomous tool-using
agents, SSO, billing, and a second vector database. They would add operational
surface without improving the core demonstration.

### What is the weakest part of the architecture?

Tenant isolation is primarily enforced by application queries plus foreign
keys; row-level security is not active. Local document storage and the
in-memory rate limiter also assume a simpler deployment than many independently
scaled replicas. The RAG evaluation set demonstrates method, but it is too
small to support a broad quality claim.
