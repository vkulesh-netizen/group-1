"""Shared state contract for the sleep-health research workflow.

LangGraph passes one ResearchState between the nodes for each question.
``trace`` uses an append reducer, so every node adds its own entries and the
complete exchange can be written to the JSON feedback log at the end.
"""
import operator
from typing import Annotated, TypedDict


class EvidenceRecord(TypedDict):
    id: str
    text: str
    url: str


class DraftRecord(TypedDict):
    id: str
    text: str


class ClaimReview(TypedDict):
    claim: str | None
    citation: str | None
    support_ratio: float
    supported: bool
    gap: str | None          # no_evidence | uncited_claim | citation_not_retrieved | low_support
    action: str | None       # search_again | find_evidence | narrow_claim
    instruction: str | None  # sent to the Research Worker on a revision


class Review(TypedDict):
    verdict: str             # pass | revise | insufficient
    claims: list[ClaimReview]
    gaps: list[ClaimReview]


class ResearchState(TypedDict, total=False):
    question: str
    evidence: list[EvidenceRecord]
    draft: list[DraftRecord]
    review: Review
    revision_count: int
    feedback: str            # instruction message for the next research attempt
    verdict: str
    answer: str
    limits: list[str]        # where the evidence falls short, shown to the analyst
    trace: Annotated[list[dict], operator.add]
    log_path: str
