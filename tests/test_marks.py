from pathlib import Path
from tempfile import TemporaryDirectory

import pymupdf
import pytest

from src.pdf_workbench.marks import (
    FILL_OPACITY,
    MAXIMUM_MARKS,
    MAXIMUM_POINTS,
    BoxMark,
    PencilMark,
    parse_marks,
    serialize_marks,
)
from src.pdf_workbench.text_editor import TextEdit, create_edited_pdf


def create_pdf_file(pdf_path: Path, page_count: int = 1) -> None:
    document = pymupdf.open()
    try:
        for page_number in range(page_count):
            page = document.new_page()
            page.insert_text((72, 72), f"Page {page_number + 1}")
        document.save(pdf_path)
    finally:
        document.close()


def create_box_value() -> dict:
    return {
        "page_index": 0,
        "kind": "box",
        "color": "#ff0000",
        "line_width": 3,
        "filled": True,
        "horizontal_position": 0.1,
        "vertical_position": 0.2,
        "width": 0.3,
        "height": 0.4,
    }


def create_pencil_value() -> dict:
    return {
        "page_index": 0,
        "kind": "pencil",
        "color": "#000000",
        "line_width": 2,
        "filled": False,
        "points": [[0.2, 0.2], [0.4, 0.5], [0.6, 0.3]],
    }


def test_create_edited_pdf_draws_box_and_keeps_text() -> None:
    with TemporaryDirectory() as temporary_directory_name:
        pdf_path = Path(temporary_directory_name) / "source.pdf"
        create_pdf_file(pdf_path)
        box_mark = parse_marks([create_box_value()], page_count=1)[0]

        output_bytes = create_edited_pdf(
            pdf_path,
            [
                TextEdit(
                    page_index=0,
                    text="Still here",
                    font_size=18,
                    horizontal_position=0.1,
                    vertical_position=0.1,
                )
            ],
            [box_mark],
        )

    with pymupdf.open(stream=output_bytes, filetype="pdf") as document:
        page = document[0]
        drawing = page.get_drawings()[0]
        assert "Still here" in page.get_text()
        assert drawing["type"] == "fs"
        assert drawing["color"] == pytest.approx((1, 0, 0))
        assert drawing["fill"] == pytest.approx((1, 0, 0))
        assert drawing["fill_opacity"] == pytest.approx(FILL_OPACITY)
        assert drawing["width"] == pytest.approx(3)
        assert drawing["rect"].x0 == pytest.approx(page.rect.width * 0.1)
        assert drawing["rect"].y0 == pytest.approx(page.rect.height * 0.2)
        assert drawing["rect"].x1 == pytest.approx(page.rect.width * 0.4)
        assert drawing["rect"].y1 == pytest.approx(page.rect.height * 0.6)


def test_create_edited_pdf_draws_pencil_stroke() -> None:
    with TemporaryDirectory() as temporary_directory_name:
        pdf_path = Path(temporary_directory_name) / "source.pdf"
        create_pdf_file(pdf_path)
        pencil_mark = parse_marks([create_pencil_value()], page_count=1)[0]

        output_bytes = create_edited_pdf(pdf_path, [], [pencil_mark])

    with pymupdf.open(stream=output_bytes, filetype="pdf") as document:
        drawing = document[0].get_drawings()[0]
        assert drawing["type"] == "s"
        assert drawing["fill"] is None
        assert drawing["width"] == pytest.approx(2)
        assert len(drawing["items"]) == 2


def test_create_edited_pdf_draws_on_rotated_page() -> None:
    with TemporaryDirectory() as temporary_directory_name:
        pdf_path = Path(temporary_directory_name) / "rotated.pdf"
        create_pdf_file(pdf_path)
        with pymupdf.open(pdf_path) as document:
            document[0].set_rotation(90)
            document.saveIncr()

        output_bytes = create_edited_pdf(
            pdf_path,
            [],
            [parse_marks([create_pencil_value()], page_count=1)[0]],
        )

    with pymupdf.open(stream=output_bytes, filetype="pdf") as document:
        assert document[0].rotation == 0
        assert len(document[0].get_drawings()) == 1


def test_create_edited_pdf_requires_text_or_drawing() -> None:
    with TemporaryDirectory() as temporary_directory_name:
        pdf_path = Path(temporary_directory_name) / "source.pdf"
        create_pdf_file(pdf_path)

        with pytest.raises(ValueError, match="before creating"):
            create_edited_pdf(pdf_path, [])


def test_parse_marks_round_trips_box_and_pencil() -> None:
    parsed_marks = parse_marks(
        [create_box_value(), create_pencil_value()],
        page_count=1,
    )

    assert parsed_marks == (
        BoxMark(
            page_index=0,
            color=(1.0, 0.0, 0.0),
            line_width=3,
            filled=True,
            horizontal_position=0.1,
            vertical_position=0.2,
            width=0.3,
            height=0.4,
        ),
        PencilMark(
            page_index=0,
            color=(0.0, 0.0, 0.0),
            line_width=2,
            filled=False,
            points=((0.2, 0.2), (0.4, 0.5), (0.6, 0.3)),
        ),
    )
    assert parse_marks(serialize_marks(parsed_marks), page_count=1) == parsed_marks


@pytest.mark.parametrize(
    "mark_value",
    [
        {**create_box_value(), "color": "red"},
        {**create_box_value(), "line_width": True},
        {**create_box_value(), "filled": 1},
        {**create_box_value(), "width": 0},
        {**create_box_value(), "horizontal_position": 0.9, "width": 0.2},
        {**create_box_value(), "kind": "arrow"},
        {**create_box_value(), "page_index": 4},
        {**create_pencil_value(), "points": [[0.1, 0.1]]},
        {**create_pencil_value(), "points": [[0.1, 1.2], [0.2, 0.2]]},
    ],
)
def test_parse_marks_rejects_invalid_drawings(mark_value: dict) -> None:
    assert parse_marks([mark_value], page_count=3) is None


def test_parse_marks_rejects_too_many_drawings_and_points() -> None:
    assert parse_marks(
        [create_box_value()] * (MAXIMUM_MARKS + 1),
        page_count=1,
    ) is None
    long_stroke = create_pencil_value()
    long_stroke["points"] = [[0.1, 0.1]] * (MAXIMUM_POINTS + 1)
    assert parse_marks([long_stroke], page_count=1) is None
