import io
import zipfile
from pathlib import Path

import streamlit as st

from src.pdf_workbench.basic_ops import export_selected_pages, merge_selected
from src.pdf_workbench.organizer_controls import show_organizer
from src.pdf_workbench.page_selector import select_pdf_pages
from src.pdf_workbench.split_controls import SPLIT_MODES, show_split_controls
from src.pdf_workbench.workspace import StoredPdf


def show_page_selection(stored_pdfs: list[StoredPdf]) -> dict[str, list[int]]:
    selections: dict[str, list[int]] = {}
    for stored_pdf in stored_pdfs:
        with st.expander(
            f"{stored_pdf.display_name} ({stored_pdf.page_count} pages)",
            expanded=len(stored_pdfs) <= 2,
        ):
            selections[stored_pdf.document_id] = select_pdf_pages(
                pdf_path=stored_pdf.path,
                content_hash=stored_pdf.content_hash,
                document_id=stored_pdf.document_id,
                page_count=stored_pdf.page_count,
            )
    return selections


st.title("Workbench")
selected_tool = st.segmented_control(
    "Workbench tool",
    ("Select pages", "Split PDFs", "Organizer"),
    default="Select pages",
    required=True,
    key="workbench_tabs",
    label_visibility="collapsed",
)

stored_pdfs = list(st.session_state.get("workbench_docs", []))
if not stored_pdfs:
    st.info("Open PDFs from the sidebar first.")
    st.stop()

if selected_tool == "Organizer":
    show_organizer(stored_pdfs)
    st.stop()

if selected_tool == "Split PDFs":
    split_mode = st.selectbox("Split mode", SPLIT_MODES)
    selections = {}
    if split_mode == "Selected pages":
        selections = show_page_selection(stored_pdfs)
    show_split_controls(stored_pdfs, selections, split_mode)
    st.stop()

st.caption("A PDF with no pages selected uses all of its pages.")
selections = show_page_selection(stored_pdfs)

selected_page_count = sum(len(pages) for pages in selections.values())
page_label = "page" if selected_page_count == 1 else "pages"
st.caption(f"{selected_page_count} {page_label} selected")

merge_column, save_column, extract_column = st.columns(3)
can_merge = len(stored_pdfs) >= 2
merge_pdf = merge_column.button(
    "Merge PDFs",
    type="primary",
    width="stretch",
    disabled=not can_merge,
    help=None if can_merge else "Open two or more PDFs to merge them.",
)
save_selected_pages = save_column.button(
    "Save selected pages", width="stretch"
)
extract_contents = extract_column.button("Extract contents", width="stretch")

if merge_pdf:
    merged_pdf = merge_selected(
        [
            (stored_pdf.document_id, stored_pdf.path)
            for stored_pdf in stored_pdfs
        ],
        selections,
    )
    st.download_button(
        "Download merged.pdf",
        data=merged_pdf,
        file_name="merged.pdf",
        mime="application/pdf",
        width="stretch",
        on_click="ignore",
    )

if save_selected_pages:
    if len(stored_pdfs) == 1:
        stored_pdf = stored_pdfs[0]
        download_name = f"{Path(stored_pdf.display_name).stem}_selected.pdf"
        st.download_button(
            f"Download {download_name}",
            data=export_selected_pages(
                stored_pdf.path,
                selections.get(stored_pdf.document_id, []),
            ),
            file_name=download_name,
            mime="application/pdf",
            width="stretch",
            on_click="ignore",
        )
    else:
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(
            zip_buffer, "w", zipfile.ZIP_DEFLATED
        ) as zip_file:
            for file_number, stored_pdf in enumerate(stored_pdfs, 1):
                file_stem = Path(stored_pdf.display_name).stem
                zip_file.writestr(
                    f"{file_number}_{file_stem}_selected.pdf",
                    export_selected_pages(
                        stored_pdf.path,
                        selections.get(stored_pdf.document_id, []),
                    ),
                )
        st.download_button(
            "Download selected_pages.zip",
            data=zip_buffer.getvalue(),
            file_name="selected_pages.zip",
            mime="application/zip",
            width="stretch",
            on_click="ignore",
        )

if extract_contents:
    # Table extraction has heavy imports, so load it only for this action.
    from src.pdf_workbench.extract import build_extraction_zip

    with st.spinner("Extracting contents..."):
        extraction_zip = build_extraction_zip(
            [
                (stored_pdf.display_name, stored_pdf.path)
                for stored_pdf in stored_pdfs
            ]
        )
    st.download_button(
        "Download extracted_contents.zip",
        data=extraction_zip,
        file_name="extracted_contents.zip",
        mime="application/zip",
        width="stretch",
        on_click="ignore",
    )
