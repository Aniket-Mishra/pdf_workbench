import {clamp, copyTextEdits} from "./text_editor_state.js";
import {positionTextElement} from "./text_editor_view.js";

export function createTextDragHandlers(editor) {
  let dragState = null;

  function begin(event) {
    const textElement = event.target.closest(".text-edit");
    if (!textElement || event.button !== 0) {
      return;
    }

    const textEdit = editor.findTextEdit(textElement.dataset.textEditId);
    const pageElement = textElement.closest(".pdf-page");
    if (!textEdit || !pageElement) {
      return;
    }

    editor.setSelectedTextEditId(textEdit.id);
    editor.pageContainer.querySelectorAll(".text-edit").forEach((element) => {
      element.classList.toggle(
        "selected",
        element.dataset.textEditId === textEdit.id,
      );
    });
    dragState = {
      pointerId: event.pointerId,
      textElement,
      textEdit,
      pageBounds: pageElement.getBoundingClientRect(),
      startClientX: event.clientX,
      startClientY: event.clientY,
      startHorizontalPosition: textEdit.horizontal_position,
      startVerticalPosition: textEdit.vertical_position,
      previousTextEdits: copyTextEdits(editor.getTextEdits()),
      moved: false,
    };
    textElement.classList.add("dragging");
    textElement.setPointerCapture(event.pointerId);
    editor.updateToolbar();
  }

  function move(event) {
    if (!dragState || event.pointerId !== dragState.pointerId) {
      return;
    }

    const horizontalDistance = event.clientX - dragState.startClientX;
    const verticalDistance = event.clientY - dragState.startClientY;
    if (Math.abs(horizontalDistance) + Math.abs(verticalDistance) > 3) {
      dragState.moved = true;
      event.preventDefault();
    }

    const maximumHorizontalPosition = Math.max(
      0,
      1 - dragState.textElement.offsetWidth / dragState.pageBounds.width,
    );
    const maximumVerticalPosition = Math.max(
      0,
      1 - dragState.textElement.offsetHeight / dragState.pageBounds.height,
    );
    dragState.textEdit.horizontal_position = clamp(
      dragState.startHorizontalPosition
        + horizontalDistance / dragState.pageBounds.width,
      0,
      maximumHorizontalPosition,
    );
    dragState.textEdit.vertical_position = clamp(
      dragState.startVerticalPosition
        + verticalDistance / dragState.pageBounds.height,
      0,
      maximumVerticalPosition,
    );
    positionTextElement(dragState.textElement, dragState.textEdit);
  }

  function finish(event, cancelMove = false) {
    if (!dragState || event.pointerId !== dragState.pointerId) {
      return;
    }

    const completedDragState = dragState;
    dragState = null;
    completedDragState.textElement.classList.remove("dragging");
    if (!completedDragState.moved && !cancelMove) {
      return;
    }
    if (cancelMove) {
      editor.replaceTextEdits(completedDragState.previousTextEdits);
      editor.renderTextEdits();
      return;
    }

    editor.rememberTextEdits(completedDragState.previousTextEdits);
    editor.renderTextEdits();
    editor.showStatus("Text moved.");
    editor.sendChange();
  }

  return {begin, move, finish};
}
