from pathlib import Path

import streamlit as st

from src.pdf_workbench.page_filters import clear_page_facts_cache
from src.pdf_workbench.thumbnails import clear_thumbnail_cache
from src.pdf_workbench.workspace import (
    create_workspace_directory,
    remove_unlisted_pdfs,
    store_uploaded_pdfs,
)


def clear_document_session_state() -> None:
    state_keys = (
        "organizer_pages",
        "organizer_source_manifest",
        "organizer_build_action_id",
        "organizer_load_action_id",
        "organizer_loaded_pages",
        "organized_pdf_bytes",
    )
    for state_key in state_keys:
        st.session_state.pop(state_key, None)

    selection_prefixes = (
        "selected_pages:",
        "window_start:",
        "grid_version:",
        "loaded_pages:",
        "visible_pages:",
        "load_more_action:",
        "filter_enabled:",
        "filter_text:",
        "filter_regex:",
        "filter_types:",
        "filter_orientations:",
        "filter_sizes:",
    )
    for state_key in list(st.session_state):
        if state_key.startswith(selection_prefixes):
            del st.session_state[state_key]


st.title("PDF viewer")
st.caption("Open and read PDFs here. Choose another tool when needed.")

uploaded_files = st.file_uploader(
    "Open PDFs",
    type=["pdf"],
    accept_multiple_files=True,
    key="viewer_upload",
) or []

if "workspace_directory" not in st.session_state:
    st.session_state["workspace_directory"] = create_workspace_directory()

upload_manifest = tuple(
    (uploaded_file.file_id, uploaded_file.name, uploaded_file.size)
    for uploaded_file in uploaded_files
)
if st.session_state.get("viewer_upload_manifest") != upload_manifest:
    try:
        stored_pdfs = store_uploaded_pdfs(
            st.session_state["workspace_directory"],
            [
                (uploaded_file.name, uploaded_file.getvalue())
                for uploaded_file in uploaded_files
            ],
            source_name="viewer",
        )
    except ValueError as error:
        st.error(str(error))
        st.stop()

    remove_unlisted_pdfs(
        st.session_state["workspace_directory"],
        stored_pdfs,
    )
    clear_thumbnail_cache()
    clear_page_facts_cache()
    clear_document_session_state()
    st.session_state["workbench_docs"] = stored_pdfs
    st.session_state["viewer_upload_manifest"] = upload_manifest
    st.rerun()

documents = list(st.session_state.get("workbench_docs", []))
if not documents:
    st.info("Open one or more PDFs to view them.")
    st.stop()

if len(documents) == 1:
    selected_document = documents[0]
else:
    documents_by_id = {
        document.document_id: document for document in documents
    }
    selected_document_id = st.selectbox(
        "Document",
        options=list(documents_by_id),
        format_func=lambda document_id: (
            documents_by_id[document_id].display_name
        ),
    )
    selected_document = documents_by_id[selected_document_id]

file_size_bytes = selected_document.path.stat().st_size
if file_size_bytes >= 1_000_000:
    file_size = f"{file_size_bytes / 1_000_000:.1f} MB"
else:
    file_size = f"{file_size_bytes / 1_000:.0f} KB"
st.subheader(selected_document.display_name)
st.caption(f"{selected_document.page_count} pages, {file_size}")
st.caption("Ctrl or Cmd + scroll over the PDF to zoom.")
controls_path = (
    Path(__file__).parents[1]
    / "src/pdf_workbench/pdf_viewer_controls.html"
)
st.html(controls_path, unsafe_allow_javascript=True)
st.pdf(
    selected_document.path,
    height=800,
    key=f"pdf_viewer:{selected_document.document_id}",
)
