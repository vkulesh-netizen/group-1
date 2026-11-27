"""Tool layer: the CDC knowledge base and the LangChain retrieval tool.

Nothing in this module makes a decision or calls an LLM. Agents reach the
knowledge base only through ``retrieve_sleep_evidence``:

* the Research Worker calls the tool and the tool queries ChromaDB;
* the Reflective Worker never queries ChromaDB. It reads only the passages the
  tool returned, which LangGraph passes to it in the workflow state.
"""
import json
import re

import chromadb
from langchain.tools import tool

SOURCE = "https://www.cdc.gov/sleep/about/index.html"
COLLECTION = "cdc_sleep_v1"
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


def tokens(text):
    return set(re.findall(r"[a-z]+", text.lower())) - STOP


def vector(words, vocabulary):
    return [float(word in words) for word in vocabulary]


def build_retrieval_tool():
    """Index the curated CDC passages in ChromaDB and return the retrieval tool."""
    vocabulary = sorted(tokens(" ".join(keywords for keywords, _ in CORPUS.values())))
    collection = chromadb.EphemeralClient().get_or_create_collection(
        COLLECTION, configuration={"hnsw": {"space": "cosine"}}
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

    return retrieve_sleep_evidence
