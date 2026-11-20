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

The prototype indexes four curated paraphrases from CDC About Sleep in an in-memory Chroma collection. Binary term vectors support small, transparent retrieval. The research worker is a LangChain agent that calls the retrieval tool and writes a short summary citing a passage for every sentence. The reflective worker checks each sentence against the passage it cites. LangGraph controls routing.

Try the example questions in the Streamlit app. The tests also show the reviewer flagging an invented claim and a citation to a passage that was never retrieved.

Use a private GitHub repository with issues and reviewed pull requests. Exclude local environments and secrets. Add actual meeting records, verify the AI disclosure, and confirm the official section and team number before submission. Submit peer evaluations individually through the course shell.
