import io
import zipfile
from pathlib import Path
from typing import Dict, List, Tuple

import streamlit as st
from src.pdf_workbench.basic_ops import *
from src.pdf_workbench.extract import *
from src.pdf_workbench.utils import *

st.set_page_config(page_title="PDF Tools", layout="wide")
st.title("PDF Tools (Merge, Filter, Extract)")
st.caption(
    "Upload one or more PDFs, preview pages, select pages, then **Merge**, **Filter**, or **Extract contents**."
)

uploaded = st.file_uploader(
    "Upload PDF file(s)", type=["pdf"], accept_multiple_files=True
)
if "pdf_store" not in st.session_state:
    st.session_state["pdf_store"] = {}  # {filename: bytes}

if not uploaded:
    st.info("Upload one or more PDF files to begin.")
    st.stop()

pdf_items: List[Tuple[str, bytes]] = []
for f in uploaded:
    label = f.name
    if label not in st.session_state["pdf_store"]:
        st.session_state["pdf_store"][label] = f.getvalue()
    data = st.session_state["pdf_store"][label]
    pdf_items.append((label, data))

docs_for_org = []
for f in uploaded:
    data = f.read()
    docs_for_org.append({"name": f.name, "data": data})

st.session_state["workbench_docs"] = docs_for_org

st.page_link("pages/organizer.py", label="Open Organizer")

c1, c2, c3 = st.columns([1, 1, 1])
merge_top = filter_top = extract_top = False
with c1:
    merge_top = st.button("Create Merged PDF", type="primary", key="merge_top")
with c2:
    filter_top = st.button("Create Filtered PDF(s)", key="filter_top")
with c3:
    extract_top = st.button("Extract Contents (ZIP)", key="extract_top")

# sel_summary = st.empty()
if "total_selected" not in st.session_state:
    st.session_state["total_selected"] = 0

hcol, mcol = st.columns([6, 2], vertical_alignment="center")
with hcol:
    st.subheader("Select Pages")
with mcol:
    sel_summary = st.empty()
    sel_summary.metric("Pages selected", st.session_state["total_selected"])

selections: Dict[str, List[int]] = {}
for idx, (label, data) in enumerate(pdf_items):
    with st.expander(f"{label}", expanded=(len(pdf_items) <= 2)):
        selected = st_page_selector(
            file_label=label, pdf_bytes=data, key_prefix=f"pdf{idx}"
        )
        selections[label] = selected

# total_selected = sum(len(v) for v in selections.values())
# sel_summary.metric("Pages selected", total_selected)
new_total = sum(len(v) for v in selections.values())
if new_total != st.session_state["total_selected"]:
    st.session_state["total_selected"] = new_total
sel_summary.metric("Pages selected", st.session_state["total_selected"])

st.divider()

b1, b2, b3 = st.columns([1, 1, 1])
merge_bot = filter_bot = extract_bot = False
with b1:
    merge_bot = st.button("Create Merged PDF", type="primary", key="merge_bot")
with b2:
    filter_bot = st.button("Create Filtered PDF(s)", key="filter_bot")
with b3:
    extract_bot = st.button("Extract Contents (ZIP)", key="extract_bot")

do_merge = merge_top or merge_bot
do_filter = filter_top or filter_bot
do_extract = extract_top or extract_bot

if do_merge:
    merged_bytes = merge_selected(pdf_items, selections)
    st.success("Merged PDF ready!")
    st.download_button(
        "Download merged.pdf",
        data=merged_bytes,
        file_name="merged.pdf",
        mime="application/pdf",
        key="dl_merge",
    )

if do_filter:
    results = []
    for label, data in pdf_items:
        sel = selections.get(label, [])
        out_bytes = filter_selected_per_file(label, data, sel)
        results.append((label, out_bytes))

    if len(results) == 1:
        label, out_bytes = results[0]
        st.success(f"Filtered PDF for **{label}** ready!")
        st.download_button(
            f"Download {Path(label).stem}_filtered.pdf",
            data=out_bytes,
            file_name=f"{Path(label).stem}_filtered.pdf",
            mime="application/pdf",
            key="dl_filter_single",
        )
    else:
        zbuf = io.BytesIO()
        with zipfile.ZipFile(
            zbuf, "w", compression=zipfile.ZIP_DEFLATED
        ) as zf:
            for label, out_bytes in results:
                zf.writestr(f"{Path(label).stem}_filtered.pdf", out_bytes)
        st.success("Filtered PDFs ready!")
        st.download_button(
            "Download filtered_pdfs.zip",
            data=zbuf.getvalue(),
            file_name="filtered_pdfs.zip",
            mime="application/zip",
            key="dl_filter_zip",
        )

if do_extract:
    st.info(
        "Extracting… this may take a moment for large PDFs with many images/tables."
    )
    zbytes = build_extraction_zip(pdf_items)
    st.success("Extraction complete!")
    st.download_button(
        "Download extracted_contents.zip",
        data=zbytes,
        file_name="extracted_contents.zip",
        mime="application/zip",
        key="dl_extract",
    )

st.divider()
