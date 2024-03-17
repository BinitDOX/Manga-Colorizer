(() => {

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
                document.querySelectorAll("img:not(.mangacolor)").forEach(img => {
                    if (img.complete && img.width > 500 && img.height > 500) {
                        try {
                            imgName = (img.src || img.dataset.src).rsplit('/', 1)[1];
                            console.log('imgName', imgName)

                            const imgCanvas = document.createElement("canvas");
                            imgCanvas.width = img.width;
                            imgCanvas.height = img.height;
                    
                            const imgContext = imgCanvas.getContext("2d", { willReadFrequently: true });
                            imgContext.drawImage(img, 0, 0, img.width, img.height);
        
                            if (isColoredContext(imgContext)) {
                                console.log('already colored');
                                img.classList.add("mangacolor");
                            } else {
                                const imgData = imgCanvas.toDataURL("image/png");
                                const mangaTitle = document.location.hostname;
                                const mangaChapter = document.location.pathname?.slice(1).replace(/\//g, '_');
                            
                                const postData = {
                                    mangaTitle: mangaTitle,
                                    mangaChapter: mangaChapter,
                                    useCachedPanels: useCachedPanels,
                                    imgName: imgName,
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
                                        img.classList.add("mangacolor");
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
                });
            }
        });
    }

    colorizeMangaEventHandler();
})();
