"""Sleep-health research workflow."""
import json
import re
from pathlib import Path
from typing import TypedDict

import chromadb
from langchain.agents import create_agent
from langchain.tools import tool
from langgraph.graph import END, START, StateGraph

from research_agent import SYSTEM_PROMPT, make_llm, run_research_agent

SOURCE = "https://www.cdc.gov/sleep/about/index.html"
CORPUS = {
    "duration": ("sleep hours duration age adults children recommended amount",
                 "CDC organizes recommended sleep duration by age group."),
    "quality": ("sleep quality signs waking tired falling asleep",
                "CDC describes sleep quality in terms of uninterrupted and refreshing sleep."),
    "habits": ("sleep habits hygiene bedtime schedule screens electronics",
               "CDC lists keeping a regular bedtime and wake time among habits for better sleep."),
    "benefits": ("sleep benefits health mood attention memory",
                 "CDC associates sufficient sleep with better mood, attention, and memory."),
}
STOP = set(
    "a an and are as at be by can cdc do does for from good how i in is it of on or say should "
    "that the their this to what which who with you about help tell".split()
)
SUPPORT_THRESHOLD = 0.6


def tokens(text):
    return set(re.findall(r"[a-z]+", text.lower())) - STOP


def stems(text):
    """Content words with a plural or verb "s" removed, so "habits" matches "habit"."""
    return {w[:-1] if len(w) > 3 and w.endswith("s") and not w.endswith("ss") else w
            for w in tokens(text)}


def supported(sentence, passage):
    """True when most content words of a draft sentence appear in its cited passage."""
    words = stems(sentence)
    return bool(words) and len(words & stems(passage)) / len(words) >= SUPPORT_THRESHOLD


def vector(words, vocabulary):
    return [float(word in words) for word in vocabulary]


def build_workflow(llm=None):
    """Compile the LangGraph workflow. ``llm`` defaults to the Groq model in .env."""
    vocabulary = sorted(tokens(" ".join(keywords for keywords, _ in CORPUS.values())))
    database = chromadb.EphemeralClient()
    collection = database.get_or_create_collection(
        "cdc_sleep_v1", configuration={"hnsw": {"space": "cosine"}}
    )
    collection.upsert(
        ids=list(CORPUS),
        documents=[text for _, text in CORPUS.values()],
        embeddings=[vector(tokens(words), vocabulary) for words, _ in CORPUS.values()],
        metadatas=[{"source": SOURCE, "section": key} for key in CORPUS],
    )

    @tool
    def retrieve_sleep_evidence(query: str) -> str:
        """Retrieve CDC sleep-health evidence and citation IDs for a research question."""
        words = tokens(query) - {"sleep", "health"}
        if not words.intersection(vocabulary):
            return "[]"
        result = collection.query(
            query_embeddings=[vector(words, vocabulary)], n_results=3,
            include=["documents", "metadatas", "distances"],
        )
        return json.dumps([
            {"id": key, "text": passage, "url": meta["source"]}
            for key, passage, meta, distance in zip(
                result["ids"][0], result["documents"][0],
                result["metadatas"][0], result["distances"][0],
            )
            if distance < 0.999
        ])

    agent = create_agent(
        llm or make_llm(), [retrieve_sleep_evidence],
        system_prompt=SYSTEM_PROMPT, name="research_worker",
    )

    def research(state):
        return run_research_agent(agent, state["question"])

    graph = StateGraph(ResearchState)
    graph.add_node("research", research)
    graph.add_node("reflect", reflect)
    graph.add_node("scope_reply", lambda _: {
        "verdict": "outside scope", "answer": "Ask a general research question about sleep health."
    })
    graph.add_conditional_edges(START, select, {"research": "research", "scope_reply": "scope_reply"})
    graph.add_edge("research", "reflect")
    graph.add_edge("reflect", END)
    graph.add_edge("scope_reply", END)
    return graph.compile()


class ResearchState(TypedDict, total=False):
    question: str
    evidence: list[dict[str, str]]
    draft: list[dict[str, str]]
    verdict: str
    answer: str


def select(state):
    question = state["question"].lower()
    personal = re.search(
        r"\b(i|my|me)\b|\b(diagnos\w*|dosage|prescri\w*|treat\w*|medicat\w*|supplement\w*)\b",
        question,
    )
    return "research" if tokens(question) & {"sleep", "bedtime"} and not personal else "scope_reply"


def reflect(state):
    evidence = {item["id"]: item["text"] for item in state["evidence"]}
    draft = state["draft"]
    if not draft:
        return {"verdict": "insufficient evidence", "answer": "The indexed CDC material did not match this question."}
    if not all(supported(item["text"], evidence.get(item["id"], "")) for item in draft):
        return {"verdict": "unsupported draft", "answer": "The review found a claim without matching evidence."}
    return {
        "verdict": "evidence matched",
        "answer": "\n\n".join(f'{item["text"]} [{item["id"]}]' for item in draft),
    }

