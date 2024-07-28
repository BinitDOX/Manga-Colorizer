import torch
from torchvision.transforms import ToTensor
import numpy as np

from networks.colorizer import Colorizer
from denoising.denoiser import FFDNetDenoiser
from utils.utils import resize_pad, tile_process


class MangaColorizator:
    def __init__(self, config):
        if config.device == 'cuda' and not torch.cuda.is_available():
            print("[-] CUDA not available, using CPU.")
            self.device = 'cpu'
        else:
            self.device = config.device

        self.tile_size = config.colorizer_tile_size
        self.tile_pad = config.tile_pad

        self.model = Colorizer().to(self.device)
        state_dict = torch.load(config.colorizer_path, map_location=self.device)
        self.model.generator.load_state_dict(state_dict)
        self.model = self.model.eval()
        
        self.denoiser = FFDNetDenoiser(self.device)
        
        self.current_image = None
        self.current_hint = None
        self.current_pad = None

        self.scale = 1
        

    def set_image(self, image, size=576, transform = ToTensor()):
        if size % 32 != 0:
            raise RuntimeError("[-] Size is not divisible by 32")
        
        image, self.current_pad = resize_pad(image, size)
        self.current_image = transform(image).unsqueeze(0).to(self.device)
        self.current_hint = torch.zeros(1, 4, self.current_image.shape[2], self.current_image.shape[3])\
            .float().to(self.device)
    
    def update_hint(self, hint, mask):
        if issubclass(hint.dtype.type, np.integer):
            hint = hint.astype('float32') / 255
            
        hint = (hint - 0.5) / 0.5
        hint = torch.FloatTensor(hint).permute(2, 0, 1)
        mask = torch.FloatTensor(np.expand_dims(mask, 0))

        self.current_hint = torch.cat([hint * mask, mask], 0).unsqueeze(0).to(self.device)

    def colorize(self):
        with torch.no_grad():
            img = torch.cat([self.current_image, self.current_hint], 1)

            if self.tile_size > 0:
                fake_color = tile_process(self.model, img, self.scale, self.tile_size, self.tile_pad)
            else:
                fake_color, _ = self.model(img)
            result = fake_color[0].detach().permute(1, 2, 0) * 0.5 + 0.5
            if self.current_pad[0] != 0:
                result = result[:-self.current_pad[0]]
            if self.current_pad[1] != 0:
                result = result[:, :-self.current_pad[1]]

        return (result.detach().cpu().numpy() * 255.0).round().astype(np.uint8)