(() => {
    const COLOREDCLASS = "mangacolor"; // class applied to img if already colored or coloring requested
    var activeFetches = 0;
    var maxActiveFetches = 1;
    var maxImgWidth = 992;
    var minDistFromGray = 30;

    String.prototype.rsplit = function(sep, maxsplit) {
        const split = this.split(sep);
        return maxsplit ? [ split.slice(0, -maxsplit).join(sep) ].concat(split.slice(-maxsplit)) : split;
    }

    const maxDistFromGray = (ctx) => {
        const imageData = ctx.getImageData(0, 0, ctx.canvas.width, ctx.canvas.height);
        var maxDist = 0;
        for (let i = 0; i < imageData.data.length; i += 4) {
            const red = imageData.data[i];
            const green = imageData.data[i + 1];
            const blue = imageData.data[i + 2];
            maxDist = Math.max(Math.abs(red-blue), Math.abs(red-green), Math.abs(blue-green), maxDist)
        }
        console.log('maxDistFromGray', maxDist)
        return maxDist;
    }

    const isColoredContext = (ctx) => {
        return maxDistFromGray(ctx) >= minDistFromGray;
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

    const setColoredOrFetch = (img, apiURL, imgContext) => {
        var canSendData = true;
        try {
            if (isColoredContext(imgContext)) {
                img.classList.add(COLOREDCLASS);
                console.log('MC: already colored', imgName);
                return
            }
        } catch(eIsColor) {
            canSendData = false
            if (!eIsColor.message.startsWith("Failed to execute 'getImageData'")) {
                console.log('MC: isColoredContext error', eIsColor)
            } else {
                console.log('MC: isColoredContext: Failed to execute getImageData')
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
                .then(() => {
                    activeFetches -= 1;
                    colorizeMangaEventHandler();
                });
        }
    }

    const colorizeImg = (img, apiURL, event) => {
        if (event) {
            alert('colorizeImg called with event', img, apiURL, event, "colorizing...");
        }
        if (apiURL && !img.classList?.contains(COLOREDCLASS)) try {
            if (!img.complete) throw ('image not complete');
            imgName = (img.src || img.dataset?.src || '').rsplit('/', 1)[1];
            if (imgName) {
                imgContext = canvasContextFromImg(img);
                setColoredOrFetch(img, apiURL, imgContext);
            }
        } catch(e1) {
            console.log('MC: colorizeImg error', e1)
        }
    }

    const colorizeMangaEventHandler = () => {
        try {
            chrome.storage.local.get(["apiURL"], (result) => {
                const apiURL = result.apiURL;
                if (apiURL) {
                    console.log('MC: Scanning images...')
                    document.querySelectorAll('img:not(.' + COLOREDCLASS + ')').forEach(img => {
                        if (img.width < 500 || img.height < 500) {
                            // skip small images
                        } else if (!img.complete) { // try again when this image loads
                            console.log('image not complete, adding EventListener------------------------------------------');
                            img.addEventListener('load', colorizeImg.bind(img, apiURL));
                        } else {
                            colorizeImg(img, apiURL, null);
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
