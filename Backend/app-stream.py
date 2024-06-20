from os import error
from flask import Flask, request, send_from_directory, url_for, jsonify, abort
from flask_cors import CORS

import time
import torch
import matplotlib.pyplot as plt
import PIL.Image
import numpy as np
import base64, io
import urllib.request, urllib.error
import argparse

from colorizator import MangaColorizator, distance_from_grayscale

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

@app.route('/')
def index():
    return 'Manga Colorizer is Up and Running!'

@app.route('/colorize-image-data', methods=['POST'])
def colorize_image_data():
    response = False
    try:
        req_json = request.get_json()
        img_name = req_json.get('imgName') or 'Image'
        img_size = req_json.get('imgWidth')
        if (img_size > 0):
            img_size = closestDivisibleBy32(img_size)
        else:
            img_size = 576
        print(f'Requested {img_name} size {img_size}')
        generator = req_json.get('generator') or 'networks/generator.zip'
        extractor = req_json.get('extractor') or 'networks/extractor.pth'
        denoiser = True
        denoiser_sigma = 25
        device = req_json.get('device') or 'cuda'
        img_data = req_json.get('imgData')
        img_url = req_json.get('imgURL')
        if (img_data):
            img_metadata, img_data64 = img_data.split(',', 1)
            # print("img_metadata", img_metadata)
            orig_image_binary = base64.decodebytes(bytes(img_data64, encoding='utf-8'))
        elif (img_url): # did not find imgData, look for imgURL instead
            orig_image_binary = retrieve_image_binary(request, img_url)
        else:
            return jsonify({'msg': f'{img_name} Neither imgData nor imgURL found in request JSON'})

        imgio = io.BytesIO(orig_image_binary)
        image = PIL.Image.open(imgio) 

        if not img_data:
            coloredness = distance_from_grayscale(image)
            print(f'Image distance from grayscale: {coloredness}')
            if (coloredness > 1):
                return jsonify({'msg': f'{img_name} already colored: {coloredness} > 1'})

        colorizer = MangaColorizator(device, generator, extractor)
        color_image_data64 = colorize_image(image, colorizer, img_size, denoiser, denoiser_sigma)
        if (color_image_data64):
            response = jsonify({'colorImgData': color_image_data64})
    except RuntimeError as e:
        print(str(e)[:256])
    response = response or jsonify({'msg': f'{img_name}: unable to color.'})
    return response

def retrieve_image_binary(orig_req, url):
    # print("Original headers", orig_req.headers)
    headers={
        'User-Agent': orig_req.headers.get('User-Agent'),
        'Referer': request.referrer,
        'Origin': request.origin,
        'Accept': 'image/png;q=1.0,image/jpg;q=0.9,image/webp;q=0.7,image/*;q=0.5',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'identity' }
    print("Retrieving", url, headers)
    try:
        req = urllib.request.Request(url, headers=headers)
        return urllib.request.urlopen(req).read()
    except urllib.error.URLError as e:
        print("URLError", e.reason)
        abort(500)
    except error as e2:
        print("Retrieve error", e2)
    return False        

def colorize_image(image, colorizer, size, denoiser, denoiser_sigma):
    while (size > 32):
        start_time = time.time()
        try:
            colorizer.set_image((np.array(image).astype('float32') / 255), size, denoiser, denoiser_sigma)
            colorized_img = colorizer.colorize()
            print(f'Colorized size {size} in {time.time() - start_time} seconds.')
            return img_to_base64_str(colorized_img)
        except RuntimeError as e:
            se = str(e)
            if 'out of memory' in se:
                se0 = se.split('.')[0]
                print(f'{se0} Size {size} in {time.time() - start_time} seconds. Trying with smaller size.')
                torch.cuda.empty_cache()
                size -= 64
            else:
                raise e
    return False

# def img_from_base64(img64):
#     orig_image_binary = base64.decodebytes(bytes(img64, encoding='utf-8'))
#     imgio = io.BytesIO(orig_image_binary)
#     return mpimg.imread(imgio, format='PNG')

def img_to_base64_str(img):
    buffered = io.BytesIO()
    plt.imsave(buffered, img, format="PNG")
    buffered.seek(0)
    img_byte = buffered.getvalue()
    return "data:image/png;base64," + base64.b64encode(img_byte).decode('utf-8')

# Function to find the number closest 
# to n and divisible by 32
def closestDivisibleBy32(n):
    divby = 32
    q = int(n / divby)
    n1 = divby * q
    if((n * divby) > 0):
        n2 = (divby * (q + 1)) 
    else:
        n2 = (divby * (q - 1))
    if (abs(n - n1) < abs(n - n2)) :
        return n1
    return n2

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run Flask app with optional SSL context.')
    parser.add_argument('--no-ssl', action='store_true', help='Disable SSL context.')
    
    args = parser.parse_args()

    if args.no_ssl:
        app.run(host='0.0.0.0', port=5000)
    else:
        context = ('server.crt', 'server.key')
        app.run(host='0.0.0.0', port=5000, ssl_context=context)
