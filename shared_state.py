

"""Shared state contract for the sleep-health research workflow."""

from typing import TypedDict


class EvidenceRecord(TypedDict):
    id: str
    text: str
    url: str


class DraftRecord(TypedDict):
    id: str
    text: str


class ResearchState(TypedDict, total=False):
    question: str
    evidence: list[EvidenceRecord]
    draft: list[DraftRecord]
    verdict: str
    answer: str
