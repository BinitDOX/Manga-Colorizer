chrome.runtime.onInstalled.addListener(async () => {
  console.log("About to add context menu");
  chrome.contextMenus.create({
    id: 'colorize',
    title: 'Colorize',
    type: 'normal',
  });
  console.log("Added context menu");
});

chrome.contextMenus.onClicked.addListener((item, tab) => {
  console.log("Clicked context menu");
  console.log(item);
  console.log(tab);
  const tabId = tab?.id;

  if (tabId && item.menuItemId === 'colorize'){
    chrome.scripting.executeScript({
      target: {tabId: tabId, allFrames: true},
      files: ["contentScript.js"]
    }, function() {
      if (chrome.runtime.lastError) {
          console.error(chrome.runtime.lastError.message);
      }
      else
      {
        console.log("No error after injecting script.");

          // setTimeout(function(){ 
          //     send_to_content(obj); //Call send_to_content(obj) after content.js injected
          // }, 300);
      }
    });
  }
});