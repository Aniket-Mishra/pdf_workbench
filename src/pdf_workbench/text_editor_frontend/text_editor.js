import {
  calculatePagePosition,
  findPageElement,
  renderPdfPages,
  renderTextEdits,
  updateRenderedTextSizes,
} from "./text_editor_view.js";
import {createTextDraftController} from "./text_draft.js";
import {createTextDragHandlers} from "./text_drag.js";
import {
  copyTextEdits,
  createTextEditId,
} from "./text_editor_state.js";
import {createTextEditorCommands} from "./text_editor_commands.js";
import {
  copyMarks,
  createMarkDrawHandlers,
  createMarkEditHandlers,
  createMarkStyleHandlers,
  renderMarks,
} from "./marks.js";
import {
  announceComponentReady,
  applyStreamlitTheme,
  sendEditorState as sendStreamlitEditorState,
  updateStreamlitFrameHeight,
} from "./streamlit_component.js";

const pageContainer = document.getElementById("pages");
const viewport = document.getElementById("viewport");
const addTextButton = document.getElementById("add-text");
const addBoxButton = document.getElementById("add-box");
const addPencilButton = document.getElementById("add-pencil");
const fontSizeInput = document.getElementById("font-size");
const lineWidthInput = document.getElementById("line-width");
const colorInput = document.getElementById("mark-color");
const fillInput = document.getElementById("fill");
const undoButton = document.getElementById("undo");
const deleteTextButton = document.getElementById("delete-text");
const clearTextButton = document.getElementById("clear-text");
const buildPdfButton = document.getElementById("build-pdf");
const status = document.getElementById("status");
const loadingStatus = document.getElementById("loading-status");

let documentId = null;
let pages = [];
let pageCount = 0;
let textEdits = [];
let marks = [];
let textEditHistory = [];
let selectedTextEditId = null;
let selectedMarkId = null;
let tool = null;
let defaultFontSize = 18;
let minimumFontSize = 8;
let maximumFontSize = 72;
let maximumTextLength = 500;
let lineWidth = 2;
let markColor = "#000000";
let filled = false;
let minimumLineWidth = 1;
let maximumLineWidth = 12;
let maximumMarks = 100;
let maximumPoints = 500;
let fillOpacity = 0.35;
let loadingMorePages = false;
let downloadWasReady = false;

function sendEditorState(action) {
  updateToolbar();
  sendStreamlitEditorState(textEdits, marks, action);
}

function showStatus(message) {
  status.textContent = message;
}

function rememberTextEdits(previousTextEdits = textEdits, previousMarks = marks) {
  // Drawings share this stack so undo cannot restore text and leave a new stroke.
  textEditHistory.push({
    textEdits: copyTextEdits(previousTextEdits),
    marks: copyMarks(previousMarks),
  });
  if (textEditHistory.length > 30) {
    textEditHistory.shift();
  }
}

function findTextEdit(textEditId) {
  return textEdits.find((textEdit) => textEdit.id === textEditId);
}

function getSelectedTextEdit() {
  return findTextEdit(selectedTextEditId);
}

function findMark(markId) {
  return marks.find((mark) => mark.id === markId);
}

function getSelectedMark() {
  return findMark(selectedMarkId);
}

function updateToolbar() {
  const selectedTextEdit = getSelectedTextEdit();
  const hasEdits = textEdits.length > 0 || marks.length > 0;
  addTextButton.setAttribute("aria-pressed", String(tool === "text"));
  addBoxButton.setAttribute("aria-pressed", String(tool === "box"));
  addPencilButton.setAttribute("aria-pressed", String(tool === "pencil"));
  undoButton.disabled = textEditHistory.length === 0;
  deleteTextButton.disabled = !selectedTextEdit && !getSelectedMark();
  clearTextButton.disabled = !hasEdits;
  buildPdfButton.disabled = !hasEdits;
  fontSizeInput.value = selectedTextEdit
    ? selectedTextEdit.font_size
    : defaultFontSize;
  lineWidthInput.value = lineWidth;
  colorInput.value = markColor;
  fillInput.checked = filled;
}

function renderCurrentTextEdits() {
  renderTextEdits(pageContainer, textEdits, selectedTextEditId);
  updateToolbar();
}

function renderCurrentMarks() {
  renderMarks(pageContainer, marks, selectedMarkId, fillOpacity);
  updateToolbar();
}

function keepTextInsidePage(textEdit) {
  const pageElement = findPageElement(
    pageContainer,
    textEdit.page_index,
  );
  const textElement = pageContainer.querySelector(
    `[data-text-edit-id="${CSS.escape(textEdit.id)}"]`,
  );
  if (!pageElement || !textElement) {
    return false;
  }

  const previousHorizontalPosition = textEdit.horizontal_position;
  const previousVerticalPosition = textEdit.vertical_position;
  textEdit.horizontal_position = Math.min(
    previousHorizontalPosition,
    Math.max(0, 1 - textElement.offsetWidth / pageElement.clientWidth),
  );
  textEdit.vertical_position = Math.min(
    previousVerticalPosition,
    Math.max(0, 1 - textElement.offsetHeight / pageElement.clientHeight),
  );
  return (
    textEdit.horizontal_position !== previousHorizontalPosition
    || textEdit.vertical_position !== previousVerticalPosition
  );
}

function setSelectedTextEditId(textEditId) {
  selectedTextEditId = textEditId;
  if (!textEditId || !selectedMarkId) {
    return;
  }
  selectedMarkId = null;
  renderCurrentMarks();
}

function selectTextEdit(textEditId) {
  setSelectedTextEditId(textEditId);
  pageContainer.querySelectorAll(".text-edit").forEach((textElement) => {
    textElement.classList.toggle(
      "selected",
      textElement.dataset.textEditId === textEditId,
    );
  });
  updateToolbar();
  if (textEditId) {
    showStatus("Text selected. Drag to move it.");
  }
}

function selectMark(markId) {
  selectedMarkId = markId;
  if (markId) {
    selectedTextEditId = null;
    pageContainer.querySelectorAll(".text-edit.selected").forEach((element) => {
      element.classList.remove("selected");
    });
    const mark = findMark(markId);
    if (mark) {
      lineWidth = mark.line_width;
      markColor = mark.color;
      filled = mark.filled;
    }
  }
  renderCurrentMarks();
}

function isDrawTool() {
  return tool === "box" || tool === "pencil";
}

function setTool(nextTool) {
  tool = nextTool;
  document.body.dataset.tool = tool || "";
  updateToolbar();
  if (tool === "text") {
    showStatus("Click a page and type. Press Enter to place the text.");
    return;
  }
  if (tool === "box") {
    showStatus("Drag on a page to draw a box.");
    return;
  }
  if (tool === "pencil") {
    showStatus("Drag on a page to draw.");
    return;
  }
  showStatus("Choose Add text, Box, or Pencil.");
}

function toggleTool(nextTool) {
  textDraftController.finish(true);
  markDrawHandlers.cancel();
  setTool(tool === nextTool ? null : nextTool);
}

const textDraftController = createTextDraftController({
  pageContainer,
  findTextEdit,
  getTextEdits: () => textEdits,
  getMaximumTextLength: () => maximumTextLength,
  keepTextInsidePage,
  rememberTextEdits,
  renderTextEdits: renderCurrentTextEdits,
  sendChange: () => sendEditorState("change"),
  setSelectedTextEditId,
  showStatus,
});

function handlePageClick(event) {
  // Pointer capture retargets the click after a drag to the page list.
  if (event.target.id === "pages") {
    return;
  }
  if (event.target.closest(".draft-text, .mark-shape") || isDrawTool()) {
    return;
  }

  const textElement = event.target.closest(".text-edit");
  if (textElement) {
    selectTextEdit(textElement.dataset.textEditId);
    return;
  }

  const pageElement = event.target.closest(".pdf-page");
  if (!pageElement || tool !== "text") {
    selectTextEdit(null);
    selectMark(null);
    return;
  }

  const position = calculatePagePosition(
    event,
    pageElement,
    defaultFontSize,
  );
  textDraftController.start(
    pageElement,
    {
      id: createTextEditId(),
      page_index: Number(pageElement.dataset.pageIndex),
      text: "",
      font_size: defaultFontSize,
      horizontal_position: position.horizontalPosition,
      vertical_position: position.verticalPosition,
    },
  );
}

function handleTextDoubleClick(event) {
  if (isDrawTool()) {
    return;
  }
  const textElement = event.target.closest(".text-edit");
  if (!textElement) {
    return;
  }

  const textEdit = findTextEdit(textElement.dataset.textEditId);
  const pageElement = textElement.closest(".pdf-page");
  if (textEdit && pageElement) {
    textDraftController.start(pageElement, {...textEdit}, textEdit.id);
  }
}

const textDragHandlers = createTextDragHandlers({
  pageContainer,
  findTextEdit,
  getTextEdits: () => textEdits,
  rememberTextEdits,
  renderTextEdits: renderCurrentTextEdits,
  replaceTextEdits: (replacementTextEdits) => {
    textEdits = replacementTextEdits;
  },
  sendChange: () => sendEditorState("change"),
  setSelectedTextEditId,
  showStatus,
  updateToolbar,
});

const markDrawHandlers = createMarkDrawHandlers({
  getFilled: () => filled,
  getFillOpacity: () => fillOpacity,
  getLineWidth: () => lineWidth,
  getMarkColor: () => markColor,
  getMarks: () => marks,
  getMaximumMarks: () => maximumMarks,
  getMaximumPoints: () => maximumPoints,
  getTool: () => tool,
  rememberTextEdits,
  renderMarks: renderCurrentMarks,
  selectMark,
  sendChange: () => sendEditorState("change"),
  showStatus,
});

const markEditHandlers = createMarkEditHandlers({
  getMarks: () => marks,
  rememberTextEdits,
  renderMarks: renderCurrentMarks,
  replaceMarks: (replacementMarks) => {
    marks = replacementMarks;
  },
  selectMark,
  sendChange: () => sendEditorState("change"),
  showStatus,
});

const markStyleHandlers = createMarkStyleHandlers({
  colorInput,
  fillInput,
  getSelectedMark,
  lineWidthInput,
  getMaximumLineWidth: () => maximumLineWidth,
  getMinimumLineWidth: () => minimumLineWidth,
  rememberTextEdits,
  renderMarks: renderCurrentMarks,
  sendChange: () => sendEditorState("change"),
  setFilled: (nextFilled) => {
    filled = nextFilled;
  },
  setLineWidth: (nextLineWidth) => {
    lineWidth = nextLineWidth;
  },
  setMarkColor: (nextColor) => {
    markColor = nextColor;
  },
  showStatus,
  updateToolbar,
});

const textEditorCommands = createTextEditorCommands({
  fontSizeInput,
  cancelDrawing: markDrawHandlers.cancel,
  finishDraft: textDraftController.finish,
  getMaximumFontSize: () => maximumFontSize,
  getMinimumFontSize: () => minimumFontSize,
  getMarks: () => marks,
  getSelectedMark,
  getSelectedTextEdit,
  getSelectedTextEditId: () => selectedTextEditId,
  getTextEdits: () => textEdits,
  keepTextInsidePage,
  rememberTextEdits,
  renderMarks: renderCurrentMarks,
  renderTextEdits: renderCurrentTextEdits,
  replaceMarks: (replacementMarks) => {
    marks = replacementMarks;
  },
  replaceTextEdits: (replacementTextEdits) => {
    textEdits = replacementTextEdits;
  },
  sendChange: () => sendEditorState("change"),
  setDefaultFontSize: (fontSize) => {
    defaultFontSize = fontSize;
  },
  setSelectedMarkId: (markId) => {
    selectedMarkId = markId;
  },
  setSelectedTextEditId,
  showStatus,
  takePreviousTextEdits: () => textEditHistory.pop(),
  updateToolbar,
});

function requestMorePages() {
  if (loadingMorePages || pages.length >= pageCount) {
    return;
  }
  const remainingScroll = (
    viewport.scrollHeight - viewport.scrollTop - viewport.clientHeight
  );
  if (remainingScroll > 480) {
    return;
  }

  loadingMorePages = true;
  loadingStatus.hidden = false;
  showStatus("Loading more pages.");
  sendEditorState("load_more");
}

window.addEventListener("message", (event) => {
  if (event.data.type !== "streamlit:render") {
    return;
  }

  const componentArguments = event.data.args;
  const incomingDocumentId = componentArguments.document_id;
  const incomingPages = componentArguments.pages;
  const incomingTextEdits = componentArguments.text_edits;
  const incomingMarks = componentArguments.marks || [];
  const documentChanged = incomingDocumentId !== documentId;
  const pagesChanged = documentChanged
    || incomingPages.length !== pages.length;

  documentId = incomingDocumentId;
  pageCount = componentArguments.page_count;
  minimumFontSize = componentArguments.minimum_font_size;
  maximumFontSize = componentArguments.maximum_font_size;
  maximumTextLength = componentArguments.maximum_text_length;
  minimumLineWidth = componentArguments.minimum_line_width;
  maximumLineWidth = componentArguments.maximum_line_width;
  maximumMarks = componentArguments.maximum_marks;
  maximumPoints = componentArguments.maximum_points;
  fillOpacity = componentArguments.fill_opacity;
  fontSizeInput.min = minimumFontSize;
  fontSizeInput.max = maximumFontSize;
  lineWidthInput.min = minimumLineWidth;
  lineWidthInput.max = maximumLineWidth;
  applyStreamlitTheme(event.data.theme);

  if (documentChanged) {
    textEdits = copyTextEdits(incomingTextEdits);
    marks = copyMarks(incomingMarks);
    textEditHistory = [];
    selectedTextEditId = null;
    selectedMarkId = null;
    markDrawHandlers.cancel();
    setTool(null);
  }

  if (pagesChanged) {
    const previousScrollPosition = viewport.scrollTop;
    markDrawHandlers.cancel();
    pages = incomingPages;
    renderPdfPages(pageContainer, pages);
    renderCurrentTextEdits();
    renderCurrentMarks();
    viewport.scrollTop = previousScrollPosition;
  }

  loadingMorePages = false;
  loadingStatus.hidden = true;
  updateToolbar();
  const downloadReady = Boolean(componentArguments.download_ready);
  if (downloadReady && !downloadWasReady) {
    showStatus("PDF ready to download below.");
  }
  downloadWasReady = downloadReady;
  requestAnimationFrame(() => {
    updateRenderedTextSizes(pageContainer, textEdits);
    requestMorePages();
    updateStreamlitFrameHeight();
  });
});

function onPointerDown(event) {
  if (markEditHandlers.begin(event)) {
    return;
  }
  if (isDrawTool()) {
    markDrawHandlers.begin(event);
    return;
  }
  textDragHandlers.begin(event);
}

function onPointerMove(event) {
  markEditHandlers.move(event);
  markDrawHandlers.move(event);
  textDragHandlers.move(event);
}

function onPointerUp(event) {
  markEditHandlers.finish(event);
  markDrawHandlers.finish(event);
  textDragHandlers.finish(event);
}

function onPointerCancel(event) {
  markEditHandlers.finish(event, true);
  markDrawHandlers.finish(event, true);
  textDragHandlers.finish(event, true);
}

pageContainer.addEventListener("click", handlePageClick);
pageContainer.addEventListener("dblclick", handleTextDoubleClick);
pageContainer.addEventListener("pointerdown", onPointerDown);
pageContainer.addEventListener("pointermove", onPointerMove);
pageContainer.addEventListener("pointerup", onPointerUp);
pageContainer.addEventListener("pointercancel", onPointerCancel);
viewport.addEventListener("scroll", requestMorePages, {passive: true});
addTextButton.addEventListener("click", () => {
  toggleTool("text");
});
addBoxButton.addEventListener("click", () => {
  toggleTool("box");
});
addPencilButton.addEventListener("click", () => {
  toggleTool("pencil");
});
fontSizeInput.addEventListener(
  "change",
  textEditorCommands.changeFontSize,
);
fontSizeInput.addEventListener("keydown", (event) => {
  if (event.key !== "Enter") {
    return;
  }
  event.preventDefault();
  textEditorCommands.changeFontSize();
});
lineWidthInput.addEventListener(
  "change",
  markStyleHandlers.changeLineWidth,
);
lineWidthInput.addEventListener("keydown", (event) => {
  if (event.key !== "Enter") {
    return;
  }
  event.preventDefault();
  markStyleHandlers.changeLineWidth();
});
colorInput.addEventListener("change", markStyleHandlers.changeColor);
fillInput.addEventListener("change", markStyleHandlers.changeFill);
function undoLastEdit() {
  if (markDrawHandlers.isDrawing()) {
    markDrawHandlers.cancel();
    showStatus("Drawing cancelled.");
    return;
  }
  if (markEditHandlers.isEditing()) {
    markEditHandlers.cancel();
    showStatus("Edit cancelled.");
    return;
  }
  textEditorCommands.undoLastChange();
}

function deleteSelectedEdit() {
  if (markDrawHandlers.isDrawing()) {
    markDrawHandlers.cancel();
    showStatus("Drawing cancelled.");
    return;
  }
  if (markEditHandlers.isEditing()) {
    markEditHandlers.cancel();
    showStatus("Edit cancelled.");
    return;
  }
  textEditorCommands.deleteSelected();
}

undoButton.addEventListener("click", undoLastEdit);
deleteTextButton.addEventListener("click", deleteSelectedEdit);
clearTextButton.addEventListener("click", textEditorCommands.clearEdits);
buildPdfButton.addEventListener("click", () => {
  textDraftController.finish(true);
  markDrawHandlers.commit();
  if (textEdits.length || marks.length) {
    showStatus("Creating PDF.");
    sendEditorState("build");
  }
});
document.addEventListener("keydown", (event) => {
  if (event.target.matches("input")) {
    return;
  }
  if (event.key === "Escape") {
    markEditHandlers.cancel();
    markDrawHandlers.cancel();
    setTool(null);
  } else if (
    event.key === "Delete"
    || event.key === "Backspace"
  ) {
    event.preventDefault();
    deleteSelectedEdit();
  } else if (
    (event.ctrlKey || event.metaKey)
    && event.key.toLowerCase() === "z"
  ) {
    event.preventDefault();
    undoLastEdit();
  } else if (event.key === "Enter" && selectedTextEditId && !isDrawTool()) {
    const textEdit = getSelectedTextEdit();
    const pageElement = textEdit
      ? findPageElement(pageContainer, textEdit.page_index)
      : null;
    if (textEdit && pageElement) {
      textDraftController.start(pageElement, {...textEdit}, textEdit.id);
    }
  }
});
window.addEventListener("resize", () => {
  updateRenderedTextSizes(pageContainer, textEdits);
  updateStreamlitFrameHeight();
});
announceComponentReady();
