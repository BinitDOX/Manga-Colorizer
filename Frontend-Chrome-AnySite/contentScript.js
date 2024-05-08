'use strict';
if (window.injectedMC !== 1) {
    window.injectedMC = 1;
    console.log('MC: Starting context script.');
    const maxColoredSrc = 200; // length of img.src to keep in img.coloredsrc

    var activeFetches = 0;
    var maxActiveFetches = 1;
    var maxImgWidth = 992;

    var colTol = 30;  // If difference between red, blue, and green values is greater than this for any pixel,
                      // image is assumed to be in color and will not be recolored.

    var colorStride = 4; // When checking for an already-colored image,
                         // skip this many rows and columns at edges and between pixels.
                         // Check every pixel for color if zero.

    String.prototype.rsplit = function(sep, maxsplit) {
        const split = this.split(sep);
        return maxsplit ? [ split.slice(0, -maxsplit).join(sep) ].concat(split.slice(-maxsplit)) : split;
    }

    const maxDistFromGray = (ctx) => {
        const bpp = 4 // Bytes per pixel = number of channels (RGBA)
        const rows = ctx.canvas.height - colorStride * 2;
        const cols = ctx.canvas.width - colorStride * 2;
        // skip first and last colorStride rows and columns when getting data
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
        console.log('maxDistFromGray', maxDist)
        return maxDist;
    }

    const isColoredContext = (ctx) => {
        return (colTol < 255) && maxDistFromGray(ctx) > colTol;
    }

    async function fetchColorizedImg(url, options, img, imgName) {
        console.log("MC: fetching:", url, imgName);
        return fetch(url, options)
            .then(response => {
                if(!response.ok)
                    return response.text().then(text => {throw text})
                else
                    return response.json()})
            .then(json => {
                if (json.msg)
                    console.log('MC: ', json.msg);
                if (json.colorImgData) {
                    img.coloredsrc = json.colorImgData.slice(0, maxColoredSrc);
                    img.src = json.colorImgData;
                    if (img.dataset?.src) img.dataset.src = '';
                    if (img.srcset) img.srcset = '';
                    console.log('MC: Colorized', imgName);
                }
            })
            .catch(error => {
                console.log('MC: fetchColorizedImg:', error);
            });
    }

    const canvasContextFromImg = (img) => {
        const imgCanvas = document.createElement("canvas");
        imgCanvas.width = img.width;
        imgCanvas.height = img.height;

        const imgContext = imgCanvas.getContext("2d", { willReadFrequently: true });
        imgContext.drawImage(img, 0, 0, imgCanvas.width, imgCanvas.height);
        return imgContext
    }

    const setColoredOrFetch = (img, imgName, apiURL, colorStride, imgContext) => {
        var canSendData = true;
        try {
            if (isColoredContext(imgContext, colorStride)) {
                img.coloredsrc = img.src.slice(0, maxColoredSrc);
                console.log('MC: already colored', imgName);
                return
            }
        } catch(eIsColor) {
            canSendData = false
            if (!eIsColor.message.startsWith("Failed to execute 'getImageData'")) {
                console.log('MC: isColoredContext error', eIsColor)
            } else {
                // console.log('MC: isColoredContext: Could not use getImageData')
            }
        }

        if (activeFetches < maxActiveFetches) {
            activeFetches += 1;
            img.coloredsrc = img.src.slice(0, maxColoredSrc); // assume already colored while fetch is in progress
            const postData = {
                imgName: imgName,
                imgWidth: Math.min(img.width, maxImgWidth)
            }
            if (canSendData)
                postData.imgData = imgContext.canvas.toDataURL("image/png");
            else
                postData.imgURL = img.src;

            const options = {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(postData)
            };
            fetchColorizedImg(new URL('colorize-image-data', apiURL).toString(), options, img, imgName)
                .finally(() => {
                    activeFetches -= 1;
                    img.coloredsrc = img.src.slice(0, maxColoredSrc);
                    colorizeMangaEventHandler();
                });
        }
    }

    const imgSrcMatchesColoredSrc = (img) => { return img.src.startsWith(img.coloredsrc)}

    const colorizeImg = (img, apiURL, colorStride) => {
        if (apiURL && (!imgSrcMatchesColoredSrc(img))) try {
            if (!img.complete) throw ('image not complete');
            const imgName = (img.src || img.dataset?.src || '').rsplit('/', 1)[1];
            if (imgName) {
                let imgContext = canvasContextFromImg(img);
                setColoredOrFetch(img, imgName, apiURL, colorStride, imgContext);
            }
        } catch(e1) {
            console.log('MC: colorizeImg error', e1)
        }
    }

    const colorizeMangaEventHandler = (event=null) => {
        // if (event) console.log('MC: colorizeMangaEventHandler called with event', event);
        try {
            chrome.storage.local.get(["apiURL", "colTol", "colorStride", "minImgHeight", "minImgHeight"], (result) => {
                const apiURL = result.apiURL;
                if (apiURL) {
                    const storedColTol = result.colTol;
                    const storedColorStride = result.colorStride;
                    const minImgHeight = Math.min(result.minImgHeight || 200, window.innerHeight/2);
                    const minImgWidth = Math.min(result.minImgWidth || 400, window.innerWidth/2);                
                    if (storedColTol > -1) colTol = storedColTol;
                    if (storedColorStride > -1) colorStride = storedColorStride;
                    console.log('MC: Scanning images...')
                    for (let img of document.querySelectorAll('img')) {
                        if (imgSrcMatchesColoredSrc(img)) continue;
                        img.addEventListener('load', colorizeMangaEventHandler, { passive: true });
                        if (activeFetches >= maxActiveFetches) break;
                        if (!img.complete || !img.src) {
                            // image not loaded, wait for load event listener
                        } else if (img.width > 0 && img.width < minImgWidth || img.height > 0 && img.height < minImgHeight) {
                            // skip small images
                            // console.log('MC: skip small image', img.width, 'x', img.height)
                        } else {
                            colorizeImg(img, apiURL, colorStride);
                        }
                    }
                }
            });
        } catch (err) {
            if (err.toString().includes("Extension context invalidated")) {
                console.log("MC: Extension reloaded, stopping old version");
                window.injectedMC = undefined;
                observer?.disconnect();
            } else {
                console.error("MC:", err);
            }
        }
    }

    colorizeMangaEventHandler();

    const observer = new MutationObserver(colorizeMangaEventHandler);
    observer.observe(document.querySelector("body"), { subtree: true, childList: true });
};
