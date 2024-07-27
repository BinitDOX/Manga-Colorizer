from os import error

import cv2
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
        img_width = req_json.get('imgWidth')
        img_height = req_json.get('imgHeight')

        print(f'Image Height: {img_height}, Image Width: {img_width}')

        if args.resize_method == 'closest_fit' and img_width > 0:
            colored_img_size = closest_divisible_by_32(img_width)
        else:
            colored_img_size = 576

        print(f'Requested {img_name} size {img_width}')
        denoiser = True
        denoiser_sigma = 25
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

        color_image_data64 = colorize_image(image, colorizer, colored_img_size, denoiser, denoiser_sigma, (img_width, img_height))
        if (color_image_data64):
            response = jsonify({'colorImgData': color_image_data64})
    except RuntimeError as e:
        print(str(e)[:256])
    response = response or jsonify({'msg': f'{colored_img_size}: unable to color.'})
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

def colorize_image(image, colorizer, size, denoiser, denoiser_sigma, original_size):
    if args.resize_method == 'closest_fit':
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

    else:
        start_time = time.time()
        colorizer.set_image((np.array(image).astype('float32') / 255), size, denoiser, denoiser_sigma)
        colorized_img = colorizer.colorize()
        print(f'Colorized size {size} in {time.time() - start_time} seconds.')

        if args.resize_method == 'basic':
            colorized_img = upscale_basic(colorized_img, original_size)
            return img_to_base64_str(colorized_img)
        if args.resize_method == 'antialias':
            colorized_img = upscale_antialias(colorized_img, original_size)
            return img_to_base64_str(colorized_img)
        elif args.resize_method == 'super_resolution':
            colorized_img = upscale_superres(colorized_img, original_size)
            return img_to_base64_str(colorized_img)

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
def closest_divisible_by_32(n):
    divby = 32
    q = int(n / divby)
    n1 = divby * q
    if (n * divby) > 0:
        n2 = (divby * (q + 1)) 
    else:
        n2 = (divby * (q - 1))
    if abs(n - n1) < abs(n - n2):
        return n1
    return n2

def upscale_basic(image, target_size):
    image = (image * 255).astype(np.uint8)
    upscaled_image = cv2.resize(image, target_size, interpolation=cv2.INTER_CUBIC)
    return upscaled_image / 255.0


def upscale_antialias(image, target_size):
    image = (image * 255).astype(np.uint8)
    image_pil = PIL.Image.fromarray(image)
    upscaled_image = image_pil.resize(target_size, PIL.Image.LANCZOS)
    upscaled_image = np.array(upscaled_image) / 255.0
    return upscaled_image

# TODO: Use a faster and better model
def upscale_superres(image, target_size):
    image = (image * 255).astype(np.uint8)
    sr = cv2.dnn_superres.DnnSuperResImpl_create()
    path = args.super_resolution  # Path to the pre-trained model file
    sr.readModel(path)
    sr.setPreferableBackend(cv2.dnn.DNN_BACKEND_CUDA)
    sr.setPreferableTarget(cv2.dnn.DNN_TARGET_CUDA)
    sr.setModel("edsr", 2)  # The EDSR model with a scaling factor of 4
    upscaled_image = sr.upsample(image)
    upscaled_image = cv2.resize(upscaled_image, target_size, interpolation=cv2.INTER_CUBIC)
    return upscaled_image / 255.0

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run Flask app with optional SSL context.')
    parser.add_argument('--no-ssl', action='store_true', help='Disable SSL context.')
    parser.add_argument('--device', choices=['cpu', 'cuda'], default='cuda', help='Device to use')
    parser.add_argument('--resize_method', choices=['closest_fit', 'super_resolution', 'basic', 'antialias'],
                        default='basic', help='Image resize method')
    parser.add_argument("-gen", "--generator", default = 'networks/generator.zip')
    parser.add_argument("-ext", "--extractor", default = 'networks/extractor.pth')
    parser.add_argument("-sres", "--super_resolution", default='networks/EDSR_x4.pb')
    
    args = parser.parse_args()

    colorizer = MangaColorizator(args.device, args.generator, args.extractor)

    if args.no_ssl:
        app.run(host='0.0.0.0', port=5000)
    else:
        context = ('server.crt', 'server.key')
        app.run(host='0.0.0.0', port=5000, ssl_context=context)
