(() => {
    let mangaTitle = '';
    let mangaChapter = '';
    let useCachedPanels = true;
    let baseUrl = '';

    String.prototype.rsplit = function(sep, maxsplit) {
        var split = this.split(sep);
        return maxsplit ? [ split.slice(0, -maxsplit).join(sep) ].concat(split.slice(-maxsplit)) : split;
    }

    chrome.storage.local.get("baseURL").then((result) => {
        baseUrl = result.baseURL || "";
      });

    chrome.storage.local.get("cachedPanels", ({ cachedPanels: value }) => {
      if (value !== undefined) {
        useCachedPanels = value;
      }
    });

    chrome.runtime.onMessage.addListener((message) => {
        if (message.useCachedPanels !== undefined) {
          useCachedPanels = message.useCachedPanels;
        }
    });

    const newChapterLoaded = () => {
        mangaTitle = document.getElementsByClassName('panel-breadcrumb')[0].querySelectorAll('a')[1].innerText;
        mangaChapter = document.getElementsByClassName('panel-breadcrumb')[0].querySelectorAll('a')[2].innerText;

        const colorizeBtnExists = document.getElementsByClassName('colorize-btn')[0];
        if (!colorizeBtnExists) {
            const colorizeBtn = document.createElement('a');

            colorizeBtn.className = 'colorize-btn ' + 'navi-change-chapter-btn-next';
            colorizeBtn.innerHTML = 'COLORIZE CHAPTER'
            colorizeBtn.title = 'Click to colorize current chapter';

            mangaNavigationControls = document.getElementsByClassName('navi-change-chapter-btn')[0];
            
            mangaNavigationControls.append(colorizeBtn);
            colorizeBtn.addEventListener('click', colorizeMangaEventHandler);
        }
    }

    const colorizeMangaEventHandler = () => {
        chrome.storage.local.get("cachedPanels", ({ cachedPanels: value }) => {
            if (value !== undefined) {
              useCachedPanels = value;
            }
        });

        chrome.storage.local.get("baseURL").then((result) => {
            baseUrl = result.baseURL || "";
        });

        console.log('MC: Sending Panels...')
        const colorizeBtn = document.getElementsByClassName('colorize-btn navi-change-chapter-btn-next')[0];
        colorizeBtn.innerHTML = 'COLORIZING...';
        colorizeBtn.removeEventListener("click", colorizeMangaEventHandler);

        imageElements = document.getElementsByClassName('container-chapter-reader')[0].querySelectorAll('img');
        
        const imgSrcList = [];
        imageElements.forEach(imageElement => {
            if(imageElement.src != '')
                imgSrcList.push(imageElement.src)
            else if(imageElement.dataset.src != '')
                imgSrcList.push(imageElement.dataset.src)
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

        let curl = baseUrl + '/colorize-images';
        fetch(curl, options)
            .then(response => response.json())
            .then(data => {
                console.log('MC: Setting Panels...');
                colorized_urls = data['colorized_urls']
                imageElements = document.getElementsByClassName('container-chapter-reader')[0].querySelectorAll('img');
                imageElements.forEach(imageElement => {
                    if(imageElement.src != ''){
                        f_name = imageElement.src.rsplit('/', 1)[1].rsplit('.', 1)[0];
                        colorized_urls.forEach(url => {
                            if(url.includes(f_name)){
                                imageElement.src = baseUrl + url;
                                imageElement.dataset.src = '';
                            }
                        });
                    } else if(imageElement.dataset.src != ''){
                        f_name = imageElement.dataset.src.rsplit('/', 1)[1].rsplit('.', 1)[0];
                        colorized_urls.forEach(url => {
                            if(url.includes(f_name)){
                                imageElement.src = baseUrl + url;
                                imageElement.dataset.src = '';
                            }
                        });
                    }
                });
                colorizeBtn.innerHTML = 'COLORIZED!'
            })
            .catch(error => {
                colorizeBtn.innerHTML = 'ERROR!'
                console.error('MC: ' + error);
                colorizeBtn.addEventListener('click', colorizeMangaEventHandler);
            });
        }

    newChapterLoaded();
})();
