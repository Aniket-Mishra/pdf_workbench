export function createPageCard(
  page,
  sourcePage,
  selected,
  selectable,
  reorderable,
) {
  const card = document.createElement("div");
  const isCopy = page.id !== page.source_id;
  const pageDescription = sourcePage.document_name
    ? `${sourcePage.document_name}, ${sourcePage.caption}`
    : sourcePage.caption;
  card.tabIndex = 0;
  card.setAttribute("role", "button");
  card.className = [
    "page-card",
    selected ? "selected" : "",
    reorderable ? "reorderable" : "",
  ].filter(Boolean).join(" ");
  card.dataset.pageId = page.id;
  card.draggable = reorderable;
  if (sourcePage.document_number) {
    card.dataset.documentColor = (
      (sourcePage.document_number - 1) % 8
    ) + 1;
  }
  if (selectable) {
    card.setAttribute("aria-pressed", String(selected));
  }
  card.setAttribute(
    "aria-label",
    [
      pageDescription,
      isCopy ? "copy" : "",
      page.rotation ? `rotated ${page.rotation} degrees` : "",
      selected ? "selected" : "",
      reorderable ? "drag to reorder" : "",
    ].filter(Boolean).join(", "),
  );
  if (reorderable) {
    card.title = `${pageDescription}. Click to select. Drag to reorder.`;
  }

  const imageFrame = document.createElement("span");
  imageFrame.className = "page-image";
  if (sourcePage.image) {
    const image = document.createElement("img");
    image.src = sourcePage.image;
    image.alt = "";
    image.loading = "lazy";
    image.decoding = "async";
    image.draggable = false;
    if (page.rotation) {
      const scale = page.rotation % 180 === 0 ? 1 : 0.75;
      image.style.transform = `rotate(${page.rotation}deg) scale(${scale})`;
    }
    imageFrame.append(image);
  } else {
    const loadingLabel = document.createElement("span");
    loadingLabel.className = "page-loading";
    loadingLabel.textContent = "Loading preview";
    imageFrame.append(loadingLabel);
  }
  if (sourcePage.document_number) {
    const documentBadge = document.createElement("span");
    documentBadge.className = "document-badge";
    documentBadge.textContent = sourcePage.document_number;
    documentBadge.setAttribute("aria-hidden", "true");
    imageFrame.append(documentBadge);
  }

  const caption = document.createElement("span");
  caption.className = "page-caption";
  caption.textContent = sourcePage.caption + (isCopy ? " copy" : "");

  const selectedLabel = document.createElement("span");
  selectedLabel.className = "selected-label";
  selectedLabel.textContent = "Selected";
  card.append(imageFrame, caption, selectedLabel);
  return card;
}
