# SecureLife Local Insurance AI Assistant

A local, offline AI assistant for a fictional insurance company. The project uses **FastAPI**, **Ollama**, local open-source language models, document retrieval, structured JSON analysis, and session-based customer verification.

The goal is to demonstrate practical AI engineering skills: local inference, intent routing, RAG over company documents, private customer-data access after verification, deterministic structured outputs, and production-style guardrails.

## Features

- Runs locally with Ollama; no external LLM API is required.
- FastAPI backend with separate endpoints for chat, message analysis, general Q&A, customer verification, and the complete assistant flow.
- LLM-based insurance message analyzer that returns structured JSON.
- Pydantic validation and fallback handling for invalid model outputs.
- Embedding-based retriever over company documents using `mxbai-embed-large`.
- General answers are grounded in files under `data/general`.
- Personal answers use private CSV records only after policy-number and access-code verification.
- Session-based verification: once verified, the user can ask more personal questions in the same session without repeating verification.
- Access-code retry control: after several failed attempts, the session is cleared and the user is asked to contact support.
- Local benchmarking fields on the `/chat` endpoint: latency, token count, and tokens per second.

## Project structure

```text
securelife-local-ai-assistant/
├── app/
│   ├── main.py
│   ├── schemas.py
│   ├── ollama_client.py
│   ├── insurance_database.py
│   ├── document_retriever.py
│   ├── settings.py
│   └── prompts/
│       ├── insurance_prompt.py
│       ├── general_answer_prompt.py
│       └── personal_answer_prompt.py
├── data/
│   ├── general/
│   │   ├── claims_process_faq.txt
│   │   ├── company_profile.txt
│   │   ├── complaints_escalation.txt
│   │   ├── motor_comprehensive_policy.txt
│   │   └── renewals_cancellations_refunds.txt
│   └── private/
│       ├── customers.csv
│       ├── policies.csv
│       ├── claims.csv
│       ├── claim_documents.csv
│       ├── payments.csv
│       ├── policy_addons.csv
│       └── support_tickets.csv
├── docs/
├── examples/
├── requirements.txt
└── README.md
```

## Requirements

- Python 3.11+
- Ollama installed and running
- At least one chat model, for example `qwen2.5:7b`, `phi4-mini`, or `llama3.2:3b`
- The embedding model used by the retriever:

```bash
ollama pull mxbai-embed-large
```

Recommended model for better answers:

```bash
ollama pull qwen2.5:7b
```

Smaller fallback model:

```bash
ollama pull llama3.2:1b
```

## Setup

Create and activate a virtual environment:

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Start Ollama in the background, then run the API:

```bash
uvicorn app.main:app --reload
```

Open the interactive API docs:

```text
http://127.0.0.1:8000/docs
```

## Main endpoint

Use this endpoint for the complete assistant flow:

```text
POST /securelife-assistant
```

Example request:

```json
{
  "session_id": "demo-user-1",
  "message": "What policies does SecureLife offer?",
  "model": "qwen2.5:7b",
  "temperature": 0
}
```

Expected behavior:

```text
The assistant answers from the general company documents.
```

## Verification flow

For personal questions, the assistant first asks for the policy number, then the access code.

Step 1:

```json
{
  "session_id": "demo-user-1",
  "message": "What is the status of my claim?",
  "model": "qwen2.5:7b",
  "temperature": 0
}
```

Step 2:

```json
{
  "session_id": "demo-user-1",
  "message": "SL-MOTOR-1001",
  "model": "qwen2.5:7b",
  "temperature": 0
}
```

Step 3:

```json
{
  "session_id": "demo-user-1",
  "message": "1234",
  "model": "qwen2.5:7b",
  "temperature": 0
}
```

After successful verification, another personal question in the same `session_id` should be answered directly:

```json
{
  "session_id": "demo-user-1",
  "message": "Which add-ons are included in my policy?",
  "model": "qwen2.5:7b",
  "temperature": 0
}
```

End the session and reset verification:

```text
POST /end-session?session_id=demo-user-1
```

## Example test data

The included data is fictional and designed for portfolio/demo use.

Useful sample credentials:

| Policy number | Access code | Customer |
|---|---:|---|
| SL-MOTOR-1001 | 1234 | Ahmed Hassan |
| SL-HEALTH-2001 | 5678 | Mariam Ali |
| SL-TRAVEL-3001 | 2468 | Omar Khaled |
| SL-MOTOR-1002 | 1357 | Nour Samir |
| SL-HEALTH-2002 | 9999 | Youssef Nabil |

## Important design choices

This project intentionally separates general and personal questions.

General questions use RAG over company documents. Personal questions require verification before reading private CSV records. This mirrors real insurance-assistant constraints where policy, claim, payment, and add-on data must not be exposed before authentication.

The assistant uses an analyzer first, then routes the request to one of these actions:

- answer a general question
- request policy number
- request access code
- answer a personal question
- transfer to a human agent
- reject out-of-scope questions

- answer grounding
- latency
- tokens per second
- memory usage

Use `docs/MODEL_COMPARISON_TEMPLATE.md` to document your results.
