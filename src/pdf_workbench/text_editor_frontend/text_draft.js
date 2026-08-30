import {createDraftInput} from "./text_editor_view.js";

export function createTextDraftController(editor) {
  let draftState = null;

  function finish(saveText) {
    if (!draftState) {
      return;
    }

    const {draftInput, textEditId, pendingTextEdit} = draftState;
    const text = draftInput.value.trim();
    draftState = null;
    draftInput.remove();
    if (!saveText || !text) {
      editor.renderTextEdits();
      return;
    }

    const existingTextEdit = editor.findTextEdit(textEditId);
    if (existingTextEdit?.text === text) {
      editor.renderTextEdits();
      return;
    }

    editor.rememberTextEdits();
    let savedTextEdit;
    if (existingTextEdit) {
      existingTextEdit.text = text;
      editor.setSelectedTextEditId(existingTextEdit.id);
      savedTextEdit = existingTextEdit;
    } else {
      pendingTextEdit.text = text;
      editor.getTextEdits().push(pendingTextEdit);
      editor.setSelectedTextEditId(pendingTextEdit.id);
      savedTextEdit = pendingTextEdit;
    }
    editor.renderTextEdits();
    if (editor.keepTextInsidePage(savedTextEdit)) {
      editor.renderTextEdits();
    }
    editor.showStatus("Text saved.");
    editor.sendChange();
  }

  function start(pageElement, pendingTextEdit, textEditId = null) {
    finish(true);
    editor.setSelectedTextEditId(textEditId);
    editor.renderTextEdits();

    const draftInput = createDraftInput(
      pageElement,
      pendingTextEdit,
      editor.getMaximumTextLength(),
    );
    const existingTextElement = textEditId
      ? editor.pageContainer.querySelector(
        `[data-text-edit-id="${CSS.escape(textEditId)}"]`,
      )
      : null;
    if (existingTextElement) {
      existingTextElement.hidden = true;
    }

    draftState = {draftInput, textEditId, pendingTextEdit};
    draftInput.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        finish(true);
      } else if (event.key === "Escape") {
        event.preventDefault();
        finish(false);
      }
    });
    draftInput.addEventListener("blur", () => finish(true));
    draftInput.focus();
    draftInput.select();
  }

  return {finish, start};
}
