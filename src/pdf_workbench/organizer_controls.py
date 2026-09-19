import streamlit as st

from src.pdf_workbench.organizer import (
    list_page_ids,
    merge_pages_in_order,
    render_organizer_thumbnails,
    split_page_id,
)
from src.pdf_workbench.page_grid import (
    GRID_LOAD_BATCH_SIZE,
    GridPage,
    PageThumbnail,
    show_page_grid,
)
from src.pdf_workbench.workspace import StoredPdf, create_source_manifest


def show_organizer(documents: list[StoredPdf]) -> None:
    st.caption("Click to select pages, drag to reorder.")

    page_ids = list_page_ids(documents)
    source_manifest = create_source_manifest(documents)
    if (
        st.session_state.get("organizer_source_manifest") != source_manifest
        or "organizer_pages" not in st.session_state
    ):
        st.session_state["organizer_source_manifest"] = source_manifest
        st.session_state["organizer_pages"] = [
            GridPage(page_id, page_id) for page_id in page_ids
        ]
        st.session_state["organizer_loaded_pages"] = min(
            GRID_LOAD_BATCH_SIZE,
            len(page_ids),
        )
        st.session_state.pop("organized_pdf_bytes", None)

    ordered_pages: list[GridPage] = st.session_state["organizer_pages"]
    loaded_page_count = min(
        st.session_state["organizer_loaded_pages"],
        len(ordered_pages),
    )
    document_label = "PDF" if len(documents) == 1 else "PDFs"
    st.caption(
        f"{len(documents)} {document_label}, {len(ordered_pages)} pages"
    )

    thumbnails_by_id = render_organizer_thumbnails(
        documents,
        {page.source_page_id for page in ordered_pages[:loaded_page_count]},
    )
    show_document_markers = len(documents) > 1
    pages: list[PageThumbnail] = []
    for page_id in page_ids:
        document_index, page_index = split_page_id(page_id)
        thumbnail = thumbnails_by_id.get(page_id)
        pages.append(
            PageThumbnail(
                page_id=page_id,
                caption=f"Page {page_index + 1}",
                image_url=thumbnail.image_url if thumbnail else None,
                document_number=(
                    document_index + 1 if show_document_markers else None
                ),
                document_name=(
                    documents[document_index].display_name
                    if show_document_markers
                    else None
                ),
            )
        )

    with st.container(key="organizer_workspace"):
        grid_state = show_page_grid(
            pages=pages,
            ordered_pages=ordered_pages,
            selected_ids=set(),
            selectable=True,
            reorderable=True,
            visible_page_count=loaded_page_count,
            key="organizer_grid:" + "|".join(source_manifest),
        )

    updated_pages = list(grid_state.ordered_pages)
    if grid_state.action == "load_more":
        st.session_state["organizer_pages"] = updated_pages
        st.session_state["organizer_loaded_pages"] = min(
            loaded_page_count + GRID_LOAD_BATCH_SIZE,
            len(updated_pages),
        )
        st.rerun()

    if grid_state.action == "build":
        st.session_state["organizer_pages"] = updated_pages
        with st.spinner("Building PDF..."):
            st.session_state["organized_pdf_bytes"] = merge_pages_in_order(
                documents,
                updated_pages,
            )

    organized_pdf_bytes = st.session_state.get("organized_pdf_bytes")
    if organized_pdf_bytes:
        st.download_button(
            "Download organized.pdf",
            data=organized_pdf_bytes,
            file_name="organized.pdf",
            mime="application/pdf",
            width="stretch",
            on_click="ignore",
        )
