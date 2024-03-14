let checkboxInput = document.getElementById("checkbox-input");
let urlInput = document.getElementById("url-input-field");

chrome.storage.local.get(["apiURL", "cachedPanels"], (result) => {
  urlInput.value = result.apiURL || "";
  let useCachedPanels = true;
  if (result.cachedPanels !== undefined) 
    checkboxInput.checked = result.cachedPanels
  else
    checkboxInput.checked = true;
});

urlInput.addEventListener("change", (event) => {
  chrome.storage.local.set({ apiURL: event.target.value.trim() });
});

checkboxInput.addEventListener("change", () => {
  chrome.storage.local.set({ cachedPanels: checkboxInput.checked });
});
