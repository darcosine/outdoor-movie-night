from django import forms
from django.core.exceptions import ValidationError

from registrations.models import FeaturedMovie
from registrations.services.images import validate_poster_image


class FeaturedMovieForm(forms.ModelForm):
    poster_upload = forms.FileField(
        required=False,
        label="Movie poster",
        widget=forms.FileInput(
            attrs={
                "accept": "image/jpeg,image/png,image/webp",
                "class": "poster-upload-input",
            }
        ),
    )

    class Meta:
        model = FeaturedMovie
        fields = ("title",)
        widgets = {
            "title": forms.TextInput(
                attrs={
                    "class": "field-input",
                    "placeholder": "Movie title",
                    "maxlength": 160,
                }
            )
        }

    def clean_poster_upload(self):
        uploaded = self.cleaned_data.get("poster_upload")
        return validate_poster_image(uploaded) if uploaded else None

    def clean(self):
        cleaned = super().clean()
        if not self.instance.poster_image_url and not cleaned.get("poster_upload"):
            self.add_error("poster_upload", "Upload a poster to publish the featured movie.")
        return cleaned
