from io import BytesIO
from pathlib import Path

from django import forms
from django.core.files.base import ContentFile
from PIL import Image

from patients.models import Patient

from .models import LostPetReport, Sighting


def photo_without_location_metadata(uploaded_file):
    if not uploaded_file:
        return uploaded_file
    image = Image.open(uploaded_file)
    image.load()
    image_format = "JPEG" if image.format in {"JPEG", "JPG"} else "PNG"
    if image_format == "JPEG" and image.mode not in {"RGB", "L"}:
        image = image.convert("RGB")
    output = BytesIO()
    image.save(output, format=image_format, quality=90, optimize=True)
    suffix = ".jpg" if image_format == "JPEG" else ".png"
    filename = f"{Path(uploaded_file.name).stem}{suffix}"
    return ContentFile(output.getvalue(), name=filename)


class LostPetReportForm(forms.ModelForm):
    class Meta:
        model = LostPetReport
        fields = ["patient", "name", "species", "breed", "description", "photo", "last_seen_at", "area_label", "latitude", "longitude"]
        labels = {"patient": "Paciente registrado (opcional)", "name": "Nombre del animal", "species": "Especie", "breed": "Raza", "description": "Señas particulares", "photo": "Foto", "last_seen_at": "Última vez visto", "area_label": "Zona o barrio", "latitude": "Latitud exacta (opcional)", "longitude": "Longitud exacta (opcional)"}
        widgets = {"last_seen_at": forms.DateTimeInput(attrs={"type": "datetime-local"}), "description": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["patient"].queryset = Patient.objects.filter(active=True).order_by("name")
        self.fields["patient"].empty_label = "No vincular por ahora"
        self.fields["area_label"].widget.attrs["placeholder"] = "Ej.: Parque Central, Barrio Norte"

    def clean(self):
        cleaned = super().clean()
        latitude, longitude = cleaned.get("latitude"), cleaned.get("longitude")
        if (latitude is None) != (longitude is None):
            self.add_error("latitude" if latitude is None else "longitude", "Completá ambas coordenadas o dejá ambas vacías.")
        return cleaned

    def clean_photo(self):
        return photo_without_location_metadata(self.cleaned_data.get("photo"))


class SightingForm(forms.ModelForm):
    class Meta:
        model = Sighting
        fields = ["seen_at", "area_label", "description", "photo", "latitude", "longitude"]
        labels = {"seen_at": "Cuándo lo viste", "area_label": "Zona o barrio", "description": "Qué observaste", "photo": "Foto (opcional)", "latitude": "Latitud exacta (opcional)", "longitude": "Longitud exacta (opcional)"}
        widgets = {"seen_at": forms.DateTimeInput(attrs={"type": "datetime-local"}), "description": forms.Textarea(attrs={"rows": 3})}

    def clean(self):
        cleaned = super().clean()
        latitude, longitude = cleaned.get("latitude"), cleaned.get("longitude")
        if (latitude is None) != (longitude is None):
            self.add_error("latitude" if latitude is None else "longitude", "Completá ambas coordenadas o dejá ambas vacías.")
        return cleaned

    def clean_photo(self):
        return photo_without_location_metadata(self.cleaned_data.get("photo"))
