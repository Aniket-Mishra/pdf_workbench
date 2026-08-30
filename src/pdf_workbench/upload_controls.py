import streamlit as st

from src.pdf_workbench.editor_pages import clear_editor_page_cache
from src.pdf_workbench.page_filters import clear_page_facts_cache
from src.pdf_workbench.thumbnails import clear_thumbnail_cache
from src.pdf_workbench.workspace import (
    create_workspace_directory,
    remove_unlisted_pdfs,
    store_uploaded_pdfs,
)


DOCUMENT_STATE_KEYS = (
    "workbench_docs",
    "viewer_selected_document_id",
    "organizer_pages",
    "organizer_source_manifest",
    "organizer_build_action_id",
    "organizer_load_action_id",
    "organizer_loaded_pages",
    "organized_pdf_bytes",
    "text_edits_by_document",
    "edited_pdf_bytes_by_document",
)

DOCUMENT_STATE_PREFIXES = (
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
    "editor_",
)


def clear_document_state() -> None:
    for state_key in DOCUMENT_STATE_KEYS:
        st.session_state.pop(state_key, None)

    for state_key in list(st.session_state):
        if state_key.startswith(DOCUMENT_STATE_PREFIXES):
            del st.session_state[state_key]


def reset_uploaded_documents() -> None:
    workspace_directory = st.session_state.get("workspace_directory")
    if workspace_directory:
        remove_unlisted_pdfs(workspace_directory, [])

    clear_thumbnail_cache()
    clear_editor_page_cache()
    clear_page_facts_cache()
    clear_document_state()
    st.session_state["document_revision"] = (
        st.session_state.get("document_revision", 0) + 1
    )
    st.session_state["pdf_upload_manifest"] = ()
    st.session_state.pop("pdf_upload_widget", None)


def show_upload_controls() -> None:
    if "workspace_directory" not in st.session_state:
        st.session_state["workspace_directory"] = create_workspace_directory()

    uploaded_files = st.file_uploader(
        "Open PDFs",
        type=["pdf"],
        accept_multiple_files=True,
        key="pdf_upload_widget",
    ) or []

    upload_manifest = tuple(
        (uploaded_file.file_id, uploaded_file.name, uploaded_file.size)
        for uploaded_file in uploaded_files
    )
    previous_manifest = st.session_state.get("pdf_upload_manifest", ())

    if uploaded_files and upload_manifest != previous_manifest:
        try:
            stored_pdfs = store_uploaded_pdfs(
                st.session_state["workspace_directory"],
                [
                    (uploaded_file.name, uploaded_file.getvalue())
                    for uploaded_file in uploaded_files
                ],
                source_name="upload",
            )
        except ValueError as error:
            st.error(str(error))
            st.stop()

        remove_unlisted_pdfs(
            st.session_state["workspace_directory"],
            stored_pdfs,
        )
        clear_thumbnail_cache()
        clear_editor_page_cache()
        clear_page_facts_cache()
        clear_document_state()
        st.session_state["document_revision"] = (
            st.session_state.get("document_revision", 0) + 1
        )
        st.session_state["workbench_docs"] = stored_pdfs
        st.session_state["pdf_upload_manifest"] = upload_manifest
        st.rerun()

    documents = st.session_state.get("workbench_docs", [])
    st.button(
        "Reset PDFs",
        on_click=reset_uploaded_documents,
        disabled=not documents,
        width="stretch",
    )
