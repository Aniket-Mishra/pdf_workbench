from pathlib import Path

import streamlit as st

from src.pdf_workbench.document_selector import select_document
from src.pdf_workbench.marks import Mark
from src.pdf_workbench.page_images import (
    EDITOR_PAGE_WIDTH,
    RENDER_BATCH_SIZE,
    render_pages,
)
from src.pdf_workbench.text_editor import create_edited_pdf
from src.pdf_workbench.text_editor_component import show_text_editor
from src.pdf_workbench.utils import sanitize_filename


st.title("Edit PDFs")

documents = list(st.session_state.get("workbench_docs", []))
if not documents:
    st.info("Open PDFs from the sidebar first.")
    st.stop()

document = select_document(
    documents, "editor_selected_document_id", "PDF to edit"
)
document_id = document.document_id

text_edits_by_document = st.session_state.setdefault(
    "text_edits_by_document", {}
)
marks_by_document = st.session_state.setdefault("marks_by_document", {})
edited_pdf_by_document = st.session_state.setdefault(
    "edited_pdf_bytes_by_document", {}
)
text_edits = list(text_edits_by_document.get(document_id, []))
marks: list[Mark] = list(marks_by_document.get(document_id, []))

loaded_pages_key = f"editor_loaded_pages:{document_id}"
loaded_page_count = min(
    st.session_state.get(loaded_pages_key, RENDER_BATCH_SIZE),
    document.page_count,
)
rendered_pages = render_pages(
    document.content_hash,
    str(document.path),
    tuple(range(loaded_page_count)),
    EDITOR_PAGE_WIDTH,
)

with st.container(key="editor_workspace"):
    editor_state = show_text_editor(
        document_id=document_id,
        pages=rendered_pages,
        page_count=document.page_count,
        text_edits=text_edits,
        marks=marks,
        download_ready=document_id in edited_pdf_by_document,
        key=(
            f"text_editor:{document_id}:"
            f"{st.session_state.get('document_revision', 0)}"
        ),
    )

updated_text_edits = list(editor_state.text_edits)
updated_marks = list(editor_state.marks)
if updated_text_edits != text_edits or updated_marks != marks:
    text_edits = updated_text_edits
    marks = updated_marks
    text_edits_by_document[document_id] = text_edits
    marks_by_document[document_id] = marks
    edited_pdf_by_document.pop(document_id, None)

if editor_state.action == "load_more":
    st.session_state[loaded_pages_key] = min(
        loaded_page_count + RENDER_BATCH_SIZE,
        document.page_count,
    )
    st.rerun()

if editor_state.action == "build":
    if not text_edits and not marks:
        st.warning("Add text or a drawing before creating the PDF.")
    else:
        try:
            with st.spinner("Creating PDF..."):
                edited_pdf_by_document[document_id] = create_edited_pdf(
                    document.path,
                    text_edits,
                    marks,
                )
        except ValueError as error:
            st.error(str(error))
        else:
            st.rerun()

edited_pdf_bytes = edited_pdf_by_document.get(document_id)
if edited_pdf_bytes:
    download_name = (
        f"{sanitize_filename(Path(document.display_name).stem)}_edited.pdf"
    )
    st.download_button(
        f"Download {download_name}",
        data=edited_pdf_bytes,
        file_name=download_name,
        mime="application/pdf",
        width="stretch",
        on_click="ignore",
    )
