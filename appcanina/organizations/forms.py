from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

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


class CommunityCollaboratorForm(UserCreationForm):
    first_name = forms.CharField(label="Nombre", max_length=150, required=False)
    last_name = forms.CharField(label="Apellido", max_length=150, required=False)
    email = forms.EmailField(label="Correo electrónico", required=False)
    password1 = forms.CharField(label="Contraseña", strip=False, widget=forms.PasswordInput)
    password2 = forms.CharField(label="Repetir contraseña", strip=False, widget=forms.PasswordInput)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "first_name", "last_name", "email", "password1", "password2")
        labels = {"username": "Usuario para iniciar sesión"}
        help_texts = {"username": "Usará este nombre para ingresar desde la app móvil."}
