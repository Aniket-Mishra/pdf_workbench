from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import pymupdf as fitz  # PyMuPDF
import streamlit as st
from streamlit_sortables import sort_items  # ohtaman API

st.set_page_config(page_title="PDF Organizer", layout="wide")

st.title("Organizer - reorderer")
st.caption(
    "Drag pages between the lists on the left (one list per PDF). "
    "The right panel shows thumbnails in the merged order."
)


@dataclass(frozen=True)
class PageRef:
    doc_idx: int
    page_idx: int
    label: str
    uid: str


@dataclass
class DocBlob:
    name: str
    data: bytes
    pages: int


@st.cache_data(show_spinner=False)
def _read_doc(bytes_: bytes) -> int:
    with fitz.open(stream=bytes_, filetype="pdf") as doc:
        return len(doc)


@st.cache_data(show_spinner=False)
def _make_thumb(
    bytes_: bytes,
    page_idx: int,
    max_w: int = 200,
    gray: bool = True,
    scale_base: float = 1.1,
) -> bytes:
    with fitz.open(stream=bytes_, filetype="pdf") as doc:
        page = doc[page_idx]
        mat = fitz.Matrix(scale_base, scale_base)
        if gray:
            pix = page.get_pixmap(
                matrix=mat, colorspace=fitz.csGRAY, alpha=False
            )
        else:
            pix = page.get_pixmap(matrix=mat, alpha=False)
        if pix.width > max_w:
            scale = max_w / pix.width
            mat2 = fitz.Matrix(scale, scale)
            if gray:
                pix = page.get_pixmap(
                    matrix=mat * mat2, colorspace=fitz.csGRAY, alpha=False
                )
            else:
                pix = page.get_pixmap(matrix=mat * mat2, alpha=False)
        return pix.tobytes("png")


def _build_page_refs(docs: List[DocBlob]) -> List[PageRef]:
    refs: List[PageRef] = []
    for di, d in enumerate(docs):
        for pi in range(d.pages):
            uid = f"{di}:{pi}"
            refs.append(
                PageRef(
                    doc_idx=di,
                    page_idx=pi,
                    label=f"{d.name} • p{pi + 1}",
                    uid=uid,
                )
            )
    return refs


def _merge_in_order(docs: List[DocBlob], order_uids: List[str]) -> bytes:
    out = fitz.open()
    opened: Dict[int, fitz.Document] = {}
    try:
        for uid in order_uids:
            di, pi = map(int, uid.split(":"))
            if di not in opened:
                opened[di] = fitz.open(stream=docs[di].data, filetype="pdf")
            out.insert_pdf(opened[di], from_page=pi, to_page=pi)
        buf = out.tobytes()
    finally:
        out.close()
        for d in opened.values():
            d.close()
    return buf


st.sidebar.subheader("Upload (Organizer)")
org_files = st.sidebar.file_uploader(
    "Add PDFs for organizing or use uploaded files",
    type=["pdf"],
    accept_multiple_files=True,
    key="org_upload",
)

thumb_w = st.sidebar.slider("Thumbnail width (px)", 120, 320, 200, step=10)
gray = st.sidebar.checkbox("Grayscale thumbnails (faster)", value=True)
scale_base = st.sidebar.slider(
    "Render scale (lower = faster)", 0.8, 2.0, 1.1, step=0.1
)
max_thumbs = st.sidebar.number_input(
    "Max thumbnails to render", 12, 600, 120, step=12
)
window_start = st.sidebar.number_input(
    "Visible window start index", 0, 100000, 0, step=12
)

docs: List[DocBlob] = []

preloaded = st.session_state.get("workbench_docs", [])
for it in preloaded:
    try:
        name, data = it["name"], it["data"]
        docs.append(DocBlob(name=name, data=data, pages=_read_doc(data)))
    except Exception:
        pass

if org_files:
    for f in org_files:
        data = f.read()
        docs.append(DocBlob(name=f.name, data=data, pages=_read_doc(data)))

if not docs:
    st.info(
        "Upload PDFs here (or load some on the main page) to start organizing."
    )
    st.stop()

st.success(
    f"Loaded {len(docs)} document(s), total pages: {sum(d.pages for d in docs)}"
)
with st.expander("Documents loaded", expanded=False):
    for i, d in enumerate(docs):
        st.write(f"**{i + 1}. {d.name}** — {d.pages} page(s)")

st.divider()

st.subheader(
    "Arrange: drag between lists to see merged preview. I am still working on making the thumbnails draggable."
)

page_refs = _build_page_refs(docs)
uid_to_meta: Dict[str, PageRef] = {pr.uid: pr for pr in page_refs}


def _initial_containers() -> List[Dict]:
    containers: List[Dict] = []
    for di, d in enumerate(docs):
        items = [f"{di}:{pi} | {d.name} • p{pi + 1}" for pi in range(d.pages)]
        containers.append({"header": f"{d.name}", "items": items})
    return containers


if "org_containers" not in st.session_state:
    st.session_state.org_containers = _initial_containers()

left, right = st.columns([1, 2], gap="large")

with left:
    st.markdown("**Drag items across containers**")
    sorted_containers = sort_items(
        st.session_state.org_containers,
        multi_containers=True,  # ← per ohtaman docs
        custom_style="",  # you can theme this if you like
        key="organizer_multi",
    )
    # Persist so the right preview/merge reflects current order
    st.session_state.org_containers = sorted_containers

# Flatten containers → ordered uids
ordered_uids: List[str] = []
for c in st.session_state.org_containers:
    for s in c["items"]:
        uid = s.split(" | ", 1)[0]
        ordered_uids.append(uid)

with right:
    st.markdown("**Merged order preview (thumbnails)**")
    total = len(ordered_uids)
    start = min(window_start, max(0, total - 1))
    end = min(start + int(max_thumbs), total)
    st.caption(f"Rendering thumbnails {start + 1}–{end} of {total}")

    cols = st.slider("Preview columns", 2, 8, 5, key="preview_cols")

    def chunk(seq, n):
        for i in range(0, len(seq), n):
            yield seq[i : i + n]

    visible = ordered_uids[start:end]
    for row in chunk(visible, cols):
        ccols = st.columns(len(row))
        for j, uid in enumerate(row):
            pr = uid_to_meta[uid]
            png = _make_thumb(
                docs[pr.doc_idx].data,
                pr.page_idx,
                max_w=thumb_w,
                gray=gray,
                scale_base=scale_base,
            )
            ccols[j].image(png, caption=pr.label, use_container_width=True)

st.divider()

ca, cb, _ = st.columns([1, 1, 5])
with ca:
    if st.button("Reset lists", use_container_width=True):
        st.session_state.org_containers = _initial_containers()
        st.rerun()

with cb:
    build = st.button(
        "Build & Download", type="primary", use_container_width=True
    )

if build:
    if not ordered_uids:
        st.error("No pages selected.")
        st.stop()
    with st.spinner("Assembling your PDF..."):
        merged = _merge_in_order(docs, ordered_uids)
    st.success("Done! Download your organized PDF below.")
    st.download_button(
        "Download organized.pdf",
        data=merged,
        file_name="organized.pdf",
        mime="application/pdf",
        use_container_width=True,
    )
