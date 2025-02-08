import torch
import numpy as np

from networks.RRDBNet import Upscaler as ESRUpscaler
from networks.aura_sr import Upscaler as GigaUpscaler, upscale_4x_overlapped, upscale_4x
from utils.utils import tile_process

class MangaUpscaler:
    def __init__(self, config):
        if config.device == 'cuda' and not torch.cuda.is_available():
            print("[-] CUDA not available, using CPU.")
            self.device = 'cpu'
        else:
            self.device = config.device

        self.tile_size = config.upscaler_tile_size
        self.tile_pad = config.tile_pad

        if config.upscaler_type == 'GigaGAN':
            self.model = GigaUpscaler().to(self.device)
        else:
            self.model = ESRUpscaler().to(self.device)

        model_or_chkpt = torch.load(config.upscaler_path, map_location=self.device, weights_only=False)
        if config.upscaler_path.endswith(".pt"):
            self.model.generator = model_or_chkpt
        else:
            self.model.generator.load_state_dict(model_or_chkpt, strict=True)

        self.model = self.model.eval()


    def upscale(self, image, scale):
        if image.shape[2] == 4:
            image = image[:, :, :3]  # Discard the alpha channel

        with torch.no_grad():
            if isinstance(self.model, GigaUpscaler):
                result = upscale_4x(image, self.model)
            else:
                img_tensor = torch.from_numpy(image).to(self.device)
                result = img_tensor.permute(2, 0, 1).unsqueeze(0)
                if self.tile_size > 0:
                    result = tile_process(self.model, result.detach(), scale, self.tile_size, self.tile_pad)
                else:
                    result = self.model(result.detach())
                result = result.data.squeeze().float().cpu().clamp_(0, 1).numpy()
                result = np.transpose(result[[2, 1, 0], :, :], (1, 2, 0))
                result = (result * 255.0).round().astype(np.uint8)
                result = result[:, :, ::-1]
            return result
