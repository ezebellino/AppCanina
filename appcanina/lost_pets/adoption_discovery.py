"""Shared discovery filters; distances use only coarse animal reference points."""
from django import forms
from django.core.paginator import Paginator
from django.db.models import F, Q, Value, FloatField, ExpressionWrapper
from django.db.models.functions import ACos, Cos, Sin, Radians, Least, Greatest, Cast
from organizations.models import Organization
from patients.models import Patient
from .models import AdoptionPost


class DiscoveryForm(forms.Form):
    q = forms.CharField(label="Buscar animal", required=False, max_length=100)
    species = forms.ChoiceField(label="Especie", required=False, choices=[("", "Todas"), *Patient.Species.choices])
    shelter = forms.ModelChoiceField(label="Refugio o perrera", required=False,
        queryset=Organization.objects.none(), empty_label="Todos los refugios")
    locality = forms.CharField(label="Localidad del animal", required=False, max_length=120,
        help_text="Podés buscar una ciudad sin activar tu ubicación.")
    radius = forms.ChoiceField(label="Distancia desde mi ubicación", required=False,
        choices=[("", "Sin límite"), *[(str(n), f"Hasta {n} km") for n in (10, 25, 50, 100)]])
    lat = forms.DecimalField(required=False, min_value=-90, max_value=90, widget=forms.HiddenInput)
    lon = forms.DecimalField(required=False, min_value=-180, max_value=180, widget=forms.HiddenInput)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['shelter'].queryset = Organization.objects.filter(
            kind='shelter', adoption_posts__status='published',
        ).distinct().order_by('name', 'locality', 'id')
        self.fields['shelter'].label_from_instance = lambda obj: ' · '.join(filter(None, [obj.name, obj.locality]))

    def clean(self):
        data = super().clean()
        lat, lon = data.get('lat'), data.get('lon')
        if (lat is None) != (lon is None):
            raise forms.ValidationError('Volvé a indicar tu ubicación o quitá el filtro de distancia.')
        if data.get('radius') and (lat is None or lon is None):
            raise forms.ValidationError('Para filtrar por distancia, usá Mi ubicación. Sin GPS podés buscar por localidad.')
        return data


def discover(posts, params, per_page=24):
    form = DiscoveryForm(params)
    missing = 0
    if not form.is_valid():
        return form, Paginator(posts.none(), per_page).get_page(1), missing
    data = form.cleaned_data
    if data['q']:
        posts = posts.filter(Q(name__icontains=data['q']) | Q(breed__icontains=data['q']) |
                             Q(area_label__icontains=data['q']) | Q(organization__name__icontains=data['q']))
    if data['species']:
        posts = posts.filter(species=data['species'])
    if data['shelter']:
        posts = posts.filter(organization=data['shelter'])
    if data['locality']:
        # Do not silently substitute the shelter's address for a foster home's town.
        posts = posts.filter(Q(locality__icontains=data['locality']) | Q(area_label__icontains=data['locality']))
    if data.get('lat') is not None:
        lat, lon = float(round(data['lat'], 2)), float(round(data['lon'], 2))
        cosine = (Sin(Radians(Value(lat))) * Sin(Radians(Cast('location_latitude', FloatField()))) +
                  Cos(Radians(Value(lat))) * Cos(Radians(Cast('location_latitude', FloatField()))) *
                  Cos(Radians(Cast('location_longitude', FloatField()) - Value(lon))))
        distance = ExpressionWrapper(6371.0 * ACos(Least(Value(1.0), Greatest(Value(-1.0), cosine))), output_field=FloatField())
        # CASE avoids database-specific NULL handling in least/greatest.
        from django.db.models import Case, When
        posts = posts.annotate(distance_km=Case(
            When(location_latitude__isnull=False, location_longitude__isnull=False, then=distance),
            default=Value(None), output_field=FloatField()))
        missing = posts.filter(distance_km__isnull=True).count()
        if data['radius']:
            posts = posts.filter(distance_km__lte=int(data['radius']))
        posts = posts.order_by(F('distance_km').asc(nulls_last=True), '-created_at', '-id')
    else:
        posts = posts.order_by('-created_at', '-id')
    return form, Paginator(posts, per_page).get_page(params.get('page', 1)), missing


class AdoptionLocationForm(forms.ModelForm):
    class Meta:
        model = AdoptionPost
        fields = ['locality', 'location_latitude', 'location_longitude']
        help_texts = {'locality': 'Ciudad donde está el animal, aunque sea un hogar de tránsito.'}

    def clean(self):
        data = super().clean()
        if (data.get('location_latitude') is None) != (data.get('location_longitude') is None):
            raise forms.ValidationError('Indicá ambas coordenadas o dejá ambas vacías.')
        return data
