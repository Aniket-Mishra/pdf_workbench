import {clamp} from "./text_editor_state.js";

export function renderPdfPages(pageContainer, pages) {
  const pageElements = pages.map((page) => {
    const wrapper = document.createElement("section");
    wrapper.className = "page-wrapper";
    wrapper.setAttribute("aria-label", `Page ${page.page_index + 1}`);

    const pageElement = document.createElement("div");
    pageElement.className = "pdf-page";
    pageElement.dataset.pageIndex = page.page_index;
    pageElement.dataset.widthPoints = page.width_points;
    pageElement.dataset.heightPoints = page.height_points;
    pageElement.style.aspectRatio = (
      `${page.width_points} / ${page.height_points}`
    );

    const pageImage = document.createElement("img");
    pageImage.src = page.image;
    pageImage.alt = `Page ${page.page_index + 1}`;
    pageImage.draggable = false;
    pageImage.decoding = "async";

    const textLayer = document.createElement("div");
    textLayer.className = "text-layer";
    pageElement.append(pageImage, textLayer);

    const pageNumber = document.createElement("span");
    pageNumber.className = "page-number";
    pageNumber.textContent = `Page ${page.page_index + 1}`;
    wrapper.append(pageElement, pageNumber);
    return wrapper;
  });
  pageContainer.replaceChildren(...pageElements);
}

export function renderTextEdits(
  pageContainer,
  textEdits,
  selectedTextEditId,
) {
  pageContainer.querySelectorAll(".text-layer").forEach((textLayer) => {
    textLayer.replaceChildren();
  });

  textEdits.forEach((textEdit) => {
    const pageElement = findPageElement(
      pageContainer,
      textEdit.page_index,
    );
    if (!pageElement) {
      return;
    }

    const textElement = document.createElement("span");
    textElement.className = "text-edit";
    textElement.dataset.textEditId = textEdit.id;
    textElement.tabIndex = 0;
    textElement.setAttribute("role", "button");
    textElement.setAttribute(
      "aria-label",
      `${textEdit.text}. Drag to move. Double click to edit.`,
    );
    textElement.classList.toggle(
      "selected",
      textEdit.id === selectedTextEditId,
    );
    textElement.textContent = textEdit.text;
    positionTextElement(textElement, textEdit);
    pageElement.querySelector(".text-layer").append(textElement);
  });
  updateRenderedTextSizes(pageContainer, textEdits);
}

export function updateRenderedTextSizes(pageContainer, textEdits) {
  textEdits.forEach((textEdit) => {
    const pageElement = findPageElement(
      pageContainer,
      textEdit.page_index,
    );
    const textElement = pageContainer.querySelector(
      `[data-text-edit-id="${CSS.escape(textEdit.id)}"]`,
    );
    if (!pageElement || !textElement) {
      return;
    }

    const pageWidthPoints = Number(pageElement.dataset.widthPoints);
    const pageScale = pageElement.clientWidth / pageWidthPoints;
    textElement.style.fontSize = `${textEdit.font_size * pageScale}px`;
  });
}

export function calculatePagePosition(event, pageElement, fontSize) {
  const pageBounds = pageElement.getBoundingClientRect();
  const pageHeightPoints = Number(pageElement.dataset.heightPoints);
  const maximumVerticalPosition = Math.max(
    0,
    1 - fontSize / pageHeightPoints,
  );
  return {
    horizontalPosition: clamp(
      (event.clientX - pageBounds.left) / pageBounds.width,
      0,
      1,
    ),
    verticalPosition: clamp(
      (event.clientY - pageBounds.top) / pageBounds.height,
      0,
      maximumVerticalPosition,
    ),
  };
}

export function createDraftInput(
  pageElement,
  textEdit,
  maximumTextLength,
) {
  const draftInput = document.createElement("input");
  draftInput.className = "draft-text";
  draftInput.type = "text";
  draftInput.maxLength = maximumTextLength;
  draftInput.value = textEdit.text;
  draftInput.setAttribute("aria-label", "Text to add");
  positionTextElement(draftInput, textEdit);

  const pageWidthPoints = Number(pageElement.dataset.widthPoints);
  const pageScale = pageElement.clientWidth / pageWidthPoints;
  draftInput.style.fontSize = `${textEdit.font_size * pageScale}px`;
  pageElement.querySelector(".text-layer").append(draftInput);
  return draftInput;
}

export function positionTextElement(textElement, textEdit) {
  textElement.style.left = `${textEdit.horizontal_position * 100}%`;
  textElement.style.top = `${textEdit.vertical_position * 100}%`;
}

export function findPageElement(pageContainer, pageIndex) {
  return pageContainer.querySelector(
    `[data-page-index="${pageIndex}"]`,
  );
}
