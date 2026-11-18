"""Streamlit frontend for the Sleep Health Research multi-agent prototype.

Owner: Kristy Riano (frontend design and responsible AI).

The frontend only talks to the compiled LangGraph workflow through
``workflow().invoke({"question": ...})``. ``normalize()`` accepts both the
team's shared ``AgentState`` (shared_state.py: review_status, final_answer,
retrieved_documents, draft_answer, citations, review_feedback) and the early
prototype keys (verdict, answer, evidence, draft), so the UI keeps working
while modules are integrated.
It never stores questions or answers outside the current browser session.
"""
import re

import streamlit as st

from pipeline import build_workflow

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
MAX_CHARS = 300
SOURCE = "https://www.cdc.gov/sleep/about/index.html"

# shared_state.py review_status -> verdict shown in the UI
STATUS_TO_VERDICT = {
    "PASS": "evidence matched",
    "INSUFFICIENT": "insufficient evidence",
    "REVISE": "unsupported draft",
}

EXAMPLES = {
    "Sleep habits": "What sleep habits does CDC suggest?",
    "Sleep duration": "How many hours of sleep are recommended by age?",
    "No evidence": "How does sleep change on Mars?",
    "Out of scope": "What sleep medication should I take?",
}

# How each reviewer verdict is shown to the Research Analyst.
VERDICTS = {
    "evidence matched": (
        "success",
        "Reviewed: every statement matches a retrieved CDC passage.",
    ),
    "insufficient evidence": (
        "warning",
        "No answer given: the indexed CDC material does not cover this question, "
        "so the system abstains instead of guessing.",
    ),
    "unsupported draft": (
        "error",
        "Draft withheld: the reflective agent found a statement that does not "
        "match its cited evidence.",
    ),
    "outside scope": (
        "info",
        "Not answered: the router only accepts general sleep-health research "
        "questions, not personal or medical advice.",
    ),
}

# Simple patterns for personal data the analyst should not type in.
PII_PATTERNS = {
    "an email address": r"[\w.+-]+@[\w-]+\.[\w.]+",
    "a phone number": r"\b\d{3}[\s.-]?\d{3}[\s.-]?\d{4}\b",
    "an ID or health-card number": r"\b\d{6,}\b",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
@st.cache_resource
def workflow():
    """Build the LangGraph workflow once per server process."""
    return build_workflow()


def normalize(state):
    """Map the workflow state to the fields the UI displays."""
    if "verdict" in state:  # early prototype format
        return {
            "verdict": state["verdict"],
            "answer": state.get("answer", ""),
            "evidence": state.get("evidence", []),
            "draft": state.get("draft", []),
            "feedback": "",
        }
    status = state.get("review_status")
    verdict = STATUS_TO_VERDICT.get(status, "review unavailable")
    evidence = [
        {
            "id": doc.get("source_id", ""),
            "text": doc.get("content", ""),
            "url": doc.get("url", SOURCE),
            "title": doc.get("title", "Source"),
        }
        for doc in state.get("retrieved_documents", [])
    ]
    draft = state.get("draft_answer", "")
    return {
        "verdict": verdict,
        "answer": state.get("final_answer") or state.get("review_feedback")
        or "The workflow did not return a recognized review outcome.",
        "evidence": evidence,
        "draft": [{"id": ", ".join(state.get("citations", [])), "text": draft}] if draft else [],
        "feedback": state.get("review_feedback", ""),
    }


def find_personal_data(text):
    """Return the kinds of personal data detected in the question, if any."""
    return [label for label, pattern in PII_PATTERNS.items() if re.search(pattern, text)]


def show_verdict(verdict):
    kind, message = VERDICTS.get(verdict, ("info", f"Review outcome: {verdict}"))
    getattr(st, kind)(f"**{verdict.capitalize()}** — {message}")


def show_sources(evidence):
    st.subheader("Sources")
    for item in evidence:
        with st.container(border=True):
            st.markdown(f"**[{item['id']}]** {item['text']}")
            title = item.get("title", "CDC About Sleep")
            st.link_button(f"Open {title} · {item['id']}", item["url"])


def show_review_trace(result):
    """Explainability: show what the reflective agent compared."""
    with st.expander("How was this answer reviewed?"):
        st.markdown(
            "1. **Router** checked that the question is about sleep and asks for no "
            "personal medical advice.\n"
            "2. **Research agent** called the ChromaDB retrieval tool and built a "
            "draft from the top passages.\n"
            "3. **Reflective agent** compared every draft statement with the passage "
            "it cites before anything was shown."
        )
        evidence = {item["id"]: item["text"] for item in result.get("evidence", [])}
        rows = [
            {
                "Citation": item["id"],
                "Draft statement": item["text"],
                "Matches evidence": "Yes" if evidence.get(item["id"]) == item["text"] else "No",
            }
            for item in result.get("draft", [])
        ]
        if rows:
            st.table(rows)
        else:
            st.caption("No draft was produced for this question.")
        if result.get("feedback"):
            st.markdown(f"**Reflection feedback:** {result['feedback']}")


def run(question):
    result = normalize(workflow().invoke({"question": question}))
    st.divider()
    st.markdown(f"**Question:** {question}")
    show_verdict(result["verdict"])
    if result["verdict"] == "evidence matched":
        st.markdown(result["answer"])
        show_sources(result["evidence"])
    else:
        st.caption(result["answer"])
    if result["verdict"] in STATUS_TO_VERDICT.values():
        show_review_trace(result)


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------
st.set_page_config(page_title="Sleep Health Research", page_icon="🌙")

with st.sidebar:
    st.header("About this tool")
    st.markdown(
        "A research assistant for **general sleep-health questions**. "
        f"Answers come only from curated passages of [CDC About Sleep]({SOURCE})."
    )
    st.markdown(
        "**Not medical advice.** For personal health concerns, talk to a "
        "health professional."
    )
    st.markdown(
        "**Privacy.** Questions are processed locally and are not saved. "
        "Do not include names, contact details, or health records."
    )
    st.markdown(
        "**Limits.** English only, one U.S. public-health source, four passages. "
        "Coverage may not fit every age group or population."
    )

st.title("🌙 Sleep Health Research")
st.caption(
    "Ask a general research question. Every answer is checked against its "
    "sources before it is shown."
)

st.write("Try an example:")
columns = st.columns(len(EXAMPLES))
for column, (label, example) in zip(columns, EXAMPLES.items()):
    if column.button(label, use_container_width=True):
        st.session_state["pending"] = example

with st.form("research"):
    question = st.text_input(
        "Research question",
        placeholder="What sleep habits does CDC suggest?",
        max_chars=MAX_CHARS,
    )
    submitted = st.form_submit_button("Search and review", type="primary")

if submitted:
    question = question.strip()
    if not question:
        st.warning("Please type a research question.")
    elif found := find_personal_data(question):
        st.warning(
            f"Your question seems to include {', '.join(found)}. "
            "Please remove personal details and ask a general question."
        )
    else:
        run(question)
elif pending := st.session_state.pop("pending", None):
    run(pending)
