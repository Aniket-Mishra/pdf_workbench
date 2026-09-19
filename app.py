from pathlib import Path

import streamlit as st

from src.pdf_workbench.upload_controls import show_upload_controls


st.set_page_config(
    page_title="PDF Workbench",
    layout="wide",
    initial_sidebar_state="expanded",
)

style_path = Path(__file__).parent / "src/pdf_workbench/app.css"
st.markdown(f"<style>{style_path.read_text()}</style>", unsafe_allow_html=True)

selected_page = st.navigation(
    {
        "PDF Workbench": [
            st.Page("pages/viewer.py", title="PDF viewer", default=True),
            st.Page("pages/editor.py", title="Editor"),
            st.Page("pages/workbench.py", title="Workbench"),
        ]
    },
    expanded=True,
)

with st.sidebar:
    show_upload_controls()
    documents = st.session_state.get("workbench_docs", [])
    if documents:
        document_label = "PDF" if len(documents) == 1 else "PDFs"
        page_count = sum(document.page_count for document in documents)
        st.caption(
            f"{len(documents)} {document_label} open, {page_count} pages"
        )

selected_page.run()
