from django import forms

from patients.models import Patient
from patients.image_utils import safe_image_upload

from .models import AdoptionPost, LostPetReport, Sighting


def photo_without_location_metadata(uploaded_file):
    return safe_image_upload(uploaded_file)


class LostPetReportForm(forms.ModelForm):
    class Meta:
        model = LostPetReport
        fields = ["patient", "name", "species", "breed", "description", "photo", "last_seen_at", "area_label", "latitude", "longitude"]
        labels = {"patient": "Paciente registrado (opcional)", "name": "Nombre del animal", "species": "Especie", "breed": "Raza", "description": "Señas particulares", "photo": "Foto", "last_seen_at": "Última vez visto", "area_label": "Zona o barrio", "latitude": "Latitud exacta (opcional)", "longitude": "Longitud exacta (opcional)"}
        widgets = {"last_seen_at": forms.DateTimeInput(attrs={"type": "datetime-local"}), "description": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, patient_queryset=None, **kwargs):
        super().__init__(*args, **kwargs)
        queryset = patient_queryset if patient_queryset is not None else Patient.objects.none()
        self.fields["patient"].queryset = queryset.filter(active=True).order_by("name")
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


class AdoptionPostForm(forms.ModelForm):
    class Meta:
        model = AdoptionPost
        fields = ["name", "species", "breed", "age_label", "description", "photo", "area_label"]
        labels = {
            "name": "Nombre del animal", "species": "Especie", "breed": "Raza", "age_label": "Edad aproximada",
            "description": "Historia y cuidados importantes", "photo": "Foto", "area_label": "Zona o barrio",
        }
        widgets = {"description": forms.Textarea(attrs={"rows": 4})}

    def clean_photo(self):
        return photo_without_location_metadata(self.cleaned_data.get("photo"))
