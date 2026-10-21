"""Safe, privacy-preserving processing for user-uploaded animal photos."""

from io import BytesIO
from pathlib import Path

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from PIL import Image, UnidentifiedImageError


MAX_UPLOAD_BYTES = 8 * 1024 * 1024
MAX_IMAGE_PIXELS = 20_000_000


def safe_image_upload(uploaded_file):
    """Validate, bound and rewrite images without EXIF metadata.

    The rewrite removes location metadata before photos are persisted.  Bounds
    keep an accidental or hostile oversized image from exhausting worker memory.
    """
    if not uploaded_file:
        return uploaded_file
    if uploaded_file.size > MAX_UPLOAD_BYTES:
        raise ValidationError("La imagen supera el límite de 8 MB.")
    try:
        image = Image.open(uploaded_file)
        image.verify()
        uploaded_file.seek(0)
        image = Image.open(uploaded_file)
        if image.width * image.height > MAX_IMAGE_PIXELS:
            raise ValidationError("La imagen es demasiado grande. Elegí una de hasta 20 megapíxeles.")
        image.load()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as error:
        raise ValidationError("La foto no es una imagen válida o no se puede procesar.") from error

    image_format = "JPEG" if image.format in {"JPEG", "JPG"} else "PNG"
    if image_format == "JPEG" and image.mode not in {"RGB", "L"}:
        image = image.convert("RGB")
    output = BytesIO()
    image.save(output, format=image_format, quality=90, optimize=True)
    suffix = ".jpg" if image_format == "JPEG" else ".png"
    return ContentFile(output.getvalue(), name=f"{Path(uploaded_file.name).stem}{suffix}")
