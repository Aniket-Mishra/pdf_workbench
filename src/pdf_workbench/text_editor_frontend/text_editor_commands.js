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

  function deleteSelectedText() {
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

  function undoTextChange() {
    const previousTextEdits = editor.takePreviousTextEdits();
    if (!previousTextEdits) {
      return;
    }
    editor.finishDraft(false);
    editor.replaceTextEdits(previousTextEdits);
    editor.setSelectedTextEditId(null);
    editor.renderTextEdits();
    editor.showStatus("Last change undone.");
    editor.sendChange();
  }

  function clearTextEdits() {
    if (!editor.getTextEdits().length) {
      return;
    }
    const shouldClear = window.confirm(
      "Remove all added text from this PDF?",
    );
    if (!shouldClear) {
      return;
    }

    editor.finishDraft(false);
    editor.rememberTextEdits();
    editor.replaceTextEdits([]);
    editor.setSelectedTextEditId(null);
    editor.renderTextEdits();
    editor.showStatus("All added text removed.");
    editor.sendChange();
  }

  return {
    changeFontSize,
    clearTextEdits,
    deleteSelectedText,
    undoTextChange,
  };
}
