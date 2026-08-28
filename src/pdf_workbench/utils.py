import re
from io import BytesIO

import numpy as np


FORMULA_SYMBOLS = (
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
)


def sanitize_filename(filename: str) -> str:
    safe_filename = re.sub(r"[^a-zA-Z0-9]+", "_", filename).strip("_")
    return safe_filename or "pdf"


def extract_formulas(text: str) -> list[str]:
    formulas: list[str] = []
    for line in text.splitlines():
        stripped_line = line.strip()
        if len(stripped_line) > 3 and any(
            symbol in stripped_line for symbol in FORMULA_SYMBOLS
        ):
            formulas.append(stripped_line)
    return formulas


def encode_text(text: str) -> bytes:
    return text.encode("utf-8")


def encode_numpy_array(array: np.ndarray) -> bytes:
    output_buffer = BytesIO()
    np.save(output_buffer, array)
    return output_buffer.getvalue()
