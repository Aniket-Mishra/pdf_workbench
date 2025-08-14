import io
import zipfile
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import pdfplumber
import pymupdf as fitz

from .utils import *


def extract_pdf_content_to_memory(
    pdf_bytes: bytes, paper_name: str
) -> Dict[str, bytes]:
    files: Dict[str, bytes] = {}
    base = Path(paper_name)

    with fitz.open(stream=pdf_bytes, filetype="pdf") as pdf_obj:
        for page_num in range(len(pdf_obj)):
            page = pdf_obj.load_page(page_num)
            text = page.get_text()

            # text
            txt_rel = base / "text" / f"{paper_name}_page_{page_num + 1}.txt"
            md_rel = base / "text" / f"{paper_name}_page_{page_num + 1}.md"
            files[str(txt_rel)] = bytes_utf8(text)
            files[str(md_rel)] = bytes_utf8(f"# Page {page_num + 1}\n\n{text}")

            # formulas
            formulas = extract_formulas(text)
            if formulas:
                fmd_rel = (
                    base
                    / "formulas"
                    / f"{paper_name}_page_{page_num + 1}_formulas.md"
                )
                md_block = "# Formulas\n\n" + "\n\n".join(
                    [f"$$\n{f}\n$$" for f in formulas]
                )
                files[str(fmd_rel)] = bytes_utf8(md_block)

            # images
            for img_index, img in enumerate(page.get_images(full=True)):
                xref = img[0]
                base_image = pdf_obj.extract_image(xref)
                image_bytes = base_image["image"]
                image_ext = base_image.get("ext", "png")

                img_rel = (
                    base
                    / "images"
                    / f"{paper_name}_page_{page_num + 1}_img_{img_index + 1}.{image_ext}"
                )
                files[str(img_rel)] = image_bytes

                arr = np.frombuffer(image_bytes, dtype=np.uint8)
                npy_rel = (
                    base
                    / "images"
                    / f"{paper_name}_page_{page_num + 1}_img_{img_index + 1}.npy"
                )
                files[str(npy_rel)] = npy_bytes_from_array(arr)

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as plumber_pdf:
        for page_num, page in enumerate(plumber_pdf.pages):
            tables = page.extract_tables()
            if tables:
                for table_index, table in enumerate(tables):
                    df = pd.DataFrame(table)
                    filename_base = f"{paper_name}_page_{page_num + 1}_table_{table_index + 1}"

                    csv_rel = base / "tables" / f"{filename_base}.csv"
                    files[str(csv_rel)] = df.to_csv(
                        index=False, header=False
                    ).encode("utf-8")

                    try:
                        md_rel = base / "tables" / f"{filename_base}.md"
                        files[str(md_rel)] = bytes_utf8(
                            df.to_markdown(index=False)
                        )
                    except Exception:
                        md_rel = base / "tables" / f"{filename_base}.md"
                        simple = "\n".join(
                            [" | ".join(map(str, row)) for row in table]
                        )
                        files[str(md_rel)] = bytes_utf8(simple)

    # text
    page_txts = []
    idx = 1
    while True:
        key = str(base / "text" / f"{paper_name}_page_{idx}.txt")
        if key not in files:
            break
        page_txts.append(files[key].decode("utf-8"))
        idx += 1

    combined = "\n\n".join(page_txts) if page_txts else ""
    comb_dir = base / "combined_text"
    files[str(comb_dir / f"{paper_name}_combined_all_text.txt")] = bytes_utf8(
        combined
    )
    files[str(comb_dir / f"{paper_name}_combined_all_text.md")] = bytes_utf8(
        f"# {paper_name} Combined Text\n\n{combined}"
    )

    return files


def build_extraction_zip(pdf_items: List[Tuple[str, bytes]]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for label, data in pdf_items:
            paper = sanitize(Path(label).stem)
            files = extract_pdf_content_to_memory(data, paper)
            for rel_path, blob in files.items():
                zf.writestr(str(rel_path), blob)
    return buf.getvalue()
