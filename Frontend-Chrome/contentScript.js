'use strict';
if (window.injectedMC !== 1) {
    window.injectedMC = 1;
    console.log('[MC] Starting context script');
    const maxColoredSrc = 200; // Length of img.src to keep in img.coloredsrc
    var activeFetches = 0;

    var maxActiveFetches = 1;  // Number of images to request and process parallely
    var colorTolerance = 30;  // If difference between red, blue, and green values is greater than this for any pixel,
                      // image is assumed to be in color and will not be recolored.
    var colorStride = 4; // When checking for an already-colored image,
                         // skip this many rows and columns at edges and between pixels.
                         // Check every pixel for color if zero.
    var denoise = true
    var colorize = true
    var upscale = true
    var upscaleFactor = 4  // Image upscale factor x2 or x4
    var denoiseSigma = 25  // Expected noise in image

    String.prototype.rsplit = function(sep, maxsplit) {
        const split = this.split(sep);
        return maxsplit ? [ split.slice(0, -maxsplit).join(sep) ].concat(split.slice(-maxsplit)) : split;
    }

    const siteConfigurations = {
        'mangadex.org': {
            titleSelector: 'a[data-v-5d3b2210]',
            chapterSelector: 'div#chapter-selector span[data-v-d2fabe5b]',
            getTitle: (document) => document.querySelector(siteConfigurations['mangadex.org'].titleSelector)?.innerText,
            getChapter: (document) => document.querySelector(siteConfigurations['mangadex.org'].chapterSelector)?.innerText,
        },
        'senkuro.com': {
            titleSelector: 'p.nav-reader-caption__desktop',
            chapterSelector: 'p.nav-reader-caption__mobile',
            getTitle: (document) => document.querySelector(siteConfigurations['senkuro.com'].titleSelector)?.innerText,
            getChapter: (document) => document.querySelector(siteConfigurations['senkuro.com'].chapterSelector)?.innerText,
        },
        'chapmanganelo.com': {
            titleSelector: 'div.panel-breadcrumb a[title]',
            chapterSelector: 'div.panel-breadcrumb a[title]',
            getTitle: (document) => document.querySelectorAll(siteConfigurations['chapmanganelo.com'].titleSelector)?.[1]?.innerText,
            getChapter: (document) => document.querySelectorAll(siteConfigurations['chapmanganelo.com'].chapterSelector)?.[2]?.innerText,
        },
        'fanfox.net' : {
            titleSelector: 'p.reader-header-title-1 a[href]',
            chapterSelector: 'p.reader-header-title-2',
            getTitle: (document) => document.querySelector(siteConfigurations['fanfox.net'].titleSelector)?.innerText,
            getChapter: (document) => document.querySelector(siteConfigurations['fanfox.net'].chapterSelector)?.innerText,
        }
    };

    const maxDistFromGray = (ctx) => {
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
        console.log('[MC] Max distance from gray: ', maxDist)
        return maxDist;
    }

    const isColoredContext = (ctx) => {
        return (colorTolerance < 255) && maxDistFromGray(ctx) > colorTolerance;
    }

    async function fetchColorizedImg(url, options, img, imgName) {
        console.log('[MC] Fetching: ', url, imgName);
        return fetch(url, options)
            .then(response => {
                if(!response.ok)
                    return response.text().then(text => {throw text})
                else
                    return response.json()})
            .then(json => {
                if (json.msg)
                    console.log('[MC] Message: ', json.msg);
                if (json.colorImgData) {
                    img.coloredsrc = json.colorImgData.slice(0, maxColoredSrc);
                    img.src = json.colorImgData;
                    if (img.dataset?.src) img.dataset.src = '';
                    if (img.srcset) img.srcset = '';
                    console.log('[MC] Processed: ', imgName);
                }
            })
            .catch(error => {
                console.log('[MC] Fetch error: ', error);
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

    const setColoredOrFetch = (img, imgName, apiURL, colorStride, imgContext, mangaProps) => {
        var canSendData = true;
        try {
            if (isColoredContext(imgContext, colorStride)) {
                img.coloredsrc = img.src.slice(0, maxColoredSrc);
                console.log('[MC] Already colored: ', imgName);
                return 1;
            }
        } catch(eIsColor) {
            canSendData = false
            if (!eIsColor.message.startsWith("Failed to execute 'getImageData'")) {
                console.log('[MC] Colorized context error: ', eIsColor)
                return 0;
            }
        }

        if (activeFetches < maxActiveFetches) {
            activeFetches += 1;
            img.coloredsrc = img.src.slice(0, maxColoredSrc); // Assume already colored while fetch is in progress
            const postData = {
                imgName: imgName,
                imgWidth: img.width,
				imgHeight: img.height,
				denoise: denoise,
				colorize: colorize,
				upscale: upscale,
				denoiseSigma: Number(denoiseSigma),
				upscaleFactor: Number(upscaleFactor),

				mangaTitle: mangaProps.title,
				mangeChapter: mangaProps.chapter,
				mangaPage: mangaProps.page.toString()
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
            return 3
        } else {
            return 2;
        }
    }

    const imgSrcMatchesColoredSrc = (img) => { return img.src.startsWith(img.coloredsrc)}

    const colorizeImg = (img, apiURL, colorStride, mangaProps) => {
        if (apiURL && (!imgSrcMatchesColoredSrc(img))) try {
            if (!img.complete) throw ('image not complete');
            const imgName = (img.src || img.dataset?.src || '').rsplit('/', 1)[1];
            if (imgName) {
                let imgContext = canvasContextFromImg(img);
                return setColoredOrFetch(img, imgName, apiURL, colorStride, imgContext, mangaProps);
            }
            return 0;
        } catch(e) {
            console.log('[MC] Colorize image error: ', e)
            return 0;
        }
    }

    const colorizeMangaEventHandler = (event=null) => {
        try {
            chrome.storage.local.get(["apiURL", "maxActiveFetches", "denoise", "colorize", "upscale", "denoiseSigma", "upscaleFactor",
                "colorTolerance", "colorStride", "minImgHeight", "minImgHeight"], (result) => {
                const apiURL = result.apiURL;
                if (apiURL) {
                    maxActiveFetches = Number(result.maxActiveFetches || "1")
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
                    const title = site ? (siteConfigurations[site].getTitle(document) || '') : '';
                    const chapter = site ? (siteConfigurations[site].getChapter(document) || '') : '';

                    console.log(title, chapter)
                    return;

                    console.log('[MC] Scanning images...')

                    let total = 0;
                    let skipped = 0;
                    let colored = 0;
                    let failed = 0;
                    let awaited = 0;
                    let processing = 0;

                    const images = document.querySelectorAll('img');
                    total= images.length;

                    images.forEach((img, index) => {
                        if (imgSrcMatchesColoredSrc(img)) {
                            colored++;
                        } else if (!img.complete || !img.src) {
                            img.addEventListener('load', colorizeMangaEventHandler, { passive: true });
                            skipped++
                        } else if (img.width > 0 && img.width < minImgWidth || img.height > 0 && img.height < minImgHeight) {
                            skipped++
                        } else {
                            mangaProps = {title: title, chapter: chapter, page: index}
                            let status = colorizeImg(img, apiURL, colorStride, mangaProps);
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

    colorizeMangaEventHandler();

    const observer = new MutationObserver(colorizeMangaEventHandler);
    observer.observe(document.querySelector("body"), { subtree: true, childList: true });
};
