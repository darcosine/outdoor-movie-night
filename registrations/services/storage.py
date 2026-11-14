"""Store and remove validated uploads in Cloudinary, S3-compatible, or local storage."""

import uuid
from urllib.parse import unquote, urlparse

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.files.storage import default_storage


def _store_image(content, folder_name: str) -> str:
    name = f"{folder_name}/{uuid.uuid4().hex}.jpg"
    content.seek(0)

    if settings.CLOUDINARY_URL:
        import cloudinary
        import cloudinary.uploader

        cloudinary.config(cloudinary_url=settings.CLOUDINARY_URL)
        result = cloudinary.uploader.upload(
            content,
            folder=f"movie-night/{folder_name}",
            resource_type="image",
            format="jpg",
        )
        url = result.get("secure_url") or ""
        if not url:
            raise ImproperlyConfigured("Cloudinary did not return an image URL.")
        return url

    if settings.AWS_STORAGE_BUCKET_NAME and settings.AWS_ACCESS_KEY_ID:
        import boto3

        client = boto3.client(
            "s3",
            endpoint_url=settings.AWS_S3_ENDPOINT_URL or None,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION or None,
        )
        content.seek(0)
        client.upload_fileobj(
            content,
            settings.AWS_STORAGE_BUCKET_NAME,
            name,
            ExtraArgs={"ContentType": "image/jpeg"},
        )
        base = (settings.AWS_S3_PUBLIC_URL or "").rstrip("/")
        if not base:
            raise ImproperlyConfigured("Set AWS_S3_PUBLIC_URL so uploaded images can be opened.")
        return f"{base}/{name}"

    if settings.ALLOW_LOCAL_MEDIA:
        saved = default_storage.save(name, content)
        return f"{settings.MEDIA_URL}{saved}"

    raise ImproperlyConfigured(
        "Image storage is not configured. Set CLOUDINARY_URL or an S3-compatible bucket."
    )


def store_poster(content) -> str:
    return _store_image(content, "posters")


def _delete_image(image_url: str, folder_name: str) -> None:
    """Delete an image only when its URL belongs to the configured image folder."""
    if not image_url:
        return

    if settings.CLOUDINARY_URL:
        import cloudinary
        import cloudinary.uploader

        path = urlparse(image_url).path.lstrip("/")
        marker = "image/upload/"
        if marker not in path:
            raise ImproperlyConfigured("The image URL is not a Cloudinary upload URL.")
        public_id = path.split(marker, 1)[1]
        pieces = public_id.split("/")
        if pieces and pieces[0].startswith("v") and pieces[0][1:].isdigit():
            pieces = pieces[1:]
        public_id = "/".join(pieces).rsplit(".", 1)[0]
        expected_folder = f"movie-night/{folder_name}/"
        if not public_id.startswith(expected_folder):
            raise ImproperlyConfigured("Refusing to delete an image outside its managed folder.")
        cloudinary.config(cloudinary_url=settings.CLOUDINARY_URL)
        result = cloudinary.uploader.destroy(
            public_id,
            resource_type="image",
            invalidate=True,
        )
        if result.get("result") not in {"ok", "not found"}:
            raise ImproperlyConfigured("Cloudinary did not confirm image deletion.")
        return

    if settings.AWS_STORAGE_BUCKET_NAME and settings.AWS_ACCESS_KEY_ID:
        import boto3

        base = urlparse(settings.AWS_S3_PUBLIC_URL)
        candidate = urlparse(image_url)
        if not base.scheme or candidate.netloc != base.netloc:
            raise ImproperlyConfigured("The image URL does not match the configured bucket URL.")
        base_path = base.path.rstrip("/") + "/"
        if not candidate.path.startswith(base_path):
            raise ImproperlyConfigured("The image URL is outside the configured bucket path.")
        key = unquote(candidate.path[len(base_path):])
        if not key.startswith(f"{folder_name}/"):
            raise ImproperlyConfigured("Refusing to delete an object outside its managed folder.")
        client = boto3.client(
            "s3",
            endpoint_url=settings.AWS_S3_ENDPOINT_URL or None,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION or None,
        )
        client.delete_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=key)
        return

    if settings.ALLOW_LOCAL_MEDIA:
        path = urlparse(image_url).path
        media_url = settings.MEDIA_URL
        if not path.startswith(media_url):
            raise ImproperlyConfigured("The image URL is outside local media storage.")
        name = unquote(path[len(media_url):])
        if not name.startswith(f"{folder_name}/") or ".." in name.split("/"):
            raise ImproperlyConfigured("Refusing to delete a file outside its managed folder.")
        default_storage.delete(name)
        return

    raise ImproperlyConfigured("No configured image storage is available for deletion.")


def delete_poster(image_url: str) -> None:
    _delete_image(image_url, "posters")
