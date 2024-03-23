(() => {
    const COLOREDCLASS = "mangacolor"; // class applied to img if already colored or coloring requested
    var activeFetches = 0;
    var maxActiveFetches = 2;

    String.prototype.rsplit = function(sep, maxsplit) {
        const split = this.split(sep);
        return maxsplit ? [ split.slice(0, -maxsplit).join(sep) ].concat(split.slice(-maxsplit)) : split;
    }

    const isColoredContext = (ctx) => {
        const imageData = ctx.getImageData(0, 0, ctx.canvas.width, ctx.canvas.height);
        for (let i = 0; i < imageData.data.length; i += 4) {
            const red = imageData.data[i];
            const green = imageData.data[i + 1];
            const blue = imageData.data[i + 2];
            // red == blue == green is a perfect gray, but also count values within 2 as gray
            if (red - green > 2 || red - blue > 2 || blue - red > 2 || green - red > 2) {
                return true;
            }
        }
        return false;
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
            .catch(error => {
                console.error('MC: ' + error);
            });
    }

    const colorizeImg = (img, apiURL, event) => {
        if (event) {
            alert('imgLoaded', img, apiURL, useCachedPanels, event, "colorizing...");
        }
        if (apiURL && !img.classList?.contains(COLOREDCLASS)) try {
            if (!img.complete) throw ('image not complete');
            imgName = (img.src || img.dataset?.src || '').rsplit('/', 1)[1];
            if (imgName) {
                const imgCanvas = document.createElement("canvas");
                imgCanvas.width = img.width;
                imgCanvas.height = img.height;
        
                const imgContext = imgCanvas.getContext("2d", { willReadFrequently: true });
                imgContext.drawImage(img, 0, 0, img.width, img.height);

                if (isColoredContext(imgContext)) {
                    img.classList.add(COLOREDCLASS); // Add early so we don't try again while fetching
                    console.log('MC: already colored', imgName);
                } else if (activeFetches < maxActiveFetches) {
                    activeFetches += 1;
                    img.classList.add(COLOREDCLASS); // Add early so we don't try again while fetching
                    const postData = {
                        imgName: imgName,
                        imgWidth: img.width,
                        imgData: imgCanvas.toDataURL("image/png")
                    };

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
        } catch(e1) {
            console.log('MC: colorizeImg error', e1)
        }
    }

    const colorizeMangaEventHandler = () => {
        try {
            chrome.storage.local.get(["apiURL"], (result) => {
                // console.log("MC content: storage.local.get result:", result);
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
