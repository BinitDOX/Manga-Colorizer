var websites = [];

const setWebsitesFromString = ((str) => {
    if (str) websites = str.split(/[\n,\s+]/)
});

browser.runtime.onInstalled.addListener(({reason}) => {
    if (reason === 'install') {
    browser.tabs.create({
        url: "popup.html"
    });
}
});

const injectContent = ((tab) => {
    if (tab?.url?.startsWith("http") || tab?.url?.startsWith("file")) try {
        console.log("Injecting in", tab.url);
        browser.scripting.executeScript({
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
        browser.tabs.query({url: websites.map(host => '*://' + host + '/*')}, (tabs) => {
            tabs.forEach(tab => { injectIfMatches(tab) });
        });
});

const injectInCurrentTab = (() => {
    browser.tabs.query({currentWindow: true, active: true}, (tabs) => {
        injectContent(tabs[0]);
    })
})
async function storageChangeListener(changes, area) {
    if (area === 'local') {
        if (changes?.websites?.newValue) {
            setWebsitesFromString(changes?.websites?.newValue);
            injectInWebsites();
        }
        if (changes?.currentTab?.newValue) {
            injectInCurrentTab();
            browser.storage.local.set({ currentTab: false }); 
        }
    }
};

browser.storage.onChanged.addListener(storageChangeListener);

browser.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
    console.log("tabs.onUpdated", tab.url, JSON.stringify(changeInfo));
    if (changeInfo.url) injectIfMatches(tab);
});
browser.tabs.onCreated.addListener((tab) => {
    console.log("tabs.onCreated", tab.url);
    injectIfMatches(tab);
});

async function initWebsitesAndTabs() {
    return browser.storage.local.get("websites", (result) => {
        console.log('initState', JSON.stringify(result));
        setWebsitesFromString(result.websites);
        console.log('websites', websites);
        injectInWebsites();
    });
};

initWebsitesAndTabs();
