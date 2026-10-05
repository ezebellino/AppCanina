from django import forms

from .models import Organization


class BusinessProfileForm(forms.ModelForm):
    class Meta:
        model = Organization
        fields = ["name", "kind", "logo", "phone", "email", "address"]
        labels = {
            "name": "Nombre de la veterinaria o negocio",
            "kind": "Tipo de negocio",
        }
        help_texts = {
            "logo": "Opcional. Se verá en el perfil y junto al nombre del negocio.",
        }
