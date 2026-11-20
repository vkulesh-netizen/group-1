import os
import unittest

from dotenv import load_dotenv
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

from pipeline import build_workflow, reflect
from research_agent import parse_draft

load_dotenv()
HABITS = "CDC lists keeping a regular bedtime and wake time among habits for better sleep [habits]."


class ScriptedModel(GenericFakeChatModel):
    """Offline stand-in for the LLM that replays fixed replies, tool calls included."""

    def bind_tools(self, tools, **kwargs):
        return self


def search(query):
    return AIMessage(content="", tool_calls=[
        {"name": "retrieve_sleep_evidence", "args": {"query": query}, "id": "call_1"}
    ])


def run(question, *replies):
    graph = build_workflow(ScriptedModel(messages=iter(replies)))
    return graph.invoke({"question": question})


class ResearchTests(unittest.TestCase):
    def test_habits(self):
        result = run("What sleep habits does CDC suggest?", search("sleep habits"), AIMessage(HABITS))
        self.assertEqual(result["verdict"], "evidence matched")
        self.assertIn("[habits]", result["answer"])

    def test_bedtime_question_without_sleep_word(self):
        result = run("What bedtime habits does CDC recommend?", search("bedtime habits"), AIMessage(HABITS))
        self.assertEqual(result["verdict"], "evidence matched")
        self.assertIn("[habits]", result["answer"])

    def test_outside_scope(self):
        result = run("What sleep medication should I take?")
        self.assertEqual(result["verdict"], "outside scope")

    def test_missing_evidence(self):
        result = run("How does sleep change on Mars?", search("sleep Mars"), AIMessage("NO_EVIDENCE"))
        self.assertEqual(result["evidence"], [])
        self.assertEqual(result["verdict"], "insufficient evidence")

    def test_reflection_flags_invented_claim(self):
        result = run(
            "What sleep habits does CDC suggest?", search("sleep habits"),
            AIMessage("CDC says melatonin supplements cure insomnia within a week [habits]."),
        )
        self.assertEqual(result["verdict"], "unsupported draft")

    def test_reflection_flags_citation_that_was_not_retrieved(self):
        result = run(
            "What sleep habits does CDC suggest?", search("sleep habits"),
            AIMessage("CDC describes sleep quality in terms of uninterrupted and refreshing sleep [quality]."),
        )
        self.assertNotIn("quality", [item["id"] for item in result["evidence"]])
        self.assertEqual(result["verdict"], "unsupported draft")

    def test_reflection_blocks_unsupported_draft(self):
        result = reflect({
            "evidence": [{"id": "habits", "text": "Source passage"}],
            "draft": [{"id": "habits", "text": "Unsupported claim"}],
        })
        self.assertEqual(result["verdict"], "unsupported draft")

    def test_parse_draft_keeps_uncited_sentences(self):
        draft = parse_draft("- Sleep matters [benefits]. It also helps with everything.")
        self.assertEqual(draft, [
            {"id": "benefits", "text": "Sleep matters."},
            {"id": "", "text": "It also helps with everything."},
        ])


@unittest.skipUnless(
    os.getenv("GROQ_API_KEY", "your_groq_api_key_here") != "your_groq_api_key_here",
    "GROQ_API_KEY is not set in .env",
)
class LiveGroqTests(unittest.TestCase):
    def test_habits_with_real_model(self):
        result = build_workflow().invoke({"question": "What sleep habits does CDC suggest?"})
        self.assertEqual(result["verdict"], "evidence matched", result.get("draft"))
        self.assertIn("[habits]", result["answer"])
