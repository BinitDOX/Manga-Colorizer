(() => {
    const COLOREDCLASS = "mangacolor"; // class applied to img if already colored or coloring requested

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

    const colorizeImg = (img, apiURL, useCachedPanels, event) => {
        if (event) {
            alert('imgLoaded', img, apiURL, useCachedPanels, event, "colorizing...");
        }
        if (apiURL && !img.classList?.contains(COLOREDCLASS)) try {
            imgName = (img.src || img.dataset.src).rsplit('/', 1)[1];
            console.log('colorize', imgName)
            img.classList.add(COLOREDCLASS); // Add early so we don't try again while fetching

            const imgCanvas = document.createElement("canvas");
            imgCanvas.width = img.width;
            imgCanvas.height = img.height;
    
            const imgContext = imgCanvas.getContext("2d", { willReadFrequently: true });
            imgContext.drawImage(img, 0, 0, img.width, img.height);

            if (isColoredContext(imgContext)) {
                console.log('already colored');
            } else {
                const imgData = imgCanvas.toDataURL("image/png");
                const mangaTitle = document.location.hostname;
                const mangaChapter = document.location.pathname?.slice(1).replace(/\//g, '_');

                const postData = {
                    mangaTitle: mangaTitle,
                    mangaChapter: mangaChapter,
                    useCachedPanels: useCachedPanels,
                    imgName: imgName,
                    imgWidth: img.width,
                    imgData: imgData
                };

                const options = {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(postData)
                };
                let curl = apiURL + '/colorize-image-data';
                console.log("MC: Sending to:", curl);
                fetch(curl, options)
                    .then(response => response.json())
                    .then(data => {
                        console.log('MC: Setting Data');
                        img.src = data.colorImgData;
                        img.dataset.src = '';
                        console.log('MC: COLORIZED!');
                    })
                    .catch(error => {
                        console.error('MC: ' + error);
                    });
            }
        } catch(e1) {
            console.log('Could not get data URL', e1)
        }

    }

    const colorizeMangaEventHandler = () => {
        chrome.storage.local.get(["apiURL", "cachedPanels"], (result) => {
            console.log("MC content: storage.local.get result:", result);
            const apiURL = result.apiURL;
            if (apiURL) {
                var useCachedPanels = true;
                if (result.cachedPanels !== undefined) {
                    useCachedPanels = result.cachedPanels;
                }
                console.log('MC: Scanning images...')
                document.querySelectorAll('img:not(.' + COLOREDCLASS + ')').forEach(img => {
                    if (img.width < 500 || img.height < 500) {
                        // skip small images
                    } else if (!img.complete) { // try again when this image loads
                        console.log('image not complete, adding EventListener------------------------------------------');
                        img.addEventListener('load', colorizeImg.bind(img, apiURL, useCachedPanels));
                    } else {
                        colorizeImg(img, apiURL, useCachedPanels, null);
                    }
                });
            }
        });
    }

    colorizeMangaEventHandler();

    const observer = new MutationObserver(colorizeMangaEventHandler);
    observer.observe(document.querySelector("body"), { subtree: true, childList: true });
})();
