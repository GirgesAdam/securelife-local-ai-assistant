# Future Work

This project is currently a local demo of an AI-powered insurance assistant using FastAPI, Ollama, RAG, semantic retrieval, and session-based customer verification. The following improvements could make the system closer to a production-ready insurance assistant.

## 1. Replace CSV Files with a Real Database

The current version uses CSV files as a simple private customer database. A future version could use a real database such as PostgreSQL, MySQL, or SQLite.

This would improve:

- data reliability
- query performance
- customer record management
- scalability
- support for updates, inserts, and audit history

## 2. Add Production-Grade Authentication

The current project uses policy number and access code verification for demo purposes. In a real system, authentication should be handled by a secure identity provider or backend authentication service.

Possible improvements:

- secure login system
- one-time password verification
- encrypted session storage
- automatic session expiry
- logout endpoint
- rate limiting for failed verification attempts
- audit logs for personal-data access

## 3. Use Persistent Session Storage

The current session state is stored in memory. This is acceptable for a local demo, but it resets when the server restarts.

A future version could store session data in:

- Redis
- a database session table
- secure server-side session storage

This would make verified sessions more reliable across server restarts and multiple backend workers.

## 4. Improve Retrieval with a Vector Database

The current retriever uses local embedding storage and cosine similarity. A future version could use a vector database for faster and more scalable retrieval.

Possible options:

- FAISS
- ChromaDB
- Qdrant
- Weaviate
- pgvector

This would help when the company knowledge base becomes larger.

## 5. Add an Admin Document Upload Pipeline

Currently, general company documents are stored as text files. A future version could allow admins to upload new documents through an interface.

The pipeline could include:

- document upload
- text extraction
- chunking
- embedding generation
- index refresh
- document versioning

This would make the assistant easier to maintain when insurance policies or procedures change.

## 6. Add Automated Evaluation Tests

The project can be improved by adding a test dataset of questions and expected behaviors.

Examples:

- general questions should be answered from RAG
- personal questions should require verification
- wrong access codes should not expose private data
- out-of-scope questions should be rejected
- answers should not include unsupported claims or guarantees

This would make the assistant easier to test after prompt or retrieval changes.

## 7. Improve Answer Quality Evaluation

A future version could include an evaluation framework for answer quality.

Evaluation criteria could include:

- answer grounding
- correctness
- completeness
- hallucination rate
- response clarity
- retrieval relevance
- authentication safety

This would make it easier to measure whether changes improve or harm the assistant.

## 8. Add a Frontend Chat Interface

The current version is tested through FastAPI Swagger UI. A future version could include a simple chat frontend.

Possible options:

- Streamlit
- React
- Next.js
- simple HTML/CSS/JavaScript frontend

This would make the project easier to demonstrate to users, recruiters, and hiring managers.

## 9. Add Docker Support

A future version could include Docker files to simplify setup and deployment.

Possible additions:

- Dockerfile
- docker-compose.yml
- environment configuration
- Ollama service instructions

This would make the project easier to run on another machine.

## 10. Add Monitoring and Logging

A production-ready assistant should include structured logging and monitoring.

Useful logs could include:

- request type
- selected intent
- retrieved document sources
- authentication result
- failed access-code attempts
- fallback usage
- errors and exceptions

Sensitive data such as access codes should never be logged.

## 11. Add Human-Agent Handoff Integration

The current assistant can return a transfer-to-human response. A future version could integrate this with a real support workflow.

Possible integrations:

- ticket creation
- email notification
- CRM system
- support dashboard
- escalation queue

## 12. Add Multilingual Support

A future version could support customers in multiple languages, such as English and Arabic.

This would require:

- multilingual prompts
- multilingual retrieval testing
- translated company documents
- language detection
- consistent safety behavior across languages

## 13. Optional Local Model Comparison

Although model comparison is not part of the current project scope, it could be added later as a separate experiment.

Possible comparison criteria:

- answer quality
- JSON-following reliability
- retrieval-grounded response quality
- speed
- memory usage
- suitability for offline deployment

This should be treated as a future experiment, not part of the current core assistant.

## 14. Replace Demo Data with a Safer Synthetic Data Generator

The current project includes sample synthetic CSV data. A future version could include a script that generates fake customers, policies, claims, payments, and support tickets.

This would make the dataset easier to extend while avoiding real customer data.

## 15. Add CI Checks

A future version could include GitHub Actions for basic code checks.

Possible checks:

- install dependencies
- run Python syntax checks
- run unit tests
- validate example requests
- check formatting

This would make the repository more professional and easier to maintain.
