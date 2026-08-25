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
    st.session_state.pop("organizer_build_action_id", None)
    st.session_state.pop("organized_pdf_bytes", None)

page_placements = list(st.session_state["organizer_pages"])
total_pages = len(page_placements)
st.caption(f"{len(documents)} PDF(s), {total_pages} pages")
thumbnails_by_id = render_organizer_thumbnails(documents, page_references)
show_document_markers = len(documents) > 1
grid_state = show_page_grid(
    pages=[
        PageThumbnail(
            page_id=page.uid,
            image_bytes=thumbnails_by_id[page.uid].image_bytes,
            image_mime_type=thumbnails_by_id[page.uid].mime_type,
            caption=f"Page {page.page_index + 1}",
            document_number=(
                page.document_index + 1 if show_document_markers else None
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
    key=organizer_grid_key,
    reset_order_ids=initial_order,
)

new_build_requested = (
    grid_state.action == "build"
    and grid_state.action_id is not None
    and grid_state.action_id
    != st.session_state.get("organizer_build_action_id")
)
if new_build_requested:
    page_placements = [
        PagePlacement(
            instance_id=page.page_id,
            source_page_id=page.source_page_id,
            rotation=page.rotation,
        )
        for page in grid_state.ordered_pages
    ]
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
