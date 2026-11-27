# Selection Routing and Agent Workflows

## Selection and routing

The planner makes two decisions.

`select()` routes each question. It accepts questions containing
"sleep" or "bedtime" unless they also contain first-person pronouns
or medical-advice terms. Other questions go to `scope_reply`.

`route_after_review()` runs after every review and decides the next
step: publish when the review passes, send the draft back once with
the reviewer's instructions when it finds a gap, and otherwise report
to the analyst what the evidence supports and where it falls short.
`MAX_REVISIONS = 1` in `pipeline.py`.

## Agent workflows

The research worker is a LangChain agent backed by an LLM on Groq. It
chooses a keyword query, invokes the retrieval tool (ChromaDB), and
writes a short summary in which every sentence cites a passage ID. On
a revision it receives the reviewer's instructions with the question.

The reflective worker checks every claim: it must cite a passage, the
passage must have been retrieved, and at least 60% of its content
words must appear in the passage. Each failure is a named gap with one
instruction: search again, find evidence for the claim, or narrow the
claim to the passage. The worker returns this review. It does not
decide what happens next.

| Final verdict | When |
|---|---|
| evidence matched | Every claim supported (first attempt or after revision) |
| partially supported | After one revision, some claims supported; only those are shown, with the limits listed |
| unsupported draft | After one revision, no claim supported |
| insufficient evidence | After one revision, still no cited draft |
| outside scope | Router `select()` rejected the question |

Each run ends in the `record` node, which writes a JSON log
(`logs/run-*.json`, schema in `schemas/feedback_log.schema.json`).

The UML sequence is in `interaction.puml`. Individual workflows are in
`diagrams/router_workflow.puml`, `diagrams/research_workflow.puml` and
`diagrams/reflect_workflow.puml`; the log structure is in
`diagrams/feedback_log.puml`. Before/after copies and a summary of the
diagram changes are in `diagrams/versions/`.

## Verification

The unit tests replace the LLM with a scripted stand-in, so they run
offline and give the same result every time. They cover routing, a
cited answer, abstention after one retry, an invented claim narrowed
on revision, an unretrieved citation fixed on revision, a partial
answer with limits, a draft still unsupported after revision, the
router's decisions, and validate every log against the JSON schema.
One extra test calls the real Groq model and runs only when
GROQ_API_KEY is set in `.env`.
