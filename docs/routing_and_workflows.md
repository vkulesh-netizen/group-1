# Selection Routing and Agent Workflows

## Selection and routing

The planner uses `select()` to route each question. It accepts questions
containing "sleep" or "bedtime" unless they also contain first-person
pronouns or medical-advice terms. Other questions go to `scope_reply`.
This deterministic rule is easy to inspect and test, but it may reject
valid sleep research questions phrased in the first person or with
other sleep-related words.

## Agent workflows

The research worker is a LangChain agent backed by an LLM on Groq.
It receives an accepted question, chooses a keyword query, and
invokes the LangChain retrieval tool. The tool searches the in-memory
ChromaDB collection of curated CDC sleep passages. The agent then
writes a short summary in which every sentence cites a passage ID.

The reflective worker receives both the draft and the evidence. It
checks that every draft sentence cites a retrieved passage and that
most of the sentence's content words appear in that passage. A matching draft becomes the cited answer. If no
evidence was retrieved, it returns "insufficient evidence" and gives
no answer. If a draft line does not match its evidence, it returns
"unsupported draft" and withholds that draft. The prototype does not
retry the search after either failure.

LangGraph connects these steps: selection routes to research or a
scope reply; research passes its state to reflection; reflection
returns the final verdict. The UML sequence is in `interaction.puml`.
Individual workflows are in `diagrams/router_workflow.puml`,
`diagrams/research_workflow.puml`, and
`diagrams/reflect_workflow.puml`.

## Verification

The unit tests replace the LLM with a scripted stand-in, so they run
offline and give the same result every time. They cover routing, a
cited answer, missing evidence, an invented claim, and a citation to
a passage that was never retrieved. One extra test calls the real
Groq model and runs only when GROQ_API_KEY is set in `.env`.