(() => {
    const COLOREDCLASS = "mangacolor"; // class applied to img if already colored or coloring requested
    // Remove COLOREDCLASS from all images when Colorize is pressed to force rescan of all
    [].forEach.call( document.images, function( img ) {img.classList.remove(COLOREDCLASS)})

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
            .then(function(response) {
                if(!response.ok)
                    throw response.text();
                else
                    return response.json()})
            .then(json => {
                img.src = json.colorImgData;
                img.dataset.src = '';
                console.log('MC: Colorized', imgName);
            })
            // .catch(error => {
            //     console.error('MC: caught fetchColorizedImg error', error);
            // });
    }

    const canvasContextFromImg = (img) => {
        const imgCanvas = document.createElement("canvas");
        imgCanvas.width = img.width;
        imgCanvas.height = img.height;

        const imgContext = imgCanvas.getContext("2d", { willReadFrequently: true });
        imgContext.drawImage(img, 0, 0, img.width, img.height);
        return imgContext
    }

    const setColoredOrFetch = (img, apiURL, colorStride, imgContext) => {
        var canSendData = true;
        try {
            if (isColoredContext(imgContext, colorStride)) {
                img.classList.add(COLOREDCLASS);
                console.log('MC: already colored', imgName);
                return
            }
        } catch(eIsColor) {
            canSendData = false
            if (!eIsColor.message.startsWith("Failed to execute 'getImageData'")) {
                console.log('MC: isColoredContext error', eIsColor)
            } else {
                console.log('MC: isColoredContext: Could not use getImageData')
            }
        }

        if (activeFetches < maxActiveFetches) {
            activeFetches += 1;
            img.classList.add(COLOREDCLASS); // Add early so we don't try again while fetching
            const postData = {
                imgName: imgName,
                imgWidth: Math.min(img.width, maxImgWidth)
            }
            if (canSendData)
                postData.imgData = imgContext.canvas.toDataURL("image/png");
            else
                postData.imgURL = img.src || img.dataset?.src;

            const options = {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(postData)
            };
            fetchColorizedImg(apiURL + '/colorize-image-data', options, img, imgName)
                .finally(() => {
                    activeFetches -= 1;
                    colorizeMangaEventHandler();
                });
        }
    }

    const colorizeImg = (img, apiURL, colorStride, event) => {
        if (event) {
            alert('colorizeImg called with event', img, apiURL, event, "colorizing...");
        }
        if (apiURL && !img.classList?.contains(COLOREDCLASS)) try {
            if (!img.complete) throw ('image not complete');
            imgName = (img.src || img.dataset?.src || '').rsplit('/', 1)[1];
            if (imgName) {
                imgContext = canvasContextFromImg(img);
                setColoredOrFetch(img, apiURL, colorStride, imgContext);
            }
        } catch(e1) {
            console.log('MC: colorizeImg error', e1)
        }
    }

    const colorizeMangaEventHandler = () => {
        try {
            chrome.storage.local.get(["apiURL", "colTol", "colorStride"], (result) => {
                const apiURL = result.apiURL;
                const storedColTol = result.colTol;
                const storedColorStride = result.colorStride;
                if (apiURL) {
                    if (storedColTol > -1) colTol = storedColTol; 
                    console.log('MC: Scanning images...')
                    document.querySelectorAll('img:not(.' + COLOREDCLASS + ')').forEach(img => {
                        if (img.width < 500 || img.height < 500) {
                            // skip small images
                        } else if (!img.complete) { // try again when this image loads
                            console.log('image not complete, adding EventListener------------------------------------------');
                            img.addEventListener('load', colorizeImg.bind(img, apiURL));
                        } else {
                            colorizeImg(img, apiURL, colorStride, null);
                        }
                    });
                }
            });
        } catch (err) {
            if (err.toString().includes("Extension context invalidated")) {
                console.log("MC: Extension reloaded, stopping old version");
                observer?.disconnect();
            } else {
                console.error("MC:", err);
            }
        }
    }

    colorizeMangaEventHandler();

    const observer = new MutationObserver(colorizeMangaEventHandler);
    observer.observe(document.querySelector("body"), { subtree: true, childList: true });
})();
