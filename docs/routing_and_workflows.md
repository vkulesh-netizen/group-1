# Selection Routing and Agent Workflows

## Selection and routing

The planner uses `select()` to route each question. It accepts general
sleep research questions containing the terms "sleep" or "bedtime".
It sends personal medical-advice requests and questions outside this
scope to `scope_reply`. These rules are deterministic, so the routing
decision is easy to inspect and test. Their limitation is that other
valid ways of asking about sleep may still be rejected.

## Agent workflows

The research worker receives an accepted question and invokes the
LangChain retrieval tool. The tool searches the in-memory ChromaDB
collection of curated CDC sleep passages. The worker returns the
retrieved evidence with citation IDs and builds an extractive draft.

The reflective worker receives both the draft and the evidence. It
checks whether every draft line exactly matches the passage identified
by its citation ID. A matching draft becomes the cited answer. If no
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

The original four unit tests and the new bedtime-routing test pass.
The Streamlit demo also showed a cited answer for a bedtime-habits
question and an insufficient-evidence verdict for a question about
sleep on Mars.