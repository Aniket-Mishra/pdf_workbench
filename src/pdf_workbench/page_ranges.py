def parse_page_range(page_range: str, page_count: int) -> list[int]:
    if page_count < 1:
        raise ValueError("The PDF has no pages.")

    range_parts = [part.strip().lower() for part in page_range.split(",")]
    if not page_range.strip() or any(not part for part in range_parts):
        raise ValueError("Enter pages such as 1-5, 8, 12-end.")

    selected_pages: set[int] = set()
    for range_part in range_parts:
        selected_pages.update(parse_range_part(range_part, page_count))

    return sorted(selected_pages)


def parse_range_part(range_part: str, page_count: int) -> range:
    if "-" not in range_part:
        page_number = parse_page_number(range_part, page_count)
        return range(page_number - 1, page_number)

    if range_part.count("-") != 1:
        raise ValueError(f"Invalid page range: {range_part}.")

    first_text, last_text = (part.strip() for part in range_part.split("-"))
    first_page = parse_page_number(first_text, page_count)
    last_page = parse_page_number(last_text, page_count)
    if first_page > last_page:
        raise ValueError(f"Page range runs backwards: {range_part}.")

    return range(first_page - 1, last_page)


def parse_page_number(page_text: str, page_count: int) -> int:
    if page_text == "end":
        return page_count

    try:
        page_number = int(page_text)
    except ValueError as error:
        raise ValueError(f"Invalid page number: {page_text}.") from error

    if page_number < 1 or page_number > page_count:
        raise ValueError(
            f"Page {page_number} is outside this {page_count}-page PDF."
        )
    return page_number
