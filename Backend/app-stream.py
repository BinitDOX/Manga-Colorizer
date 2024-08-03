import argparse
import base64
import io
import json
import random
import time
import urllib.error
import urllib.request
import os
import gc

import PIL.Image
import numpy as np
from flask import Flask, request, jsonify, abort
from flask_cors import CORS

from denoisator import MangaDenoiser
from colorizator import MangaColorizator
from upscalator import MangaUpscaler
from utils.utils import distance_from_grayscale, generate_random_id, \
    image_to_base64, load_image_as_base64, save_image, sanitize_string, clear_torch_cache


app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})


@app.route('/')
def index():
    return 'Manga Colorizer is Up and Running!'


@app.route('/colorize-image-data', methods=['POST'])
def colorize_image_data():
    rid = generate_random_id()

    try:
        req_json = request.get_json()
        img_name = req_json.get('imgName', f'Image-{rid}')
        img_url = req_json.get('imgURL', '')
        img_data = req_json.get('imgData')
        img_width = req_json.get('imgWidth', -1)
        img_height = req_json.get('imgHeight', -1)
        colorize = req_json.get('colorize', config.colorize)
        upscale = req_json.get('upscale', config.upscale)
        denoise = req_json.get('denoise', config.denoise)
        denoise_sigma = req_json.get('denoiseSigma', config.denoise_sigma)
        upscale_factor = req_json.get('upscaleFactor', config.upscale_factor)
        cache = req_json.get('cache', False)
        manga_title = req_json.get('mangaTitle', '')
        manga_chapter = req_json.get('mangaChapter', '')

        if denoise_sigma < 0:
            print(f'[-] [{rid}] Denoiser sigma ({denoise_sigma}) cannot be negative, using default')
            denoise_sigma = config.denoise_sigma

        if upscale_factor not in [2, 4]:
            print(f'[-] [{rid}] Upscale factor ({upscale_factor}) must be 2 or 4, using default')
            upscale_factor = config.upscale_factor

        check_model_availability(rid, colorize, config.colorize, 'colorize')
        check_model_availability(rid, upscale, config.upscale, 'upscale')
        check_model_availability(rid, denoise, config.denoise, 'denoise')

        if manga_title and manga_chapter:
            print(f'[+] [{rid}] Detected manga: {manga_title} >> {manga_chapter}')
            if cache and not rid in img_name:
                cached_image = load_from_cache(manga_title, manga_chapter, img_name)
                if cached_image:
                    print(f'[+] [{rid}] Retrieving cached image')
                    return jsonify({'colorImgData': cached_image})

        print(f'[+] [{rid}] Requested image: {img_name}, Width: {img_width}, Height: {img_height}')
        print(f'[+] [{rid}] Colorize: {colorize}, Upscale: {upscale}{f"(x{upscale_factor})" if upscale else ""}, Denoise: {denoise}')

        if img_data:
            img_metadata, img_data64 = img_data.split(',', 1)
            orig_image_binary = base64.decodebytes(bytes(img_data64, encoding='utf-8'))
        elif img_url:  # Could not find imgData, look for imgURL instead
            orig_image_binary = retrieve_image_binary(rid, request, img_url)
        else:
            msg = 'Neither imgData nor imgURL found in the request'
            print(f'[-] [{rid}] {msg}')
            return jsonify({'msg': f'Image: {img_name}, Error: {msg}'})

        imgio = io.BytesIO(orig_image_binary)
        image = PIL.Image.open(imgio)
        image = np.array(image)

        if not img_data:
            coloredness = distance_from_grayscale(image)
            print(f'[+] [{rid}] Image distance from grayscale: {coloredness}')
            if coloredness > 1:
                print(f'[+] [{rid}] Image already colored: {coloredness}')
                return jsonify({'msg': f'Image: {img_name}, Already colored: {coloredness} > 1'})

        if denoise:
            print(f'[*] [{rid}] Denoising image...')
            image = denoise_image(rid, image, denoiser, denoise_sigma)

        if colorize:
            print(f'[*] [{rid}] Colorizing image...')
            image = colorize_image(rid, image, colorizer, config.colorized_image_size)

        if upscale:
            print(f'[*] [{rid}] Upscaling image...')
            image = upscale_image(rid, image, upscaler, upscale_factor)

        if cache:
            try:
                if manga_title and manga_chapter and rid not in img_name:
                    save_to_cache(manga_title, manga_chapter, img_name, image)
                    print(f'[+] [{rid}] Imaged cached')
                else:
                    print(f'[-] [{rid}] Caching enabled, but manga details could not be detected, skipping')
            except Exception as te:
                print(f'[-] [{rid}] Error while cacheing: {te}')

        result_image_data64 = image_to_base64(image)
        return jsonify({'colorImgData': result_image_data64})

    except RuntimeError as e:
        print(f'[!] [{rid}] Error: {e}')
        handle_cuda_error(e)

    response = jsonify({'msg': f'Image: {img_name}, Error: Unable to colorize'})
    return response


def handle_cuda_error(e):
    global colorizer, upscaler, denoiser

    if 'CUDA error: an illegal memory access was encountered' \
        in str(e) or 'CUDA out of memory' in str(e) or \
        'CUDA error: misaligned address' in str(e):
        print(f'[-] CUDA Error encountered, reinitializing...')
        colorizer = None
        upscaler = None
        denoiser = None
        clear_torch_cache()
        gc.collect()
        initialize_components()

def get_cache_filename(manga_title, manga_chapter, image_name):
    chapter_dir = get_cache_dir(manga_title, manga_chapter)
    filename = f"{sanitize_string(image_name.strip())}.webp"
    return os.path.join(chapter_dir, filename)

def get_cache_dir(manga_title, manga_chapter):
    title_dir = os.path.join(config.cache_root.strip().replace(' ', '_'), sanitize_string(manga_title.strip()))
    chapter_dir = os.path.join(title_dir, sanitize_string(manga_chapter.strip()))
    return chapter_dir

def save_to_cache(manga_title, manga_chapter, image_name, image):
    cache_filename = get_cache_filename(manga_title, manga_chapter, image_name)
    os.makedirs(os.path.dirname(cache_filename), exist_ok=True)
    save_image(image, cache_filename)

def load_from_cache(manga_title, manga_chapter, image_name):
    cache_filename = get_cache_filename(manga_title, manga_chapter, image_name)
    if os.path.exists(cache_filename):
        return load_image_as_base64(cache_filename)
    return None

def check_model_availability(rid, requested, available, name):
    if requested and not available:
        print(f'[-] [{rid}] Requested {name}, but model is not initialized, please run the server without --no-{name}')


def retrieve_image_binary(rid, original_request, url):
    user_agent = original_request.headers.get('User-Agent', '')
    referer = request.referrer if request.referrer else ''
    origin = request.origin if request.origin else ''

    referer = referer if referer else origin
    origin = origin if origin else referer

    headers = {
        'User-Agent': user_agent,
        'Referer': referer,
        'Origin': origin,
        'Accept': 'image/png;q=1.0,image/jpg;q=0.9,image/webp;q=0.7,image/*;q=0.5',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'identity'
    }

    print(f'[*] Retrieving image from url={url}')
    try:
        req = urllib.request.Request(url, headers=headers)
        return urllib.request.urlopen(req).read()
    except urllib.error.URLError as e:
        print(f'[!] [{rid}] URLError: {e.reason}')
        abort(500)
    except os.error as ex:
        print(f'[!] [{rid}] Retrieve error: {ex}')
    return False


def denoise_image(rid, image, denoiser, sigma):
    start_time = time.time()
    denoised_image = denoiser.denoise(image, sigma)
    elapsed_time = time.time() - start_time
    print(f'[+] [{rid}] Denoised image {[*image.shape]}->{[*denoised_image.shape]} in {elapsed_time:.2f} seconds.')
    return denoised_image


def colorize_image(rid, image, colorizer, size):
    start_time = time.time()
    colorizer.set_image((image.astype('float32') / 255), size)
    colorized_image = colorizer.colorize()
    elapsed_time = time.time() - start_time
    print(f'[+] [{rid}] Colorized image {[*image.shape]}->{[*colorized_image.shape]} in {elapsed_time:.2f} seconds.')
    return colorized_image


def upscale_image(rid, image, upscaler, factor):
    start_time = time.time()
    upscaled_image = upscaler.upscale((image.astype('float32') / 255), factor)
    elapsed_time = time.time() - start_time
    print(f'[+] [{rid}] Upscaled image (x{factor}) {[*image.shape]}->{[*upscaled_image.shape]} in {elapsed_time:.2f} seconds.')
    return upscaled_image


config = None
colorizer = None
upscaler = None
denoiser = None

def initialize_components():
    global colorizer, upscaler, denoiser

    colorizer = MangaColorizator(config) if config.colorize else None
    upscaler = MangaUpscaler(config) if config.upscale else None
    denoiser = MangaDenoiser(config) if config.denoise else None
    print(f'[+] Components initialized')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run Manga Colorizer server')
    parser.add_argument('--device', choices=['cpu', 'cuda'], default='cuda', help='Device to use')

    parser.add_argument('--colorizer_path', default='networks/generator.zip')
    parser.add_argument('--extractor_path', default='networks/extractor.pth')
    parser.add_argument('--upscaler_path', default='networks/RealESRGAN_x4plus_anime_6B.pt')
    parser.add_argument('--upscaler_type', choices=['ESRGAN', 'GigaGAN'], default='ESRGAN')

    parser.add_argument('--no-ssl', dest='ssl', action='store_false', default=True, help='Disable SSL context.')
    parser.add_argument('--no-upscale', dest='upscale', action='store_false', default=True, help='Disable upscaling')
    parser.add_argument('--no-colorize', dest='colorize', action='store_false', default=True,
                        help='Disable colorization')
    parser.add_argument('--no-denoise', dest='denoise', action='store_false', default=True, help='Disable denoiser')
    parser.add_argument('--upscale_factor', choices=[2, 4], default=4, type=int, help='Upscale by x2 or x4')
    parser.add_argument('--denoise_sigma', default=25, type=int, help='How much noise to expect from the image')

    config = parser.parse_args()

    config.upscaler_tile_size = 256
    config.colorizer_tile_size = 0
    config.tile_pad = 8
    config.colorized_image_size = 576  # Width
    config.cache_root = 'manga'

    initialize_components()

    if config.ssl:
        context = ('ssl/server.crt', 'ssl/server.key')
        app.run(host='0.0.0.0', port=5000, ssl_context=context)
    else:
        app.run(host='0.0.0.0', port=5000)
