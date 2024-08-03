import base64
import io
import math
import random
import re
import string

import numpy as np
import cv2
import torch
from matplotlib import pyplot as plt
import PIL.ImageChops, PIL.ImageOps, PIL.Image


def resize_pad(img, size = 256):
            
    if len(img.shape) == 2:
        img = np.expand_dims(img, 2)
        
    if img.shape[2] == 1:
        img = np.repeat(img, 3, 2)
        
    if img.shape[2] == 4:
        img = img[:, :, :3]

    pad = None        
            
    if (img.shape[0] < img.shape[1]):
        height = img.shape[0]
        ratio = height / (size * 1.5)
        width = int(np.ceil(img.shape[1] / ratio))
        img = cv2.resize(img, (width, int(size * 1.5)), interpolation = cv2.INTER_AREA)

        
        new_width = width + (32 - width % 32)
            
        pad = (0, new_width - width)
        
        img = np.pad(img, ((0, 0), (0, pad[1]), (0, 0)), 'maximum')
    else:
        width = img.shape[1]
        ratio = width / size
        height = int(np.ceil(img.shape[0] / ratio))
        img = cv2.resize(img, (size, height), interpolation = cv2.INTER_AREA)

        new_height = height + (32 - height % 32)
            
        pad = (new_height - height, 0)
        
        img = np.pad(img, ((0, pad[0]), (0, 0), (0, 0)), 'maximum')
        
    if (img.dtype == 'float32'):
        np.clip(img, 0, 1, out = img)

    return img[:, :, :1], pad

def image_to_base64(img, format="WEBP"):
    buffered = io.BytesIO()
    img = PIL.Image.fromarray(img)
    img.save(buffered, format=format)
    buffered.seek(0)
    img_byte = buffered.getvalue()
    return f"data:image/{format.lower()};base64," + base64.b64encode(img_byte).decode('utf-8')

def load_image_as_base64(filepath, format="WEBP"):
    with open(filepath, "rb") as img_file:
        img_byte = img_file.read()
    return f"data:image/{format.lower()};base64," + base64.b64encode(img_byte).decode('utf-8')

def save_image(image, filename, format="WEBP"):
    image_pil = PIL.Image.fromarray(image)
    image_pil.save(filename, format=format)

def sanitize_string(input_string):
    sanitized_string = re.sub(r'[^\w]', '_', input_string)
    return sanitized_string

def distance_from_grayscale(image):
    try:
        img_diff = PIL.ImageChops.difference(image, PIL.ImageOps.grayscale(image).convert('RGB'))
        dist = np.array(img_diff.getdata()).mean()
        return dist
    except:
        return 0

def generate_random_id(length=8):
    characters = string.ascii_uppercase + string.digits
    random_id = ''.join(random.choices(characters, k=length))
    return random_id

def clear_torch_cache():
    torch.cuda.empty_cache()

def tile_process(model, img, scale, tile_size, tile_pad):
    if scale == 2: print('[-] ScaleFactor=2 is broken, please do not use it yet')
    batch, channel, height, width = img.shape
    output_height = height * scale
    output_width = width * scale
    output_shape = (batch, 3, output_height, output_width)

    # start with black image
    output = img.new_zeros(output_shape)
    tiles_x = math.ceil(width / tile_size)
    tiles_y = math.ceil(height / tile_size)

    # loop over all tiles
    for y in range(tiles_y):
        for x in range(tiles_x):
            # extract tile from input image
            ofs_x = x * tile_size
            ofs_y = y * tile_size
            # input tile area on total image
            input_start_x = ofs_x
            input_end_x = min(ofs_x + tile_size, width)
            input_start_y = ofs_y
            input_end_y = min(ofs_y + tile_size, height)

            # input tile area on total image with padding
            input_start_x_pad = max(input_start_x - tile_pad, 0)
            input_end_x_pad = min(input_end_x + tile_pad, width)
            input_start_y_pad = max(input_start_y - tile_pad, 0)
            input_end_y_pad = min(input_end_y + tile_pad, height)

            # input tile dimensions
            input_tile_width = input_end_x - input_start_x
            input_tile_height = input_end_y - input_start_y
            tile_idx = y * tiles_x + x + 1
            input_tile = img[:, :, input_start_y_pad:input_end_y_pad, input_start_x_pad:input_end_x_pad]

            # upscale tile
            try:
                with torch.no_grad():
                    if model.name == 'colorizer':
                        output_tile,_ = model(input_tile)
                        # print(f'[+] Colorize Tile {tile_idx}/{tiles_x * tiles_y}')

                    if model.name == 'upscaler':
                        output_tile = model(input_tile)
                        # print(f'[+] Upscale Tile {tile_idx}/{tiles_x * tiles_y}')

            except RuntimeError as error:
                print('[!] Error: ', error)

            # output tile area on total image
            output_start_x = input_start_x * scale
            output_end_x = input_end_x  * scale
            output_start_y = input_start_y  * scale
            output_end_y = input_end_y  * scale

            # output tile area without padding
            output_start_x_tile = (input_start_x - input_start_x_pad)  * scale
            output_end_x_tile = output_start_x_tile + input_tile_width  * scale
            output_start_y_tile = (input_start_y - input_start_y_pad)  * scale
            output_end_y_tile = output_start_y_tile + input_tile_height * scale

            # put tile into output image
            output[:, :, output_start_y:output_end_y,
                        output_start_x:output_end_x] = output_tile[:, :, output_start_y_tile:output_end_y_tile,
                                                                   output_start_x_tile:output_end_x_tile]
    return output