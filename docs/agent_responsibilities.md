
# Agent Responsibilities and Technology Choices

## Architecture
Two-level hierarchical multi-agent architecture.

Level 1: Planner / Router Agent
Level 2: Research, Summarization, and Reflection Agents

## 1. Planner / Router Agent
Responsibility:
Classify incoming health questions and select the
appropriate workflow.

LLM:
Groq-hosted GPT-OSS-20B (proposed).

Tools:
LangGraph conditional routing.

Justification:
Centralized routing separates task coordination
from specialized agent processing.

## 2. Research Agent
Responsibility:
Retrieve relevant evidence from the health
knowledge base.

LLM:
Optional; retrieval itself can be deterministic.

Tools:
LangChain Retriever, ChromaDB, embedding model.

Justification:
RAG grounds health responses in retrievable
documents and provides source references.

## 3. Summarization Agent
Responsibility:
Generate clear summaries using retrieved evidence.

LLM:
Groq-hosted GPT-OSS-20B (proposed).

Tools:
LangChain prompt templates.

Justification:
The LLM converts retrieved information into
readable, context-aware summaries.

## 4. Reflection Agent
Responsibility:
Review summaries for factual grounding,
citation support, and completeness.

LLM:
Groq-hosted GPT-OSS-20B (proposed).

Tools:
Structured review prompt and LangGraph routing.

Justification:
Reflection identifies unsupported statements
and requests revision or reports insufficient
evidence when necessary.
