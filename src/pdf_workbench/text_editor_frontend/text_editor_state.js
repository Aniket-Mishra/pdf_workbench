export function clamp(value, minimum, maximum) {
  return Math.min(Math.max(value, minimum), maximum);
}

export function copyTextEdits(textEdits) {
  return textEdits.map((textEdit) => ({...textEdit}));
}

let textEditSequence = 0;

export function createTextEditId() {
  textEditSequence += 1;
  return `text-${Date.now()}-${textEditSequence}`;
}
