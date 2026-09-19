from pathlib import Path

import streamlit as st

from src.pdf_workbench.document_selector import select_document

st.title("PDF viewer")

documents = list(st.session_state.get("workbench_docs", []))
if not documents:
    st.info("Open one or more PDFs from the sidebar.")
    st.stop()

document = select_document(
    documents, "viewer_selected_document_id", "Document"
)

file_size_bytes = document.path.stat().st_size
if file_size_bytes >= 1_000_000:
    file_size = f"{file_size_bytes / 1_000_000:.1f} MB"
else:
    file_size = f"{file_size_bytes / 1_000:.0f} KB"
st.caption(
    f"{document.display_name}, {document.page_count} pages, {file_size}"
)

# Adds ctrl/cmd + wheel zoom to st.pdf, which only offers buttons.
controls_path = (
    Path(__file__).parents[1] / "src/pdf_workbench/pdf_viewer_controls.html"
)
st.html(controls_path, unsafe_allow_javascript=True)
st.pdf(document.path, height=900, key=f"pdf_viewer:{document.document_id}")
