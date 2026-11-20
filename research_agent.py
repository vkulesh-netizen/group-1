"""Tool-using research worker for the sleep-health research workflow.

Owner: Jonas Harvie (research agent, drafting and summarization).

The worker is a LangChain agent backed by a Groq-hosted LLM. It decides how to
query the retrieval tool, reads the passages the tool returns, and writes a short
summary in which every sentence ends with the citation ID of its supporting
passage. The evidence handed to the reflective worker is taken from the tool
results themselves, not from the model's own account of what it retrieved.
"""
import json
import os
import re

from dotenv import load_dotenv
from langchain_core.messages import ToolMessage

DEFAULT_MODEL = "openai/gpt-oss-20b"
NO_EVIDENCE = "NO_EVIDENCE"

SYSTEM_PROMPT = f"""You are the research worker in a sleep-health research assistant for a Research Analyst.

1. Always call retrieve_sleep_evidence first, with a short keyword query based on the question.
   If it returns [], you may try once more with different keywords.
2. Write a summary of 1 to 3 sentences that answers the question using only facts stated
   in the retrieved passages. Keep close to the passage wording. Do not add outside
   knowledge, advice, or numbers that are not in the passages.
3. End every sentence with the ID of the passage that supports it in square brackets, for example:
   CDC lists keeping a regular bedtime and wake time among habits for better sleep [habits].
4. Write only those sentences: no heading, list, or introduction.

If the tool returns [] or nothing relevant to the question, reply with exactly: {NO_EVIDENCE}"""

CITED_SENTENCE = re.compile(r"\[([a-z_]+)\]")


def make_llm():
    """Create the Groq chat model from GROQ_API_KEY and LLM_MODEL in .env."""
    from langchain_groq import ChatGroq

    load_dotenv()
    key = os.getenv("GROQ_API_KEY", "")
    if not key or key == "your_groq_api_key_here":
        raise RuntimeError("Set GROQ_API_KEY in the .env file to run the research agent.")
    return ChatGroq(model=os.getenv("LLM_MODEL", DEFAULT_MODEL), temperature=0)


def collect_evidence(messages):
    """Gather the passages the retrieval tool actually returned, without duplicates."""
    evidence = {}
    for message in messages:
        if isinstance(message, ToolMessage) and message.name == "retrieve_sleep_evidence":
            for item in json.loads(message.content or "[]"):
                evidence.setdefault(item["id"], item)
    return list(evidence.values())


def parse_draft(text):
    """Split the agent's summary into sentences, each paired with its citation ID.

    A sentence without a citation keeps an empty ID so that the reflective
    worker can flag it as unsupported instead of it being silently dropped.
    """
    if text.strip() == NO_EVIDENCE:
        return []
    draft = []
    for line in text.splitlines():
        line = re.sub(r"^\s*(?:[-*•#]+|\d+[.)])\s*", "", line).replace("**", "")
        for sentence in re.split(r"(?<=[.!?\]])\s+(?=[A-Z])", line):
            ids = CITED_SENTENCE.findall(sentence)
            claim = CITED_SENTENCE.sub("", sentence).strip(" .")
            if claim:
                draft.append({"id": ids[0] if ids else "", "text": claim + "."})
    return draft


def run_research_agent(agent, question):
    """Run the agent on one question and return evidence and a cited draft."""
    result = agent.invoke({"messages": [{"role": "user", "content": question}]})
    return {
        "evidence": collect_evidence(result["messages"]),
        "draft": parse_draft(result["messages"][-1].text),
    }
