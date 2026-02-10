const MENU_ID = "smartbookmarker_save_selection";
const DEFAULT_ENDPOINT = "http://127.0.0.1:8787/api/save";

chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: MENU_ID,
    title: "Send selected text to SmartBookmarker",
    contexts: ["selection"]
  });
});

function getEndpoint() {
  return new Promise((resolve) => {
    chrome.storage.sync.get({ backend_endpoint: DEFAULT_ENDPOINT }, (items) => {
      resolve(items.backend_endpoint || DEFAULT_ENDPOINT);
    });
  });
}

chrome.contextMenus.onClicked.addListener(async (info) => {
  if (info.menuItemId !== MENU_ID) {
    return;
  }
  const selectedText = (info.selectionText || "").trim();
  if (!selectedText) {
    return;
  }

  const endpoint = await getEndpoint();
  try {
    const response = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: selectedText })
    });
    const payload = await response.json();
    if (!response.ok || !payload.ok) {
      throw new Error(payload.error || "save_failed");
    }
    chrome.notifications.create({
      type: "basic",
      iconUrl: "icon.png",
      title: "SmartBookmarker",
      message: `Saved to ${payload.note.category}`
    });
  } catch (err) {
    chrome.notifications.create({
      type: "basic",
      iconUrl: "icon.png",
      title: "SmartBookmarker",
      message: `Failed to save selection: ${String(err)}`
    });
  }
});
