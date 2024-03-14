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
            console.log("MC content: Get apiURL:", apiURL);
            console.log("MC content: Get cachedPanels:", useCachedPanels);

            console.log('MC: Scanning images...')

            const imgSrcList = [];
            Array.from(document.images).forEach(img => {
                if (img.width > 500 && img.height > 500)
                    if(img.src != '')
                        imgSrcList.push(img.src)
                    else if(img.dataset.src != '')
                        imgSrcList.push(img.dataset.src)
                    else
                        imgSrcList.push('error')
            });

            const data = {
                mangaTitle: mangaTitle,
                mangaChapter: mangaChapter,
                imgSrcList: imgSrcList,
                useCachedPanels: useCachedPanels
            };

            const options = {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            };
            console.log("MC: Sending data:", data);
            let curl = apiURL + '/colorize-images';
            console.log("MC: Sending to:", curl);
            fetch(curl, options)
                .then(response => response.json())
                .then(data => {
                    console.log('MC: Setting Panels...');
                    colorized_urls = data['colorized_urls']
                    Array.from(document.images).forEach(img => {
                    if (img.width > 500 && img.height > 500)
                        if(img.src != ''){
                            f_name = img.src.rsplit('/', 1)[1].rsplit('.', 1)[0];
                            colorized_urls.forEach(url => {
                                const cf_name = url.rsplit('/', 1)[1].rsplit('.', 1)[0];
                                if(cf_name === f_name){
                                    img.src = apiURL + url;
                                    img.dataset.src = '';
                                }
                            });
                        } else if(img.dataset.src != ''){
                            f_name = img.dataset.src.rsplit('/', 1)[1].rsplit('.', 1)[0];
                            colorized_urls.forEach(url => {
                                const cf_name = url.rsplit('/', 1)[1].rsplit('.', 1)[0];
                                if(cf_name === f_name){
                                    img.src = apiURL + url;
                                    img.dataset.src = '';
                                }
                            });
                        }
                    });
                    console.log('MC: COLORIZED!');
                })
                .catch(error => {
                    console.error('MC: ' + error);
                });
        });
    }

    colorizeMangaEventHandler();
})();
