
from typing import TypedDict, Literal


class SourceDocument(TypedDict):
    source_id: str
    title: str
    url: str
    content: str


class AgentState(TypedDict, total=False):
    question: str
    session_id: str

    route: str

    retrieved_documents: list[SourceDocument]

    draft_answer: str
    citations: list[str]

    review_status: Literal[
        "PASS",
        "REVISE",
        "INSUFFICIENT"
    ]

    review_feedback: str
    revision_count: int

    final_answer: str
