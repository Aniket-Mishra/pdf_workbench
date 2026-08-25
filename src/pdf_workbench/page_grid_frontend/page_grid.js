import {
  containSamePageIds,
  copyPagePlacements,
  deletePages,
  duplicatePages,
  movePage,
  movePageBy,
  restoreOriginalPages,
  rotatePages,
} from "./organizer_actions.js";
import {createPageCard} from "./page_card.js";
import {createPageDragHandlers} from "./page_drag.js";

const grid = document.getElementById("grid");
const viewport = document.getElementById("viewport");
const documentLegend = document.getElementById("document-legend");
const organizerActions = document.getElementById("organizer-actions");
const orderStatus = document.getElementById("order-status");
const undoButton = document.getElementById("undo-change");
const rotateLeftButton = document.getElementById("rotate-left");
const rotateRightButton = document.getElementById("rotate-right");
const duplicateButton = document.getElementById("duplicate-pages");
const deleteButton = document.getElementById("delete-pages");
const resetOrderButton = document.getElementById("reset-order");
const buildPdfButton = document.getElementById("build-pdf");

let pageSources = [];
let orderedPages = [];
let resetOrderIds = [];
let selectedPageIds = new Set();
let organizerHistory = [];
let selectable = false;
let reorderable = false;
let copySequence = 0;
let lastFrameHeight = 0;
let initialized = false;

function sendStreamlitMessage(type, extra = {}) {
  window.parent.postMessage(
    {isStreamlitMessage: true, type, ...extra},
    "*",
  );
}

function sendGridState(action = null) {
  sendStreamlitMessage("streamlit:setComponentValue", {
    value: {
      ordered_pages: orderedPages,
      selected_ids: orderedPages
        .map((page) => page.id)
        .filter((pageId) => selectedPageIds.has(pageId)),
      action,
      action_id: action ? `${action}:${Date.now()}` : null,
    },
    dataType: "json",
  });
}

function showStatus(message) {
  orderStatus.textContent = message;
}

function rememberOrganizerState() {
  organizerHistory.push({
    orderedPages: copyPagePlacements(orderedPages),
    selectedPageIds: [...selectedPageIds],
  });
  if (organizerHistory.length > 30) {
    organizerHistory.shift();
  }
}

function updateActionButtons() {
  const hasSelection = selectedPageIds.size > 0;
  undoButton.disabled = organizerHistory.length === 0;
  rotateLeftButton.disabled = !hasSelection;
  rotateRightButton.disabled = !hasSelection;
  duplicateButton.disabled = !hasSelection;
  deleteButton.disabled = !hasSelection;
}

function updateFrameHeight() {
  const legendHeight = documentLegend.hidden
    ? 0
    : documentLegend.offsetHeight + 8;
  const actionsHeight = organizerActions.hidden
    ? 0
    : organizerActions.offsetHeight + 12;
  const frameHeight = legendHeight + viewport.offsetHeight + actionsHeight + 2;
  if (frameHeight === lastFrameHeight) {
    return;
  }
  lastFrameHeight = frameHeight;
  sendStreamlitMessage("streamlit:setFrameHeight", {height: frameHeight});
}

function renderDocumentLegend() {
  const documentsByNumber = new Map();
  pageSources.forEach((sourcePage) => {
    if (sourcePage.document_number && sourcePage.document_name) {
      documentsByNumber.set(
        sourcePage.document_number,
        sourcePage.document_name,
      );
    }
  });

  const documents = [...documentsByNumber.entries()];
  documentLegend.hidden = documents.length < 2;
  if (documentLegend.hidden) {
    documentLegend.replaceChildren();
    return;
  }

  const legendItems = documents.map(([documentNumber, documentName]) => {
    const item = document.createElement("span");
    item.className = "document-legend-item";
    item.dataset.documentColor = ((documentNumber - 1) % 8) + 1;
    item.title = documentName;

    const number = document.createElement("span");
    number.className = "document-legend-number";
    number.textContent = documentNumber;

    const name = document.createElement("span");
    name.className = "document-legend-name";
    name.textContent = documentName;
    item.append(number, name);
    return item;
  });
  documentLegend.replaceChildren(...legendItems);
}

function moveFocusedPage(pageId, distance) {
  const nextPages = movePageBy(orderedPages, pageId, distance);
  if (!nextPages) {
    return;
  }

  rememberOrganizerState();
  orderedPages = nextPages;
  renderGrid(pageId);
  showStatus("Order changed");
}

function togglePage(pageId) {
  if (!selectable) {
    return;
  }
  if (selectedPageIds.has(pageId)) {
    selectedPageIds.delete(pageId);
  } else {
    selectedPageIds.add(pageId);
  }
  renderGrid(pageId);
  showStatus(`${selectedPageIds.size} selected`);
  if (!reorderable) {
    sendGridState();
  }
}

function moveDraggedPage(sourcePageId, targetPageId, placeAfter) {
  rememberOrganizerState();
  orderedPages = movePage(
    orderedPages,
    sourcePageId,
    targetPageId,
    placeAfter,
  );
  renderGrid(sourcePageId);
  showStatus("Order changed");
}

function findEventPageId(event) {
  return event.target.closest(".page-card")?.dataset.pageId;
}

function handlePageClick(event) {
  const pageId = findEventPageId(event);
  if (!pageId || pageDragHandlers.shouldIgnoreClick()) {
    return;
  }
  togglePage(pageId);
}

function handlePageKeyDown(event) {
  const pageId = findEventPageId(event);
  if (!pageId) {
    return;
  }
  if (selectable && (event.key === "Enter" || event.key === " ")) {
    event.preventDefault();
    togglePage(pageId);
    return;
  }
  if (!reorderable || !event.altKey) {
    return;
  }
  if (event.key === "ArrowLeft") {
    event.preventDefault();
    moveFocusedPage(pageId, -1);
  } else if (event.key === "ArrowRight") {
    event.preventDefault();
    moveFocusedPage(pageId, 1);
  }
}

function renderGrid(focusPageId = null) {
  const pageSourcesById = new Map(
    pageSources.map((sourcePage) => [sourcePage.id, sourcePage]),
  );
  const cards = orderedPages.map((page) => (
    createPageCard(
      page,
      pageSourcesById.get(page.source_id),
      selectedPageIds.has(page.id),
      selectable,
      reorderable,
    )
  ));
  grid.replaceChildren(...cards);

  if (focusPageId) {
    const selector = `[data-page-id="${CSS.escape(focusPageId)}"]`;
    grid.querySelector(selector)?.focus();
  }
  updateActionButtons();
  requestAnimationFrame(updateFrameHeight);
}

function rotateSelectedPages(degrees) {
  if (!selectedPageIds.size) {
    return;
  }
  rememberOrganizerState();
  orderedPages = rotatePages(orderedPages, selectedPageIds, degrees);
  renderGrid();
  showStatus("Selected pages rotated");
}

function duplicateSelectedPages() {
  if (!selectedPageIds.size) {
    return;
  }
  rememberOrganizerState();

  const copyTime = Date.now();
  const createPageId = () => {
    copySequence += 1;
    return `copy-${copyTime}-${copySequence}`;
  };
  const duplicateResult = duplicatePages(
    orderedPages,
    selectedPageIds,
    createPageId,
  );

  orderedPages = duplicateResult.pages;
  selectedPageIds = new Set(duplicateResult.duplicatedPageIds);
  renderGrid(duplicateResult.duplicatedPageIds[0]);
  showStatus(`${duplicateResult.duplicatedPageIds.length} page(s) duplicated`);
}

function deleteSelectedPages() {
  if (!selectedPageIds.size) {
    return;
  }
  if (selectedPageIds.size === orderedPages.length) {
    showStatus("Keep at least one page");
    return;
  }

  rememberOrganizerState();
  const deletedPageCount = selectedPageIds.size;
  orderedPages = deletePages(orderedPages, selectedPageIds);
  selectedPageIds.clear();
  renderGrid();
  showStatus(`${deletedPageCount} page(s) deleted`);
}

function undoOrganizerChange() {
  const previousState = organizerHistory.pop();
  if (!previousState) {
    return;
  }
  orderedPages = previousState.orderedPages;
  selectedPageIds = new Set(previousState.selectedPageIds);
  renderGrid();
  showStatus("Last change undone");
}

function resetOrganizer() {
  rememberOrganizerState();
  orderedPages = restoreOriginalPages(resetOrderIds);
  selectedPageIds.clear();
  renderGrid();
  showStatus("Original pages restored");
}

function applyTheme(theme) {
  if (!theme) {
    return;
  }
  const rootStyle = document.documentElement.style;
  rootStyle.setProperty("--primary-color", theme.primaryColor);
  rootStyle.setProperty(
    "--secondary-background-color",
    theme.secondaryBackgroundColor,
  );
  rootStyle.setProperty("--text-color", theme.textColor);
  rootStyle.fontFamily = theme.font;
}

window.addEventListener("message", (event) => {
  if (event.data.type !== "streamlit:render") {
    return;
  }
  const componentArguments = event.data.args;
  const incomingPages = componentArguments.ordered_pages;
  const pagesChanged = !initialized
    || !containSamePageIds(orderedPages, incomingPages);

  pageSources = componentArguments.pages;
  resetOrderIds = componentArguments.reset_order_ids;
  renderDocumentLegend();
  if (pagesChanged) {
    orderedPages = incomingPages.map((page) => ({...page}));
    selectedPageIds = new Set(componentArguments.selected_ids);
    organizerHistory = [];
  }
  initialized = true;
  selectable = componentArguments.selectable;
  reorderable = componentArguments.reorderable;
  document.body.classList.toggle("organizer", reorderable);
  organizerActions.hidden = !reorderable;
  applyTheme(event.data.theme);
  renderGrid();
  requestAnimationFrame(updateFrameHeight);
});

const pageDragHandlers = createPageDragHandlers({
  grid,
  viewport,
  canReorder: () => reorderable,
  movePage: moveDraggedPage,
});
grid.addEventListener("click", handlePageClick);
grid.addEventListener("keydown", handlePageKeyDown);
grid.addEventListener("dragstart", pageDragHandlers.start);
grid.addEventListener("dragover", pageDragHandlers.over);
grid.addEventListener("drop", pageDragHandlers.drop);
grid.addEventListener("dragend", pageDragHandlers.finish);
undoButton.addEventListener("click", undoOrganizerChange);
rotateLeftButton.addEventListener("click", () => rotateSelectedPages(-90));
rotateRightButton.addEventListener("click", () => rotateSelectedPages(90));
duplicateButton.addEventListener("click", duplicateSelectedPages);
deleteButton.addEventListener("click", deleteSelectedPages);
resetOrderButton.addEventListener("click", resetOrganizer);
buildPdfButton.addEventListener("click", () => {
  showStatus("Building PDF");
  sendGridState("build");
});
document.addEventListener("keydown", (event) => {
  if (!reorderable || (!event.ctrlKey && !event.metaKey)) {
    return;
  }
  if (event.key.toLowerCase() === "z") {
    event.preventDefault();
    undoOrganizerChange();
  }
});
new ResizeObserver(updateFrameHeight).observe(viewport);
new ResizeObserver(updateFrameHeight).observe(documentLegend);
sendStreamlitMessage("streamlit:componentReady", {apiVersion: 1});
