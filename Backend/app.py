from flask import Flask, request, send_from_directory, url_for, jsonify
from flask_cors import CORS

import os
import re
import urllib.request

from colorizator import MangaColorizator
from inference import colorize_images as batch_colorize_images

app = Flask(__name__)
CORS(app)
image_folder = './manga'

@app.route('/')
def index():
    return 'Manga Colorizer is Up and Running!'

@app.route('/colorized-images/<path:filename>')
def serve_image(filename):
    subfolder, filename = filename.rsplit('/', 1)
    filename = filename.rsplit('.', 1)[0]+'.png'
    print(f'{image_folder}/{subfolder}', filename)
    return send_from_directory(f'{image_folder}/{subfolder}', filename)

@app.route('/colorize-images', methods=['POST'])
def colorize_images():
    data = request.get_json()
    manga_title = data['mangaTitle']
    manga_chapter = data['mangaChapter']
    img_src_list = data['imgSrcList']
    use_cached_panels = data['useCachedPanels']

    manga_title = re.sub('[^a-zA-Z0-9 \n\.]', '', manga_title).strip()
    manga_chapter = re.sub('[^a-zA-Z0-9 \n\.]', '', manga_chapter).strip()
    os.makedirs(f'manga/{manga_title}/{manga_chapter}', exist_ok=True)

    print(f'[+] Got: {manga_title} >> {manga_chapter}')
    
    opener=urllib.request.build_opener()
    opener.addheaders=[('User-Agent','Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/111.0'),
        ('Accept', 'image/avif,image/webp,*/*'), ('Accept-Language', 'en-US,en;q=0.5'), ('Accept-Encoding', 'gzip, deflate, br'), ('Referer', 'https://chapmanganelo.com/')]
    urllib.request.install_opener(opener)

    print('[*] Downloading...')
    for i, img_url in enumerate(img_src_list):
        if img_url == 'error':
            continue
        img_name = img_url.rsplit('/', 1)[1]
        f_path = f'manga/{manga_title}/{manga_chapter}/{img_name}'
        if os.path.exists(f_path) == False:
            urllib.request.urlretrieve(img_url, f_path)
    
    print(f'[*] Colorizing...')
    run_batch_colorizer(manga_title, manga_chapter, use_cached_panels)

    print('[*] Uploading...')
    colorized_urls = []
    for i, img_url in enumerate(img_src_list):
        img_url = img_url.rsplit('/', 1)[1]
        fpath = f'{manga_title}/{manga_chapter}/colored/{img_url}'
        colorized_urls.append(url_for('serve_image', filename=fpath))

    print('[+] Response Sent...')
    response = jsonify({'colorized_urls': colorized_urls})
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response


def run_batch_colorizer(m_title, m_chapter, use_cached):
    class Configuration:
        def __init__(self):
            self.path = f'manga/{m_title}/{m_chapter}'
            self.generator = 'networks/generator.zip'
            self.extractor = 'networks/extractor.pth'
            self.gpu = True
            self.denoiser = True
            self.denoiser_sigma =25
            self.size = 576
            self.use_cached = use_cached

    args = Configuration()

    if args.gpu:
        device = 'cuda'
    else:
        device = 'cpu'
        
    colorizer = MangaColorizator(device, args.generator, args.extractor)

    colorization_path = os.path.join(f'manga/{m_title}/{m_chapter}/colored')
    os.makedirs(colorization_path, exist_ok=True)
    
    batch_colorize_images(colorization_path, colorizer, args)



if __name__ == '__main__':
    context = ('server.crt', 'server.key')
    app.run(host='0.0.0.0', port=5000, ssl_context=context)