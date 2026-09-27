import re
from collections.abc import Sequence
from dataclasses import dataclass
from math import isfinite

import pymupdf


MINIMUM_LINE_WIDTH = 1
MAXIMUM_LINE_WIDTH = 12
MAXIMUM_MARKS = 100
MAXIMUM_POINTS = 500
# A solid fill hides the page under the mark. Keep it light, like a highlight.
FILL_OPACITY = 0.35
PAGE_EDGE_TOLERANCE = 1e-4

COLOR_PATTERN = re.compile(r"#[0-9A-Fa-f]{6}")


@dataclass(frozen=True)
class BoxMark:
    page_index: int
    color: tuple[float, float, float]
    line_width: int
    filled: bool
    horizontal_position: float
    vertical_position: float
    width: float
    height: float


@dataclass(frozen=True)
class PencilMark:
    page_index: int
    color: tuple[float, float, float]
    line_width: int
    filled: bool
    points: tuple[tuple[float, float], ...]


Mark = BoxMark | PencilMark


def format_color(color: tuple[float, float, float]) -> str:
    return "#" + "".join(f"{round(channel * 255):02x}" for channel in color)


def parse_marks(
    mark_values: object,
    page_count: int,
) -> tuple[Mark, ...] | None:
    if not isinstance(mark_values, list) or len(mark_values) > MAXIMUM_MARKS:
        return None

    marks: list[Mark] = []
    for mark_value in mark_values:
        mark = parse_mark(mark_value, page_count)
        if mark is None:
            return None
        marks.append(mark)
    return tuple(marks)


def parse_mark(mark_value: object, page_count: int) -> Mark | None:
    mark = mark_from_value(mark_value)
    if mark is None:
        return None
    try:
        validate_mark(mark, page_count)
    except ValueError:
        return None
    return mark


def serialize_marks(marks: Sequence[Mark]) -> list[dict]:
    return [
        serialize_mark(mark, mark_number)
        for mark_number, mark in enumerate(marks)
    ]


def apply_marks(document: pymupdf.Document, marks: Sequence[Mark]) -> None:
    if len(marks) > MAXIMUM_MARKS:
        raise ValueError(f"A PDF can have at most {MAXIMUM_MARKS} drawings.")

    for mark in marks:
        validate_mark(mark, document.page_count)
        # Same overlay path as added text, so the download shows the marks
        # in viewers that hide annotation objects.
        draw_mark(document[mark.page_index], mark)


def validate_mark(mark: Mark, page_count: int) -> None:
    if (
        isinstance(mark.page_index, bool)
        or not isinstance(mark.page_index, int)
        or not 0 <= mark.page_index < page_count
    ):
        raise ValueError(f"Page {mark.page_index + 1} does not exist.")
    if not is_line_width(mark.line_width):
        raise ValueError(
            f"Line width must be {MINIMUM_LINE_WIDTH} to {MAXIMUM_LINE_WIDTH}."
        )
    if not isinstance(mark.filled, bool):
        raise ValueError("Fill must be on or off.")
    if not is_color(mark.color):
        raise ValueError("Color must be a hex value like #112233.")
    if isinstance(mark, BoxMark):
        validate_box(mark)
        return
    if isinstance(mark, PencilMark):
        validate_pencil(mark)
        return
    raise ValueError("Drawing type is invalid.")


def mark_from_value(mark_value: object) -> Mark | None:
    if not isinstance(mark_value, dict):
        return None

    kind = mark_value.get("kind")
    page_index = mark_value.get("page_index")
    color = parse_color(mark_value.get("color"))
    line_width = mark_value.get("line_width")
    filled = mark_value.get("filled")
    if (
        kind not in {"box", "pencil"}
        or isinstance(page_index, bool)
        or not isinstance(page_index, int)
        or color is None
        or not is_line_width(line_width)
        or not isinstance(filled, bool)
    ):
        return None

    if kind == "box":
        return box_from_value(mark_value, page_index, color, line_width, filled)
    return pencil_from_value(mark_value, page_index, color, line_width, filled)


def box_from_value(
    mark_value: dict,
    page_index: int,
    color: tuple[float, float, float],
    line_width: int,
    filled: bool,
) -> BoxMark | None:
    horizontal_position = parse_number(mark_value.get("horizontal_position"))
    vertical_position = parse_number(mark_value.get("vertical_position"))
    width = parse_number(mark_value.get("width"))
    height = parse_number(mark_value.get("height"))
    if None in {horizontal_position, vertical_position, width, height}:
        return None
    return BoxMark(
        page_index=page_index,
        color=color,
        line_width=line_width,
        filled=filled,
        horizontal_position=horizontal_position,
        vertical_position=vertical_position,
        width=width,
        height=height,
    )


def pencil_from_value(
    mark_value: dict,
    page_index: int,
    color: tuple[float, float, float],
    line_width: int,
    filled: bool,
) -> PencilMark | None:
    points = parse_points(mark_value.get("points"))
    if points is None:
        return None
    return PencilMark(
        page_index=page_index,
        color=color,
        line_width=line_width,
        filled=filled,
        points=points,
    )


def validate_box(mark: BoxMark) -> None:
    if (
        not is_fraction(mark.horizontal_position)
        or not is_fraction(mark.vertical_position)
        or not is_fraction(mark.width)
        or not is_fraction(mark.height)
        or mark.width <= 0
        or mark.height <= 0
    ):
        raise ValueError("Box is too small.")
    if (
        mark.horizontal_position + mark.width > 1 + PAGE_EDGE_TOLERANCE
        or mark.vertical_position + mark.height > 1 + PAGE_EDGE_TOLERANCE
    ):
        raise ValueError("Box extends past the page.")


def validate_pencil(mark: PencilMark) -> None:
    if len(mark.points) < 2:
        raise ValueError("Pencil stroke is too short.")
    if len(mark.points) > MAXIMUM_POINTS:
        raise ValueError(
            f"A pencil stroke can have at most {MAXIMUM_POINTS} points."
        )
    if any(
        not is_fraction(horizontal) or not is_fraction(vertical)
        for horizontal, vertical in mark.points
    ):
        raise ValueError("Pencil stroke is outside the page.")


def draw_mark(page: pymupdf.Page, mark: Mark) -> None:
    fill = mark.color if mark.filled else None
    fill_opacity = FILL_OPACITY if mark.filled else 1
    if isinstance(mark, BoxMark):
        page.draw_rect(
            box_rect(page, mark),
            color=mark.color,
            fill=fill,
            width=mark.line_width,
            fill_opacity=fill_opacity,
            overlay=True,
        )
        return

    page.draw_polyline(
        [
            point_on_page(page, horizontal, vertical)
            for horizontal, vertical in mark.points
        ],
        color=mark.color,
        fill=fill,
        width=mark.line_width,
        closePath=mark.filled,
        lineCap=1,
        lineJoin=1,
        fill_opacity=fill_opacity,
        overlay=True,
    )


def serialize_mark(mark: Mark, mark_number: int) -> dict:
    serialized = {
        "id": f"saved-mark-{mark_number}",
        "page_index": mark.page_index,
        "kind": "box" if isinstance(mark, BoxMark) else "pencil",
        "color": format_color(mark.color),
        "line_width": mark.line_width,
        "filled": mark.filled,
    }
    if isinstance(mark, BoxMark):
        serialized.update(
            {
                "horizontal_position": mark.horizontal_position,
                "vertical_position": mark.vertical_position,
                "width": mark.width,
                "height": mark.height,
            }
        )
        return serialized
    serialized["points"] = [
        [horizontal, vertical] for horizontal, vertical in mark.points
    ]
    return serialized


def box_rect(page: pymupdf.Page, mark: BoxMark) -> pymupdf.Rect:
    return pymupdf.Rect(
        point_on_page(page, mark.horizontal_position, mark.vertical_position),
        point_on_page(
            page,
            mark.horizontal_position + mark.width,
            mark.vertical_position + mark.height,
        ),
    )


def point_on_page(
    page: pymupdf.Page,
    horizontal: float,
    vertical: float,
) -> pymupdf.Point:
    return pymupdf.Point(
        page.rect.x0 + page.rect.width * horizontal,
        page.rect.y0 + page.rect.height * vertical,
    )


def parse_color(value: object) -> tuple[float, float, float] | None:
    if not isinstance(value, str) or COLOR_PATTERN.fullmatch(value) is None:
        return None
    return (
        int(value[1:3], 16) / 255,
        int(value[3:5], 16) / 255,
        int(value[5:7], 16) / 255,
    )


def parse_points(
    value: object,
) -> tuple[tuple[float, float], ...] | None:
    if not isinstance(value, (list, tuple)) or len(value) > MAXIMUM_POINTS:
        return None
    points: list[tuple[float, float]] = []
    for point in value:
        if not isinstance(point, (list, tuple)) or len(point) != 2:
            return None
        horizontal = parse_number(point[0])
        vertical = parse_number(point[1])
        if horizontal is None or vertical is None:
            return None
        points.append((horizontal, vertical))
    return tuple(points)


def parse_number(value: object) -> float | None:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not isfinite(value)
    ):
        return None
    return float(value)


def is_line_width(value: object) -> bool:
    return (
        isinstance(value, int)
        and not isinstance(value, bool)
        and MINIMUM_LINE_WIDTH <= value <= MAXIMUM_LINE_WIDTH
    )


def is_fraction(value: object) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and isfinite(value)
        and 0 <= float(value) <= 1
    )


def is_color(color: object) -> bool:
    return (
        isinstance(color, tuple)
        and len(color) == 3
        and all(is_unit_channel(channel) for channel in color)
    )


def is_unit_channel(value: object) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and isfinite(value)
        and 0 <= float(value) <= 1
    )
