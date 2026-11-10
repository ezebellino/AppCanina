from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from .models import Organization


class InitialSetupForm(forms.Form):
    business_name = forms.CharField(label="Nombre del negocio", max_length=160, widget=forms.TextInput(attrs={"placeholder": "Nombre de tu veterinaria o refugio"}))
    business_kind = forms.ChoiceField(label="Tipo de negocio", choices=Organization.Kind.choices, initial=Organization.Kind.VETERINARY)
    username = forms.CharField(label="Usuario administrador", max_length=150)
    email = forms.EmailField(label="Correo electrónico", required=False)
    password1 = forms.CharField(label="Contraseña", strip=False, widget=forms.PasswordInput)
    password2 = forms.CharField(label="Repetir contraseña", strip=False, widget=forms.PasswordInput)

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("Ese usuario ya existe.")
        return username

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("password1") and cleaned.get("password2") and cleaned["password1"] != cleaned["password2"]:
            self.add_error("password2", "Las contraseñas no coinciden.")
        if cleaned.get("password1"):
            user = User(username=cleaned.get("username", ""), email=cleaned.get("email", ""))
            try:
                validate_password(cleaned["password1"], user)
            except ValidationError as error:
                self.add_error("password1", error)
        return cleaned
