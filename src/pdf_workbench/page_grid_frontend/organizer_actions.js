export function copyPagePlacements(pages) {
  return pages.map((page) => ({...page}));
}

export function containSamePageIds(currentPages, incomingPages) {
  if (incomingPages.length !== currentPages.length) {
    return false;
  }
  const currentPageIds = new Set(currentPages.map((page) => page.id));
  return incomingPages.every((page) => currentPageIds.has(page.id));
}

export function movePage(pages, pageId, targetPageId, placeAfter) {
  const nextPages = copyPagePlacements(pages);
  const sourceIndex = nextPages.findIndex((page) => page.id === pageId);
  let targetIndex = nextPages.findIndex((page) => page.id === targetPageId);
  targetIndex += Number(placeAfter);

  const [sourcePage] = nextPages.splice(sourceIndex, 1);
  if (sourceIndex < targetIndex) {
    targetIndex -= 1;
  }
  nextPages.splice(targetIndex, 0, sourcePage);
  return nextPages;
}

export function movePageBy(pages, pageId, distance) {
  const sourceIndex = pages.findIndex((page) => page.id === pageId);
  const targetIndex = sourceIndex + distance;
  if (targetIndex < 0 || targetIndex >= pages.length) {
    return null;
  }

  const nextPages = copyPagePlacements(pages);
  [nextPages[sourceIndex], nextPages[targetIndex]] = [
    nextPages[targetIndex],
    nextPages[sourceIndex],
  ];
  return nextPages;
}

export function rotatePages(pages, selectedPageIds, degrees) {
  return pages.map((page) => (
    selectedPageIds.has(page.id)
      ? {...page, rotation: (page.rotation + degrees + 360) % 360}
      : page
  ));
}

export function duplicatePages(pages, selectedPageIds, createPageId) {
  const duplicatedPageIds = [];
  const nextPages = [];

  pages.forEach((page) => {
    nextPages.push(page);
    if (!selectedPageIds.has(page.id)) {
      return;
    }
    const duplicate = {...page, id: createPageId()};
    nextPages.push(duplicate);
    duplicatedPageIds.push(duplicate.id);
  });

  return {pages: nextPages, duplicatedPageIds};
}

export function deletePages(pages, selectedPageIds) {
  return pages.filter((page) => !selectedPageIds.has(page.id));
}

export function restoreOriginalPages(pageIds) {
  return pageIds.map((pageId) => ({
    id: pageId,
    source_id: pageId,
    rotation: 0,
  }));
}
