from os import error

from flask import Flask, request, jsonify, abort
from flask_cors import CORS

import time
import torch
import PIL.Image
import numpy as np
import base64, io
import urllib.request, urllib.error
import argparse

from matplotlib import pyplot as plt

from utils.utils import closest_divisible_by_32, img_to_base64_str, distance_from_grayscale, generate_random_id
from colorizator import MangaColorizator
from upscalator import MangaUpscaler

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

@app.route('/')
def index():
    return 'Manga Colorizer is Up and Running!'

@app.route('/colorize-image-data', methods=['POST'])
def colorize_image_data():
    rid = generate_random_id()
    response = False
    try:
        req_json = request.get_json()
        img_name = req_json.get('imgName') or f'Image-{rid}'
        img_width = req_json.get('imgWidth')
        img_height = req_json.get('imgHeight')

        if config.upscale_method == 'closest_fit' and img_width > 0:
            colored_img_size = closest_divisible_by_32(img_width)
        else:
            colored_img_size = 576

        print(f'[+] [{rid}] Requested image: {img_name}, Width: {img_width} Height: {img_height}')

        img_data = req_json.get('imgData')
        img_url = req_json.get('imgURL')
        if img_data:
            img_metadata, img_data64 = img_data.split(',', 1)
            orig_image_binary = base64.decodebytes(bytes(img_data64, encoding='utf-8'))
        elif img_url:  # Could not find imgData, look for imgURL instead
            orig_image_binary = retrieve_image_binary(rid, request, img_url)
        else:
            msg = 'Neither imgData nor imgURL found in request JSON'
            print(f'[-] [{rid}] {msg}')
            return jsonify({'msg': f'Image: {img_name}, Error: {msg}'})

        imgio = io.BytesIO(orig_image_binary)
        image = PIL.Image.open(imgio) 

        if not img_data:
            coloredness = distance_from_grayscale(image)
            print(f'[+] [{rid}] Image distance from grayscale: {coloredness}')
            if coloredness > 1:
                print(f'[+] [{rid}] Image already colored: {coloredness}')
                return jsonify({'msg': f'Image: {img_name}, Already colored: {coloredness} > 1'})

        print(f'[*] [{rid}] Colorizing image')
        result_image_data64 = colorize_and_scale_image(rid, image, colorizer, colored_img_size)
        if result_image_data64:
            return jsonify({'colorImgData': result_image_data64})

    except RuntimeError as e:
        print(f'[!] [{rid}] Error: {e}')

    response = jsonify({'msg': f'Image: {img_name}, Error: Unable to colorize'})
    return response

def retrieve_image_binary(rid, orig_req, url):
    headers={
        'User-Agent': orig_req.headers.get('User-Agent'),
        'Referer': request.referrer,
        'Origin': request.origin,
        'Accept': 'image/png;q=1.0,image/jpg;q=0.9,image/webp;q=0.7,image/*;q=0.5',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'identity' }
    print(f'[*] Retrieving image from url={url}')
    try:
        req = urllib.request.Request(url, headers=headers)
        return urllib.request.urlopen(req).read()
    except urllib.error.URLError as e:
        print(f'[!] [{rid}] URLError: {e.reason}')
        abort(500)
    except error as ex:
        print(f'[!] [{rid}] Retrieve error: {ex}')
    return False

def colorize_and_scale_image(rid, image, colorizer, size):
    if config.upscale_method == 'closest_fit':
        while size > 32:
            start_time = time.time()
            try:
                colorizer.set_image((np.array(image).astype('float32') / 255), size, config.denoise)
                colorized_img = colorizer.colorize(return_tensor=False)
                print(f'[+] [{rid}] Colorized size={size} in time={time.time() - start_time}s')
                return img_to_base64_str(colorized_img)
            except RuntimeError as e:
                se = str(e)
                if 'out of memory' in se:
                    se0 = se.split('.')[0]
                    print(f'[-] [{rid}] {se0} Size {size} in {time.time() - start_time} seconds. Trying with smaller size')
                    torch.cuda.empty_cache()
                    size -= 64
                else:
                    raise e

    if config.upscale_method == 'super_resolution':
        image = np.array(image)
        start_time = time.time()
        colorizer.set_image((image.astype('float32') / 255), size)
        colorized_img_tensor = colorizer.colorize(return_tensor=True)
        print(f'[+] [{rid}] Colorized image {image.shape}->{[*colorized_img_tensor.shape]} in {time.time() - start_time} seconds.')

        start_time = time.time()
        upscaled_img = upscaler.upscale(colorized_img_tensor)
        print(f'[+] [{rid}] Upscaled image {[*colorized_img_tensor.shape]}->{upscaled_img.shape} in {time.time() - start_time} seconds.')

        save_image_debug((colorized_img_tensor.detach().cpu().numpy() * 255.0).round().astype(np.uint8), 'colored.png')
        save_image_debug(upscaled_img, 'upscaled.png')
        return img_to_base64_str(upscaled_img)

    return False

def save_image_debug(image, filename):
    plt.imsave(filename, image, format="PNG")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run Flask app with optional SSL context.')
    parser.add_argument('--no-ssl', action='store_true', help='Disable SSL context.')
    parser.add_argument('--device', choices=['cpu', 'cuda'], default='cuda', help='Device to use')
    parser.add_argument('--upscale_method', choices=['closest_fit', 'super_resolution'], default='super_resolution')
    parser.add_argument('--colorizer_path', default = 'networks/generator.zip')
    parser.add_argument('--extractor_path', default = 'networks/extractor.pth')
    parser.add_argument('--upscaler_path', default='networks/RealESRGAN_x4plus_anime_6B.pt')
    
    config = parser.parse_args()

    config.denoise = True
    config.upscaler_tile_size = 256
    config.colorizer_tile_size = 0
    config.tile_pad = 8

    colorizer = MangaColorizator(config)

    if config.upscale_method == 'super_resolution':
        upscaler = MangaUpscaler(config)

    if config.no_ssl:
        app.run(host='0.0.0.0', port=5000)
    else:
        context = ('server.crt', 'server.key')
        app.run(host='0.0.0.0', port=5000, ssl_context=context)
