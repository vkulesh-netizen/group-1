"""Orchestration layer: the LangGraph sleep-health research workflow.

Layers
  Orchestration (this file)  Planner/Router: select() for scope and
                             route_after_review() for the next step after review.
  Agent layer                research_agent.py (Research Worker, LLM)
                             reflect_agent.py  (Reflective Worker, deterministic)
  Tool layer                 tools.py (retrieval tool + ChromaDB)
                             feedback_log.py (JSON chat and feedback logs)

Reflection and adaptation loop
  research -> reflect -> route_after_review:
    pass                              -> publish
    gap found, revision_count < 1     -> revise -> research (with the reviewer's instructions)
    gap found after one revision      -> report_limits (what the evidence supports, and where
                                         it falls short)
  Every path ends in record, which writes the JSON log.
"""
import os
import re

from langchain.agents import create_agent
from langgraph.graph import END, START, StateGraph

from feedback_log import chat_log, write_log
from reflect_agent import feedback_message, limits_of, review_draft, supported  # noqa: F401  (supported is used by app.py)
from research_agent import SYSTEM_PROMPT, make_llm, run_research_agent
from shared_state import ResearchState
from tools import SOURCE, build_retrieval_tool, tokens  # noqa: F401  (SOURCE kept for importers)

MAX_REVISIONS = 1
DEFAULT_LOG_DIR = "logs"


def select(state):
    """Planner/Router, first decision: send in-scope questions to research."""
    question = state["question"].lower()
    personal = re.search(
        r"\b(i|my|me)\b|\b(diagnos\w*|dosage|prescri\w*|treat\w*|medicat\w*|supplement\w*)\b",
        question,
    )
    return "research" if tokens(question) & {"sleep", "bedtime"} and not personal else "scope_reply"


def route_after_review(state):
    """Planner/Router, second decision: who decides the next step after reflection.

    The Reflective Worker only reports gaps; this router decides whether to
    publish, send the draft back once with the reviewer's instructions, or tell
    the analyst what the evidence supports and where it falls short.
    """
    if state["review"]["verdict"] == "pass":
        return "publish"
    if state.get("revision_count", 0) < MAX_REVISIONS:
        return "revise"
    return "report_limits"


def decision(state, step, reason):
    return {"actor": "langgraph_router", "attempt": state.get("revision_count", 0),
            "decision": step, "reason": reason}


def reflect(state):
    """Reflective Worker node: review the current draft against its evidence."""
    review = review_draft(state.get("evidence", []), state.get("draft", []))
    return {"review": review, "trace": [
        {"actor": "reflective_worker", "attempt": state.get("revision_count", 0), "review": review}
    ]}


def revise(state):
    attempt = state.get("revision_count", 0)
    gaps = ", ".join(sorted({gap["gap"] for gap in state["review"]["gaps"]}))
    return {
        "revision_count": attempt + 1,
        "feedback": feedback_message(state["review"], attempt),
        "trace": [decision(state, "revise", f"Gaps found ({gaps}); revision {attempt + 1} of {MAX_REVISIONS}.")],
    }


def publish(state):
    claims = state["review"]["claims"]
    return {
        "verdict": "evidence matched",
        "answer": "\n\n".join(f'{claim["claim"]} [{claim["citation"]}]' for claim in claims),
        "limits": [],
        "trace": [decision(state, "publish", "Every claim is supported by its cited passage.")],
    }


def report_limits(state):
    """Tell the analyst what the evidence supports and where it falls short."""
    review = state["review"]
    backed = [claim for claim in review["claims"] if claim["supported"]]
    if backed:
        verdict = "partially supported"
        answer = "\n\n".join(f'{claim["claim"]} [{claim["citation"]}]' for claim in backed)
    elif review["verdict"] == "insufficient":
        verdict = "insufficient evidence"
        answer = "The indexed CDC material did not match this question."
    else:
        verdict = "unsupported draft"
        answer = "The review found a claim without matching evidence, and the revision did not fix it."
    return {
        "verdict": verdict,
        "answer": answer,
        "limits": limits_of(review),
        "trace": [decision(state, "report_limits",
                           f"Gaps remain after {state.get('revision_count', 0)} revision(s).")],
    }


def scope_reply(state):
    return {
        "verdict": "outside scope",
        "answer": "Ask a general research question about sleep health.",
        "limits": [],
        "trace": [decision(state, "scope_reply", "Not a general sleep question, or asks for personal advice.")],
    }


def build_workflow(llm=None, log_dir=None):
    """Compile the LangGraph workflow.

    ``llm`` defaults to the Groq model in .env. ``log_dir`` defaults to the
    FEEDBACK_LOG_DIR environment variable, or "logs"; an empty string turns
    the JSON logs off.
    """
    if log_dir is None:
        log_dir = os.getenv("FEEDBACK_LOG_DIR", DEFAULT_LOG_DIR)
    agent = create_agent(
        llm or make_llm(), [build_retrieval_tool()],
        system_prompt=SYSTEM_PROMPT, name="research_worker",
    )

    def research(state):
        attempt = state.get("revision_count", 0)
        feedback = state.get("feedback") if attempt else None
        result = run_research_agent(agent, state["question"], feedback)
        evidence = {item["id"]: item for item in state.get("evidence", [])}
        for item in result["evidence"]:
            evidence.setdefault(item["id"], item)
        return {
            "revision_count": attempt,
            "evidence": list(evidence.values()),
            "draft": result["draft"],
            "trace": [{
                "actor": "research_worker",
                "attempt": attempt,
                "feedback_received": feedback,
                "messages": chat_log(result["messages"]),
                "output": {"evidence_ids": [item["id"] for item in result["evidence"]],
                           "draft": result["draft"]},
            }],
        }

    def record(state):
        return {"log_path": write_log(log_dir, state, MAX_REVISIONS) if log_dir else ""}

    graph = StateGraph(ResearchState)
    for name, node in [("research", research), ("reflect", reflect), ("revise", revise),
                       ("publish", publish), ("report_limits", report_limits),
                       ("scope_reply", scope_reply), ("record", record)]:
        graph.add_node(name, node)
    graph.add_conditional_edges(START, select, {"research": "research", "scope_reply": "scope_reply"})
    graph.add_edge("research", "reflect")
    graph.add_conditional_edges("reflect", route_after_review,
                                {"publish": "publish", "revise": "revise", "report_limits": "report_limits"})
    graph.add_edge("revise", "research")
    for name in ("publish", "report_limits", "scope_reply"):
        graph.add_edge(name, "record")
    graph.add_edge("record", END)
    return graph.compile()
