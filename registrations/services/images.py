"""Validate uploaded movie posters with Pillow."""

from io import BytesIO

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from PIL import Image, UnidentifiedImageError

Image.MAX_IMAGE_PIXELS = 24_000_000
_ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}


def validate_poster_image(uploaded):
    if uploaded.size > 5 * 1024 * 1024:
        raise ValidationError("Movie poster must be under 5 MB.")
    data = uploaded.read()
    try:
        uploaded.seek(0)
    except Exception:
        pass
    try:
        probe = Image.open(BytesIO(data))
        probe.verify()
        image = Image.open(BytesIO(data))
        width, height = image.size
        if width > 8000 or height > 8000 or width * height > 24_000_000:
            raise ValidationError("That image is too large. Crop it and try again.")
        image.load()
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as exc:
        raise ValidationError("Upload a valid JPEG, PNG, or WebP image.") from exc
    if image.format not in _ALLOWED_FORMATS:
        raise ValidationError("Use a JPEG, PNG, or WebP image. HEIC is not accepted.")
    if width < 300 or height < 400:
        raise ValidationError("Poster image must be at least 300 × 400 pixels.")
    buffer = BytesIO()
    image.convert("RGB").save(buffer, format="JPEG", quality=88, optimize=True)
    return ContentFile(buffer.getvalue(), name="upload.jpg")
