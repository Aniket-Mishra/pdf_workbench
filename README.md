# PDF Workbench

Local, browser-based PDF tools built on Streamlit and PyMuPDF. Files never leave your machine.

- **Viewer**: read PDFs, ctrl/cmd + scroll to zoom.
- **Editor**: click anywhere on a page to add text, then download the result.
- **Workbench**: pick pages with thumbnails, search and filters, then merge, save a selection, split by ranges / every N pages / selected pages, or extract text, tables, formulas and images to a zip.
- **Organizer**: drag pages across PDFs into a new order, rotate, duplicate, delete, then build one PDF.

## Run

```sh
uv sync
uv run streamlit run app.py
```

## Test

```sh
uv run pytest
```

## Layout

- `app.py` sets up navigation and the sidebar uploader.
- `pages/` holds one script per screen.
- `src/pdf_workbench/` holds the PDF operations (`basic_ops`, `split`, `organizer`, `text_editor`, `extract`) and the Streamlit controls that drive them (`*_controls.py`, `page_selector.py`).
- `page_grid_frontend/` and `text_editor_frontend/` are the two custom components, plain HTML/CSS/JS with no build step.
