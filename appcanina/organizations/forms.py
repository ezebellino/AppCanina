from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Organization
from .models import OrganizationMembership


class PersonalProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]
        labels = {"first_name": "Nombre", "last_name": "Apellido", "email": "Correo electrónico"}

    def clean_email(self):
        email = self.cleaned_data["email"].strip()
        if email and User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Este correo ya está asociado a otra cuenta.")
        return email


class BusinessProfileForm(forms.ModelForm):
    location_confirmed = forms.BooleanField(required=False, widget=forms.HiddenInput())
    def clean(self):
        data = super().clean()
        lat, lon = data.get('latitude'), data.get('longitude')
        if (lat is None) != (lon is None):
            raise forms.ValidationError('La ubicación debe incluir latitud y longitud. Volvé a marcar el local.')
        if (self.instance.pk and any(field in self.changed_data for field in ['address', 'locality'])
                and not data.get('location_confirmed')):
            data['latitude'] = data['longitude'] = None
        return data

    class Meta:
        model = Organization
        fields = ["name", "kind", "logo", "phone", "email", "address", "locality", "latitude", "longitude", "donation_alias", "donation_message"]
        widgets = {'latitude': forms.HiddenInput(), 'longitude': forms.HiddenInput()}
        labels = {
            "name": "Nombre de la institución",
            "kind": "Tipo de institución",
            "donation_alias": "Alias de cobro o colaboración",
            "donation_message": "Mensaje para compartir con clientes",
        }
        help_texts = {
            "logo": "Opcional. Se verá en el perfil y junto al nombre del negocio.",
            "donation_alias": "Opcional. Ej.: veterinaria.parque. Podés compartirlo con clientes para transferencias.",
            "donation_message": "Opcional. Se muestra junto al alias en este perfil.",
        }


class ShelterProfileForm(forms.ModelForm):
    class Meta:
        model = Organization
        fields = ["name", "logo", "phone", "email", "address", "donation_alias", "donation_message"]
        labels = {
            "name": "Nombre del refugio",
            "donation_alias": "Alias de colaboración",
            "donation_message": "Mensaje debajo de cada animal",
        }
        help_texts = {
            "logo": "Opcional. Se verá junto al nombre del refugio y en sus publicaciones.",
            "donation_alias": "Ej.: refugio.patitas. Se mostrará solo si decidís completarlo.",
            "donation_message": "Opcional. Si lo dejás vacío, usaremos un mensaje amable predeterminado.",
        }


class OrganizationMembershipForm(forms.ModelForm):
    class Meta:
        model = OrganizationMembership
        fields = ["user", "role"]
        labels = {"user": "Usuario existente", "role": "Rol dentro del refugio"}


class CommunityCollaboratorForm(UserCreationForm):
    first_name = forms.CharField(label="Nombre", max_length=150, required=False)
    last_name = forms.CharField(label="Apellido", max_length=150, required=False)
    email = forms.EmailField(label="Correo electrónico", required=False)
    password1 = forms.CharField(label="Contraseña", strip=False, widget=forms.PasswordInput,
                               help_text="Al menos 8 caracteres. Evitá claves comunes, solo números o parecidas a tus datos personales.")
    password2 = forms.CharField(label="Repetir contraseña", strip=False, widget=forms.PasswordInput)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "first_name", "last_name", "email", "password1", "password2")
        labels = {"username": "Usuario para iniciar sesión"}
        help_texts = {"username": "Usará este nombre para ingresar desde la app móvil."}


class PublicRegistrationForm(CommunityCollaboratorForm):
    account_type = forms.ChoiceField(label="Tipo de cuenta", choices=[
        ("community", "Colaborador"), ("shelter", "Institución"),
        ("veterinary", "Negocio · Veterinaria"),
    ], widget=forms.RadioSelect, initial="community")
    email = forms.EmailField(label="Correo electrónico", required=True,
                            help_text="Para recuperar tu contraseña y recibir novedades de tus solicitudes.")
    organization_name = forms.CharField(label="Nombre de la institución o veterinaria", max_length=160, required=False)
    locality = forms.CharField(label="Localidad", max_length=120, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].help_text = "Podés ingresar con este usuario o con tu correo."
        for name in ("password1", "password2"):
            self.fields[name].widget.attrs["autocomplete"] = "new-password"

    def clean_email(self):
        email = self.cleaned_data["email"].strip()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Este correo ya está asociado a una cuenta. Podés ingresar o recuperar tu contraseña.")
        return email

    def clean(self):
        data = super().clean()
        if data.get("account_type") in {"shelter", "veterinary"}:
            for field in ("organization_name", "locality"):
                if not data.get(field):
                    self.add_error(field, "Completá este dato para registrar tu institución o veterinaria.")
        return data
