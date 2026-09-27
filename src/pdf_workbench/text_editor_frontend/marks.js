import {clamp} from "./text_editor_state.js";
import {findPageElement} from "./text_editor_view.js";

const svgNamespace = "http://www.w3.org/2000/svg";
const minimumBoxSize = 0.005;
const minimumPointDistance = 0.004;

export function copyMarks(marks) {
  return marks.map((mark) => {
    const markCopy = {...mark};
    if (mark.points) {
      markCopy.points = mark.points.map((point) => [...point]);
    }
    return markCopy;
  });
}

let markSequence = 0;

export function createMarkId() {
  markSequence += 1;
  return `mark-${Date.now()}-${markSequence}`;
}

export function renderMarks(
  pageContainer,
  marks,
  selectedMarkId,
  fillOpacity,
) {
  pageContainer.querySelectorAll(".mark-layer").forEach((markLayer) => {
    markLayer.replaceChildren();
  });

  marks.forEach((mark) => {
    const pageElement = findPageElement(pageContainer, mark.page_index);
    if (!pageElement) {
      return;
    }
    pageElement.querySelector(".mark-layer").append(
      createMarkElement(mark, pageElement, selectedMarkId, fillOpacity),
    );
  });
}

export function createMarkDrawHandlers(editor) {
  let drawState = null;

  function begin(event) {
    if (event.button !== 0) {
      return;
    }
    const tool = editor.getTool();

    const existingMark = event.target.closest(".mark-shape");
    if (existingMark) {
      editor.selectMark(existingMark.dataset.markId);
      editor.showStatus("Drawing selected.");
      return;
    }

    const pageElement = event.target.closest(".pdf-page");
    if (!pageElement) {
      return;
    }
    if (editor.getMarks().length >= editor.getMaximumMarks()) {
      editor.showStatus(
        `A PDF can have at most ${editor.getMaximumMarks()} drawings.`,
      );
      return;
    }

    const position = readPagePosition(event, pageElement);
    drawState = {
      pointerId: event.pointerId,
      tool,
      pageElement,
      pageIndex: Number(pageElement.dataset.pageIndex),
      origin: position,
      points: [position],
    };
    event.preventDefault();
    event.currentTarget.setPointerCapture(event.pointerId);
    editor.selectMark(null);
    updatePreview();
  }

  function move(event) {
    if (!drawState || event.pointerId !== drawState.pointerId) {
      return;
    }

    const position = readPagePosition(event, drawState.pageElement);
    if (drawState.tool === "box") {
      drawState.current = position;
      updatePreview();
      return;
    }

    const lastPoint = drawState.points[drawState.points.length - 1];
    const distance = Math.hypot(
      position.x - lastPoint.x,
      position.y - lastPoint.y,
    );
    if (
      distance < minimumPointDistance
      || drawState.points.length >= editor.getMaximumPoints()
    ) {
      return;
    }
    drawState.points.push(position);
    updatePreview();
  }

  function finish(event, cancelDraw = false) {
    if (!drawState || event.pointerId !== drawState.pointerId) {
      return;
    }
    if (cancelDraw) {
      cancel();
      return;
    }
    commit();
  }

  function commit() {
    if (!drawState) {
      return;
    }
    const completedDraw = drawState;
    drawState = null;
    removePreview(completedDraw.pageElement);
    const mark = completedDraw.tool === "box"
      ? boxFromDraw(completedDraw)
      : pencilFromDraw(completedDraw);
    if (!mark) {
      editor.showStatus(
        completedDraw.tool === "box"
          ? "Box was too small."
          : "Stroke was too short.",
      );
      return;
    }

    editor.rememberTextEdits();
    editor.getMarks().push(mark);
    editor.selectMark(mark.id);
    editor.showStatus(
      completedDraw.tool === "box" ? "Box added." : "Stroke added.",
    );
    editor.sendChange();
  }

  function cancel() {
    if (!drawState) {
      return;
    }
    const pageElement = drawState.pageElement;
    drawState = null;
    removePreview(pageElement);
  }

  function updatePreview() {
    const mark = drawState.tool === "box"
      ? boxFromDraw(drawState, true)
      : pencilFromDraw(drawState, true);
    removePreview(drawState.pageElement);
    if (!mark) {
      return;
    }
    const preview = createVisibleShape(
      mark,
      drawState.pageElement,
      editor.getFillOpacity(),
    );
    preview.setAttribute("class", "mark-preview");
    drawState.pageElement.querySelector(".mark-layer").append(preview);
  }

  function boxFromDraw(completedDraw, allowSmall = false) {
    const end = completedDraw.current || completedDraw.origin;
    const horizontalPosition = Math.min(completedDraw.origin.x, end.x);
    const verticalPosition = Math.min(completedDraw.origin.y, end.y);
    const width = Math.min(
      Math.abs(end.x - completedDraw.origin.x),
      1 - horizontalPosition,
    );
    const height = Math.min(
      Math.abs(end.y - completedDraw.origin.y),
      1 - verticalPosition,
    );
    if (!allowSmall && (width < minimumBoxSize || height < minimumBoxSize)) {
      return null;
    }
    return {
      id: createMarkId(),
      page_index: completedDraw.pageIndex,
      kind: "box",
      color: editor.getMarkColor(),
      line_width: editor.getLineWidth(),
      filled: editor.getFilled(),
      horizontal_position: horizontalPosition,
      vertical_position: verticalPosition,
      width,
      height,
    };
  }

  function pencilFromDraw(completedDraw, allowShort = false) {
    if (!allowShort && completedDraw.points.length < 2) {
      return null;
    }
    return {
      id: createMarkId(),
      page_index: completedDraw.pageIndex,
      kind: "pencil",
      color: editor.getMarkColor(),
      line_width: editor.getLineWidth(),
      filled: editor.getFilled(),
      points: completedDraw.points.map((point) => [point.x, point.y]),
    };
  }

  function isDrawing() {
    return drawState !== null;
  }

  return {begin, cancel, commit, finish, isDrawing, move};
}

export function createMarkStyleHandlers(editor) {
  function changeLineWidth() {
    const requestedLineWidth = Number.parseInt(editor.lineWidthInput.value, 10);
    if (!Number.isFinite(requestedLineWidth)) {
      editor.updateToolbar();
      return;
    }
    const lineWidth = clamp(
      requestedLineWidth,
      editor.getMinimumLineWidth(),
      editor.getMaximumLineWidth(),
    );
    editor.setLineWidth(lineWidth);
    updateSelectedMark("line_width", lineWidth, "Line width changed.");
  }

  function changeColor() {
    const color = editor.colorInput.value;
    editor.setMarkColor(color);
    updateSelectedMark("color", color, "Color changed.");
  }

  function changeFill() {
    const filled = editor.fillInput.checked;
    editor.setFilled(filled);
    updateSelectedMark(
      "filled",
      filled,
      filled ? "Fill turned on." : "Fill turned off.",
    );
  }

  function updateSelectedMark(fieldName, value, statusMessage) {
    const selectedMark = editor.getSelectedMark();
    if (!selectedMark || selectedMark[fieldName] === value) {
      editor.updateToolbar();
      return;
    }
    editor.rememberTextEdits();
    selectedMark[fieldName] = value;
    editor.renderMarks();
    editor.showStatus(statusMessage);
    editor.sendChange();
  }

  return {changeColor, changeFill, changeLineWidth};
}

function createMarkElement(mark, pageElement, selectedMarkId, fillOpacity) {
  const visibleShape = createVisibleShape(mark, pageElement, fillOpacity);
  visibleShape.setAttribute("class", "mark-visible");
  const hitShape = createVisibleShape(mark, pageElement, fillOpacity);
  hitShape.setAttribute("class", "mark-hit");
  // Fill "none" is not clickable, so an empty box interior would draw again.
  hitShape.setAttribute(
    "fill",
    mark.kind === "box" || mark.filled ? "transparent" : "none",
  );
  hitShape.setAttribute("stroke", "transparent");
  hitShape.setAttribute("stroke-width", String(mark.line_width + 8));

  const markElement = document.createElementNS(svgNamespace, "g");
  markElement.setAttribute("class", "mark-shape");
  markElement.dataset.markId = mark.id;
  if (mark.id === selectedMarkId) {
    markElement.classList.add("selected");
  }
  markElement.append(hitShape, visibleShape);
  return markElement;
}

function createVisibleShape(mark, pageElement, fillOpacity) {
  const widthPoints = Number(pageElement.dataset.widthPoints);
  const heightPoints = Number(pageElement.dataset.heightPoints);
  const shape = document.createElementNS(
    svgNamespace,
    mark.kind === "box" ? "rect" : "polyline",
  );
  if (mark.kind === "box") {
    shape.setAttribute("x", String(mark.horizontal_position * widthPoints));
    shape.setAttribute("y", String(mark.vertical_position * heightPoints));
    shape.setAttribute("width", String(mark.width * widthPoints));
    shape.setAttribute("height", String(mark.height * heightPoints));
  } else {
    shape.setAttribute(
      "points",
      mark.points
        .map((point) => (
          `${point[0] * widthPoints},${point[1] * heightPoints}`
        ))
        .join(" "),
    );
    shape.setAttribute("stroke-linecap", "round");
    shape.setAttribute("stroke-linejoin", "round");
  }
  shape.setAttribute("fill", mark.filled ? mark.color : "none");
  shape.setAttribute("stroke", mark.color);
  shape.setAttribute("stroke-width", String(mark.line_width));
  if (mark.filled) {
    shape.setAttribute("fill-opacity", String(fillOpacity));
  }
  return shape;
}

function readPagePosition(event, pageElement) {
  const pageBounds = pageElement.getBoundingClientRect();
  return {
    x: clamp((event.clientX - pageBounds.left) / pageBounds.width, 0, 1),
    y: clamp((event.clientY - pageBounds.top) / pageBounds.height, 0, 1),
  };
}

function removePreview(pageElement) {
  pageElement.querySelector(".mark-preview")?.remove();
}
