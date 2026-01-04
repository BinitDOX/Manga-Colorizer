import numpy as np
import torch

from networks.RRDBNet import Upscaler as ESRGANNet
from networks.aura_sr import Upscaler as GigaGANNet, upscale_4x, upscale_4x_overlapped
from utils.utils import tile_process


class UpscalingStrategy:
    def __init__(self, config):
        self.config = config
        self.device = config.device
        self.model = None

    def upscale(self, image, factor):
        raise NotImplementedError


class ESRGANStrategy(UpscalingStrategy):
    def __init__(self, config):
        super().__init__(config)
        self.model = ESRGANNet().to(self.device)
        self.load_weights(config.upscaler_path)
        self.model.eval()
        self.params = config.esrgan

    def load_weights(self, path):
        try:
            model_or_chkpt = torch.load(path, map_location=self.device, weights_only=False)
            self.model.generator = model_or_chkpt
            print(f"[+] Loaded ESRGAN weights  from {path}")
        except Exception as e:
            print(f"[-] Failed to load ESRGAN weights: {e}")

    def upscale(self, image, factor):
        img_tensor = torch.from_numpy(image).to(self.device)
        result = img_tensor.permute(2, 0, 1).unsqueeze(0).float()

        with torch.no_grad():
            if self.params.tile_size > 0:
                result = tile_process(
                    self.model,
                    result,
                    factor,
                    self.params.tile_size,
                    self.params.tile_pad
                )
            else:
                result = self.model(result)

        result = result.data.squeeze().float().cpu().clamp_(0, 1).numpy()
        result = np.transpose(result[[2, 1, 0], :, :], (1, 2, 0))
        result = (result * 255.0).round().astype(np.uint8)
        result = result[:, :, ::-1]

        return result


class GigaGANStrategy(UpscalingStrategy):
    def __init__(self, config):
        super().__init__(config)
        self.model = GigaGANNet().to(self.device)
        self.load_weights(config.upscaler_path)
        self.model.eval()
        self.params = config.gigagan
        print(f"[*] GigaGAN Config: Batch={self.params.batch_size}, Overlap={self.params.use_overlap}")

    def load_weights(self, path):
        try:
            checkpoint = torch.load(path, map_location=self.device, weights_only=False)
            if 'state_dict' in checkpoint:
                sd = checkpoint['state_dict']
                new_sd = {k.replace('model.', '').replace('generator.', ''): v for k, v in sd.items()}
                self.model.generator.load_state_dict(new_sd, strict=False)
            else:
                self.model.generator.load_state_dict(checkpoint, strict=False)
            print(f"[+] GigaGAN weights loaded from {path}")
        except Exception as e:
            print(f"[-] Failed to load GigaGAN weights: {e}")

    def upscale(self, image, factor):
        if factor != 4:
            print(f"[-] Warning: GigaGAN is natively 4x. Requested {factor}x.")

        try:
            req_size = self.model.generator.input_image_size
        except AttributeError:
            req_size = 64

        with torch.no_grad():
            if self.params.use_overlap:
                result = upscale_4x_overlapped(
                    image,
                    self.model,
                    input_image_size=req_size,
                    max_batch_size=self.params.batch_size
                )
            else:
                result = upscale_4x(
                    image,
                    self.model,
                    input_image_size=req_size,
                    max_batch_size=self.params.batch_size
                )

        if result.dtype != np.uint8:
            result = (result).clip(0, 255).astype(np.uint8)

        return result

class MangaUpscaler:
    def __init__(self, config):
        if config.device == 'cuda' and not torch.cuda.is_available():
            print("[-] CUDA not available, using CPU.")
            config.device = 'cpu'

        if config.upscaler_type == 'GigaGAN':
            self.strategy = GigaGANStrategy(config)
        elif config.upscaler_type == 'ESRGAN':
            self.strategy = ESRGANStrategy(config)
        else:
            raise Exception('Invalid upscaler type')

    def upscale(self, image, factor):
        if image.shape[2] == 4:
            image = image[:, :, :3]

        return self.strategy.upscale(image, factor)