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
  announceComponentReady,
  applyStreamlitTheme,
  sendEditorState as sendStreamlitEditorState,
  updateStreamlitFrameHeight,
} from "./streamlit_component.js";

const pageContainer = document.getElementById("pages");
const viewport = document.getElementById("viewport");
const addTextButton = document.getElementById("add-text");
const fontSizeInput = document.getElementById("font-size");
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
let textEditHistory = [];
let selectedTextEditId = null;
let addTextMode = false;
let defaultFontSize = 18;
let minimumFontSize = 8;
let maximumFontSize = 72;
let maximumTextLength = 500;
let loadingMorePages = false;

function sendEditorState(action) {
  updateToolbar();
  sendStreamlitEditorState(textEdits, action);
}

function showStatus(message) {
  status.textContent = message;
}

function rememberTextEdits(previousTextEdits = textEdits) {
  textEditHistory.push(copyTextEdits(previousTextEdits));
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

function updateToolbar() {
  const selectedTextEdit = getSelectedTextEdit();
  addTextButton.setAttribute("aria-pressed", String(addTextMode));
  undoButton.disabled = textEditHistory.length === 0;
  deleteTextButton.disabled = !selectedTextEdit;
  clearTextButton.disabled = textEdits.length === 0;
  buildPdfButton.disabled = textEdits.length === 0;
  fontSizeInput.value = selectedTextEdit
    ? selectedTextEdit.font_size
    : defaultFontSize;
}

function renderCurrentTextEdits() {
  renderTextEdits(pageContainer, textEdits, selectedTextEditId);
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

function selectTextEdit(textEditId) {
  selectedTextEditId = textEditId;
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

function setAddTextMode(enabled) {
  addTextMode = enabled;
  document.body.classList.toggle("add-text-mode", enabled);
  updateToolbar();
  showStatus(
    enabled
      ? "Click a page and type. Press Enter to place the text."
      : "Choose Add text to place text.",
  );
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
  setSelectedTextEditId: (textEditId) => {
    selectedTextEditId = textEditId;
  },
  showStatus,
});

function handlePageClick(event) {
  if (event.target.closest(".draft-text")) {
    return;
  }

  const textElement = event.target.closest(".text-edit");
  if (textElement) {
    selectTextEdit(textElement.dataset.textEditId);
    return;
  }

  const pageElement = event.target.closest(".pdf-page");
  if (!pageElement || !addTextMode) {
    selectTextEdit(null);
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
  setSelectedTextEditId: (textEditId) => {
    selectedTextEditId = textEditId;
  },
  showStatus,
  updateToolbar,
});

const textEditorCommands = createTextEditorCommands({
  fontSizeInput,
  finishDraft: textDraftController.finish,
  getMaximumFontSize: () => maximumFontSize,
  getMinimumFontSize: () => minimumFontSize,
  getSelectedTextEdit,
  getSelectedTextEditId: () => selectedTextEditId,
  getTextEdits: () => textEdits,
  keepTextInsidePage,
  rememberTextEdits,
  renderTextEdits: renderCurrentTextEdits,
  replaceTextEdits: (replacementTextEdits) => {
    textEdits = replacementTextEdits;
  },
  sendChange: () => sendEditorState("change"),
  setDefaultFontSize: (fontSize) => {
    defaultFontSize = fontSize;
  },
  setSelectedTextEditId: (textEditId) => {
    selectedTextEditId = textEditId;
  },
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
  const documentChanged = incomingDocumentId !== documentId;
  const pagesChanged = documentChanged
    || incomingPages.length !== pages.length;

  documentId = incomingDocumentId;
  pageCount = componentArguments.page_count;
  minimumFontSize = componentArguments.minimum_font_size;
  maximumFontSize = componentArguments.maximum_font_size;
  maximumTextLength = componentArguments.maximum_text_length;
  fontSizeInput.min = minimumFontSize;
  fontSizeInput.max = maximumFontSize;
  applyStreamlitTheme(event.data.theme);

  if (documentChanged) {
    textEdits = copyTextEdits(incomingTextEdits);
    textEditHistory = [];
    selectedTextEditId = null;
    setAddTextMode(false);
  }

  if (pagesChanged) {
    const previousScrollPosition = viewport.scrollTop;
    pages = incomingPages;
    renderPdfPages(pageContainer, pages);
    renderCurrentTextEdits();
    viewport.scrollTop = previousScrollPosition;
  }

  loadingMorePages = false;
  loadingStatus.hidden = true;
  updateToolbar();
  if (componentArguments.download_ready) {
    showStatus("PDF ready to download below.");
  }
  requestAnimationFrame(() => {
    updateRenderedTextSizes(pageContainer, textEdits);
    requestMorePages();
    updateStreamlitFrameHeight();
  });
});

pageContainer.addEventListener("click", handlePageClick);
pageContainer.addEventListener("dblclick", handleTextDoubleClick);
pageContainer.addEventListener("pointerdown", textDragHandlers.begin);
pageContainer.addEventListener("pointermove", textDragHandlers.move);
pageContainer.addEventListener("pointerup", textDragHandlers.finish);
pageContainer.addEventListener("pointercancel", (event) => {
  textDragHandlers.finish(event, true);
});
viewport.addEventListener("scroll", requestMorePages, {passive: true});
addTextButton.addEventListener("click", () => {
  setAddTextMode(!addTextMode);
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
undoButton.addEventListener("click", textEditorCommands.undoTextChange);
deleteTextButton.addEventListener(
  "click",
  textEditorCommands.deleteSelectedText,
);
clearTextButton.addEventListener(
  "click",
  textEditorCommands.clearTextEdits,
);
buildPdfButton.addEventListener("click", () => {
  textDraftController.finish(true);
  if (textEdits.length) {
    showStatus("Creating PDF.");
    sendEditorState("build");
  }
});
document.addEventListener("keydown", (event) => {
  if (event.target.matches("input")) {
    return;
  }
  if (event.key === "Escape") {
    setAddTextMode(false);
  } else if (
    event.key === "Delete"
    || event.key === "Backspace"
  ) {
    event.preventDefault();
    textEditorCommands.deleteSelectedText();
  } else if (
    (event.ctrlKey || event.metaKey)
    && event.key.toLowerCase() === "z"
  ) {
    event.preventDefault();
    textEditorCommands.undoTextChange();
  } else if (event.key === "Enter" && selectedTextEditId) {
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
