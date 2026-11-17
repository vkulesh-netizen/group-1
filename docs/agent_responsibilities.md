

# Agent Responsibilities and Design Decisions

## 1. Overview

The Sleep Health Research system uses a two-level architecture:
- Level 1: Planner / Router
- Level 2: Research Worker and Reflective Worker

LangGraph orchestrates the workflow. LangChain provides
the retrieval tool, ChromaDB stores the evidence collection,
and Streamlit provides the user interface.

The implemented prototype does not invoke an LLM.

## 2. Planner / Router

Implementation: select() in pipeline.py

Responsibility:
- Receive the user's question.
- Check whether it concerns sleep.
- Reject personal medical-advice requests.
- Route supported questions to the Research Worker.
- Return a scope message for unsupported requests.

LLM: None.

Tools: Python regular expressions and LangGraph routing.

Justification:
Deterministic routing is transparent, inexpensive,
repeatable, and suitable for the narrow demonstration.

Limitation:
Keyword rules may reject valid paraphrases or fail
to recognize some unsafe or out-of-scope questions.

Workflow:
Question -> Scope check -> Research or Scope Reply

## 3. Research Worker

Implementation: research() in pipeline.py

Responsibility:
- Receive the supported question.
- Invoke the LangChain retrieval tool.
- Retrieve up to three matching passages.
- Construct an extractive draft with citation IDs.
- Pass the draft and evidence to the reviewer.

LLM: None.

Tool:
retrieve_sleep_evidence(), implemented using LangChain.

Knowledge base:
ChromaDB collection cdc_sleep_v1.

Justification:
Extractive drafting preserves a direct relationship
between the response and the retrieved passages.

Limitation:
The worker cannot generate nuanced summaries or
synthesize information beyond the curated evidence.

Workflow:
Question -> RAG Tool -> ChromaDB -> Evidence -> Draft

## 4. Reflective Worker

Implementation: reflect() in pipeline.py

Responsibility:
- Receive the draft and retrieved evidence.
- Verify each draft citation ID and its exact text.
- Return an evidence-matched verdict when valid.
- Withhold unsupported drafts.
- Report insufficient evidence when no draft exists.

LLM: None.

Tools:
Python dictionary lookup and exact string comparison.

Justification:
Exact matching offers predictable and testable
grounding checks for an extractive prototype.

Limitation:
It cannot establish clinical correctness, assess
semantic paraphrases, or detect all misleading claims.

Workflow:
Draft + Evidence -> Exact Match Check ->
Publish, Insufficient Evidence, or Unsupported Draft

## 5. Knowledge Base

Storage technology: ChromaDB EphemeralClient.

Collection: cdc_sleep_v1.

Source:
https://www.cdc.gov/sleep/about/index.html

Content:
Four curated paraphrases about:
- Sleep duration
- Sleep quality
- Healthy sleep habits
- Benefits of sleep

Retrieval representation:
Binary keyword vectors with cosine distance.

Stored records contain:
- Record ID
- Text
- Source URL
- Section
- Binary embedding vector

The collection is recreated in memory when
build_workflow() runs.

## 6. Shared Workflow State

The implemented ResearchState contains:
- question
- evidence
- draft
- verdict
- answer

LangGraph passes this state between workflow nodes.

## 7. Design Trade-offs

Deterministic routing:
+ Transparent and repeatable
- Limited language understanding

Extractive drafting:
+ Easy to trace to evidence
- Limited synthesis

Exact-match reflection:
+ Easy to test
- Does not verify medical correctness

In-memory ChromaDB:
+ Simple setup and demonstration
- Does not persist indexed data

Binary term vectors:
+ No model download or embedding API required
- Limited semantic retrieval

## 8. Future Enhancements

Possible extensions, not currently implemented:
- LLM-assisted summarization
- Semantic embeddings
- Semantic reflection
- Persistent vector storage
- Expanded health-document corpus
- Improved clinical safety review
