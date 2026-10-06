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

function handleLength(widthPoints, heightPoints) {
  return Math.min(widthPoints, heightPoints) * 0.018;
}

function pointBounds(points) {
  let minX = 1;
  let minY = 1;
  let maxX = 0;
  let maxY = 0;
  for (const [x, y] of points) {
    minX = Math.min(minX, x);
    minY = Math.min(minY, y);
    maxX = Math.max(maxX, x);
    maxY = Math.max(maxY, y);
  }
  return {x: minX, y: minY, width: maxX - minX, height: maxY - minY};
}

function markBounds(mark) {
  if (mark.kind === "box") {
    return {
      x: mark.horizontal_position,
      y: mark.vertical_position,
      width: mark.width,
      height: mark.height,
    };
  }
  return pointBounds(mark.points);
}

export function moveBox(start, dx, dy) {
  return {
    x: clamp(start.x + dx, 0, Math.max(0, 1 - start.width)),
    y: clamp(start.y + dy, 0, Math.max(0, 1 - start.height)),
    width: start.width,
    height: start.height,
  };
}

export function resizeBox(start, handleName, pointer) {
  let left = start.x;
  let top = start.y;
  let right = start.x + start.width;
  let bottom = start.y + start.height;
  if (handleName.endsWith("w")) {
    left = clamp(pointer.x, 0, right - minimumBoxSize);
  } else {
    right = clamp(pointer.x, left + minimumBoxSize, 1);
  }
  if (handleName.startsWith("n")) {
    top = clamp(pointer.y, 0, bottom - minimumBoxSize);
  } else {
    bottom = clamp(pointer.y, top + minimumBoxSize, 1);
  }
  return {x: left, y: top, width: right - left, height: bottom - top};
}

export function shiftPoints(points, dx, dy) {
  const bounds = pointBounds(points);
  const shiftX = clamp(dx, -bounds.x, 1 - bounds.x - bounds.width);
  const shiftY = clamp(dy, -bounds.y, 1 - bounds.y - bounds.height);
  return points.map(([x, y]) => [x + shiftX, y + shiftY]);
}

export function scalePoints(points, start, next) {
  function scaledCoordinate(value, startOrigin, startSpan, nextOrigin, nextSpan) {
    if (startSpan !== 0) {
      return nextOrigin + ((value - startOrigin) / startSpan) * nextSpan;
    }
    if (nextOrigin === startOrigin) {
      return nextOrigin + nextSpan;
    }
    return nextOrigin;
  }

  return points.map((point) => {
    const across = scaledCoordinate(
      point[0],
      start.x,
      start.width,
      next.x,
      next.width,
    );
    const down = scaledCoordinate(
      point[1],
      start.y,
      start.height,
      next.y,
      next.height,
    );
    return [clamp(across, 0, 1), clamp(down, 0, 1)];
  });
}

export function createMarkEditHandlers(editor) {
  let editState = null;

  function begin(event) {
    if (event.button !== 0) {
      return false;
    }
    const markElement = event.target.closest(".mark-shape");
    if (!markElement) {
      return false;
    }
    const mark = editor.getMarks().find(
      (item) => item.id === markElement.dataset.markId,
    );
    const pageElement = markElement.closest(".pdf-page");
    if (!mark || !pageElement) {
      return false;
    }

    const handle = event.target.closest(".mark-handle");
    const previousMarks = copyMarks(editor.getMarks());
    const savedMark = previousMarks.find((item) => item.id === mark.id);
    editor.selectMark(mark.id);
    editor.showStatus("Drawing selected.");
    event.currentTarget.setPointerCapture(event.pointerId);
    editState = {
      pointerId: event.pointerId,
      markId: mark.id,
      handleName: handle?.dataset.handle || null,
      pageElement,
      startClientX: event.clientX,
      startClientY: event.clientY,
      startPointer: readPagePosition(event, pageElement),
      startBounds: markBounds(mark),
      startPoints: savedMark.points || null,
      previousMarks,
      moved: false,
    };
    return true;
  }

  function move(event) {
    if (!editState || event.pointerId !== editState.pointerId) {
      return;
    }
    const mark = editor.getMarks().find((item) => item.id === editState.markId);
    if (!mark) {
      return;
    }

    const travel = Math.abs(event.clientX - editState.startClientX)
      + Math.abs(event.clientY - editState.startClientY);
    if (travel > 3) {
      editState.moved = true;
    }
    if (!editState.moved) {
      return;
    }

    event.preventDefault();
    const pointer = readPagePosition(event, editState.pageElement);
    placeMark(mark, editState, pointer);
    const liveElement = editState.pageElement.querySelector(
      `[data-mark-id="${CSS.escape(editState.markId)}"]`,
    );
    if (liveElement) {
      syncMarkGeometry(liveElement, mark, editState.pageElement);
    }
  }

  function finish(event, cancelEdit = false) {
    if (!editState || event.pointerId !== editState.pointerId) {
      return;
    }
    const completedEdit = editState;
    editState = null;
    if (cancelEdit) {
      editor.replaceMarks(completedEdit.previousMarks);
      editor.renderMarks();
      return;
    }
    if (!completedEdit.moved) {
      return;
    }

    editor.rememberTextEdits(undefined, completedEdit.previousMarks);
    editor.renderMarks();
    const mark = editor.getMarks().find((item) => item.id === completedEdit.markId);
    editor.showStatus(editStatus(mark, completedEdit.handleName));
    editor.sendChange();
  }

  function cancel() {
    if (!editState) {
      return;
    }
    finish({pointerId: editState.pointerId}, true);
  }

  function isEditing() {
    return editState !== null;
  }

  return {begin, cancel, finish, isEditing, move};
}

function placeMark(mark, editState, pointer) {
  const dx = pointer.x - editState.startPointer.x;
  const dy = pointer.y - editState.startPointer.y;
  if (mark.kind === "box" && !editState.handleName) {
    const moved = moveBox(editState.startBounds, dx, dy);
    mark.horizontal_position = moved.x;
    mark.vertical_position = moved.y;
    return;
  }
  if (mark.kind === "box") {
    const resized = resizeBox(
      editState.startBounds,
      editState.handleName,
      pointer,
    );
    mark.horizontal_position = resized.x;
    mark.vertical_position = resized.y;
    mark.width = resized.width;
    mark.height = resized.height;
    return;
  }
  if (!editState.handleName) {
    mark.points = shiftPoints(editState.startPoints, dx, dy);
    return;
  }
  mark.points = scalePoints(
    editState.startPoints,
    editState.startBounds,
    resizeBox(editState.startBounds, editState.handleName, pointer),
  );
}

function editStatus(mark, handleName) {
  if (mark.kind === "box") {
    return handleName ? "Box resized." : "Box moved.";
  }
  return handleName ? "Stroke resized." : "Stroke moved.";
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
  markElement.append(hitShape, visibleShape);
  if (mark.id === selectedMarkId) {
    markElement.classList.add("selected");
    appendHandles(markElement, markBounds(mark), pageElement);
  }
  return markElement;
}

function appendHandles(markElement, bounds, pageElement) {
  const widthPoints = Number(pageElement.dataset.widthPoints);
  const heightPoints = Number(pageElement.dataset.heightPoints);
  const handleSize = handleLength(widthPoints, heightPoints);
  for (const handleName of ["nw", "ne", "sw", "se"]) {
    const handle = document.createElementNS(svgNamespace, "rect");
    handle.setAttribute("class", "mark-handle");
    handle.dataset.handle = handleName;
    placeHandle(
      handle,
      bounds,
      handleName,
      handleSize,
      widthPoints,
      heightPoints,
    );
    markElement.append(handle);
  }
}

function placeHandle(
  handle,
  bounds,
  handleName,
  handleSize,
  widthPoints,
  heightPoints,
) {
  const corner = {
    x: handleName.endsWith("w") ? bounds.x : bounds.x + bounds.width,
    y: handleName.startsWith("n") ? bounds.y : bounds.y + bounds.height,
  };
  handle.setAttribute("x", String(corner.x * widthPoints - handleSize / 2));
  handle.setAttribute("y", String(corner.y * heightPoints - handleSize / 2));
  handle.setAttribute("width", String(handleSize));
  handle.setAttribute("height", String(handleSize));
}

function applyShapeGeometry(shape, mark, widthPoints, heightPoints) {
  if (mark.kind === "box") {
    shape.setAttribute("x", String(mark.horizontal_position * widthPoints));
    shape.setAttribute("y", String(mark.vertical_position * heightPoints));
    shape.setAttribute("width", String(mark.width * widthPoints));
    shape.setAttribute("height", String(mark.height * heightPoints));
    return;
  }
  shape.setAttribute(
    "points",
    mark.points
      .map((point) => `${point[0] * widthPoints},${point[1] * heightPoints}`)
      .join(" "),
  );
}

function syncMarkGeometry(markElement, mark, pageElement) {
  const widthPoints = Number(pageElement.dataset.widthPoints);
  const heightPoints = Number(pageElement.dataset.heightPoints);
  markElement.querySelectorAll(".mark-visible, .mark-hit").forEach((shape) => {
    applyShapeGeometry(shape, mark, widthPoints, heightPoints);
  });

  const bounds = markBounds(mark);
  const handleSize = handleLength(widthPoints, heightPoints);
  markElement.querySelectorAll(".mark-handle").forEach((handle) => {
    placeHandle(
      handle,
      bounds,
      handle.dataset.handle,
      handleSize,
      widthPoints,
      heightPoints,
    );
  });
}

function createVisibleShape(mark, pageElement, fillOpacity) {
  const widthPoints = Number(pageElement.dataset.widthPoints);
  const heightPoints = Number(pageElement.dataset.heightPoints);
  const shape = document.createElementNS(
    svgNamespace,
    mark.kind === "box" ? "rect" : "polyline",
  );
  applyShapeGeometry(shape, mark, widthPoints, heightPoints);
  if (mark.kind !== "box") {
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
