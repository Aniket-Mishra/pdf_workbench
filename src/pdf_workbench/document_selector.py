from collections import Counter

import streamlit as st

from src.pdf_workbench.workspace import StoredPdf


def select_document(
    documents: list[StoredPdf],
    state_key: str,
    label: str,
) -> StoredPdf:
    """Show a document picker when several PDFs are open.

    The chosen id is kept in session state so the viewer and editor
    can share it.
    """
    documents_by_id = {
        document.document_id: document for document in documents
    }
    selected_id = st.session_state.get(state_key)
    if selected_id not in documents_by_id:
        selected_id = st.session_state.get("viewer_selected_document_id")
    if selected_id not in documents_by_id:
        selected_id = documents[0].document_id

    if len(documents) > 1:
        labels_by_id = label_documents(documents)
        selected_id = st.selectbox(
            label,
            options=list(documents_by_id),
            index=list(documents_by_id).index(selected_id),
            format_func=labels_by_id.__getitem__,
            key=f"{state_key}_widget",
        )

    st.session_state[state_key] = selected_id
    return documents_by_id[selected_id]


def label_documents(documents: list[StoredPdf]) -> dict[str, str]:
    """Number duplicate file names so the picker stays unambiguous."""
    name_counts = Counter(document.display_name for document in documents)
    seen: Counter[str] = Counter()
    labels_by_id: dict[str, str] = {}
    for document in documents:
        seen[document.display_name] += 1
        label = document.display_name
        if name_counts[document.display_name] > 1:
            label = f"{label} ({seen[document.display_name]})"
        labels_by_id[document.document_id] = label
    return labels_by_id
