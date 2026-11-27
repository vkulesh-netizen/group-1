# Diagram changes: reflection, adaptation, feedback logs and layers

Author: Jonas Harvie, 27 Nov 2026. These changes respond to the professor's architecture review:

- make reflection and adaptation explicit;
- keep worker chat logs and reviewer feedback in JSON;
- separate the tool layer from the agent layer.

| Folder | Contents |
|---|---|
| `before_2026-11-25/` | PlantUML sources as submitted with the 25 Nov report. `rendered/` holds Figures 1-6 exactly as they appear in that report. |
| `after_2026-11-27/` | Updated PlantUML sources (identical to the live files in `diagrams/`, `components.puml` and `interaction.puml`). `rendered/` holds the PNGs rendered with PlantUML 1.2024.7, used as Figures 1-7 of `COMP248_Project_Report_Team1_Final_v2.pdf`. |

## Changes in every diagram

- **Who decides the next step:** the LangGraph router decides it, never a worker. Every diagram now shows the router function `route_after_review()` next to `select()`.
- **Adaptation loop:** if the review finds a gap, the draft goes back to the Research Worker **once**, with a specific instruction. If gaps remain after that one revision, the system reports what the evidence supports and where it falls short.
- **Layers:** the diagrams now name an **Agent layer** (Research Worker, Reflective Worker) and a **Tool layer** (retrieval tool, ChromaDB, feedback logger, JSON logs). They replace the earlier "Worker Layer" and "Retrieval Layer".

## Per diagram

| Diagram (report figure) | Before | After |
|---|---|---|
| `diagrams/architecture.puml` (Fig. 1) | Four layers: Presentation, Orchestration, Worker, Retrieval. A single arrow `Reflect -> Router : Reviewed result`. No LLM shown. | **Agent layer** and **Tool layer** named. Groq LLM shown as an external service. The Feedback Logger and `logs/run-*.json` added to the Tool layer. New arrows: Reflect → Router "Review: claims, gaps, instructions"; Router → Research "Revise once with reviewer instructions"; Router → Publish/Report limits; → Logger → JSON logs. Notes state the router's three-way decision and the reviewer's checks and instruction types. |
| `components.puml` (Fig. 2) | Flat components; the Research note said "extractive draft"; Reflect → Router "Verdict + answer". | Diagram name changed from `title` to `components` (it renders to `components.png`). Each interface now sits inside its component's package and the arrows point at it. Components grouped into Presentation / Orchestration / **Agent layer** / **Tool layer** packages. Added Groq LLM, Feedback logger, JSON logs and interface `IFeedbackLog`. Router → Research now carries "reviewer instructions on revision". Reflect → Router now carries "claims, gaps, instructions". Notes updated: the router has two decisions, and the reviewer "does not route". "Extractive draft" replaced by the LLM-summary wording. |
| `diagrams/router_workflow.puml` (Fig. 3) | Scope decision only. | Scope decision (`select()`) plus a **next-step decision loop** (`route_after_review()`): publish if the review passes; revise while `revision_count < 1`; otherwise report limits (partially supported / unsupported draft / insufficient evidence). Every path ends in "Record run in JSON feedback log". |
| `diagrams/research_workflow.puml` (Fig. 4) | Single pass. | On a revision, the reviewer's instructions are appended to the question. The LLM picks new keywords when told to search again and drops claims it cannot support. Tool results are merged into the evidence. Chat messages are returned for the log. |
| `diagrams/reflect_workflow.puml` (Fig. 5) | Whole-draft check with three verdicts (evidence matched / insufficient / unsupported), withhold on failure. | **Per-claim reflection** with four named gaps (`no_evidence`, `uncited_claim`, `citation_not_retrieved`, `low_support`), each paired with one instruction (search again, find evidence, narrow the claim). The output is a review (`pass` / `revise` / `insufficient`) returned to LangGraph. A note says the router, not the reviewer, decides the next step. |
| `interaction.puml` (Fig. 6) | One pass: research → reflect → verdict. Wording: "extractive draft". | A `loop` of at most 2 attempts. Inside it, `alt` publish / revise / report_limits, decided by `route_after_review()`. The Feedback logger is a participant: `record(state)` writes `logs/run-*.json` before the state returns to Streamlit. The analyst sees the answer, sources, **limits** and the review trace. |
| `diagrams/feedback_log.puml` (new, Fig. 7) | n/a | Abridged JSON example of one log, showing the exchanges (research, reflect and router turns), the feedback (claim, gap, action, instruction), the retry count and the outcome. The full schema is in `schemas/feedback_log.schema.json`; a full example is in `docs/feedback_log_example.json`. |

## Unchanged

- Knowledge base, retrieval logic, the 60% support threshold, and the scope rules in `select()`.
- The Streamlit screenshots (report Figures 7-8 in the 25 Nov report) still show the current UI for the answered and abstain paths.

## Still open

- **The "offline" comment.** We are not sure what the professor meant by moving the reflect agent "offline". The JSON logs make offline review of the reviewer's feedback possible, and nothing in the diagrams assumes more than that. Please confirm the meaning with the professor before extending the design.
