import pytest

from src.pdf_workbench.page_ranges import parse_page_range


def test_parse_page_range_supports_pages_ranges_and_end() -> None:
    assert parse_page_range("1-3, 6, 9-end", page_count=10) == [
        0,
        1,
        2,
        5,
        8,
        9,
    ]


def test_parse_page_range_removes_duplicates() -> None:
    assert parse_page_range("1-3, 2, 3-4", page_count=5) == [0, 1, 2, 3]


@pytest.mark.parametrize(
    "page_range",
    ["", "1,,3", "0", "6", "4-2", "one", "1-2-3"],
)
def test_parse_page_range_rejects_invalid_input(page_range: str) -> None:
    with pytest.raises(ValueError):
        parse_page_range(page_range, page_count=5)
