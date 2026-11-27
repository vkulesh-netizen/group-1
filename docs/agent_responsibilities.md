# Agent Responsibilities and Design Decisions

## 1. Overview

The Sleep Health Research system uses a two-level architecture:
- Level 1: Planner / Router
- Level 2: Research Worker and Reflective Worker

The code is split into separate layers:

| Layer | Files | Contents |
|---|---|---|
| Presentation | app.py | Streamlit frontend |
| Orchestration | pipeline.py | LangGraph graph, Planner/Router (select(), route_after_review()), publish / report_limits / scope_reply / record nodes |
| Agent layer | research_agent.py, reflect_agent.py | Research Worker (LLM agent), Reflective Worker (deterministic reviewer) |
| Tool layer | tools.py, feedback_log.py | Retrieval tool + ChromaDB, JSON chat and feedback logger |

Agents make decisions inside their own step; tools only execute; the
router alone decides which step runs next.

Only the Research Worker invokes an LLM. The router and the
reflective worker are deterministic.

## 2. Planner / Router

Implementation: select() and route_after_review() in pipeline.py

Responsibility:
- select(): check whether the question concerns sleep, reject
  personal medical-advice requests, and route to the Research
  Worker or the scope reply.
- route_after_review(): after every review, decide the next step:
  - review passes -> publish the cited answer;
  - gaps found and revision_count < 1 -> revise: send the
    reviewer's instructions back to the Research Worker;
  - gaps remain after one revision -> report_limits: show only
    supported claims and tell the analyst where the evidence
    falls short.

LLM: None.

Tools: Python regular expressions and LangGraph conditional edges.

Justification:
Deterministic routing is transparent, inexpensive, repeatable, and
keeps the decision about retries out of the workers, so a worker
cannot loop on its own.

Limitation:
Keyword rules may reject valid paraphrases. One revision limits
cost and latency but may stop before a fixable draft is fixed.

## 3. Research Worker

Implementation: research_agent.py, a LangChain agent
(create_agent) called by the research node in pipeline.py.

Responsibility:
- Receive the supported question (and, on a revision, the
  reviewer's instructions appended to it).
- Decide the keyword query and call the LangChain retrieval tool
  (one retry with new keywords if empty).
- Write a 1-3 sentence summary using only the retrieved passages,
  ending every sentence with a citation ID.
- On a revision, follow each instruction: search again, find
  evidence for a named claim, or narrow a claim to the passage;
  drop claims it cannot support.
- Reply NO_EVIDENCE when nothing relevant is retrieved.

LLM: openai/gpt-oss-20b hosted on Groq (LLM_MODEL in .env),
temperature 0.

How retrieved passages support the draft:
- Evidence is read from the tool's own results, not from the
  model's description of them, and merged across attempts.
- A sentence without a citation is kept with an empty ID so the
  reviewer flags it instead of it being dropped.

## 4. Reflective Worker (reflection and adaptation)

Implementation: reflect_agent.py (review_draft(), feedback_message(),
limits_of()), called by the reflect node in pipeline.py.

Reflection (what it checks), per draft claim:
1. The claim cites a passage ID (gap: uncited_claim).
2. The cited passage was returned by the tool
   (gap: citation_not_retrieved).
3. At least 60% of the claim's content words appear in that
   passage (gap: low_support).
An empty draft is the gap no_evidence.

Feedback (what it produces): a review with a verdict (pass,
revise or insufficient), a check for every claim (support ratio,
supported yes/no) and, for every gap, one specific instruction:

| Gap | Action | Instruction to the Research Worker |
|---|---|---|
| no_evidence | search_again | Search again with keywords that name the topic; answer only with what a passage states. |
| uncited_claim | find_evidence | Find evidence for this claim and cite the returned passage, or remove it. |
| citation_not_retrieved | find_evidence | The cited passage was not returned; retrieve evidence and cite a returned ID, or remove the claim. |
| low_support | narrow_claim | Narrow the claim to what passage [id] states (the passage is quoted). |

Adaptation (how feedback changes the next step): the router sends
the instructions to the Research Worker, which revises its query
or its draft; the Reflective Worker then checks the new draft. If
gaps remain after one revision, the router reports the limits.

Who decides: the Reflective Worker never decides whether to retry.
It reports; route_after_review() in the router decides.

LLM: None. Tools: dictionary lookup and content-word overlap.

Limitation:
It cannot establish clinical correctness, recognise heavy
paraphrases or synonyms, or detect misleading claims that reuse
the passage's words.

## 5. Feedback and chat logs (JSON)

Implementation: feedback_log.py, the record node in pipeline.py,
schema in schemas/feedback_log.schema.json, example in
docs/feedback_log_example.json.

One file per question, logs/run-<UTC time>-<id>.json, containing:
- exchanges: every turn in order: the Research Worker's chat
  messages (prompt, tool calls, tool results, draft) and output,
  the Reflective Worker's review, and each router decision;
- feedback: every gap: attempt, claim, citation, support ratio,
  gap, action and instruction;
- outcome: final verdict, revision count, answer and limits.

Privacy: logs contain the question, so logs/ is git-ignored and
FEEDBACK_LOG_DIR="" turns logging off.

## 6. Knowledge Base

Storage technology: ChromaDB EphemeralClient, collection
cdc_sleep_v1, four curated paraphrases of
https://www.cdc.gov/sleep/about/index.html (duration, quality,
habits, benefits). Binary keyword vectors with cosine distance.
The collection is rebuilt in memory when build_workflow() runs.

## 7. Shared Workflow State

shared_state.py defines ResearchState:
question, evidence, draft, review, revision_count, feedback,
verdict, answer, limits, trace (append-only), log_path.

## 8. Design Trade-offs

Deterministic routing and retry decision:
+ Transparent, repeatable, bounded cost
- Limited language understanding; one revision only

LLM drafting with required citations:
+ Natural summaries, agent chooses its own query
- Needs an API key; output can vary between runs

Word-overlap reflection with targeted instructions:
+ Easy to test; each instruction names the claim and the fix
- Does not verify medical correctness or synonyms

JSON run logs:
+ Every review and decision can be audited after the run
- Stores the analyst's question on the server

## 9. Future Enhancements

- Semantic embeddings and semantic reflection
- Persistent vector storage and an expanded corpus
- Using the stored feedback across requests (for example, to tune
  prompts or the support threshold), pending the team's reading of
  the professor's "offline" comment
- Improved clinical safety review
