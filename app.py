import streamlit as st

from pipeline import build_workflow

st.set_page_config(page_title="Sleep Health Research")
st.title("Sleep Health Research")
st.caption("Search a small collection of public CDC sleep-health information. Enter a general research question without personal details.")


@st.cache_resource
def workflow():
    return build_workflow()


with st.form("research"):
    question = st.text_input("Research question", placeholder="What sleep habits does CDC suggest?", max_chars=300)
    submitted = st.form_submit_button("Search and review")

if submitted and question.strip():
    result = workflow().invoke({"question": question.strip()})
    st.write(result["answer"])
    st.caption(f'Review outcome: {result["verdict"]}')
    if result["verdict"] == "evidence matched":
        st.subheader("Sources")
        for item in result["evidence"]:
            st.link_button(f'CDC About Sleep · {item["id"]}', item["url"])

