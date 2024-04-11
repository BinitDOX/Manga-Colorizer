var websites = [];

const setWebsitesFromString = ((str) => {
    if (str) websites = str.split(/[\n,\s+]/)
});

chrome.runtime.onInstalled.addListener(({reason}) => {
    if (reason === 'install') {
    chrome.tabs.create({
        url: "popup.html"
    });
}
});

const injectContent = ((tab) => {
    if (tab?.url?.startsWith("http") || tab?.url?.startsWith("file")) try {
        console.log("Injecting in", tab.url);
        chrome.scripting.executeScript({
            target: {tabId: tab.id, allFrames: false},
            files: ["contentScript.js"]
        })
    } catch {
        console.log("Unable to inject in", tab.url);
    }
});

const injectIfMatches = ((tab) => {
    if (tab?.url?.startsWith("http")
            && websites.some(host => tab.url.includes(host)))
                injectContent(tab);
});

const injectInWebsites = (() => {
    if (websites?.length > 0)
        chrome.tabs.query({url: websites.map(host => '*://' + host + '/*')}, (tabs) => {
            tabs.forEach(tab => { injectIfMatches(tab) });
        });
});

const injectInCurrentTab = (() => {
    chrome.tabs.query({currentWindow: true, active: true}, (tabs) => {
        injectContent(tabs[0]);
    })
})
async function storageChangeListener(changes, area) {
    if (area === 'local') {
        // console.log('storage.onChanged', JSON.stringify(changes));
        if (changes?.websites?.newValue) {
            setWebsitesFromString(changes?.websites?.newValue);
            injectInWebsites();
        }
        if (changes?.currentTab?.newValue) {
            injectInCurrentTab();
            chrome.storage.local.set({ currentTab: false }); 
        }
    }
};

chrome.storage.onChanged.addListener(storageChangeListener);

chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
    if (changeInfo.url) injectIfMatches(tab);
});
chrome.tabs.onCreated.addListener((tab) => {
    injectIfMatches(tab);
});

async function initWebsitesAndTabs() {
    return chrome.storage.local.get("websites", (result) => {
        console.log('initState', JSON.stringify(result));
        setWebsitesFromString(result.websites);
        console.log('websites', websites);
        injectInWebsites();
    });
};

initWebsitesAndTabs();
