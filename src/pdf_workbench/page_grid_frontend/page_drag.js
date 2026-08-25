function shouldPlaceAfter(event, targetCard) {
  const bounds = targetCard.getBoundingClientRect();
  const middleY = bounds.top + bounds.height / 2;
  const nearMiddle = Math.abs(event.clientY - middleY) < bounds.height * 0.2;

  if (nearMiddle) {
    return event.clientX > bounds.left + bounds.width / 2;
  }
  return event.clientY > middleY;
}

export function createPageDragHandlers({
  grid,
  viewport,
  canReorder,
  movePage,
}) {
  let draggedPageId = null;
  let dragChangedPage = false;

  function clearDropStyles() {
    grid.querySelectorAll(".drop-before, .drop-after").forEach((card) => {
      card.classList.remove("drop-before", "drop-after");
    });
  }

  function finish() {
    draggedPageId = null;
    grid.querySelector(".dragging")?.classList.remove("dragging");
    clearDropStyles();
    window.setTimeout(() => {
      dragChangedPage = false;
    }, 150);
  }

  function start(event) {
    const card = event.target.closest(".page-card");
    if (!card || !canReorder()) {
      event.preventDefault();
      return;
    }
    draggedPageId = card.dataset.pageId;
    dragChangedPage = true;
    event.dataTransfer.effectAllowed = "move";
    event.dataTransfer.setData("text/plain", draggedPageId);
    requestAnimationFrame(() => card.classList.add("dragging"));
  }

  function over(event) {
    if (!draggedPageId) {
      return;
    }
    const targetCard = event.target.closest(".page-card");
    if (!targetCard || targetCard.dataset.pageId === draggedPageId) {
      clearDropStyles();
      return;
    }

    event.preventDefault();
    event.dataTransfer.dropEffect = "move";
    clearDropStyles();
    targetCard.classList.add(
      shouldPlaceAfter(event, targetCard) ? "drop-after" : "drop-before",
    );

    const bounds = viewport.getBoundingClientRect();
    if (event.clientY < bounds.top + 48) {
      viewport.scrollBy(0, -24);
    } else if (event.clientY > bounds.bottom - 48) {
      viewport.scrollBy(0, 24);
    }
  }

  function drop(event) {
    const targetCard = event.target.closest(".page-card");
    const targetPageId = targetCard?.dataset.pageId;
    if (!draggedPageId || !targetPageId || targetPageId === draggedPageId) {
      finish();
      return;
    }

    event.preventDefault();
    const sourcePageId = draggedPageId;
    const placeAfter = shouldPlaceAfter(event, targetCard);
    finish();
    movePage(sourcePageId, targetPageId, placeAfter);
  }

  function shouldIgnoreClick() {
    if (!dragChangedPage) {
      return false;
    }
    dragChangedPage = false;
    return true;
  }

  return {start, over, drop, finish, shouldIgnoreClick};
}
