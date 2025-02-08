import argparse
import os
import time
import numpy as np
import PIL.Image as Image
from denoisator import MangaDenoiser
from colorizator import MangaColorizator
from upscalator import MangaUpscaler
from utils.utils import distance_from_grayscale, save_image, clear_torch_cache

def process_image(image_path, output_folder, colorizer, upscaler, denoiser, config):
    image_name = os.path.basename(image_path)
    image = Image.open(image_path).convert("RGB")
    image = np.array(image)
    
    coloredness = distance_from_grayscale(image)
    if coloredness > 1:
        print(f"[+] {image_name} is already colored, skipping.")
        return
    
    if config.denoise:
        print(f"[*] Denoising {image_name}...")
        image = denoiser.denoise(image, config.denoise_sigma)
    
    if config.colorize:
        print(f"[*] Colorizing {image_name}...")
        colorizer.set_image((image.astype('float32') / 255), config.colorized_image_size)
        image = colorizer.colorize()
    
    if config.upscale:
        print(f"[*] Upscaling {image_name} by {config.upscale_factor}x...")
        image = upscaler.upscale((image.astype('float32') / 255), config.upscale_factor)
    
    output_path = os.path.join(output_folder, image_name)
    save_image(image, output_path)
    print(f"[+] Processed {image_name} -> Saved to {output_path}")

def main():
    parser = argparse.ArgumentParser(description="Batch Colorize Images")
    parser.add_argument("--input_path", type=str, default="input", help="Folder containing images")
    parser.add_argument("--output_path", type=str, default="output", help="Folder to save processed images")
    
    parser.add_argument('--device', choices=['cpu', 'cuda'], default='cuda', help='Device to use')

    parser.add_argument('--colorizer_path', default='networks/generator.zip')
    parser.add_argument('--extractor_path', default='networks/extractor.pth')
    parser.add_argument('--upscaler_path', default='networks/RealESRGAN_x4plus_anime_6B.pt')
    parser.add_argument('--upscaler_type', choices=['ESRGAN', 'GigaGAN'], default='ESRGAN')

    parser.add_argument('--no-upscale', dest='upscale', action='store_false', default=True, help='Disable upscaling')
    parser.add_argument('--no-colorize', dest='colorize', action='store_false', default=True,
                        help='Disable colorization')
    parser.add_argument('--no-denoise', dest='denoise', action='store_false', default=True, help='Disable denoiser')
    parser.add_argument('--upscale_factor', choices=[2, 4], default=4, type=int, help='Upscale by x2 or x4')
    parser.add_argument('--denoise_sigma', default=25, type=int, help='How much noise to expect from the image')

    config = parser.parse_args()
    os.makedirs(config.output_path, exist_ok=True)
    
    config.upscaler_tile_size = 256
    config.colorizer_tile_size = 0
    config.tile_pad = 8
    config.colorized_image_size = 576  # Width
    
    colorizer = MangaColorizator(config) if config.colorize else None
    upscaler = MangaUpscaler(config) if config.upscale else None
    denoiser = MangaDenoiser(config) if config.denoise else None
    print("[+] Components initialized")
    
    images = [f for f in os.listdir(config.input_path) if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))]
    for img in images:
        process_image(os.path.join(config.input_path, img), config.output_path, colorizer, upscaler, denoiser, config)
    print("[+] Batch processing complete")
    
    clear_torch_cache()
    print("[+] Components released")
    

if __name__ == "__main__":
    main()
