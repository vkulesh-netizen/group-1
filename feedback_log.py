"""Tool layer: JSON chat and feedback logs for each workflow run.

One file is written per question to ``logs/run-<UTC time>-<id>.json`` and
follows ``schemas/feedback_log.schema.json``. It records:

* ``exchanges`` - each worker turn in order: the Research Worker's chat
  messages (prompt, tool calls, tool results, draft), the Reflective
  Worker's review, and each LangGraph router decision;
* ``feedback`` - every gap the reviewer found: the claim, the gap, the
  instruction given and the attempt it belongs to;
* ``outcome`` - final verdict, retry count, answer and limits.

The logs let the team review the reflective agent's feedback after the run
("offline") without changing how a single request is answered. They contain
the analyst's question, so they are kept out of git (.gitignore) and can be
switched off with FEEDBACK_LOG_DIR="" (see pipeline.build_workflow).
"""
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

SCHEMA_VERSION = "1.0"


def chat_log(messages):
    """Convert LangChain messages into plain JSON records."""
    records = []
    for message in messages:
        record = {"role": message.type, "content": message.text}
        if getattr(message, "tool_calls", None):
            record["tool_calls"] = [{"name": call["name"], "args": call["args"]}
                                    for call in message.tool_calls]
        if message.type == "tool":
            record["tool_name"] = message.name
        records.append(record)
    return records


def build_log(state, max_revisions, run_id=None, created_at=None):
    """Assemble the log document from the final workflow state."""
    trace = state.get("trace", [])
    feedback = [
        {"attempt": entry["attempt"], **{key: gap[key] for key in
                                         ("claim", "citation", "support_ratio", "gap", "action", "instruction")}}
        for entry in trace if entry["actor"] == "reflective_worker"
        for gap in entry["review"]["gaps"]
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id or uuid.uuid4().hex[:12],
        "created_at": created_at or datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "question": state["question"],
        "max_revisions": max_revisions,
        "exchanges": [{"step": number, **entry} for number, entry in enumerate(trace, 1)],
        "feedback": feedback,
        "outcome": {
            "verdict": state.get("verdict", ""),
            "revision_count": state.get("revision_count", 0),
            "answer": state.get("answer", ""),
            "limits": state.get("limits", []),
        },
    }


def write_log(log_dir, state, max_revisions):
    """Write the run's log file and return its path."""
    document = build_log(state, max_revisions)
    folder = Path(log_dir)
    folder.mkdir(parents=True, exist_ok=True)
    stamp = document["created_at"][:19].replace(":", "").replace("-", "")
    path = folder / f"run-{stamp}Z-{document['run_id']}.json"
    path.write_text(json.dumps(document, indent=2, ensure_ascii=False), encoding="utf-8")
    return str(path)
