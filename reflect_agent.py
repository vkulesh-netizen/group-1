"""Agent layer: the Reflective Worker (reviewer).

Owner: Jonas Harvie (reflection and adaptation redesign).

Reflection - what it checks. For every draft sentence (a "claim"):
  1. the claim cites a passage ID (no ``uncited_claim``);
  2. that passage was actually returned by the retrieval tool
     (no ``citation_not_retrieved``);
  3. at least 60% of the claim's content words appear in the passage
     (no ``low_support``).
An empty draft is the gap ``no_evidence``.

Adaptation - what feedback it produces. Each gap gets one specific
instruction for the Research Worker's next attempt:
  no_evidence            -> search_again   (new keywords for the question)
  uncited_claim          -> find_evidence  (retrieve and cite, or drop the claim)
  citation_not_retrieved -> find_evidence
  low_support            -> narrow_claim   (restate only what the passage says)

The Reflective Worker does not decide whether another attempt happens. It
returns its review to LangGraph, and the router (``route_after_review`` in
pipeline.py) decides to publish, send the instructions back for one revision,
or report to the analyst what the evidence supports and where it falls short.
"""
from tools import tokens

SUPPORT_THRESHOLD = 0.6
ACTIONS = {
    "no_evidence": "search_again",
    "uncited_claim": "find_evidence",
    "citation_not_retrieved": "find_evidence",
    "low_support": "narrow_claim",
}


def stems(text):
    """Content words with a plural or verb "s" removed, so "habits" matches "habit"."""
    return {w[:-1] if len(w) > 3 and w.endswith("s") and not w.endswith("ss") else w
            for w in tokens(text)}


def support_ratio(sentence, passage):
    """Share of the sentence's content words that also appear in the passage."""
    words = stems(sentence)
    return len(words & stems(passage)) / len(words) if words else 0.0


def supported(sentence, passage):
    """True when most content words of a draft sentence appear in its cited passage."""
    return support_ratio(sentence, passage) >= SUPPORT_THRESHOLD


def check_claim(claim, evidence):
    """Review one draft sentence against the evidence it cites."""
    text, citation = claim["text"], claim["id"]
    ratio, gap, instruction = 0.0, None, None
    if not citation:
        gap = "uncited_claim"
        instruction = (f'Find evidence for this claim or remove it: "{text}" '
                       "Call retrieve_sleep_evidence with keywords from the claim and cite "
                       "the passage ID the tool returns.")
    elif citation not in evidence:
        gap = "citation_not_retrieved"
        instruction = (f'The claim "{text}" cites [{citation}], which the tool did not return. '
                       "Retrieve evidence for it and cite a returned passage ID, or remove the claim.")
    else:
        ratio = support_ratio(text, evidence[citation])
        if ratio < SUPPORT_THRESHOLD:
            gap = "low_support"
            instruction = (f'Narrow the claim "{text}" to what passage [{citation}] states: '
                           f'"{evidence[citation]}" Remove anything the passage does not say.')
    return {
        "claim": text,
        "citation": citation,
        "support_ratio": round(ratio, 2),
        "supported": gap is None,
        "gap": gap,
        "action": ACTIONS.get(gap),
        "instruction": instruction,
    }


def review_draft(evidence_list, draft):
    """Reflect on a draft: return a verdict, per-claim checks and the gaps found.

    verdict is "pass" (every claim supported), "revise" (at least one claim has
    a gap) or "insufficient" (no cited draft at all).
    """
    evidence = {item["id"]: item["text"] for item in evidence_list}
    if not draft:
        retrieved = ", ".join(evidence) or "none"
        return {"verdict": "insufficient", "claims": [], "gaps": [{
            "claim": None,
            "citation": None,
            "support_ratio": 0.0,
            "supported": False,
            "gap": "no_evidence",
            "action": ACTIONS["no_evidence"],
            "instruction": (f"No cited draft was produced (passages retrieved: {retrieved}). "
                            "Search again with different keywords that name the topic of the "
                            "question, and answer only with what a returned passage states."),
        }]}
    claims = [check_claim(item, evidence) for item in draft]
    gaps = [claim for claim in claims if not claim["supported"]]
    return {"verdict": "revise" if gaps else "pass", "claims": claims, "gaps": gaps}


def feedback_message(review, attempt):
    """Turn a review into the instruction message sent back to the Research Worker."""
    lines = [f"Reviewer feedback on your attempt {attempt + 1}:"]
    lines += [f"- {gap['instruction']}" for gap in review["gaps"]]
    lines.append("Revise your search query or your draft to address this feedback. "
                 "Keep every rule in your instructions, and reply NO_EVIDENCE if the "
                 "passages still do not support an answer.")
    return "\n".join(lines)


def limits_of(review):
    """Plain-language list of where the evidence falls short, for the analyst."""
    reasons = {
        "no_evidence": "No indexed CDC passage answered the question.",
        "uncited_claim": 'Not shown, no source cited: "{claim}"',
        "citation_not_retrieved": 'Not shown, cited passage [{citation}] was not retrieved: "{claim}"',
        "low_support": 'Not shown, passage [{citation}] does not support it ({pct}% of words match): "{claim}"',
    }
    return [reasons[gap["gap"]].format(pct=round(gap["support_ratio"] * 100), **gap)
            for gap in review["gaps"]]
