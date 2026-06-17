# AI Receptionist

A stateful workflow-based conversational AI system for appointment orchestration, retrieval-augmented question answering, and patient workflow automation.

Built using LangGraph, Django, PostgreSQL, pgvector, and Cal.com.

---

# System Goal

Traditional chatbot architectures struggle with workflows that require:

* persistent state
* multi-turn information gathering
* external API orchestration
* deterministic business logic

This project explores a hybrid architecture that combines:

* LLM reasoning
* workflow orchestration
* persistent state management
* retrieval-augmented generation

to automate dental clinic front desk operations.

---

# Architecture

<p align="center">
  <img src="Dental Receptionist Agent 1.png" width="1100">
</p>

---


# Live Deployment

The AI Receptionist is deployed on Render and accessible through WhatsApp, REST APIs, and an admin dashboard.

### WhatsApp Demo

Send a WhatsApp message to **+1 415 523 8886** with the code:

```text
join barn-factor
```

You can test:

* Appointment Booking
* Appointment Rescheduling
* Appointment Cancellation
* Appointment Retrieval
* FAQ Queries
* Emergency Escalation

### Admin Dashboard

https://ai-receptionist-e48c.onrender.com/dashboard

Features:

* Upload clinic documents
* Manage knowledge base content
* Remove outdated documents

### API Documentation

https://ai-receptionist-e48c.onrender.com/api_v1/docs

Interactive Swagger documentation exposing:

* AI Receptionist Endpoint
* Booking Workflow
* Rescheduling Workflow
* Cancellation Workflow
* Document Management APIs
* WhatsApp Webhook Endpoints



Features available in production:

- Appointment Booking
- Appointment Rescheduling
- Appointment Cancellation
- Appointment Retrieval
- FAQ Resolution
- Emergency Escalation


# Production Metrics

Measured using LangSmith tracing.

| Metric | Value |
|----------|----------|
| FAQ Cache Hit Latency | ~1.1s |
| FAQ Cache Miss Latency | ~1.6s |
| Booking Workflow | ~0.8s - 4.6s |
| Router Latency | ~0.6s |
| State Persistence | PostgreSQL + LangGraph Checkpointer |

Repeated FAQ requests are accelerated through semantic caching, reducing response latency from approximately 2.8s to 1.0s.

# Core Design Principles

## 1. Workflow Oriented Architecture

Instead of relying on a single agent loop:

```text
User
↓
LLM
↓
Response
```

the system decomposes responsibilities into specialized workflows:

```text
Intent Router
├── FAQ Workflow
├── Booking Workflow
├── Reschedule Workflow
├── Cancellation Workflow
├── Emergency Workflow
└── Fallback Workflow
```

This improves:

* determinism
* debuggability
* failure handling
* state management

---

## 2. Separation of Storage Concerns

The system separates data into three independent storage layers.

### Conversational State

Stored using LangGraph Postgres Checkpointer.

Responsibilities:

* conversation history
* active workflow state
* active appointment context
* multi-turn memory

```text
PostgreSQL
└── LangGraph Checkpoints
```

---

### Business Data

Stores clinic facing operational records.

```text
PostgreSQL
├── Patients
└── Appointments
```

Responsibilities:

* patient persistence
* appointment tracking
* cancellation status
* rescheduling history

---

### Knowledge Storage

Stores retrieval data.

```text
Documents
↓
Chunks
↓
Embeddings
↓
pgvector
```

Responsibilities:

* semantic retrieval
* FAQ answering
* clinic-specific knowledge

---

# Intent Routing

The router acts as the entry point for all requests.

Responsibilities:

* classify user intent
* dispatch workflow
* preserve conversation context

Supported routes:

```text
FAQ
Booking
Reschedule
Cancel
Show Appointment
Emergency
Fallback
```

---

# Booking Workflow

The booking workflow combines LLM extraction with deterministic validation.

Pipeline:

```text
User Query
↓
Booking Agent
↓
Validation Node
↓
Followup Node
↓
Availability Check
↓
Cal.com API
↓
Persistence Layer
```

The booking agent extracts:

```json
{
  "date": "...",
  "time": "...",
  "service": "..."
}
```

Validation is intentionally separated from extraction.

This prevents malformed LLM outputs from reaching external systems.

---

# Reschedule Workflow

Rescheduling introduces additional complexity because appointment state must remain synchronized across:

```text
Conversation State
Cal.com
Appointment Database
```

Pipeline:

```text
Retrieve Active Appointment
↓
Extract New Date/Time
↓
Validate
↓
Check Availability
↓
Reschedule Through Cal.com
↓
Update Persistent Records
```

A previous bug involved stale booking identifiers after successful reschedules.

The workflow now synchronizes:

```text
active_appointment
booking_uid
booking_id
```

after every successful reschedule operation.

---

# Cancellation Workflow

Pipeline:

```text
Retrieve Active Appointment
↓
Cal.com Cancellation
↓
Update Appointment Status
↓
Persist Changes
```

Failure path:

```text
Cal.com Failure
↓
Human Escalation
↓
Email Notification
```

---

# Retrieval Architecture

FAQ answering uses a hybrid retrieval pipeline.

Document ingestion:

```text
PDF / DOCX / TXT
↓
Chunking
↓
Embedding Generation
↓
pgvector Storage
```

Retrieval:

```text
Query
↓
Vector Search
↓
PostgreSQL Full Text Search
↓
Reranking
↓
Context Generation
↓
LLM
```

Technologies:

* pgvector
* SearchVector
* HNSW Index
* Voyage Reranker

---

# State Management

Conversation state is persisted using:

```text
LangGraph
+
PostgresSaver
```

This enables:

* multi-turn workflows
* workflow continuation
* interruption recovery
* appointment context retention

without storing state inside the application server.

---

# Data Model

## Patient

```text
phone
created_at
```

Patients are uniquely identified through WhatsApp phone numbers.

---

## Appointment

```text
booking_uid
booking_id
service
date
time
status
patient
```

Status transitions:

```text
scheduled
↓
rescheduled
↓
cancelled
```

---

# Failure Handling

External API failures are treated as workflow failures rather than silent errors.

Recovery mechanisms:

* human escalation
* email notification
* workflow termination
* user feedback

This prevents appointment requests from being lost when third-party services are unavailable.

---

# Observability

The system is instrumented using LangSmith for:

- Workflow tracing
- Node-level latency analysis
- Token usage tracking
- Failure debugging
- Execution path visualization

This enabled identification of:

- Cache hit vs cache miss behavior
- Workflow bottlenecks
- API latency hotspots


# Technology Stack

### Backend

* Django
* Django Ninja Extra

### Workflow Engine

* LangGraph

### LLM Layer

* meta-llama/llama-4-scout-17b-16e-instruct by Groq

### Retrieval

* pgvector
* Gemini Embeddings

### Persistence

* PostgreSQL

### External Integrations

* Cal.com
* Twilio WhatsApp
* Brevo

---

# Future Work

* Document Management Portal
* Voice Calling Workflow
* Analytics Layer
* Patient Portal

---

# Running Locally

```bash
git clone https://github.com/batman00723/AI-Receptionist.git

pip install -r requirements.txt

python manage.py migrate

python manage.py runserver
```
