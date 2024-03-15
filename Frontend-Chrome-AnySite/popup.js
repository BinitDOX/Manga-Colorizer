const checkboxInput = document.getElementById("checkbox-input");
const urlInput = document.getElementById("url-input-field");
const runButton = document.getElementById("run");

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

runButton.addEventListener("click",() => {    
  chrome.tabs.query({currentWindow: true, active: true}, (tabs) => {
    const tab = tabs[0];
    if (tab) {
      console.log("Clicked run on tab ", tab);
        chrome.scripting.executeScript({
          target: {tabId: tab.id, allFrames: true},
          files: ["contentScript.js"]
        }, function() {
          if (chrome.runtime.lastError) {
            console.error(chrome.runtime.lastError.message);
          } else {
            console.log("Injected script from run button");
          }
        });
    } else {
        alert("There are no active tabs")
    }
  })
})
