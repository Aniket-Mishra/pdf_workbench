import pytest

from src.pdf_workbench.page_filters import (
    PageFacts,
    PageFilter,
    filter_page_numbers,
)


PAGE_FACTS = [
    PageFacts(0, "Invoice 1042", 612, 792, "Portrait", "Text"),
    PageFacts(1, "Technical appendix", 792, 612, "Landscape", "Text"),
    PageFacts(2, "", 612, 792, "Portrait", "Scanned"),
    PageFacts(3, "", 612, 792, "Portrait", "Blank"),
]


def test_filter_pages_by_text_and_properties() -> None:
    page_filter = PageFilter(
        text_query="invoice",
        page_types=("Text",),
        orientations=("Portrait",),
        page_sizes=((612, 792),),
    )

    assert filter_page_numbers(PAGE_FACTS, page_filter) == [0]


def test_filter_pages_supports_regular_expressions() -> None:
    page_filter = PageFilter(
        text_query=r"appendix$",
        use_regular_expression=True,
    )

    assert filter_page_numbers(PAGE_FACTS, page_filter) == [1]


def test_filter_pages_rejects_invalid_regular_expression() -> None:
    with pytest.raises(ValueError, match="Invalid regular expression"):
        filter_page_numbers(
            PAGE_FACTS,
            PageFilter(text_query="[", use_regular_expression=True),
        )


def test_empty_filter_returns_every_page() -> None:
    assert filter_page_numbers(PAGE_FACTS, PageFilter()) == [0, 1, 2, 3]
