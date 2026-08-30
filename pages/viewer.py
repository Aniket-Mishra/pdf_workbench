from pathlib import Path

import streamlit as st

st.title("PDF viewer")

documents = list(st.session_state.get("workbench_docs", []))
if not documents:
    st.info("Open one or more PDFs from the sidebar.")
    st.stop()

if len(documents) == 1:
    selected_document = documents[0]
else:
    documents_by_id = {
        document.document_id: document for document in documents
    }
    selected_document_id = st.session_state.get(
        "viewer_selected_document_id",
        documents[0].document_id,
    )
    if selected_document_id not in documents_by_id:
        selected_document_id = documents[0].document_id

    selected_document_id = st.selectbox(
        "Document",
        options=list(documents_by_id),
        index=list(documents_by_id).index(selected_document_id),
        format_func=lambda document_id: (
            documents_by_id[document_id].display_name
        ),
        key="viewer_document_widget",
    )
    st.session_state["viewer_selected_document_id"] = selected_document_id
    selected_document = documents_by_id[selected_document_id]

file_size_bytes = selected_document.path.stat().st_size
if file_size_bytes >= 1_000_000:
    file_size = f"{file_size_bytes / 1_000_000:.1f} MB"
else:
    file_size = f"{file_size_bytes / 1_000:.0f} KB"
st.subheader(selected_document.display_name)
st.caption(f"{selected_document.page_count} pages, {file_size}")
controls_path = (
    Path(__file__).parents[1]
    / "src/pdf_workbench/pdf_viewer_controls.html"
)
st.html(controls_path, unsafe_allow_javascript=True)
with st.container(key="pdf_viewer_workspace"):
    st.pdf(
        selected_document.path,
        height=900,
        key=f"pdf_viewer:{selected_document.document_id}",
    )
