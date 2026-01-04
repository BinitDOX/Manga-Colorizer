import argparse
import os
import time
import numpy as np
import PIL.Image as Image
from denoisator import MangaDenoiser
from colorizator import MangaColorizator
from upscalator import MangaUpscaler
from utils.utils import distance_from_grayscale, save_image, clear_torch_cache

DEFAULT_MODEL_PATHS = {
    # Colorizers
    'AlacGAN': 'networks/generator.zip',
    'CycleGAN': 'networks/latest_net_G_A.pth',

    # Upscalers
    'ESRGAN': 'networks/RealESRGAN_x4plus_anime_6B.pt',
    'GigaGAN': 'networks/GigaGAN.ckpt'
}

class ModelSettings:
    pass

def resolve_paths(config):
    if config.colorizer_path is None:
        config.colorizer_path = DEFAULT_MODEL_PATHS.get(config.colorizer_type)
        print(f"[*] Defaulting colorizer path to: {config.colorizer_path}")

    if config.upscaler_path is None:
        config.upscaler_path = DEFAULT_MODEL_PATHS.get(config.upscaler_type)
        print(f"[*] Defaulting upscaler path to: {config.upscaler_path}")



def process_image(image_path, output_folder, colorizer, upscaler, denoiser, config):
    image_name = os.path.basename(image_path)
    try:
        image = Image.open(image_path).convert("RGB")
        image = np.array(image)
    except Exception as e:
        print(f"[-] Could not open {image_name}: {e}")
        return

    coloredness = distance_from_grayscale(image)
    if coloredness > 1:
        print(f"[+] {image_name} is already colored (dist: {coloredness:.2f}), skipping.")
        return

    start_total = time.time()

    # 1. Denoise
    if config.denoise and denoiser:
        print(f"[*] [{image_name}] Denoising...")
        image = denoiser.denoise(image, config.denoise_sigma)

    # 2. Colorize
    if config.colorize and colorizer:
        print(f"[*] [{image_name}] Colorizing using {config.colorizer_type}...")
        colorizer.set_image((image.astype('float32') / 255))
        image = colorizer.colorize()

    # 3. Upscale
    if config.upscale and upscaler:
        print(f"[*] [{image_name}] Upscaling ({config.upscale_factor}x) using {config.upscaler_type}...")
        image = upscaler.upscale((image.astype('float32') / 255), config.upscale_factor)

    output_path = os.path.join(output_folder, image_name)
    save_image(image, output_path)

    elapsed = time.time() - start_total
    print(f"[+] Saved to {output_path} (Took {elapsed:.2f}s)")


def main():
    parser = argparse.ArgumentParser(description="Batch Colorize/Upscale Images")
    parser.add_argument("--input_path", type=str, default="input", help="Folder containing images")
    parser.add_argument("--output_path", type=str, default="output", help="Folder to save processed images")
    parser.add_argument('--device', choices=['cpu', 'cuda'], default='cuda', help='Device to use')

    parser.add_argument('--colorizer_path', default=None, help='Path to colorizer weights')
    parser.add_argument('--colorizer_type', choices=['AlacGAN', 'CycleGAN'], default='AlacGAN',
                        help='Which architecture: AlacGAN or CycleGAN')

    parser.add_argument('--upscaler_path', default=None, help='Path to upscaler weights')
    parser.add_argument('--upscaler_type', choices=['ESRGAN', 'GigaGAN'], default='ESRGAN',
                        help='Which architecture: ESRGAN or GigaGAN')

    parser.add_argument('--no-upscale', dest='upscale', action='store_false', default=True, help='Disable upscaling')
    parser.add_argument('--no-colorize', dest='colorize', action='store_false', default=True,
                        help='Disable colorization')
    parser.add_argument('--no-denoise', dest='denoise', action='store_false', default=True, help='Disable denoiser')

    parser.add_argument('--upscale_factor', choices=[2, 4], default=4, type=int, help='Upscale by x2 or x4')
    parser.add_argument('--denoise_sigma', default=25, type=int, help='How much noise to expect from the image')

    config = parser.parse_args()

    # Model Configuration
    # 1. ESRGAN Settings
    config.esrgan = ModelSettings()
    config.esrgan.tile_size = 256
    config.esrgan.tile_pad = 10

    # 2. GigaGAN (AuraSR) Settings
    config.gigagan = ModelSettings()
    config.gigagan.batch_size = 4  # Modify to 8, 16, or even 32 if enough VRAM
    config.gigagan.use_overlap = False  # True = High Quality (Slow x2), False = Fast

    # 3. AlacGAN Settings
    config.alacgan = ModelSettings()
    config.alacgan.tile_size = 0
    config.alacgan.tile_pad = 0
    config.alacgan.image_size = 576

    # 4. CycleGAN Settings
    config.cyclegan = ModelSettings()
    config.cyclegan.tile_size = 0
    config.cyclegan.tile_pad = 0
    config.cyclegan.image_size = 512

    resolve_paths(config)

    if not os.path.exists(config.input_path):
        print(f"[-] Input path '{config.input_path}' does not exist.")
        return

    os.makedirs(config.output_path, exist_ok=True)

    print("[+] Initializing models...")
    colorizer = MangaColorizator(config) if config.colorize else None
    upscaler = MangaUpscaler(config) if config.upscale else None
    denoiser = MangaDenoiser(config) if config.denoise else None
    print("[+] Models ready.")

    images = [f for f in os.listdir(config.input_path) if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))]

    if not images:
        print("[-] No images found in input folder.")
        return

    for img in images:
        process_image(os.path.join(config.input_path, img), config.output_path, colorizer, upscaler, denoiser, config)

    print("[+] Batch processing complete")
    clear_torch_cache()


if __name__ == "__main__":
    main()