// const checkboxInput = document.getElementById("checkbox-input");
const urlInput = document.getElementById("url-input-field");
const colTolInput = document.getElementById("coltol-input-field");
const colStrideInput = document.getElementById("colstride-input-field");
const runButton = document.getElementById("run");
const testApiButton = document.getElementById("test-api");

chrome.storage.local.get(["apiURL", "cachedPanels", "colTol", "colStride"], (result) => {
  urlInput.value = result.apiURL || "";
  colTolInput.value = result.colTol || "30";
  colStrideInput.value = result.colStride || "4";
  // let useCachedPanels = true;
  // if (result.cachedPanels !== undefined) 
  //   checkboxInput.checked = result.cachedPanels
  // else
  //   checkboxInput.checked = true;
});

urlInput.addEventListener("change", (event) => {
  chrome.storage.local.set({ apiURL: event.target.value.trim() });
});

colTolInput.addEventListener("change", (event) => {
  chrome.storage.local.set({ colTol: event.target.value.trim() });
});

colStrideInput.addEventListener("change", (event) => {
  chrome.storage.local.set({ colStride: event.target.value.trim() });
});

// checkboxInput.addEventListener("change", () => {
//   chrome.storage.local.set({ cachedPanels: checkboxInput.checked });
// });

testApiButton.addEventListener("click",() => {
  chrome.tabs.create({url: urlInput.value, selected: true, active: true});
})

runButton.addEventListener("click",() => {    
  chrome.tabs.query({currentWindow: true, active: true}, (tabs) => {
    const tab = tabs[0];
    if (tab?.url?.startsWith("http")) {
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
