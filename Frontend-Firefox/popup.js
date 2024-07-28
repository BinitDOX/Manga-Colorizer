const urlInput = document.getElementById("url-input-field");
const denoiseCheckbox = document.getElementById("denoiser-checkbox");
const colorizeCheckbox = document.getElementById("colorizer-checkbox");
const upscaleCheckbox = document.getElementById("upscaler-checkbox");
const upscaleFactorSelector = document.querySelectorAll("input[name='upscale-factor']");
const upscaleFactorSelector2 = document.getElementById("upscale-factor-2");
const upscaleFactorSelector4 = document.getElementById("upscale-factor-4");
const denoiseSigmaInput = document.getElementById("denoisesigma-input-field");
const colorToleranceInput = document.getElementById("colortolerance-input-field");
const colorStrideInput = document.getElementById("colorstride-input-field");
const websitesInput = document.getElementById("websites-input-field");
const addSiteButton = document.getElementById("addsite");
const runButton = document.getElementById("run");
const testApiButton = document.getElementById("test-api");

browser.storage.local.get(["apiURL", "denoise", "colorize", "upscale", "denoiseSigma", "upscaleFactor",
                "colorTolerance", "colorStride", "websites"], (result) => {
    urlInput.value = result.apiURL || "";
    denoiseCheckbox.checked = result.denoise !== undefined ? result.denoise : true;
    colorizeCheckbox.checked = result.colorize !== undefined ? result.colorize : true;
    upscaleCheckbox.checked = result.upscale !== undefined ? result.upscale : true;
    if (result.upscaleFactor === '2') {
        upscaleFactorSelector2.checked = true;
    } else if (result.upscaleFactor === '4') {
        upscaleFactorSelector4.checked = true;
    } else {
        upscaleFactorSelector4.checked = true;
    }
    denoiseSigmaInput.value = result.denoiseSigma || "25";
    colorToleranceInput.value = result.colorTolerance || "30";
    colorStrideInput.value = result.colorStride || "4";
    websitesInput.value = result.websites || "mangadex.org/chapter\nchapmanganelo.com\nfanfox.net";
    const sitesArray = websitesInput.value.split("\n");
    websitesInput.rows = sitesArray.length + 1
    websitesInput.cols = sitesArray.reduce((len, str) => { return Math.max(len, str.length) }, 25);
    addSiteButton.style.display = "none"
    browser.tabs.query({currentWindow: true, active: true}, (tabs) => {
        if (tabs[0]?.url?.startsWith("http")) {
            const hostname = new URL(tabs[0].url).hostname;
            if (hostname && !websitesInput.value.includes(hostname)) {
                addSiteButton.innerText = "Add " + hostname;
                addSiteButton.removeAttribute("style");
                addSiteButton.addEventListener("click",() => {
                    addSiteButton.style.display = "none"
                    if (websitesInput.value.length > 0 && !websitesInput.value.endsWith("\n"))
                        websitesInput.value += "\n";
                    websitesInput.value += hostname;
                    browser.storage.local.set({websites: websitesInput.value.trim()});
                });
            }
        }
    });
});


testApiButton.addEventListener("click",() => {
    browser.tabs.create({url: urlInput.value, active: true});
    browser.storage.local.set({
        apiURL: urlInput.value.trim()
    });
})

runButton.addEventListener("click",() => {
    let selectedUpscaleFactor;
    upscaleFactorSelector.forEach((radio) => {
        if (radio.checked) {
            selectedUpscaleFactor = radio.value;
        }
    });

    browser.storage.local.set({
        apiURL: urlInput.value.trim(),
        denoise: denoiseCheckbox.checked,
        colorize: colorizeCheckbox.checked,
        upscale: upscaleCheckbox.checked,
        upscaleFactor: selectedUpscaleFactor,
        denoiseSigma: denoiseSigmaInput.value.trim(),
        colorTolerance: colorToleranceInput.value.trim(),
        colorStride: colorStrideInput.value.trim(),
        websites: websitesInput.value.trim(),
        currentTab: true,
    }); 
})
