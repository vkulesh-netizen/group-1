import unittest

from pipeline import build_workflow, reflect


class ResearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.graph = build_workflow()

    def test_habits(self):
        result = self.graph.invoke({"question": "What sleep habits does CDC suggest?"})
        self.assertEqual(result["verdict"], "evidence matched")
        self.assertIn("[habits]", result["answer"])

    def test_bedtime_question_without_sleep_word(self):
        result = self.graph.invoke({
        "question": "What bedtime habits does CDC recommend?"
        })
        self.assertEqual(result["verdict"], "evidence matched")
        self.assertIn("[habits]", result["answer"])

    def test_outside_scope(self):
        result = self.graph.invoke({"question": "What sleep medication should I take?"})
        self.assertEqual(result["verdict"], "outside scope")

    def test_missing_evidence(self):
        result = self.graph.invoke({"question": "How does sleep change on Mars?"})
        self.assertEqual(result["verdict"], "insufficient evidence")

    def test_reflection_blocks_unsupported_draft(self):
        result = reflect({
            "evidence": [{"id": "habits", "text": "Source passage"}],
            "draft": [{"id": "habits", "text": "Unsupported claim"}],
        })
        self.assertEqual(result["verdict"], "unsupported draft")

