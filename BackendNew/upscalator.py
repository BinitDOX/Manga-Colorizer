import torch
import numpy as np

from networks.RRDBNet import Upscaler
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

        self.model = Upscaler().to(self.device)
        model = torch.load(config.upscaler_path, map_location=self.device)
        self.model.generator = model
        self.model = self.model.eval()

        self.scale = 4

    def upscale(self, img_tensor):
        with torch.no_grad():
            result = img_tensor.permute(2, 0, 1).unsqueeze(0)
            if self.tile_size > 0:
                result = tile_process(self.model, result.detach(), self.scale, self.tile_size, self.tile_pad)
            else:
                result = self.model(result.detach())
            result = result.data.squeeze().float().cpu().clamp_(0, 1).numpy()
            result = np.transpose(result[[2, 1, 0], :, :], (1, 2, 0))
            result = (result * 255.0).round().astype(np.uint8)
            result = result[:, :, ::-1]
        return result
