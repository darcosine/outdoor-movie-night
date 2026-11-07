"""Validate uploaded student ID cards and movie posters with Pillow."""

from io import BytesIO

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from PIL import Image, UnidentifiedImageError

Image.MAX_IMAGE_PIXELS = 24_000_000
_ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}


def _validated_jpeg(uploaded, *, min_width, min_height, size_message, dimensions_message):
    if uploaded.size > settings.ID_CARD_MAX_BYTES:
        raise ValidationError(size_message)

    data = uploaded.read()
    try:
        uploaded.seek(0)
    except Exception:
        pass

    try:
        probe = Image.open(BytesIO(data))
        probe.verify()
        image = Image.open(BytesIO(data))
        image.load()
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as exc:
        raise ValidationError("Upload a valid JPEG, PNG, or WebP image.") from exc

    if image.format not in _ALLOWED_FORMATS:
        raise ValidationError("Use a JPEG, PNG, or WebP image. HEIC is not accepted.")

    width, height = image.size
    if width < min_width or height < min_height:
        raise ValidationError(dimensions_message)
    if width > settings.ID_CARD_MAX_EDGE or height > settings.ID_CARD_MAX_EDGE:
        raise ValidationError("That image is too large. Crop it and try again.")

    buffer = BytesIO()
    image.convert("RGB").save(buffer, format="JPEG", quality=88, optimize=True)
    return ContentFile(buffer.getvalue(), name="upload.jpg")


def validate_id_card(uploaded):
    return _validated_jpeg(
        uploaded,
        min_width=settings.ID_CARD_MIN_WIDTH,
        min_height=settings.ID_CARD_MIN_HEIGHT,
        size_message="ID card photo must be under 5 MB.",
        dimensions_message="That photo is too small. Move closer so the ID card fills the frame.",
    )


def validate_poster_image(uploaded):
    return _validated_jpeg(
        uploaded,
        min_width=300,
        min_height=400,
        size_message="Movie poster must be under 5 MB.",
        dimensions_message="Poster image must be at least 300 × 400 pixels.",
    )
