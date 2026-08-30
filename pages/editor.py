from collections import Counter
from pathlib import Path

import streamlit as st

from src.pdf_workbench.editor_pages import (
    EDITOR_PAGE_BATCH_SIZE,
    render_editor_pages,
)
from src.pdf_workbench.text_editor import create_edited_pdf
from src.pdf_workbench.text_editor_component import show_text_editor
from src.pdf_workbench.utils import sanitize_filename


st.title("Edit PDFs")
st.caption("Choose Add text, then click anywhere on a page.")

documents = list(st.session_state.get("workbench_docs", []))
if not documents:
    st.info("Open PDFs from the sidebar first.")
    st.stop()

documents_by_id = {
    document.document_id: document for document in documents
}
display_name_counts = Counter(
    document.display_name for document in documents
)
display_name_occurrences: dict[str, int] = {}
document_labels_by_id: dict[str, str] = {}
for document in documents:
    occurrence = display_name_occurrences.get(document.display_name, 0) + 1
    display_name_occurrences[document.display_name] = occurrence
    document_labels_by_id[document.document_id] = document.display_name
    if display_name_counts[document.display_name] > 1:
        document_labels_by_id[document.document_id] = (
            f"{document.display_name} ({occurrence})"
        )

selected_document_id = st.session_state.get(
    "editor_selected_document_id",
    st.session_state.get(
        "viewer_selected_document_id",
        documents[0].document_id,
    ),
)
if selected_document_id not in documents_by_id:
    selected_document_id = documents[0].document_id

if len(documents) > 1:
    selected_document_id = st.selectbox(
        "PDF to edit",
        options=list(documents_by_id),
        index=list(documents_by_id).index(selected_document_id),
        format_func=lambda document_id: document_labels_by_id[document_id],
        key="editor_document_widget",
    )
st.session_state["editor_selected_document_id"] = selected_document_id
selected_document = documents_by_id[selected_document_id]

text_edits_by_document = dict(
    st.session_state.get("text_edits_by_document", {})
)
edited_pdf_bytes_by_document = dict(
    st.session_state.get("edited_pdf_bytes_by_document", {})
)
document_text_edits = list(
    text_edits_by_document.get(selected_document_id, [])
)

loaded_page_count_key = f"editor_loaded_pages:{selected_document_id}"
loaded_page_count = min(
    st.session_state.get(
        loaded_page_count_key,
        EDITOR_PAGE_BATCH_SIZE,
    ),
    selected_document.page_count,
)
rendered_pages = render_editor_pages(
    selected_document.content_hash,
    str(selected_document.path),
    loaded_page_count,
)

with st.container(key="editor_workspace"):
    editor_state = show_text_editor(
        document_id=selected_document_id,
        pages=rendered_pages,
        page_count=selected_document.page_count,
        text_edits=document_text_edits,
        download_ready=selected_document_id in edited_pdf_bytes_by_document,
        key=(
            f"text_editor:{selected_document_id}:"
            f"{st.session_state.get('document_revision', 0)}"
        ),
    )

updated_text_edits = list(editor_state.text_edits)
if updated_text_edits != document_text_edits:
    document_text_edits = updated_text_edits
    text_edits_by_document[selected_document_id] = document_text_edits
    edited_pdf_bytes_by_document.pop(selected_document_id, None)
    st.session_state["text_edits_by_document"] = text_edits_by_document
    st.session_state[
        "edited_pdf_bytes_by_document"
    ] = edited_pdf_bytes_by_document

load_action_key = f"editor_load_action:{selected_document_id}"
new_load_requested = (
    editor_state.action == "load_more"
    and editor_state.action_id is not None
    and editor_state.action_id != st.session_state.get(load_action_key)
)
if new_load_requested:
    st.session_state[load_action_key] = editor_state.action_id
    st.session_state[loaded_page_count_key] = min(
        loaded_page_count + EDITOR_PAGE_BATCH_SIZE,
        selected_document.page_count,
    )
    st.rerun()

build_action_key = f"editor_build_action:{selected_document_id}"
new_build_requested = (
    editor_state.action == "build"
    and editor_state.action_id is not None
    and editor_state.action_id != st.session_state.get(build_action_key)
)
if new_build_requested:
    st.session_state[build_action_key] = editor_state.action_id
    if not document_text_edits:
        st.warning("Add text before creating the PDF.")
    else:
        try:
            with st.spinner("Creating PDF..."):
                edited_pdf_bytes_by_document[selected_document_id] = (
                    create_edited_pdf(
                        selected_document.path,
                        document_text_edits,
                    )
                )
        except ValueError as error:
            st.error(str(error))
        else:
            st.session_state[
                "edited_pdf_bytes_by_document"
            ] = edited_pdf_bytes_by_document
            st.rerun()

edited_pdf_bytes = edited_pdf_bytes_by_document.get(selected_document_id)
if edited_pdf_bytes:
    download_name = (
        f"{sanitize_filename(Path(selected_document.display_name).stem)}"
        "_edited.pdf"
    )
    st.download_button(
        f"Download {download_name}",
        data=edited_pdf_bytes,
        file_name=download_name,
        mime="application/pdf",
        width="stretch",
        on_click="ignore",
    )
