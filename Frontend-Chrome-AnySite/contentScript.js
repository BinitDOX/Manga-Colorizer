(() => {
    let mangaTitle = document.location.hostname;
    let mangaChapter = document.location.pathname?.slice(1).replace(/\//g, '_');

    String.prototype.rsplit = function(sep, maxsplit) {
        var split = this.split(sep);
        return maxsplit ? [ split.slice(0, -maxsplit).join(sep) ].concat(split.slice(-maxsplit)) : split;
    }

    const colorizeMangaEventHandler = () => {
        chrome.storage.local.get(["apiURL", "cachedPanels"], (result) => {
            console.log("MC content: storage.local.get result:", result);
            let apiURL = result.apiURL || "";
            let useCachedPanels = true;
            if (result.cachedPanels !== undefined) {
                useCachedPanels = result.cachedPanels;
            }
            // console.log("MC content: Get apiURL:", apiURL);
            // console.log("MC content: Get cachedPanels:", useCachedPanels);

            console.log('MC: Scanning images...')
            document.querySelectorAll("img:not([colorized])").forEach(img => {
                if (img.width > 500 && img.height > 500) {
                    // console.log("img: ", img.src);
                    // console.log("img attributes: ", img.attributes);
                    var imgCanvas = document.createElement("canvas"),
                    imgContext = imgCanvas.getContext("2d");

                    try {
                        // Make sure canvas is as big as the picture
                        imgCanvas.width = img.width;
                        imgCanvas.height = img.height;

                        // Draw image into canvas element
                        imgContext.drawImage(img, 0, 0, img.width, img.height);
                        // Save image as a data URL
                        imgName = (img.src || img.dataset.src).rsplit('/', 1)[1];
                        console.log('imgName', imgName)

                        imgData = imgCanvas.toDataURL("image/png");

                        const postData = {
                            mangaTitle: mangaTitle,
                            mangaChapter: mangaChapter,
                            useCachedPanels: useCachedPanels,
                            imgName: imgName,
                            imgData: imgData
                        };
                        // console.log('postData', postData)

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
                                img.classList.add("colorized");
                                console.log('MC: COLORIZED!');
                            })
                            .catch(error => {
                                console.error('MC: ' + error);
                            });
                    } catch(e1) {
                        console.log('Could not get data URL', e1)
                    }
                }
            });
        });
    }

    colorizeMangaEventHandler();
})();
