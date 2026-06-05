# AI Receptionist — Conversational AI Workflow for Dental Clinics

AI Receptionist is a stateful conversational AI system built to automate front-desk operations at dental clinics via WhatsApp.

The system handles:

* appointment scheduling
* FAQ retrieval
* emergency escalation
* multi-turn conversations
* real-time slot booking

using LangGraph orchestration, RAG pipelines, Cal.com APIs, and Twilio messaging.

---

# Problem

Most clinic front desks still rely on:

* manual appointment handling
* repetitive FAQ answering
* fragmented communication workflows
* delayed patient responses
* overloaded reception staff

---

# Solution

AI Receptionist combines deterministic backend workflows with LLM-driven conversational orchestration.

The system can:

- Answer clinic-specific questions using RAG

- Maintain conversational memory across multiple messages

- Check real-time appointment availability

- Schedule appointments through Cal.com APIs

- Escalate urgent dental cases automatically

- Operate directly through WhatsApp

---

# Core Architecture

<p align="center">
  <img src="AI Receptionist 1.png" width="600" title="System Architecture">
</p>

---

# Technical Stack

## Backend

* Django
* Django Ninja Extra
* LangGraph
* LangChain

## AI Stack

* Llama 3.1 8B via Cerebras
* Gemini Embeddings
* Voyage AI Reranker
* Structured LLM Outputs

## Database & Retrieval

* PostgreSQL
* pgvector
* Hybrid Search
* SearchVector

## APIs

* Cal.com
* Twilio WhatsApp
* Resend Email API


---

# Current MVP Capabilities

* Conversational dental appointment booking
* WhatsApp-based AI receptionist
* Real-time slot checking
* Persistent conversation memory
* FAQ retrieval from clinic documents
* Emergency escalation workflows
* Multi-turn scheduling flows
