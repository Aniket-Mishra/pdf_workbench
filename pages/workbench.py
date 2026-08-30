import io
import zipfile
from pathlib import Path

import streamlit as st

from src.pdf_workbench.basic_ops import (
    export_selected_pages,
    merge_selected,
)
from src.pdf_workbench.page_selector import select_pdf_pages
from src.pdf_workbench.split_controls import show_split_controls
from src.pdf_workbench.workspace import StoredPdf


def show_page_selection(
    stored_pdfs: list[StoredPdf],
) -> dict[str, list[int]]:
    selections: dict[str, list[int]] = {}
    for stored_pdf in stored_pdfs:
        expander_label = (
            f"{stored_pdf.display_name} ({stored_pdf.page_count} pages)"
        )
        with st.expander(
            expander_label,
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
    ("Select pages", "Split PDFs"),
    default="Select pages",
    required=True,
    key="workbench_tabs",
    label_visibility="collapsed",
)

stored_pdfs = list(st.session_state.get("workbench_docs", []))
if not stored_pdfs:
    st.info("Open PDFs in the viewer first.")
    st.stop()

if selected_tool == "Split PDFs":
    st.subheader("Split PDFs", anchor="split-pdfs")
    selections = show_page_selection(stored_pdfs)
    st.divider()
    show_split_controls(stored_pdfs, selections)
    st.stop()

st.subheader("Select pages", anchor="select-pages")
st.caption("No selection uses every page.")
selections = show_page_selection(stored_pdfs)

selected_page_count = sum(
    len(selected_pages) for selected_pages in selections.values()
)
selected_page_label = "page" if selected_page_count == 1 else "pages"
st.caption(f"{selected_page_count} {selected_page_label} selected")

merge_column, save_column, extract_column = st.columns(3)
with merge_column:
    merge_pdf = st.button(
        "Merge PDFs",
        type="primary",
        use_container_width=True,
    )
with save_column:
    save_selected_pages = st.button(
        "Save selected pages",
        use_container_width=True,
    )
with extract_column:
    extract_contents = st.button(
        "Extract contents",
        use_container_width=True,
    )

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
    )

if save_selected_pages:
    if len(stored_pdfs) == 1:
        stored_pdf = stored_pdfs[0]
        selected_pdf = export_selected_pages(
            stored_pdf.path,
            selections.get(stored_pdf.document_id, []),
        )
        download_name = f"{Path(stored_pdf.display_name).stem}_selected.pdf"
        st.download_button(
            f"Download {download_name}",
            data=selected_pdf,
            file_name=download_name,
            mime="application/pdf",
        )
    else:
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(
            zip_buffer,
            "w",
            compression=zipfile.ZIP_DEFLATED,
        ) as zip_file:
            for file_number, stored_pdf in enumerate(
                stored_pdfs,
                1,
            ):
                download_name = (
                    f"{file_number}_{Path(stored_pdf.display_name).stem}"
                    "_selected.pdf"
                )
                selected_pdf = export_selected_pages(
                    stored_pdf.path,
                    selections.get(stored_pdf.document_id, []),
                )
                zip_file.writestr(download_name, selected_pdf)

        st.download_button(
            "Download selected_pages.zip",
            data=zip_buffer.getvalue(),
            file_name="selected_pages.zip",
            mime="application/zip",
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
    )
