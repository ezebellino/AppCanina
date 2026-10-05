from django import forms
from django.contrib.auth.models import User

from .models import Organization


class InitialSetupForm(forms.Form):
    business_name = forms.CharField(label="Nombre del negocio", max_length=160, initial="Tu Veterinaria")
    business_kind = forms.ChoiceField(label="Tipo de negocio", choices=Organization.Kind.choices, initial=Organization.Kind.VETERINARY)
    username = forms.CharField(label="Usuario administrador", max_length=150)
    email = forms.EmailField(label="Correo electrónico", required=False)
    password1 = forms.CharField(label="Contraseña", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Repetir contraseña", widget=forms.PasswordInput)

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("Ese usuario ya existe.")
        return username

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("password1") and cleaned.get("password2") and cleaned["password1"] != cleaned["password2"]:
            self.add_error("password2", "Las contraseñas no coinciden.")
        return cleaned
