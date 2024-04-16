// const checkboxInput = document.getElementById("checkbox-input");
const urlInput = document.getElementById("url-input-field");
const colTolInput = document.getElementById("coltol-input-field");
const colStrideInput = document.getElementById("colstride-input-field");
const websitesInput = document.getElementById("websites-input-field");
const runButton = document.getElementById("run");
const testApiButton = document.getElementById("test-api");

chrome.storage.local.get(["apiURL", "colTol", "colStride", "websites"], (result) => {
  urlInput.value = result.apiURL || "";
  colTolInput.value = result.colTol || "30";
  colStrideInput.value = result.colStride || "4";
  websitesInput.value = result.websites || "mangadex.org\nchapmanganelo.com\nm.manganelo.com";
  // checkboxInput.checked = result.cachedPanels !== false
});

testApiButton.addEventListener("click",() => {
  chrome.tabs.create({url: urlInput.value, selected: true, active: true});
})

runButton.addEventListener("click",() => {   
  chrome.storage.local.set({
    apiURL: urlInput.value.trim(),
    colTol: colTolInput.value.trim(),
    colStride: colStrideInput.value.trim(),
    websites: websitesInput.value.trim(),
    currentTab: true,
    // cachedPanels: checkboxInput.checked
  }); 
})
