'use strict';
if (window.injectedMC !== 1) {
    window.injectedMC = 1;
    console.log('[MC] Starting context script');

    // Dynamic private variables
    var activeFetches = 0;
    var isSelecting = false;

    // Configuration variables
    var apiURL = ''
    var maxActiveFetches = 1;  // Number of images to request and process parallely
    var colorTolerance = 30;  // MSE Cutoff check for an already-colored image
    var colorStride = 4;  // Skip every this many rows and columns pixels for MSE calculation

    var cache = false  // Saves and gets images to and from server if site config set in siteConfig.json
    var denoise = true  // Denoises (remove unnecessary details) the image before processing
    var colorize = true  // Colorizes the image
    var upscale = true  // Upscale the image using super-resolution
    var upscaleFactor = 4  // Image upscale factor x2 or x4
    var denoiseSigma = 25  // Expected noise in image, basically blur strength

    var showOriginal = false  // Shows original image, if processed (colorized)
    var showColorized = true  // Shows processed image, if processed (colorized)

    var siteConfigFile = 'siteConfig.json'  // Manga detail selector queries for organized caching
    let siteConfigurations = null;  // siteConfig.json is loaded in this variable

    // ---- Initialization functions ----
    function fetchSiteConfigurations() {
        return fetch(browser.runtime.getURL(siteConfigFile))
            .then(response => response.json());
    }
    fetchSiteConfigurations().then(config => {
        siteConfigurations = config
        console.log('[MC] Sites configuration loaded')
    });

    function injectCSS() {
        const css = `
            .isHidden {
                display: none !important;
            }
            .highlight {
                border: 2px solid red !important;
                cursor: crosshair !important;
            }
        `;
        const style = document.createElement('style');
        style.type = 'text/css';
        style.textContent = css;
        document.head.appendChild(style);
    }
    injectCSS();


    // ---- Utility functions ----
    String.prototype.rsplit = function(sep, maxSplit) {
        const split = this.split(sep);
        return maxSplit ? [ split.slice(0, -maxSplit).join(sep) ].concat(split.slice(-maxSplit)) : split;
    }

    function parseQuery(queryString, doc = document) {
        queryString = queryString.trim();

        const querySelectorRegex = /^document\.querySelector(All)?\(['"](.+?)['"]\)/;
        const indexRegex = /\[(\d+)\]/;
        const propertyRegex = /\.(innerText|innerHTML|textContent)$/;

        let queryResult = null;

        try {
            const selectorMatch = queryString.match(querySelectorRegex);
            if (!selectorMatch) throw new Error('Invalid selector format');
            const isAll = Boolean(selectorMatch[1]);
            const selector = selectorMatch[2];

            queryResult = isAll ? doc.querySelectorAll(selector) : doc.querySelector(selector);

            if (isAll) {
                const indexMatch = queryString.match(indexRegex);
                const index = indexMatch[1] !== undefined ? parseInt(indexMatch[1], 10) : 0;
                queryResult = queryResult[index];
            }

            if (!queryResult) return '';

            const propertyMatch = queryString.match(propertyRegex);
            if (propertyMatch && propertyMatch[1]) {
                return queryResult[propertyMatch[1]] || '';
            } else {
                return '';
            }
        } catch (error) {
            console.error(`[MC] Error parsing query: ${queryString}`, error);
            return '';
        }
    }

    const maxDistFromGray = (index, ctx) => {
        const bpp = 4 // Bytes per pixel = number of channels (RGBA)
        const rows = ctx.canvas.height - colorStride * 2;
        const cols = ctx.canvas.width - colorStride * 2;
        // Skip first and last colorStride rows and columns when getting data
        const imageData = ctx.getImageData(colorStride, colorStride, cols, rows);
        const rowStride = colorStride + 1;
        const rowBytes = cols * bpp;
        const pxStride = bpp * (colorStride + 1);
        var maxDist = 0;
        for (let row = 0; row < rows; row += rowStride) {
            const rowStart = row * rowBytes;
            const rowEnd = rowStart + rowBytes;
            for (let i = rowStart; i < rowEnd; i += pxStride) {
                const red = imageData.data[i];
                const green = imageData.data[i + 1];
                const blue = imageData.data[i + 2];
                maxDist = Math.max(Math.abs(red-blue), Math.abs(red-green), Math.abs(blue-green), maxDist)
            }
        }
        console.log(`[MC] [${index}] Max distance from gray: ${maxDist}`);
        return maxDist;
    }

    const canvasContextFromImg = (img) => {
        const imgCanvas = document.createElement("canvas");
        imgCanvas.width = img.width;
        imgCanvas.height = img.height;

        const imgContext = imgCanvas.getContext("2d", { willReadFrequently: true });
        imgContext.drawImage(img, 0, 0, imgCanvas.width, imgCanvas.height);
        return imgContext
    }

    // ColorStride may be added in this, if needed
    const grayscaleMSE = (index, ctx, adjustColorBias = true) => {
        const thumbFactor = 4
        const thumbWidth = Math.floor(ctx.canvas.width / thumbFactor)
        const thumbHeight = Math.floor(ctx.canvas.height / thumbFactor)
        const thumbCanvas = document.createElement('canvas');
        const thumbCtx = thumbCanvas.getContext('2d');
        thumbCanvas.width = thumbWidth;
        thumbCanvas.height = thumbHeight;

        let imageData;
        try {
            thumbCtx.drawImage(ctx.canvas, 0, 0, thumbWidth, thumbHeight);
            imageData = thumbCtx.getImageData(0, 0, thumbWidth, thumbHeight);
        } catch (insecureError) {
            console.log(`[MC] [${index}] isGrayscale check error: ${insecureError}, falling back to isColoredContext`);
            return maxDistFromGray(index, ctx) < colorTolerance
        }
        const data = imageData.data;
        let bias = [0, 0, 0];
        if (adjustColorBias) {
            let sumR = 0, sumG = 0, sumB = 0;
            for (let i = 0; i < data.length; i += 4) {
                sumR += data[i];
                sumG += data[i + 1];
                sumB += data[i + 2];
            }
            const meanR = sumR / (data.length / 4);
            const meanG = sumG / (data.length / 4);
            const meanB = sumB / (data.length / 4);
            const overallMean = (meanR + meanG + meanB) / 3;
            bias = [meanR - overallMean, meanG - overallMean, meanB - overallMean];
        }

        let SSE = 0;   // Sum of Squared Errors (SSE)
        const width = thumbCanvas.width;
        const height = thumbCanvas.height;
        for (let y = 0; y < height; y += 1) {
            for (let x = 0; x < width; x += 1) {
                const index = (y * width + x) * 4;
                const pixel = [data[index], data[index + 1], data[index + 2]];
                const mu = (pixel[0] + pixel[1] + pixel[2]) / 3;
                for (let j = 0; j < 3; j++) {
                    const delta = pixel[j] - mu - bias[j];
                    SSE += delta * delta;
                }
            }
        }

        // Mean Squared Error (MSE)
        const totalPixels = (thumbWidth * thumbHeight);
        const MSE = SSE / totalPixels;

        console.log(`[MC] [${index}] MSE for grayscale check: ${MSE.toFixed(3)}`);
        return MSE;
    };


    // ---- API functions and helpers ----
    async function fetchColorizedImg(index, url, options, img, imgName) {
    console.log(`[MC] [${index}] Fetching: ${imgName}`);
    const savedSrc = img.src
    return fetch(url, options)
        .then(response => {
            if (!response.ok)
                return response.text().then(text => { throw text })
            else
                return response.json()
        })
        .then(json => {
            if (json.msg)
                console.log(`[MC] [${index}] Message: ${json.msg}`);
            if (json.colorImgData) {
                if(img.src != savedSrc){
                    console.log(`[MC] [${index}] Image src changed while request was in progress, invalidating...`)
                    img.removeAttribute('data-is-processed')
                    return;
                }
                const imgClone = img.cloneNode(true);
                img.dataset.isColored = true;
                img.dataset.isProcessed = true;
                imgClone.dataset.isCloned = true;

                img.src = json.colorImgData;
                if (img.dataset?.src) img.dataset.src = '';
                if (img.srcset) img.srcset = '';

                img.parentNode.insertBefore(imgClone, img.nextSibling);

                img.dataset.inView = img.style.display !== 'none'
                imgClone.dataset.inView = imgClone.style.display !== 'none'

                observeImageChanges(img, imgClone);

                console.log(`[MC] [${index}] Processed: ${imgName}`);
                toggleImageVisibility(showOriginal, showColorized)
            }
        })
        .catch(error => {
            console.log(`[MC] [${index}] Fetch error: ${error}`);
        });
    }

    const setColoredOrFetch = (index, img, imgName, apiURL, force, imgContext, mangaProps) => {
        var canSendData = true;
        try {
            const grayMse = grayscaleMSE(index, imgContext);
            const grayDist = maxDistFromGray(index, imgContext);

            const ct = colorTolerance;
            if (!force && (grayMse >= ct*10 || (grayMse >= ct && grayDist!=0))) {
                img.dataset.isColored = true;
                img.dataset.isProcessed = true;
                console.log(`[MC] [${index}] Already colored: ${imgName}`);
                return 1;
            }
        } catch(eIsColor) {
            canSendData = false
            if (!eIsColor.message.startsWith("Failed to execute 'getImageData'")) {
                console.log(`[MC] [${index}] Colorized context error: ${eIsColor}`);
                return 0;
            }
        }

        const isAnimated = img.src.includes('animation')
        if (force || activeFetches < maxActiveFetches) {
            activeFetches += 1;
            img.dataset.isProcessed = true;
            const postData = {
                imgName: imgName,
                imgURL: img.src,
                imgWidth: img.width,
				imgHeight: img.height,
				cache: cache && !isAnimated,
				denoise: denoise,
				colorize: colorize,
				upscale: upscale && !isAnimated,
				denoiseSigma: Number(denoiseSigma),
				upscaleFactor: Number(upscaleFactor),

				mangaTitle: mangaProps.title,
				mangaChapter: mangaProps.chapter,
            }

            console.log(`[MC] [${index}] Sending: `, postData);

            if (canSendData)
                postData.imgData = imgContext.canvas.toDataURL("image/png");

            const options = {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(postData)
            };

            fetchColorizedImg(index, new URL('colorize-image-data', apiURL).toString(), options, img, imgName)
                .finally(() => {
                    activeFetches -= 1;
                    if(!force) colorizeMangaEventHandler();
                });
            return 3
        } else {
            return 2;
        }
    }

    const colorizeImg = (index, img, apiURL, force, mangaProps) => {
        if (apiURL) try {
            const imageName = mangaProps.altText ? img.alt : ''
            const imgName = imageName || (img.src || img.dataset?.src || '').rsplit('/', 1)[1];
            if (imgName) {
                let imgContext = canvasContextFromImg(img);
                return setColoredOrFetch(index, img, imgName, apiURL, force, imgContext, mangaProps);
            }
            return 0;
        } catch(e) {
            console.log(`[MC] [${index}] Colorize image error: ${e}`)
            return 0;
        }
    }

    // ---- Select mode functions ----
    function enterSelectMode() {
        isSelecting = true;

        document.addEventListener('mouseover', highlightImage);
        document.addEventListener('mouseout', removeHighlight);
        document.addEventListener('click', selectImage);
    }

    function isValidImageElement(element) {
        return element.tagName.toLowerCase() === 'img' && !element.dataset.isCloned
    }

    function highlightImage(event) {
        if (!isSelecting) return;

        const element = event.target;
        if (isValidImageElement(element)) {
            element.classList.add('highlight');
        }
    }

    function removeHighlight(event) {
        if (!isSelecting) return;

        const element = event.target;
        if (isValidImageElement(element)) {
            element.classList.remove('highlight');
        }
    }

    function selectImage(event) {
        if (!isSelecting) return;

        event.preventDefault();
        event.stopPropagation();
        const element = event.target;

        if (isValidImageElement(element)) {
            colorizeSingleImage(element);
            exitSelectMode();
        } else {
            exitSelectMode();
        }
    }

    function exitSelectMode() {
        isSelecting = false;
        removeAllHighlights();
        document.removeEventListener('mouseover', highlightImage);
        document.removeEventListener('mouseout', removeHighlight);
        document.removeEventListener('click', selectImage);

        browser.runtime.sendMessage({ action: "exitSelectMode" });
        console.log('[MC] Exited select mode')
    }

    function removeAllHighlights() {
        const highlightedElements = document.getElementsByClassName('highlight');
        while (highlightedElements.length > 0) {
            highlightedElements[0].classList.remove('highlight');
        }
    }

    function colorizeSingleImage(img) {
        console.log('[MC] Force colorize: ', img.src)

        const imgSrc = img.src;
        const imgs = document.querySelectorAll(`img[src="${imgSrc}"]`);
        imgs.forEach((imgElement) => {
            if(imgElement.dataset.isCloned){
                imgElement.remove();
            }
            if(imgElement.dataset.isProcessed){
                imgElement.removeAttribute('data-is-colored');
            }
            if(imgElement.dataset.isProcessed){
                console.log('[MC] A colorized image is being re-colorized')
                imgElement.removeAttribute('data-is-processed');
            }
        });

        const site = Object.keys(siteConfigurations).find(site => window.location.hostname.includes(site));
        const config = siteConfigurations[site];
        const title = site ? parseQuery(config.titleQuery) : '';
        const chapter = site ? parseQuery(config.chapterQuery) : '';
        const pageNameFromAltText = site ? config.useAltTextAsImageName : false

        const mangaProps = {title: title, chapter: chapter, altText: pageNameFromAltText}
        let status = colorizeImg(0, img, apiURL, true, mangaProps);
        console.log('[MC] Force colorization status: ', status)
    }

    // ---- Extension interface functions ----
    const colorizeMangaEventHandler = (event=null) => {
        try {
            browser.storage.local.get(["apiURL", "maxActiveFetches", "showOriginal", "showColorized", "cache", "denoise", "colorize", "upscale", "denoiseSigma", "upscaleFactor",
                "colorTolerance", "colorStride", "minImgHeight", "minImgHeight"], (result) => {
                apiURL = result.apiURL;
                if (apiURL && siteConfigurations) {
                    maxActiveFetches = Number(result.maxActiveFetches || "1")
                    showOriginal = result.showOriginal
                    showColorized = result.showColorized

                    cache = result.cache
                    denoise = result.denoise
                    colorize = result.colorize
                    upscale = result.upscale
                    denoiseSigma = result.denoiseSigma || "25"
                    upscaleFactor = result.upscaleFactor || "4"

                    const storedColorTolerance = result.colorTolerance;
                    const storedColorStride = result.colorStride;
                    const minImgHeight = Math.min(result.minImgHeight || 200, window.innerHeight/2);
                    const minImgWidth = Math.min(result.minImgWidth || 400, window.innerWidth/2);

                    if (storedColorTolerance > -1) colorTolerance = storedColorTolerance;
                    if (storedColorStride > -1) colorStride = storedColorStride;

                    const site = Object.keys(siteConfigurations).find(site => window.location.hostname.includes(site));
                    const config = siteConfigurations[site];
                    const title = site ? parseQuery(config.titleQuery) : '';
                    const chapter = site ? parseQuery(config.chapterQuery) : '';
                    const pageNameFromAltText = site ? config.useAltTextAsImageName : false

                    console.log(`[MC] Website: ${site}, Title: ${title}, Chapter: ${chapter}`)
                    console.log('[MC] Scanning images...')
                    toggleImageVisibility(showOriginal, showColorized)

                    let total = 0;
                    let skipped = 0;
                    let colored = 0;
                    let failed = 0;
                    let awaited = 0;
                    let processing = 0;

                    const images = document.querySelectorAll('img');
                    total= images.length;

                    images.forEach((img, index) => {
                        if (img.dataset.isCloned) {
                            return  // continue
                        } else if (img.dataset.isProcessed && img.dataset.isColored) {
                            colored++
                        } else if(img.dataset.isProcessed && !img.dataset.isColored){
                            failed++
                        } else if (img.dataset.isProcessed){
                            processing++
                        } else if (!img.complete || !img.src) {
                            img.addEventListener('load', colorizeMangaEventHandler, { passive: true });
                            total--
                        } else if (img.width > 0 && img.width < minImgWidth || img.height > 0 && img.height < minImgHeight) {
                            skipped++
                        } else if (activeFetches >= maxActiveFetches){
                            awaited++
                        } else {
                            const mangaProps = {title: title, chapter: chapter, altText: pageNameFromAltText}
                            let status = colorizeImg(index, img, apiURL, false, mangaProps);
                            switch(status){
                                case 0: failed++; break;
                                case 1: colored++; break;
                                case 2: awaited++; break;
                                case 3: processing++; break;
                            }
                        }
                    });
                    console.log(`[MC] Report: Processing=${processing} Success=${colored} Skipped=${skipped} Failed=${failed} Awaited=${awaited} Total=${total}`)
                }
            });
        } catch (err) {
            if (err.toString().includes('Extension context invalidated')) {
                console.log('[MC] Extension reloaded, stopping old version');
                window.injectedMC = undefined;
                observer?.disconnect();
            } else {
                console.error('[MC] Error: ', err);
            }
        }
    }

    function toggleImageVisibility(showOriginal, showColorized) {
        const coloredImages = document.querySelectorAll('img[data-is-colored="true"][data-in-view="true"]');
        const clonedImages = document.querySelectorAll('img[data-is-cloned="true"][data-in-view="true"]');

        coloredImages.forEach(img => {
            showColorized ? img.classList.remove('isHidden') : img.classList.add('isHidden')
        });

        clonedImages.forEach(img => {
            showOriginal ? img.classList.remove('isHidden') : img.classList.add('isHidden')
        });
    }

    browser.runtime.onMessage.addListener((request, sender, sendResponse) => {
        if (request.action === 'toggleVisibility') {
            console.log('[MC] Image visibility toggled')
            toggleImageVisibility(request.showOriginal, request.showColorized);
        }
        if (request.action === 'runColorizer'){
            console.log('[MC] Running colorizer')
            colorizeMangaEventHandler();
        }
        if(request.action === 'startSelectMode') {
            console.log('[MC] Entered select mode')
            enterSelectMode();
        }
        sendResponse({status: 'done'});
    });


    // ---- Observer functions ----
    function observeImageChanges(originalImg, clonedImg) {
        const handleMutation = (mutationsList) => {
            mutationsList.forEach((mutation) => {
                if (mutation.type === 'attributes' && mutation.attributeName === 'style') {
                    clonedImg.style.cssText = originalImg.style.cssText;

                    if (originalImg.style.display !== 'none'){
                        originalImg.dataset.inView = true
                        clonedImg.dataset.inView = true
                    } else if(originalImg.style.display === 'none'){
                        originalImg.dataset.inView = false
                        clonedImg.dataset.inView = false
                    }
                }

                if (mutation.type === 'attributes' && mutation.attributeName === 'src') {
                    clonedImg.remove();
                    originalImg.removeAttribute('data-is-processed')
                    originalImg.removeAttribute('data-is-colored')

                    colorizeMangaEventHandler()
                }

                if (mutation.type === 'childList') {
                    mutation.removedNodes.forEach((node) => {
                        if (node === originalImg) {
                            clonedImg.remove();
                            observer.disconnect();
                        }
                    });
                }
            });
        };

        const observer = new MutationObserver(handleMutation);
        observer.observe(originalImg, { attributes: true, attributeFilter: ['style', 'src'] });
        observer.observe(originalImg.parentNode, { childList: true });
        originalImg._observer = observer;
    }

    colorizeMangaEventHandler();

    const observer = new MutationObserver(colorizeMangaEventHandler);
    observer.observe(document.querySelector("body"), { subtree: true, childList: true });
};
