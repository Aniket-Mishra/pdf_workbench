from pathlib import Path

import streamlit as st

from src.pdf_workbench.upload_controls import show_upload_controls


st.set_page_config(
    page_title="PDF Workbench",
    layout="wide",
    initial_sidebar_state="expanded",
)

style_path = Path(__file__).parent / "src/pdf_workbench/app.css"
st.markdown(
    f"<style>{style_path.read_text()}</style>",
    unsafe_allow_html=True,
)

selected_page = st.navigation(
    {
        "PDF Workbench": [
            st.Page("pages/viewer.py", title="PDF viewer", default=True),
            st.Page("pages/editor.py", title="Editor"),
            st.Page("pages/workbench.py", title="Workbench"),
            st.Page("pages/organizer.py", title="Organizer"),
        ]
    },
    expanded=True,
)

with st.sidebar:
    show_upload_controls()
    documents = st.session_state.get("workbench_docs", [])
    st.divider()
    if documents:
        page_count = sum(document.page_count for document in documents)
        st.markdown(f"**{len(documents)} PDF(s) open**")
        st.caption(f"{page_count} pages available")
    else:
        st.caption("Open PDFs above to begin.")
    st.caption("Private, local PDF tools.")
    st.caption("Files stay on this machine.")

selected_page.run()
