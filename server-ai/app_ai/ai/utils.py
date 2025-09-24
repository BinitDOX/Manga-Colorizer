import numpy as np
import cv2
import math
import torch
import logging

logger = logging.getLogger(__name__)


def resize_pad(img: np.ndarray, size: int = 256):
    """
    Resizes and pads an image to a given square size, ensuring dimensions are divisible by 32.
    Adapted from original logic.
    Args:
        img (np.ndarray): Input image as a NumPy array (HWC).
        size (int): Taarget base size (e.g., for square images).
    Returns:
        tuple[np.ndarray, tuple[int, int]]: The resized/padded image and the padding applied (height_pad, width_pad).
    """
    if img.ndim == 2:
        img = np.expand_dims(img, 2)
    if img.shape[2] == 1:
        img = np.repeat(img, 3, 2)
    if img.shape[2] == 4:
        img = img[:, :, :3]  # Discard alpha channel

    pad = (0, 0)  # Default no padding

    # Determine dominant dimension for initial resize
    if img.shape[0] < img.shape[1]:  # Width is dominant
        height = img.shape[0]
        ratio = height / (size * 1.5)
        width = int(np.ceil(img.shape[1] / ratio))
        img = cv2.resize(img, (width, int(size * 1.5)), interpolation=cv2.INTER_AREA)

        new_width = width + (32 - width % 32) % 32  # Ensure divisibility by 32
        pad = (0, new_width - width)  # Padding only on width

        if pad[1] > 0:
            img = np.pad(img, ((0, 0), (0, pad[1]), (0, 0)), 'maximum')

    else:  # Height is dominant
        width = img.shape[1]
        ratio = width / size
        height = int(np.ceil(img.shape[0] / ratio))
        img = cv2.resize(img, (size, height), interpolation=cv2.INTER_AREA)

        new_height = height + (32 - height % 32) % 32  # Ensure divisibility by 32
        pad = (new_height - height, 0)  # Padding only on height

        if pad[0] > 0:
            img = np.pad(img, ((0, pad[0]), (0, 0), (0, 0)), 'maximum')

    # Ensure clipping to 0-1 for float32 inputs if necessary
    if img.dtype == 'float32':
        np.clip(img, 0, 1, out=img)

    return img[:, :, :1], pad


def tile_process(model, img: torch.Tensor, scale: int, tile_size: int, tile_pad: int) -> torch.Tensor:
    """
    Processes an image by tiling to manage memory for large inputs.
    Adapted from original logic.
    Args:
        model: The PyTorch model to apply (colorizer or upscaler).
        img (torch.Tensor): Input image tensor (NCHW format).
        scale (int): Upscale factor (e.g., 1 for colorization, 2 or 4 for upscaling).
        tile_size (int): Size of each tile (square).
        tile_pad (int): Padding to apply to tiles to avoid border artifacts.
    Returns:
        torch.Tensor: Processed output image tensor.
    """

    batch, channel, height, width = img.shape
    output_height = height * scale
    output_width = width * scale
    output_shape = (batch, 3, output_height, output_width)

    # Start with black image (or zeros)
    output = img.new_zeros(output_shape)
    tiles_x = math.ceil(width / tile_size)
    tiles_y = math.ceil(height / tile_size)

    logger.debug(f"Tiling image into {tiles_x}x{tiles_y} tiles for processing.")

    # Loop over all tiles
    for y in range(tiles_y):
        for x in range(tiles_x):
            ofs_x = x * tile_size
            ofs_y = y * tile_size

            # Input tile area on total image (without padding)
            input_start_x = ofs_x
            input_end_x = min(ofs_x + tile_size, width)
            input_start_y = ofs_y
            input_end_y = min(ofs_y + tile_size, height)

            # Input tile area on total image with padding (expanded)
            input_start_x_pad = max(input_start_x - tile_pad, 0)
            input_end_x_pad = min(input_end_x + tile_pad, width)
            input_start_y_pad = max(input_start_y - tile_pad, 0)
            input_end_y_pad = min(input_end_y + tile_pad, height)

            # Input tile dimensions (actual tile to be processed, including padding)
            input_tile_width = input_end_x - input_start_x
            input_tile_height = input_end_y - input_start_y

            # Extract tile from input image
            input_tile = img[:, :, input_start_y_pad:input_end_y_pad, input_start_x_pad:input_end_x_pad]

            # Upscale/colorize tile
            try:
                with torch.no_grad():
                    if hasattr(model, 'name') and model.name == 'colorizer':
                        output_tile, _ = model(input_tile)
                    elif hasattr(model, 'name') and model.name == 'upscaler':
                        output_tile = model(input_tile)
                    else:
                        # Fallback if model.name is not set or recognized
                        output_tile = model(input_tile)

            except RuntimeError as error:
                logger.error(f"Error processing tile [{y * tiles_x + x + 1}/{tiles_x * tiles_y}]: {error}",
                             exc_info=True)
                raise
            except Exception as e:
                logger.error(f"Unexpected error in tile processing: {e}", exc_info=True)
                raise

            # output tile area on total image
            output_start_x = input_start_x * scale
            output_end_x = input_end_x * scale
            output_start_y = input_start_y * scale
            output_end_y = input_end_y * scale

            # output tile area without padding
            output_start_x_tile = (input_start_x - input_start_x_pad) * scale
            output_end_x_tile = output_start_x_tile + input_tile_width * scale
            output_start_y_tile = (input_start_y - input_start_y_pad) * scale
            output_end_y_tile = output_start_y_tile + input_tile_height * scale

            # Put processed tile into total output image
            output[:, :, output_start_y:output_end_y, output_start_x:output_end_x] = \
                output_tile[:, :, output_start_y_tile:output_end_y_tile, output_start_x_tile:output_end_x_tile]
    return output
