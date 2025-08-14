import io
import re
from typing import List

import numpy as np
import pymupdf as fitz
import streamlit as st


def sanitize(s: str) -> str:
    s2 = re.sub(r"[^a-zA-Z0-9]+", "_", s).strip("_")
    return s2 or "pdf"


def extract_formulas(text: str) -> List[str]:
    math_ind = [
        "=",
        "∑",
        "∫",
        "√",
        "π",
        "\\\\",
        "^",
        "α",
        "β",
        "γ",
        "δ",
        "ε",
        "ζ",
        "η",
        "θ",
        "ι",
        "κ",
        "λ",
        "μ",
        "ν",
        "ξ",
        "ο",
        "π",
        "ρ",
        "σ",
        "τ",
        "υ",
        "φ",
        "χ",
        "ψ",
        "ω",
        "Γ",
        "Δ",
        "Θ",
        "Λ",
        "Ξ",
        "Π",
        "Σ",
        "Φ",
        "Ψ",
        "Ω",
    ]
    formulas = []
    for line in text.splitlines():
        t = line.strip()
        if len(t) > 3 and any(sym in t for sym in math_ind):
            formulas.append(t)
    return formulas


def bytes_utf8(s: str) -> bytes:
    return s.encode("utf-8")


def npy_bytes_from_array(arr: np.ndarray) -> bytes:
    bio = io.BytesIO()
    np.save(bio, arr)
    return bio.getvalue()


def _render_thumbnails_png_bytes(
    pdf_bytes: bytes, zoom: float = 1.5
) -> List[bytes]:
    thumbs: List[bytes] = []
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        mat = fitz.Matrix(zoom, zoom)
        for page in doc:
            pix = page.get_pixmap(matrix=mat, alpha=False)
            thumbs.append(pix.tobytes("png"))
    return thumbs


@st.cache_data(show_spinner=False)
def render_thumbnails_png_bytes(
    pdf_bytes: bytes, zoom: float = 1.5
) -> List[bytes]:
    return _render_thumbnails_png_bytes(pdf_bytes, zoom)


def st_page_selector(
    file_label: str, pdf_bytes: bytes, key_prefix: str
) -> List[int]:
    thumbs_png = render_thumbnails_png_bytes(pdf_bytes)
    num_pages = len(thumbs_png)

    # init checkbox state
    for i in range(num_pages):
        k = f"{key_prefix}_p{i}"
        if k not in st.session_state:
            st.session_state[k] = False

    st.markdown(f"**{file_label}** — {num_pages} page(s)")
    left, right = st.columns([1, 1])
    with left:
        if st.button("Select all", key=f"{key_prefix}_select_all"):
            for i in range(num_pages):
                st.session_state[f"{key_prefix}_p{i}"] = True
            st.rerun()
    with right:
        if st.button("Clear all", key=f"{key_prefix}_clear_all"):
            for i in range(num_pages):
                st.session_state[f"{key_prefix}_p{i}"] = False
            st.rerun()

    cols_per_row = 4
    with st.container(height=600, border=True):
        for row_start in range(0, num_pages, cols_per_row):
            cols = st.columns(cols_per_row, vertical_alignment="top")
            for offset in range(cols_per_row):
                idx = row_start + offset
                if idx >= num_pages:
                    continue
                with cols[offset]:
                    st.image(
                        thumbs_png[idx],
                        caption=f"Page {idx + 1}",
                        use_container_width=True,
                    )
                    st.checkbox("Select", key=f"{key_prefix}_p{idx}")

    return [
        i
        for i in range(num_pages)
        if st.session_state.get(f"{key_prefix}_p{i}", False)
    ]
