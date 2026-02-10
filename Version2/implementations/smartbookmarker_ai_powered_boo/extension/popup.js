const endpointInput = document.getElementById("endpoint");
const saveButton = document.getElementById("save");
const statusEl = document.getElementById("status");
const DEFAULT_ENDPOINT = "http://127.0.0.1:8787/api/save";

chrome.storage.sync.get({ backend_endpoint: DEFAULT_ENDPOINT }, (items) => {
  endpointInput.value = items.backend_endpoint || DEFAULT_ENDPOINT;
});

saveButton.addEventListener("click", () => {
  const endpoint = (endpointInput.value || DEFAULT_ENDPOINT).trim();
  chrome.storage.sync.set({ backend_endpoint: endpoint }, () => {
    statusEl.textContent = "Saved.";
    setTimeout(() => {
      statusEl.textContent = "";
    }, 1500);
  });
});
