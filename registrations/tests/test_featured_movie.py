import io

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from PIL import Image

from registrations.models import FeaturedMovie


def poster_upload():
    buffer = io.BytesIO()
    Image.new("RGB", (600, 900), "#ba5533").save(buffer, format="JPEG")
    return SimpleUploadedFile("poster.jpg", buffer.getvalue(), content_type="image/jpeg")


@pytest.mark.django_db
def test_staff_can_publish_movie_title_and_poster_on_home(client, tmp_path):
    staff = get_user_model().objects.create_user(
        username="movie-editor", password="test-pass-12345", is_staff=True,
    )
    client.force_login(staff)

    with override_settings(ALLOW_LOCAL_MEDIA=True, MEDIA_ROOT=tmp_path):
        response = client.post(reverse("dashboard:movie"), {
            "title": "The Starry Night",
            "poster_upload": poster_upload(),
        })
        movie = FeaturedMovie.objects.get(pk=1)
        page = client.get(reverse("registrations:home")).content.decode()

    assert response.status_code == 302
    assert movie.title == "The Starry Night"
    assert movie.poster_image_url.startswith("/media/posters/")
    assert "The Starry Night" in page
    assert movie.poster_image_url in page


@pytest.mark.django_db
def test_staff_can_change_movie_title_without_replacing_poster(client):
    movie = FeaturedMovie.objects.create(
        title="Old title", poster_image_url="https://example.test/posters/current.jpg",
    )
    staff = get_user_model().objects.create_user(
        username="movie-editor-2", password="test-pass-12345", is_staff=True,
    )
    client.force_login(staff)

    response = client.post(reverse("dashboard:movie"), {"title": "New title"})

    movie.refresh_from_db()
    assert response.status_code == 302
    assert movie.title == "New title"
    assert movie.poster_image_url == "https://example.test/posters/current.jpg"
