import io
from typing import Dict, List, Tuple

import pymupdf as fitz  # PyMuPDF


def merge_selected(
    pdfs: List[Tuple[str, bytes]], selections: Dict[str, List[int]]
) -> bytes:
    out = fitz.open()
    for label, data in pdfs:
        with fitz.open(stream=data, filetype="pdf") as doc:
            sel = selections.get(label, [])
            if not sel:
                out.insert_pdf(doc)
            else:
                for pno in sel:
                    out.insert_pdf(doc, from_page=pno, to_page=pno)
    buf = io.BytesIO()
    out.save(buf)
    out.close()
    return buf.getvalue()


def filter_selected_per_file(
    label: str, data: bytes, selected_pages: List[int]
) -> bytes:
    with fitz.open(stream=data, filetype="pdf") as doc_in:
        out = fitz.open()
        if not selected_pages:
            out.insert_pdf(doc_in)
        else:
            for pno in selected_pages:
                out.insert_pdf(doc_in, from_page=pno, to_page=pno)
    buf = io.BytesIO()
    out.save(buf)
    out.close()
    return buf.getvalue()
