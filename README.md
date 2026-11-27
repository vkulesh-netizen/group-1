# COMP 248 Sleep Health Research

Use Python 3.13. From the extracted project directory:

    py -3.13 -m venv .venv
    .venv\Scripts\python.exe -m pip install -r requirements.txt
    .venv\Scripts\python.exe -m unittest -v
    .venv\Scripts\python.exe -m streamlit run app.py

The research agent needs a Groq API key (free at https://console.groq.com). Create a `.env` file in the project directory, which git ignores:

    GROQ_API_KEY=your_groq_api_key_here
    LLM_MODEL=openai/gpt-oss-20b

The unit tests replace the LLM with a scripted stand-in and run without a key. One extra test calls Groq and is skipped when no key is set. No embedding download is needed.

The prototype indexes four curated paraphrases from CDC About Sleep in an in-memory Chroma collection. Binary term vectors support small, transparent retrieval. The research worker is a LangChain agent that calls the retrieval tool and writes a short summary citing a passage for every sentence. The reflective worker checks each sentence against the passage it cites and, for every gap, writes an instruction for the research worker. LangGraph controls routing: after a review it publishes, sends the draft back once with those instructions, or reports what the evidence supports and where it falls short.

Each run is logged to `logs/run-*.json` (git-ignored; schema in `schemas/feedback_log.schema.json`, example in `docs/feedback_log_example.json`). Set `FEEDBACK_LOG_DIR=` (empty) in `.env` to turn logging off.

Code layers: `app.py` (presentation), `pipeline.py` (orchestration), `research_agent.py` and `reflect_agent.py` (agent layer), `tools.py` and `feedback_log.py` (tool layer).

Try the example questions in the Streamlit app. The tests also show the reviewer flagging an invented claim and a citation to a passage that was never retrieved.

Use a private GitHub repository with issues and reviewed pull requests. Exclude local environments and secrets. Add actual meeting records, verify the AI disclosure, and confirm the official section and team number before submission. Submit peer evaluations individually through the course shell.
