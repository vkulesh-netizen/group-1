# COMP 248 Sleep Health Research

Use Python 3.13. From the extracted project directory:

    py -3.13 -m venv .venv
    .venv\Scripts\python.exe -m pip install -r requirements.txt
    .venv\Scripts\python.exe -m unittest -v
    .venv\Scripts\python.exe -m streamlit run app.py

No model API key or embedding download is required. The prototype indexes four curated paraphrases from CDC About Sleep in an in-memory Chroma collection. Binary term vectors support small, transparent retrieval. The research worker invokes a LangChain tool and assembles an extractive draft. The reflective worker checks each line against the retrieved evidence. LangGraph controls routing.

Try the three questions in test_pipeline.py. Run the unsupported-draft test to demonstrate the reflection failure path directly. The supported path, route rejection, and insufficient-evidence path can all be shown in Streamlit.

Use a private GitHub repository with issues and reviewed pull requests. Exclude local environments and secrets. Add actual meeting records, verify the AI disclosure, and confirm the official section and team number before submission. Submit peer evaluations individually through the course shell.

