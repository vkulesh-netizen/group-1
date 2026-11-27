import json
import os
import tempfile
import unittest
from pathlib import Path

import jsonschema
from dotenv import load_dotenv
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

from pipeline import build_workflow, reflect, route_after_review
from research_agent import parse_draft

load_dotenv()
HABITS = "CDC lists keeping a regular bedtime and wake time among habits for better sleep [habits]."
QUALITY = "CDC describes sleep quality in terms of uninterrupted and refreshing sleep [quality]."
INVENTED = "CDC says melatonin supplements cure insomnia within a week [habits]."
SCHEMA = json.loads(Path(__file__).with_name("schemas").joinpath("feedback_log.schema.json").read_text())


class ScriptedModel(GenericFakeChatModel):
    """Offline stand-in for the LLM that replays fixed replies, tool calls included."""

    def bind_tools(self, tools, **kwargs):
        return self


def search(query):
    return AIMessage(content="", tool_calls=[
        {"name": "retrieve_sleep_evidence", "args": {"query": query}, "id": "call_1"}
    ])


class WorkflowTest(unittest.TestCase):
    def setUp(self):
        self.logs = tempfile.TemporaryDirectory()
        self.addCleanup(self.logs.cleanup)

    def run_workflow(self, question, *replies):
        graph = build_workflow(ScriptedModel(messages=iter(replies)), log_dir=self.logs.name)
        result = graph.invoke({"question": question})
        self.log = json.loads(Path(result["log_path"]).read_text(encoding="utf-8"))
        jsonschema.validate(self.log, SCHEMA)
        return result


class ResearchTests(WorkflowTest):
    def test_habits(self):
        result = self.run_workflow("What sleep habits does CDC suggest?", search("sleep habits"), AIMessage(HABITS))
        self.assertEqual(result["verdict"], "evidence matched")
        self.assertIn("[habits]", result["answer"])
        self.assertEqual(result["revision_count"], 0)

    def test_bedtime_question_without_sleep_word(self):
        result = self.run_workflow("What bedtime habits does CDC recommend?", search("bedtime habits"), AIMessage(HABITS))
        self.assertEqual(result["verdict"], "evidence matched")
        self.assertIn("[habits]", result["answer"])

    def test_outside_scope(self):
        result = self.run_workflow("What sleep medication should I take?")
        self.assertEqual(result["verdict"], "outside scope")
        self.assertEqual(self.log["exchanges"][0]["decision"], "scope_reply")


class AdaptationTests(WorkflowTest):
    def test_missing_evidence_retries_once_then_abstains(self):
        result = self.run_workflow(
            "How does sleep change on Mars?",
            search("sleep Mars"), AIMessage("NO_EVIDENCE"),
            search("Mars planet"), AIMessage("NO_EVIDENCE"),
        )
        self.assertEqual(result["evidence"], [])
        self.assertEqual(result["verdict"], "insufficient evidence")
        self.assertEqual(result["revision_count"], 1)
        self.assertEqual([gap["action"] for gap in self.log["feedback"]], ["search_again", "search_again"])

    def test_invented_claim_is_narrowed_on_revision(self):
        result = self.run_workflow(
            "What sleep habits does CDC suggest?",
            search("sleep habits"), AIMessage(INVENTED),
            search("sleep habits"), AIMessage(HABITS),
        )
        self.assertEqual(result["verdict"], "evidence matched")
        self.assertEqual(result["revision_count"], 1)
        gap = self.log["feedback"][0]
        self.assertEqual((gap["gap"], gap["action"]), ("low_support", "narrow_claim"))
        retry = [e for e in self.log["exchanges"] if e["actor"] == "research_worker"][1]
        self.assertIn("Narrow the claim", retry["feedback_received"])
        self.assertIn("Narrow the claim", retry["messages"][0]["content"])

    def test_unretrieved_citation_gets_evidence_on_revision(self):
        result = self.run_workflow(
            "What sleep habits does CDC suggest?",
            search("sleep habits"), AIMessage(QUALITY),
            search("sleep quality"), AIMessage(QUALITY),
        )
        self.assertEqual(self.log["feedback"][0]["gap"], "citation_not_retrieved")
        self.assertIn("quality", [item["id"] for item in result["evidence"]])
        self.assertEqual(result["verdict"], "evidence matched")

    def test_partial_support_after_retry_reports_limits(self):
        draft = f"{HABITS} {INVENTED}"
        result = self.run_workflow(
            "What sleep habits does CDC suggest?",
            search("sleep habits"), AIMessage(draft),
            search("sleep habits"), AIMessage(draft),
        )
        self.assertEqual(result["verdict"], "partially supported")
        self.assertIn("[habits]", result["answer"])
        self.assertNotIn("melatonin", result["answer"])
        self.assertIn("melatonin", result["limits"][0])
        self.assertEqual(self.log["outcome"]["revision_count"], 1)
        self.assertEqual(self.log["exchanges"][-1]["decision"], "report_limits")

    def test_unsupported_after_retry_is_withheld(self):
        result = self.run_workflow(
            "What sleep habits does CDC suggest?",
            search("sleep habits"), AIMessage(INVENTED),
            search("sleep habits"), AIMessage(INVENTED),
        )
        self.assertEqual(result["verdict"], "unsupported draft")
        self.assertTrue(result["limits"])


class ReviewerAndRouterTests(unittest.TestCase):
    def test_reflection_reports_gap_and_instruction(self):
        review = reflect({
            "evidence": [{"id": "habits", "text": "Source passage"}],
            "draft": [{"id": "habits", "text": "Unsupported claim"}],
        })["review"]
        self.assertEqual(review["verdict"], "revise")
        self.assertEqual(review["gaps"][0]["gap"], "low_support")
        self.assertIn("Narrow the claim", review["gaps"][0]["instruction"])

    def test_router_decides_the_next_step(self):
        self.assertEqual(route_after_review({"review": {"verdict": "pass"}}), "publish")
        self.assertEqual(route_after_review({"review": {"verdict": "revise"}, "revision_count": 0}), "revise")
        self.assertEqual(route_after_review({"review": {"verdict": "revise"}, "revision_count": 1}), "report_limits")
        self.assertEqual(route_after_review({"review": {"verdict": "insufficient"}, "revision_count": 1}),
                         "report_limits")

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
        with tempfile.TemporaryDirectory() as logs:
            result = build_workflow(log_dir=logs).invoke({"question": "What sleep habits does CDC suggest?"})
        self.assertEqual(result["verdict"], "evidence matched", result.get("draft"))
        self.assertIn("[habits]", result["answer"])
