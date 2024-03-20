from flask import Flask, request, send_from_directory, url_for, jsonify
from flask_cors import CORS

import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import base64, io

from colorizator import MangaColorizator

app = Flask(__name__)
CORS(app)

@app.route('/')
def index():
    return 'Manga Colorizer is Up and Running!'

@app.route('/colorize-image-data', methods=['POST'])
def colorize_image_data():
    req_json = request.get_json()
    img_data = req_json['imgData']
    try:    
        img_size = closestDivisibleBy32(req_json['imgWidth'])
    except KeyError: 
        img_size = 576

    print("size", img_size)
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
    color_image_data64 = colorize_base64_image(img_data, colorizer, args)

    response = jsonify({'colorImgData': color_image_data64})
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

def colorize_base64_image(img64, colorizer, args):
    img_metadata, img_data = img64.split(',', 1)
    image = img_from_base64(img_data)
    colorizer.set_image(image, args.size, args.denoiser, args.denoiser_sigma)
    colorized_img = colorizer.colorize()
    return (img_to_base64_str(colorized_img))

def img_from_base64(img64):
    orig_image_binary = base64.decodebytes(bytes(img64, encoding='utf-8'))
    imgio = io.BytesIO(orig_image_binary)
    return mpimg.imread(imgio, format='PNG')

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
