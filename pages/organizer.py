import streamlit as st

from src.pdf_workbench.organizer import (
    PagePlacement,
    build_page_references,
    create_initial_page_placements,
    merge_pages_in_order,
    render_organizer_thumbnails,
)
from src.pdf_workbench.page_grid import (
    GridPage,
    PageThumbnail,
    show_page_grid,
)
from src.pdf_workbench.thumbnails import THUMBNAIL_BATCH_SIZE
from src.pdf_workbench.workspace import create_source_manifest

st.title("Organize pages")
st.caption("Click pages to select actions. Drag pages into place.")
documents = list(st.session_state.get("workbench_docs", []))
if not documents:
    st.info("Open PDFs in the viewer first.")
    st.stop()

page_references = build_page_references(documents)
initial_placements = create_initial_page_placements(page_references)
initial_order = [page.instance_id for page in initial_placements]
source_manifest = create_source_manifest(documents)
organizer_grid_key = "organizer_grid:" + "|".join(source_manifest)

if (
    st.session_state.get("organizer_source_manifest") != source_manifest
    or "organizer_pages" not in st.session_state
):
    st.session_state["organizer_pages"] = initial_placements
    st.session_state["organizer_source_manifest"] = source_manifest
    st.session_state["organizer_loaded_pages"] = min(
        THUMBNAIL_BATCH_SIZE,
        len(initial_placements),
    )
    st.session_state.pop("organizer_build_action_id", None)
    st.session_state.pop("organizer_load_action_id", None)
    st.session_state.pop("organized_pdf_bytes", None)

page_placements = list(st.session_state["organizer_pages"])
total_pages = len(page_placements)
loaded_page_count = min(
    st.session_state.get("organizer_loaded_pages", THUMBNAIL_BATCH_SIZE),
    total_pages,
)
st.caption(f"{len(documents)} PDF(s), {total_pages} pages")
visible_source_ids = {
    page.source_page_id for page in page_placements[:loaded_page_count]
}
visible_page_references = [
    page for page in page_references if page.uid in visible_source_ids
]
thumbnails_by_id = render_organizer_thumbnails(
    documents,
    visible_page_references,
)
show_document_markers = len(documents) > 1
with st.container(key="organizer_workspace"):
    grid_state = show_page_grid(
        pages=[
            PageThumbnail(
                page_id=page.uid,
                image_bytes=(
                    thumbnails_by_id[page.uid].image_bytes
                    if page.uid in thumbnails_by_id
                    else None
                ),
                image_mime_type=(
                    thumbnails_by_id[page.uid].mime_type
                    if page.uid in thumbnails_by_id
                    else "image/png"
                ),
                caption=f"Page {page.page_index + 1}",
                document_number=(
                    page.document_index + 1
                    if show_document_markers
                    else None
                ),
                document_name=(
                    documents[page.document_index].display_name
                    if show_document_markers
                    else None
                ),
            )
            for page in page_references
        ],
        ordered_pages=[
            GridPage(
                page_id=page.instance_id,
                source_page_id=page.source_page_id,
                rotation=page.rotation,
            )
            for page in page_placements
        ],
        selected_ids=set(),
        selectable=True,
        reorderable=True,
        visible_page_count=loaded_page_count,
        key=organizer_grid_key,
        reset_order_ids=initial_order,
    )

updated_page_placements = [
    PagePlacement(
        instance_id=page.page_id,
        source_page_id=page.source_page_id,
        rotation=page.rotation,
    )
    for page in grid_state.ordered_pages
]
new_load_requested = (
    grid_state.action == "load_more"
    and grid_state.action_id is not None
    and grid_state.action_id
    != st.session_state.get("organizer_load_action_id")
)
if new_load_requested:
    st.session_state["organizer_pages"] = updated_page_placements
    st.session_state["organizer_loaded_pages"] = min(
        loaded_page_count + THUMBNAIL_BATCH_SIZE,
        len(updated_page_placements),
    )
    st.session_state["organizer_load_action_id"] = grid_state.action_id
    st.rerun()

new_build_requested = (
    grid_state.action == "build"
    and grid_state.action_id is not None
    and grid_state.action_id
    != st.session_state.get("organizer_build_action_id")
)
if new_build_requested:
    page_placements = updated_page_placements
    st.session_state["organizer_pages"] = page_placements
    with st.spinner("Building PDF..."):
        st.session_state["organized_pdf_bytes"] = merge_pages_in_order(
            documents,
            page_placements,
        )
    st.session_state["organizer_build_action_id"] = grid_state.action_id

organized_pdf_bytes = st.session_state.get("organized_pdf_bytes")
if organized_pdf_bytes:
    st.download_button(
        "Download organized.pdf",
        data=organized_pdf_bytes,
        file_name="organized.pdf",
        mime="application/pdf",
        use_container_width=True,
        on_click="ignore",
    )
