import pytest

from src.pdf_workbench.text_editor import TextEdit
from src.pdf_workbench.text_editor_component import parse_text_edits


def create_text_edit_value() -> dict:
    return {
        "id": "text-1",
        "page_index": 1,
        "text": "Placed text",
        "font_size": 18,
        "horizontal_position": 0.25,
        "vertical_position": 0.5,
    }


def test_parse_text_edits_accepts_valid_component_value() -> None:
    parsed_text_edits = parse_text_edits(
        [create_text_edit_value()],
        page_count=3,
    )

    assert parsed_text_edits == (
        TextEdit(
            page_index=1,
            text="Placed text",
            font_size=18,
            horizontal_position=0.25,
            vertical_position=0.5,
        ),
    )


@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    [
        ("page_index", 3),
        ("font_size", True),
        ("horizontal_position", float("nan")),
        ("vertical_position", 1.1),
        ("text", "Line one\nLine two"),
    ],
)
def test_parse_text_edits_rejects_invalid_component_values(
    field_name: str,
    invalid_value: object,
) -> None:
    text_edit_value = create_text_edit_value()
    text_edit_value[field_name] = invalid_value

    assert parse_text_edits([text_edit_value], page_count=3) is None


def test_parse_text_edits_accepts_empty_list() -> None:
    assert parse_text_edits([], page_count=3) == ()
