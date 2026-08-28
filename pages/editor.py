from pathlib import Path

import streamlit as st

from src.pdf_workbench.text_editor import (
    MAXIMUM_FONT_SIZE,
    MINIMUM_FONT_SIZE,
    TextEdit,
    create_edited_pdf,
    render_text_preview,
)
from src.pdf_workbench.utils import sanitize_filename


def save_editor_session_state(
    text_edits_by_document: dict[str, list[TextEdit]],
    edited_pdf_bytes_by_document: dict[str, bytes],
) -> None:
    st.session_state["text_edits_by_document"] = text_edits_by_document
    st.session_state[
        "edited_pdf_bytes_by_document"
    ] = edited_pdf_bytes_by_document


st.title("Edit PDFs")
st.caption("Add text to PDFs. Changes stay saved when you switch tools.")

documents = list(st.session_state.get("workbench_docs", []))
if not documents:
    st.info("Open PDFs from the sidebar first.")
    st.stop()

text_edits_by_document = dict(
    st.session_state.get("text_edits_by_document", {})
)
edited_pdf_bytes_by_document = dict(
    st.session_state.get("edited_pdf_bytes_by_document", {})
)
documents_by_id = {
    document.document_id: document for document in documents
}

selected_document_id = st.session_state.get(
    "editor_selected_document_id",
    st.session_state.get(
        "viewer_selected_document_id",
        documents[0].document_id,
    ),
)
if selected_document_id not in documents_by_id:
    selected_document_id = documents[0].document_id

selected_document_id = st.selectbox(
    "PDF to edit",
    options=list(documents_by_id),
    index=list(documents_by_id).index(selected_document_id),
    format_func=lambda document_id: documents_by_id[document_id].display_name,
    key="editor_document_widget",
)
st.session_state["editor_selected_document_id"] = selected_document_id
selected_document = documents_by_id[selected_document_id]
document_edits = list(
    text_edits_by_document.get(selected_document_id, [])
)
edited_document_count = sum(
    bool(text_edits_by_document.get(document.document_id))
    for document in documents
)
if len(documents) > 1 and edited_document_count:
    if edited_document_count == 1:
        st.caption("1 PDF has saved text edits.")
    else:
        st.caption(f"{edited_document_count} PDFs have saved text edits.")

controls_column, preview_column = st.columns([1, 2], gap="large")
with controls_column:
    st.subheader("Add text")

    page_state_key = f"editor_page_index:{selected_document_id}"
    page_widget_key = f"editor_page_widget:{selected_document_id}"
    selected_page_index = min(
        st.session_state.get(page_state_key, 0),
        selected_document.page_count - 1,
    )
    selected_page_number = st.selectbox(
        "Page",
        options=range(1, selected_document.page_count + 1),
        index=selected_page_index,
        key=page_widget_key,
    )
    selected_page_index = selected_page_number - 1
    st.session_state[page_state_key] = selected_page_index

    text_state_key = f"editor_text_value:{selected_document_id}"
    text_widget_key = f"editor_text_widget:{selected_document_id}"
    clear_draft_key = f"editor_clear_draft:{selected_document_id}"
    if st.session_state.pop(clear_draft_key, False):
        st.session_state[text_widget_key] = ""
        st.session_state[text_state_key] = ""
    elif text_widget_key not in st.session_state:
        st.session_state[text_widget_key] = st.session_state.get(
            text_state_key,
            "",
        )
    text = st.text_input("Text", key=text_widget_key)
    st.session_state[text_state_key] = text

    size_state_key = f"editor_size_value:{selected_document_id}"
    size_widget_key = f"editor_size_widget:{selected_document_id}"
    if size_widget_key not in st.session_state:
        st.session_state[size_widget_key] = st.session_state.get(
            size_state_key,
            18,
        )
    font_size = st.slider(
        "Text size",
        min_value=MINIMUM_FONT_SIZE,
        max_value=MAXIMUM_FONT_SIZE,
        key=size_widget_key,
    )
    st.session_state[size_state_key] = font_size

    horizontal_state_key = (
        f"editor_horizontal_value:{selected_document_id}"
    )
    horizontal_widget_key = (
        f"editor_horizontal_widget:{selected_document_id}"
    )
    if horizontal_widget_key not in st.session_state:
        st.session_state[horizontal_widget_key] = st.session_state.get(
            horizontal_state_key,
            10,
        )
    horizontal_position = st.slider(
        "Horizontal position",
        min_value=0,
        max_value=100,
        format="%d%%",
        key=horizontal_widget_key,
    )
    st.session_state[horizontal_state_key] = horizontal_position

    vertical_state_key = f"editor_vertical_value:{selected_document_id}"
    vertical_widget_key = f"editor_vertical_widget:{selected_document_id}"
    if vertical_widget_key not in st.session_state:
        st.session_state[vertical_widget_key] = st.session_state.get(
            vertical_state_key,
            10,
        )
    vertical_position = st.slider(
        "Vertical position",
        min_value=0,
        max_value=100,
        format="%d%%",
        key=vertical_widget_key,
    )
    st.session_state[vertical_state_key] = vertical_position

    pending_edit = TextEdit(
        page_index=selected_page_index,
        text=text.strip(),
        font_size=font_size,
        horizontal_position=horizontal_position / 100,
        vertical_position=vertical_position / 100,
    )

    add_column, undo_column = st.columns(2)
    with add_column:
        add_text = st.button(
            "Add text",
            type="primary",
            disabled=not pending_edit.text,
            width="stretch",
        )
    with undo_column:
        undo_text = st.button(
            "Undo last",
            disabled=not document_edits,
            width="stretch",
        )

    clear_text = st.button(
        "Clear this PDF's edits",
        disabled=not document_edits,
        width="stretch",
    )

include_pending_preview = True
if add_text:
    try:
        render_text_preview(
            selected_document.path,
            selected_page_index,
            [*document_edits, pending_edit],
        )
    except ValueError as error:
        st.error(str(error))
        include_pending_preview = False
    else:
        document_edits.append(pending_edit)
        text_edits_by_document[selected_document_id] = document_edits
        edited_pdf_bytes_by_document.pop(selected_document_id, None)
        save_editor_session_state(
            text_edits_by_document,
            edited_pdf_bytes_by_document,
        )
        st.session_state[clear_draft_key] = True
        st.rerun()

if undo_text:
    document_edits = document_edits[:-1]
    text_edits_by_document[selected_document_id] = document_edits
    edited_pdf_bytes_by_document.pop(selected_document_id, None)
    save_editor_session_state(
        text_edits_by_document,
        edited_pdf_bytes_by_document,
    )
    st.rerun()

if clear_text:
    document_edits = []
    text_edits_by_document.pop(selected_document_id, None)
    edited_pdf_bytes_by_document.pop(selected_document_id, None)
    save_editor_session_state(
        text_edits_by_document,
        edited_pdf_bytes_by_document,
    )
    st.rerun()

save_editor_session_state(
    text_edits_by_document,
    edited_pdf_bytes_by_document,
)

preview_edits = list(document_edits)
if pending_edit.text and include_pending_preview:
    preview_edits.append(pending_edit)

with preview_column:
    st.subheader(f"Page {selected_page_number} preview")
    try:
        preview_bytes = render_text_preview(
            selected_document.path,
            selected_page_index,
            preview_edits,
        )
    except ValueError as error:
        st.warning(str(error))
        preview_bytes = render_text_preview(
            selected_document.path,
            selected_page_index,
            document_edits,
        )
    st.image(preview_bytes, width="stretch")

edit_label = "text edit" if len(document_edits) == 1 else "text edits"
st.caption(
    f"{len(document_edits)} {edit_label} saved for "
    f"{selected_document.display_name}."
)
if document_edits:
    with st.expander("Saved text"):
        for edit_number, text_edit in enumerate(document_edits, 1):
            st.text(
                f"{edit_number}. Page {text_edit.page_index + 1}, "
                f"{text_edit.font_size} pt: {text_edit.text}"
            )

build_edited_pdf = st.button(
    "Build edited PDF",
    disabled=not document_edits,
    width="stretch",
)
if build_edited_pdf:
    with st.spinner("Building PDF..."):
        edited_pdf_bytes_by_document[selected_document_id] = (
            create_edited_pdf(selected_document.path, document_edits)
        )
    save_editor_session_state(
        text_edits_by_document,
        edited_pdf_bytes_by_document,
    )

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
