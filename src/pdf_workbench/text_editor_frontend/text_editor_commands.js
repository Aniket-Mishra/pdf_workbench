import {clamp} from "./text_editor_state.js";

export function createTextEditorCommands(editor) {
  function changeFontSize() {
    const requestedFontSize = Number.parseInt(
      editor.fontSizeInput.value,
      10,
    );
    if (!Number.isFinite(requestedFontSize)) {
      editor.updateToolbar();
      return;
    }

    const fontSize = clamp(
      requestedFontSize,
      editor.getMinimumFontSize(),
      editor.getMaximumFontSize(),
    );
    editor.setDefaultFontSize(fontSize);
    const selectedTextEdit = editor.getSelectedTextEdit();
    if (!selectedTextEdit || selectedTextEdit.font_size === fontSize) {
      editor.updateToolbar();
      return;
    }

    editor.rememberTextEdits();
    selectedTextEdit.font_size = fontSize;
    editor.renderTextEdits();
    if (editor.keepTextInsidePage(selectedTextEdit)) {
      editor.renderTextEdits();
    }
    editor.showStatus("Text size changed.");
    editor.sendChange();
  }

  function deleteSelected() {
    const selectedMark = editor.getSelectedMark();
    if (selectedMark) {
      editor.rememberTextEdits();
      editor.replaceMarks(
        editor.getMarks().filter((mark) => mark.id !== selectedMark.id),
      );
      editor.setSelectedMarkId(null);
      editor.renderMarks();
      editor.showStatus("Drawing deleted.");
      editor.sendChange();
      return;
    }

    const selectedTextEditId = editor.getSelectedTextEditId();
    if (!selectedTextEditId) {
      return;
    }
    editor.rememberTextEdits();
    editor.replaceTextEdits(
      editor.getTextEdits().filter(
        (textEdit) => textEdit.id !== selectedTextEditId,
      ),
    );
    editor.setSelectedTextEditId(null);
    editor.renderTextEdits();
    editor.showStatus("Text deleted.");
    editor.sendChange();
  }

  function undoLastChange() {
    const previousState = editor.takePreviousTextEdits();
    if (!previousState) {
      return;
    }
    editor.finishDraft(false);
    editor.replaceTextEdits(previousState.textEdits);
    editor.replaceMarks(previousState.marks);
    editor.setSelectedTextEditId(null);
    editor.setSelectedMarkId(null);
    editor.renderTextEdits();
    editor.renderMarks();
    editor.showStatus("Last change undone.");
    editor.sendChange();
  }

  function clearEdits() {
    if (!editor.getTextEdits().length && !editor.getMarks().length) {
      return;
    }
    const shouldClear = window.confirm(
      "Remove everything added to this PDF?",
    );
    if (!shouldClear) {
      return;
    }

    editor.finishDraft(false);
    editor.cancelDrawing();
    editor.rememberTextEdits();
    editor.replaceTextEdits([]);
    editor.replaceMarks([]);
    editor.setSelectedTextEditId(null);
    editor.setSelectedMarkId(null);
    editor.renderTextEdits();
    editor.renderMarks();
    editor.showStatus("Everything added was removed.");
    editor.sendChange();
  }

  return {
    changeFontSize,
    clearEdits,
    deleteSelected,
    undoLastChange,
  };
}
