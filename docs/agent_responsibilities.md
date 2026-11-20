

# Agent Responsibilities and Design Decisions

## 1. Overview

The Sleep Health Research system uses a two-level architecture:
- Level 1: Planner / Router
- Level 2: Research Worker and Reflective Worker

LangGraph orchestrates the workflow. LangChain provides
the retrieval tool, ChromaDB stores the evidence collection,
and Streamlit provides the user interface.

Only the Research Worker invokes an LLM. The router and the
reflective worker are deterministic.

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

Implementation: research_agent.py, a LangChain agent
(create_agent) called by research() in pipeline.py.

Responsibility:
- Receive the supported question.
- Decide the keyword query and call the LangChain
  retrieval tool (one retry with new keywords if empty).
- Write a 1-3 sentence summary using only the retrieved
  passages, ending every sentence with a citation ID.
- Reply NO_EVIDENCE when nothing relevant is retrieved.
- Pass the draft and evidence to the reviewer.

LLM: openai/gpt-oss-20b hosted on Groq (set by LLM_MODEL
in .env), temperature 0.

Justification:
An LLM lets the worker choose its own search query and
summarize in plain language instead of pasting passages.
gpt-oss-20b is an open-weight model that supports tool
calling, and Groq serves it quickly on a free tier.
Temperature 0 keeps answers repeatable for the demo.

How retrieved passages support the draft:
- The evidence passed on is read from the tool's own
  results, not from the model's description of them.
- Every sentence must cite one retrieved passage ID.
- A sentence without a citation is kept with an empty ID
  so the reviewer flags it instead of it being dropped.

Tool:
retrieve_sleep_evidence(), implemented using LangChain.

Knowledge base:
ChromaDB collection cdc_sleep_v1.

Limitation:
The model may paraphrase beyond what the lexical reviewer
accepts, and it needs a Groq API key and network access.
It abstains when a passage is related but does not answer
the question (e.g. hours of sleep by age).

Workflow:
Question -> LLM chooses query -> RAG Tool -> ChromaDB ->
Evidence -> LLM writes cited summary -> Draft

## 4. Reflective Worker

Implementation: reflect() in pipeline.py

Responsibility:
- Receive the draft and retrieved evidence.
- Check that each draft sentence cites a retrieved passage.
- Check that at least 60% of the sentence's content words
  (after removing stop words and plural "s") appear in
  that passage.
- Return an evidence-matched verdict when valid.
- Withhold unsupported drafts.
- Report insufficient evidence when no draft exists.

LLM: None.

Tools:
Python dictionary lookup and word-overlap scoring
(supported() in pipeline.py).

Justification:
Word overlap is predictable and testable, and it tolerates
the light rewording an LLM summary introduces, which an
exact string match would reject.

Limitation:
It cannot establish clinical correctness, recognise
heavy paraphrases or synonyms, or detect all misleading
claims that reuse the passage's words.

Workflow:
Draft + Evidence -> Word-overlap Check ->
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

LLM drafting with required citations:
+ Natural summaries, agent chooses its own query
- Needs an API key; output can vary between runs

Word-overlap reflection:
+ Easy to test, tolerates light rewording
- Does not verify medical correctness or synonyms

In-memory ChromaDB:
+ Simple setup and demonstration
- Does not persist indexed data

Binary term vectors:
+ No model download or embedding API required
- Limited semantic retrieval

## 8. Future Enhancements

Possible extensions, not currently implemented:
- Semantic embeddings
- Semantic reflection
- Persistent vector storage
- Expanded health-document corpus
- Improved clinical safety review
