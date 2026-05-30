from __future__ import annotations

import base64
from io import BytesIO

from PIL import Image


def ensure_rgb(image: Image.Image) -> Image.Image:
    if image.mode == "RGB":
        return image
    if image.mode == "RGBA":
        background = Image.new("RGB", image.size, (255, 255, 255))
        background.paste(image, mask=image.getchannel("A"))
        return background
    return image.convert("RGB")


def resize_max(image: Image.Image, max_size: int) -> Image.Image:
    result = image.copy()
    result.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
    return result


def image_to_base64_jpeg(image: Image.Image, quality: int = 85) -> str:
    buffer = BytesIO()
    ensure_rgb(image).save(buffer, format="JPEG", quality=quality)
    return base64.b64encode(buffer.getvalue()).decode("ascii")

