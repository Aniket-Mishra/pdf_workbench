import io
import re

import numpy as np


def sanitize(s: str) -> str:
    s2 = re.sub(r"[^a-zA-Z0-9]+", "_", s).strip("_")
    return s2 or "pdf"


def extract_formulas(text: str) -> list[str]:
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
