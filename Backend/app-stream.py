from os import error
from flask import Flask, request, send_from_directory, url_for, jsonify
from flask_cors import CORS

import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import base64, io
import urllib.request, urllib.error

from colorizator import MangaColorizator

app = Flask(__name__)
CORS(app)

@app.route('/')
def index():
    return 'Manga Colorizer is Up and Running!'

@app.route('/colorize-image-data', methods=['POST'])
def colorize_image_data():
    img_format = 'PNG'
    req_json = request.get_json()
    try:
        img_size = closestDivisibleBy32(req_json['imgWidth'])
    except KeyError: 
        img_size = 576
    print("size", img_size)
    img_data = req_json.get('imgData')
    img_url = req_json.get('imgURL')
    if (img_data):
        img_metadata, img_data64 = img_data.split(',', 1)
        orig_image_binary = base64.decodebytes(bytes(img_data64, encoding='utf-8'))
    elif (img_url): # did not find imgData, look for imgURL instead
        orig_image_binary = retrieve_image_binary(request, img_url)
    else:
        raise Exception("Neither imgData nor imgURL found in request JSON")

    imgio = io.BytesIO(orig_image_binary)
    image = mpimg.imread(imgio, format=img_format)

    class Configuration:
        def __init__(self):
            self.generator = 'networks/generator.zip'
            self.extractor = 'networks/extractor.pth'
            self.gpu = True
            self.denoiser = True
            self.denoiser_sigma = 25
            self.size = img_size
            self.use_cached = False

    args = Configuration()

    if args.gpu:
        device = 'cuda'
    else:
        device = 'cpu'
        
    colorizer = MangaColorizator(device, args.generator, args.extractor)   
    color_image_data64 = colorize_image(image, colorizer, args)

    response = jsonify({'colorImgData': color_image_data64})
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

def retrieve_image_binary(orig_req, url):
    print("Original headers", orig_req.headers)
    headers={
        'User-Agent': orig_req.headers.get('User-Agent'),
        'Referer': request.referrer,
        'Origin': request.origin,
        'Accept': 'image/avif,image/webp,*/*',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br' }
    print("Retrieving", url, headers)
    try:
        req = urllib.request.Request(url, headers=headers)
        return urllib.request.urlopen(req).read()
    except urllib.error.URLError as e:
        print("URLError", e.reason)
    except error as e2:
        print("Retrieve error", e2)

def colorize_image(image, colorizer, args):
    colorizer.set_image(image, args.size, args.denoiser, args.denoiser_sigma)
    colorized_img = colorizer.colorize()
    return (img_to_base64_str(colorized_img))

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
    context = ('server.crt', 'server.key')
    app.run(host='0.0.0.0', port=5000, ssl_context=context)
