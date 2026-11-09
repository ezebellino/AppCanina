"""Explicit owner permission for temporary, append-only veterinary care."""
from datetime import timedelta

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from organizations.models import Organization
from .forms import ClinicalRecordForm
from .models import Patient, VeterinaryAuthorization, VeterinaryAccessLog
from .ownership import owner_relations


class VeterinaryChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return ' · '.join(part for part in [obj.name, obj.locality, obj.address] if part)


class VeterinarySelect(forms.Select):
    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex, attrs)
        if value and hasattr(value, 'instance'):
            org = value.instance
            if org.latitude is not None and org.longitude is not None:
                option['attrs']['data-latitude'] = str(org.latitude)
                option['attrs']['data-longitude'] = str(org.longitude)
        return option


class AuthorizationForm(forms.Form):
    organization = VeterinaryChoiceField(label='Veterinaria', widget=VeterinarySelect, queryset=Organization.objects.none(), empty_label='Seleccioná una veterinaria', help_text='Verificá el nombre, la localidad y la dirección antes de autorizar.')
    mode = forms.ChoiceField(label='Qué puede hacer', choices=VeterinaryAuthorization.Mode.choices)
    hours = forms.TypedChoiceField(label='Duración', coerce=int, choices=[(24, '24 horas'), (72, '3 días'), (168, '7 días')], initial=24)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['organization'].queryset = Organization.objects.filter(kind='veterinary', is_verified=True).order_by('name')


def _owner_patient(user, patient_id):
    return get_object_or_404(Patient.objects.filter(
        active=True, pk__in=owner_relations(user).filter(role='responsible').values('patient_id'),
    ), pk=patient_id)


@login_required
@never_cache
@transaction.atomic
def authorizations(request, patient_id):
    patient = _owner_patient(request.user, patient_id)
    form = AuthorizationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        Patient.objects.select_for_update().get(pk=patient.pk)
        patient.veterinary_authorizations.filter(
            organization=form.cleaned_data['organization'], revoked_at__isnull=True,
        ).update(revoked_at=timezone.now())
        VeterinaryAuthorization.objects.create(
            patient=patient, granted_by=request.user,
            organization=form.cleaned_data['organization'], mode=form.cleaned_data['mode'],
            expires_at=timezone.now() + timedelta(hours=form.cleaned_data['hours']),
        )
        messages.success(request, 'Veterinaria autorizada. Podés retirar el permiso en cualquier momento.')
        return redirect('veterinary_authorizations', patient_id=patient.pk)
    grants = patient.veterinary_authorizations.select_related('organization', 'granted_by', 'patient').order_by('-created_at')
    return render(request, 'patients/veterinary_authorizations.html', {'patient': patient, 'form': form, 'grants': grants})


@login_required
@require_POST
@transaction.atomic
def revoke_authorization(request, patient_id, authorization_id):
    patient = _owner_patient(request.user, patient_id)
    grant = get_object_or_404(VeterinaryAuthorization.objects.select_for_update(), pk=authorization_id, patient=patient)
    if not grant.revoked_at:
        grant.revoked_at = timezone.now()
        grant.save(update_fields=['revoked_at'])
    messages.success(request, 'Permiso retirado. Las atenciones ya registradas permanecen en el historial.')
    return redirect('veterinary_authorizations', patient_id=patient.pk)


def _visible_grants(user):
    # Membership is mandatory, even for accounts with global clinical permissions.
    return VeterinaryAuthorization.objects.filter(
        organization__memberships__user=user, organization__kind='veterinary',
        organization__is_verified=True, revoked_at__isnull=True, expires_at__gt=timezone.now(),
    ).select_related('patient', 'organization', 'granted_by')


@login_required
@permission_required('patients.view_clinicalrecord', raise_exception=True)
@never_cache
def authorized_patients(request):
    grants = [grant for grant in _visible_grants(request.user).order_by('patient__name') if grant.is_active]
    return render(request, 'patients/authorized_patients.html', {'grants': grants})


@login_required
@permission_required('patients.view_clinicalrecord', raise_exception=True)
@never_cache
@transaction.atomic
def authorized_history(request, authorization_id):
    # The same row lock serializes append and revocation on databases with row locks.
    grant = get_object_or_404(_visible_grants(request.user).select_for_update(), pk=authorization_id)
    if not grant.is_active:
        raise Http404
    can_append = grant.mode == VeterinaryAuthorization.Mode.ATTEND and request.user.has_perm('patients.add_clinicalrecord')
    if request.method == 'POST' and not can_append:
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied
    form = ClinicalRecordForm(request.POST or None) if can_append else None
    if request.method == 'POST' and form.is_valid():
        record = form.save(commit=False)
        record.patient = grant.patient
        record.professional = request.user
        record.organization = grant.organization
        record.authorization = grant
        record.save()
        messages.success(request, 'Atención agregada al historial. El responsable ya puede consultarla.')
        return redirect('veterinary_authorized_history', authorization_id=grant.pk)
    VeterinaryAccessLog.objects.get_or_create(authorization=grant, professional=request.user)
    return render(request, 'patients/authorized_history.html', {
        'grant': grant, 'patient': grant.patient, 'form': form,
        'records': grant.patient.clinical_records.select_related('professional', 'organization'),
    })
