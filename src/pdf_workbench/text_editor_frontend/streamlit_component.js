let actionSequence = 0;

export function sendEditorState(textEdits, action) {
  actionSequence += 1;
  sendStreamlitMessage("streamlit:setComponentValue", {
    value: {
      text_edits: textEdits,
      action,
      action_id: `${action}:${Date.now()}:${actionSequence}`,
    },
    dataType: "json",
  });
}

export function applyStreamlitTheme(theme) {
  if (!theme) {
    return;
  }
  const rootStyle = document.documentElement.style;
  rootStyle.setProperty("--background", theme.backgroundColor);
  rootStyle.setProperty("--foreground", theme.textColor);
  rootStyle.setProperty("--muted-background", theme.secondaryBackgroundColor);
  rootStyle.setProperty("--viewer-background", theme.secondaryBackgroundColor);
  rootStyle.setProperty("--primary", theme.primaryColor);
  rootStyle.setProperty("--focus", theme.primaryColor);
  rootStyle.fontFamily = theme.font;
}

export function updateStreamlitFrameHeight() {
  sendStreamlitMessage("streamlit:setFrameHeight", {
    height: document.documentElement.scrollHeight,
  });
}

export function announceComponentReady() {
  sendStreamlitMessage("streamlit:componentReady", {apiVersion: 1});
}

function sendStreamlitMessage(type, extra = {}) {
  window.parent.postMessage(
    {isStreamlitMessage: true, type, ...extra},
    "*",
  );
}
