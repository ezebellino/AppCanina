from datetime import timedelta
from urllib.parse import urlencode

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import redirect_to_login
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST, require_http_methods

from .family import accept_invitation, can_invite, owned_animals, invitation_share
from .models import PatientFamilyAccess, PatientFamilyInvite


class FamilyCodeForm(forms.Form):
    code = forms.CharField(label="Código familiar", max_length=80, widget=forms.TextInput(attrs={"autocomplete": "off", "placeholder": "FAM-…", "spellcheck": "false"}))


@login_required
@never_cache
def family_manage(request, patient_id):
    patient = get_object_or_404(owned_animals(request.user), pk=patient_id)
    if not can_invite(request.user, patient):
        raise PermissionDenied
    code = None
    invitation = None
    if request.method == "POST":
        active = patient.family_invites.filter(invited_by=request.user, accepted_at__isnull=True, revoked_at__isnull=True, expires_at__gt=timezone.now())
        if active.count() >= 3:
            messages.error(request, "Ya tenés tres invitaciones activas. Anulá una o esperá a que venza para crear otra.")
        else:
            code, invitation = PatientFamilyInvite.issue(patient, request.user, timezone.now() + timedelta(minutes=15))
    text = ""
    share_url = ""
    if code:
        share_url, text = invitation_share(request, patient, code)
    return render(request, "patients/family_manage.html", {
        "patient": patient, "code": code, "invitation": invitation,
        "share_url": share_url, "share_text": text, "whatsapp_url": "https://wa.me/?" + urlencode({"text": text}) if code else "",
        "accesses": patient.family_accesses.filter(revoked_at__isnull=True).select_related("user"),
        "invitations": patient.family_invites.filter(accepted_at__isnull=True, revoked_at__isnull=True, expires_at__gt=timezone.now()),
    })


@never_cache
@require_http_methods(["GET", "POST"])
def family_accept(request):
    # Login rotates the session key while retaining this short-lived invitation.
    # Preparing a link never consumes it or grants access, even when logged in.
    pending = request.session.get("pending_family_invitation", {})
    if pending.get("expires_at", 0) <= timezone.now().timestamp():
        request.session.pop("pending_family_invitation", None)
        pending = {}
    form = FamilyCodeForm(request.POST if request.method == "POST" else None,
                          initial={"code": pending.get("code", "")})
    if request.method == "POST" and form.is_valid():
        if request.POST.get("action") == "prepare" or not request.user.is_authenticated:
            request.session["pending_family_invitation"] = {
                "code": form.cleaned_data["code"],
                "expires_at": (timezone.now() + timedelta(minutes=15)).timestamp(),
            }
            if not request.user.is_authenticated:
                return redirect_to_login(reverse("family_accept"))
            return redirect("family_accept")
        key = f"family-web-attempts:{request.user.pk}"
        attempts = cache.get(key, 0)
        if attempts >= 10:
            form.add_error(None, "Demasiados intentos. Esperá 15 minutos y probá nuevamente.")
        else:
            cache.set(key, attempts + 1, 900)
            try:
                patient = accept_invitation(request.user, form.cleaned_data["code"], request=request)
            except ValueError as error:
                request.session.pop("pending_family_invitation", None)
                form.add_error("code", str(error))
            else:
                request.session.pop("pending_family_invitation", None)
                messages.success(request, f"{patient.name} ya aparece en Mis animales. Comparten la misma ficha e historial.", extra_tags="motion-family")
                return redirect("my_animals")
    next_query = "?" + urlencode({"next": reverse("family_accept")})
    response = render(request, "patients/family_accept.html", {
        "form": form, "login_url": reverse("login") + next_query,
        "register_url": reverse("register") + next_query,
    })
    # Django's HTTPS CSRF check needs same-origin Origin/Referer on form POST.
    # The fragment is never included, and external sites receive no Referer.
    response["Referrer-Policy"] = "same-origin"
    return response


@login_required
@require_POST
def family_revoke(request, patient_id):
    patient = get_object_or_404(owned_animals(request.user), pk=patient_id)
    if not can_invite(request.user, patient):
        raise PermissionDenied
    if request.POST.get("access_id"):
        access = get_object_or_404(PatientFamilyAccess, pk=request.POST["access_id"], patient=patient)
        access.revoked_at = timezone.now()
        access.save(update_fields=["revoked_at"])
    elif request.POST.get("invite_id"):
        invite = get_object_or_404(PatientFamilyInvite, pk=request.POST["invite_id"], patient=patient, accepted_at__isnull=True)
        invite.revoked_at = timezone.now()
        invite.save(update_fields=["revoked_at"])
    messages.success(request, "El acceso o la invitación familiar fue anulado.")
    return redirect("family_manage", patient_id=patient.id)
