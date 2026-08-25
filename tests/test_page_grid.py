from src.pdf_workbench.page_grid import GridPage, parse_ordered_pages


def test_ordered_pages_allow_copies_of_source_pages() -> None:
    ordered_pages = parse_ordered_pages(
        [
            {"id": "0:0", "source_id": "0:0", "rotation": 90},
            {"id": "copy-1", "source_id": "0:0", "rotation": 180},
        ],
        {"0:0"},
    )

    assert ordered_pages == (
        GridPage("0:0", "0:0", 90),
        GridPage("copy-1", "0:0", 180),
    )


def test_ordered_pages_reject_unknown_sources() -> None:
    assert parse_ordered_pages(
        [{"id": "copy-1", "source_id": "missing", "rotation": 0}],
        {"0:0"},
    ) == ()
