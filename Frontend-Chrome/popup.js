let checkboxInput = document.getElementById("checkbox-input");
let urlInput = document.getElementById("url-input-field");
let cachedPanels = true;

chrome.storage.local.get("cachedPanels", ({ cachedPanels: value }) => {
  if (value !== undefined) {
    cachedPanels = value;
    checkboxInput.checked = cachedPanels
  }
});

chrome.storage.local.get("baseURL").then((result) => {
  let baseUrl = result.baseURL || "";
  urlInput.value = baseUrl;
});

urlInput.addEventListener("change", (event) => {
  const baseURL = event.target.value;
  chrome.storage.local.set({ baseURL });
});

checkboxInput.addEventListener("change", () => {
  cachedPanels = checkboxInput.checked;
  chrome.storage.local.set({ cachedPanels });
});

document.addEventListener("DOMContentLoaded", () => {});
