import hashlib
import json
from datetime import timedelta
from functools import wraps
from decimal import Decimal, InvalidOperation

from django.contrib.auth import authenticate
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods, require_POST
from PIL import UnidentifiedImageError

from .forms import photo_without_location_metadata
from .models import AdoptionInterest, AdoptionPost, CommunityDevicePermission, CommunityNotification, LostPetReport, MobileAccessToken, MobilePushDevice, Sighting
from .notifications import notify_new_sighting
from organizations.forms import CommunityCollaboratorForm
from organizations.models import Organization, OrganizationMembership
from organizations.roles import ensure_base_roles
from patients.models import Contact, OwnerAccountLink, Patient, PatientContact, PatientFamilyAccess, PatientFamilyInvite, PatientSharingConsent, TravelCredential


def token_required(permission):
    def decorator(view):
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            header = request.headers.get("Authorization", "")
            if not header.startswith("Bearer "):
                return JsonResponse({"detail": "Token requerido."}, status=401)
            token = MobileAccessToken.from_raw_token(header[7:])
            if not token or not token.user.has_perm(permission):
                return JsonResponse({"detail": "Token inválido o sin permiso."}, status=403)
            token.last_used_at = timezone.now()
            token.save(update_fields=["last_used_at"])
            request.mobile_user = token.user
            request.mobile_token = token
            return view(request, *args, **kwargs)
        return wrapped
    return decorator


@csrf_exempt
@require_POST
def mobile_login(request):
    ip = request.META.get("REMOTE_ADDR", "unknown")
    cache_key = f"mobile-login:{ip}"
    if cache.get(cache_key, 0) >= 5:
        return JsonResponse({"detail": "Demasiados intentos. Probá nuevamente en unos minutos."}, status=429)
    try:
        payload = json.loads(request.body)
    except (TypeError, ValueError):
        return JsonResponse({"detail": "JSON inválido."}, status=400)
    user = authenticate(request, username=payload.get("username", ""), password=payload.get("password", ""))
    if not user or not user.has_perm("lost_pets.view_lostpetreport"):
        cache.set(cache_key, cache.get(cache_key, 0) + 1, 900)
        return JsonResponse({"detail": "Credenciales inválidas."}, status=401)
    cache.delete(cache_key)
    raw_token, _ = MobileAccessToken.issue(user, payload.get("device_name", "Dispositivo móvil"))
    return JsonResponse({"token": raw_token, "token_type": "Bearer", "user": {"username": user.username}})


@csrf_exempt
@require_POST
def mobile_register(request):
    """Create a community account, optionally with a pending organization profile."""
    ip = request.META.get("REMOTE_ADDR", "unknown")
    cache_key = f"mobile-register:{ip}"
    if cache.get(cache_key, 0) >= 3:
        return JsonResponse({"detail": "Demasiadas cuentas creadas desde esta conexión. Probá nuevamente más tarde."}, status=429)
    try:
        payload = json.loads(request.body)
    except (TypeError, ValueError):
        return JsonResponse({"detail": "JSON inválido."}, status=400)

    account_type = (payload.get("account_type") or "community").strip().lower()
    organization_kind_by_account_type = {
        "veterinary": Organization.Kind.VETERINARY,
        "shelter": Organization.Kind.SHELTER,
    }
    if account_type not in {"community", *organization_kind_by_account_type}:
        return JsonResponse({"detail": "Elegí Persona, Veterinaria o Refugio."}, status=400)
    organization_name = (payload.get("organization_name") or "").strip()
    locality = (payload.get("locality") or "").strip()
    if account_type != "community" and not organization_name:
        return JsonResponse({"detail": "Indicá el nombre de la institución."}, status=400)
    if account_type != "community" and not locality:
        return JsonResponse({"detail": "Indicá la localidad de la institución."}, status=400)

    form = CommunityCollaboratorForm({
        "username": (payload.get("username") or "").strip(),
        "first_name": (payload.get("first_name") or "").strip(),
        "email": (payload.get("email") or "").strip(),
        "password1": payload.get("password") or "",
        "password2": payload.get("password_confirmation") or "",
    })
    if not form.is_valid():
        messages = [message for errors in form.errors.values() for message in errors]
        return JsonResponse({"detail": messages[0] if messages else "No se pudo crear la cuenta."}, status=400)

    with transaction.atomic():
        collaborator = form.save()
        collaborator.groups.add(ensure_base_roles()["collaborator"])
        organization = None
        if account_type in organization_kind_by_account_type:
            organization = Organization.objects.create(
                name=organization_name[:160],
                kind=organization_kind_by_account_type[account_type],
                locality=locality[:120],
                phone=(payload.get("organization_phone") or "").strip()[:40],
                email=(payload.get("organization_email") or payload.get("email") or "").strip()[:254],
                address=(payload.get("organization_address") or "").strip()[:220],
                donation_alias=(payload.get("donation_alias") or "").strip()[:120],
            )
            OrganizationMembership.objects.create(
                organization=organization,
                user=collaborator,
                role=OrganizationMembership.Role.MANAGER,
            )
    cache.set(cache_key, cache.get(cache_key, 0) + 1, 3600)
    raw_token, _ = MobileAccessToken.issue(collaborator, payload.get("device_name", "Dispositivo móvil"))
    message = "Cuenta creada."
    if organization:
        message = "Solicitud institucional recibida. El perfil queda pendiente de validación antes de habilitar herramientas de gestión."
    return JsonResponse({
        "token": raw_token,
        "token_type": "Bearer",
        "detail": message,
        "user": {"username": collaborator.username, "account_type": account_type},
        "organization": {"id": organization.id, "name": organization.name, "verified": organization.is_verified} if organization else None,
    }, status=201)


def _mobile_report_data(request, report):
    return {
        "id": report.id,
        "name": report.name,
        "species": report.get_species_display(),
        "breed": report.breed,
        "description": report.description,
        "area": report.area_label,
        "last_seen_at": report.last_seen_at.isoformat(),
        "status": report.status,
        "status_label": report.get_status_display(),
        "photo_url": request.build_absolute_uri(report.photo.url) if report.photo else None,
    }


def _mobile_request_data(request, report):
    data = _mobile_report_data(request, report)
    data.update({
        "review_note": report.review_note,
        "editable": report.status in {LostPetReport.Status.HIDDEN, LostPetReport.Status.REJECTED},
    })
    return data


def _mobile_adoption_data(request, post):
    organization = post.organization
    donation_message = ""
    if organization and organization.donation_alias:
        donation_message = organization.donation_message or (
            f"Si querés colaborar con {organization.name}, podés transferirnos a {organization.donation_alias}. "
            "Por más mínimo que sea, nos ayudás muchísimo."
        )
    return {
        "id": post.id, "name": post.name, "species": post.get_species_display(), "breed": post.breed,
        "age": post.age_label, "description": post.description, "area": post.area_label,
        "status": post.status, "status_label": post.get_status_display(), "review_note": post.review_note,
        "photo_url": request.build_absolute_uri(post.photo.url) if post.photo else None,
        "editable": post.status in {AdoptionPost.Status.PENDING, AdoptionPost.Status.REJECTED},
        "organization": {
            "id": organization.id,
            "name": organization.name,
            "logo_url": request.build_absolute_uri(organization.logo.url) if organization and organization.logo else None,
            "donation_alias": organization.donation_alias,
            "donation_message": donation_message,
        } if organization else None,
    }


def _mobile_interest_data(interest):
    return {"id": interest.id, "post_id": interest.post_id, "animal_name": interest.post.name, "species": interest.post.get_species_display(), "status": interest.status, "status_label": interest.get_status_display(), "staff_note": interest.staff_note, "message": interest.message, "updated_at": interest.updated_at.isoformat()}


def _mobile_patient_data(request, patient):
    contact_ids = OwnerAccountLink.objects.filter(user=request.mobile_user).values_list("contact_id", flat=True)
    can_share = patient.patientcontact_set.filter(
        contact_id__in=contact_ids,
        role=PatientContact.Role.RESPONSIBLE,
    ).exists()
    sharing_enabled = PatientSharingConsent.objects.filter(
        patient=patient,
        contact_id__in=contact_ids,
        enabled=True,
    ).exists()
    return {
        "id": patient.id,
        "name": patient.name,
        "species": patient.get_species_display(),
        "breed": patient.breed,
        "birth_date": patient.birth_date.isoformat() if patient.birth_date else None,
        "microchip": patient.microchip,
        "allergies": patient.allergies,
        "photo_url": request.build_absolute_uri(patient.photo.url) if patient.photo else None,
        "sharing_enabled": sharing_enabled,
        "can_share_with_family": can_share,
        "family_members": [
            {
                "access_id": access.id,
                "username": access.user.username,
                "name": access.user.get_full_name() or access.user.username,
                "joined_at": access.created_at.isoformat(),
            }
            for access in patient.family_accesses.filter(revoked_at__isnull=True).select_related("user")
        ] if can_share else [],
        "clinical_records": [
            {
                "date": record.occurred_on.isoformat(),
                "reason": record.reason,
                "notes": record.notes,
                "professional": record.professional.get_full_name() or record.professional.username,
            }
            for record in patient.clinical_records.select_related("professional").all()
        ],
    }


def _mobile_owned_patient(request, patient_id):
    contact_ids = OwnerAccountLink.objects.filter(user=request.mobile_user).values_list("contact_id", flat=True)
    return Patient.objects.filter(pk=patient_id, active=True).filter(
        Q(
            patientcontact__contact_id__in=contact_ids,
            patientcontact__role__in=[PatientContact.Role.RESPONSIBLE, PatientContact.Role.ADOPTER],
        ) | Q(family_accesses__user=request.mobile_user, family_accesses__revoked_at__isnull=True)
    ).distinct().first()


def _mobile_user_contact(user):
    link = OwnerAccountLink.objects.filter(user=user).select_related("contact").first()
    if link:
        return link.contact
    contact = Contact.objects.create(full_name=user.get_full_name().strip() or user.username)
    OwnerAccountLink.objects.create(user=user, contact=contact)
    return contact


def _mobile_can_share_with_family(request, patient):
    contact_ids = OwnerAccountLink.objects.filter(user=request.mobile_user).values_list("contact_id", flat=True)
    return patient.patientcontact_set.filter(
        contact_id__in=contact_ids,
        role=PatientContact.Role.RESPONSIBLE,
    ).exists()


def _mobile_payload(request):
    if request.content_type and request.content_type.startswith("application/json"):
        try:
            return json.loads(request.body)
        except (TypeError, ValueError):
            return None
    return request.POST


def _mobile_coordinates(payload):
    latitude, longitude = (payload.get("latitude") or "").strip(), (payload.get("longitude") or "").strip()
    if not latitude and not longitude:
        return None, None, None
    if not latitude or not longitude:
        return None, None, "La ubicación debe incluir latitud y longitud juntas."
    try:
        latitude_value, longitude_value = Decimal(latitude), Decimal(longitude)
    except (InvalidOperation, TypeError):
        return None, None, "La ubicación no tiene un formato válido."
    if not Decimal("-90") <= latitude_value <= Decimal("90") or not Decimal("-180") <= longitude_value <= Decimal("180"):
        return None, None, "La ubicación está fuera del rango permitido."
    return latitude_value, longitude_value, None


def _mobile_photo(request):
    uploaded = request.FILES.get("photo")
    if not uploaded:
        return None
    try:
        return photo_without_location_metadata(uploaded)
    except (UnidentifiedImageError, OSError, ValueError, ValidationError):
        raise ValueError("La imagen no pudo procesarse. Probá con una foto JPG o PNG.")


@csrf_exempt
@require_GET
@token_required("lost_pets.view_lostpetreport")
def mobile_reports(request):
    state = request.GET.get("estado", "activos")
    reports = LostPetReport.objects.filter(status=LostPetReport.Status.RESOLVED if state == "encontrados" else LostPetReport.Status.PUBLISHED)
    query = request.GET.get("q", "").strip()
    if query:
        reports = reports.filter(Q(name__icontains=query) | Q(species__icontains=query) | Q(area_label__icontains=query))
    return JsonResponse({"reports": [_mobile_report_data(request, report) for report in reports[:60]]})


@csrf_exempt
@require_http_methods(["GET", "POST"])
@token_required("lost_pets.view_lostpetreport")
def mobile_my_animals(request):
    """List the owner's animals or register a new one from the mobile app."""
    if request.method == "POST":
        name = (request.POST.get("name") or "").strip()
        species = (request.POST.get("species") or "").strip().lower()
        species_aliases = {"perro": Patient.Species.DOG, "dog": Patient.Species.DOG, "gato": Patient.Species.CAT, "cat": Patient.Species.CAT, "otro": Patient.Species.OTHER, "other": Patient.Species.OTHER}
        species = species_aliases.get(species, species)
        if not name:
            return JsonResponse({"detail": "Indicá el nombre de tu animal."}, status=400)
        if species not in Patient.Species.values:
            return JsonResponse({"detail": "Elegí si es perro, gato u otro animal."}, status=400)

        birth_date = None
        raw_birth_date = (request.POST.get("birth_date") or "").strip()
        if raw_birth_date:
            birth_date = parse_date(raw_birth_date)
            if not birth_date:
                return JsonResponse({"detail": "La fecha de nacimiento no es válida."}, status=400)
        try:
            photo = _mobile_photo(request)
        except ValueError as error:
            return JsonResponse({"detail": str(error)}, status=400)

        with transaction.atomic():
            contact = _mobile_user_contact(request.mobile_user)
            patient = Patient.objects.create(
                name=name[:100],
                species=species,
                breed=(request.POST.get("breed") or "").strip()[:100],
                birth_date=birth_date,
                microchip=(request.POST.get("microchip") or "").strip()[:80],
                allergies=(request.POST.get("allergies") or "").strip(),
                photo=photo,
            )
            PatientContact.objects.create(
                patient=patient,
                contact=contact,
                role=PatientContact.Role.RESPONSIBLE,
                is_primary=True,
            )
        return JsonResponse({
            "detail": "Tu animal fue agregado y quedó vinculado a tu cuenta.",
            "animal": _mobile_patient_data(request, patient),
        }, status=201)

    contact_ids = OwnerAccountLink.objects.filter(user=request.mobile_user).values_list("contact_id", flat=True)
    patients = (
        Patient.objects.filter(active=True).filter(
            Q(
                patientcontact__contact_id__in=contact_ids,
                patientcontact__role__in=[PatientContact.Role.RESPONSIBLE, PatientContact.Role.ADOPTER],
            ) | Q(family_accesses__user=request.mobile_user, family_accesses__revoked_at__isnull=True)
        )
        .distinct()
        .prefetch_related("clinical_records__professional")
        .order_by("name")
    )
    return JsonResponse({"animals": [_mobile_patient_data(request, patient) for patient in patients]})


@csrf_exempt
@require_http_methods(["GET", "POST"])
@token_required("lost_pets.view_lostpetreport")
def mobile_my_animal_detail(request, patient_id):
    patient = _mobile_owned_patient(request, patient_id)
    if not patient:
        return JsonResponse({"detail": "Animal no encontrado o no vinculado a tu cuenta."}, status=404)

    if request.method == "POST":
        if not _mobile_can_share_with_family(request, patient):
            return JsonResponse({"detail": "Solo el responsable principal puede modificar esta preferencia."}, status=403)
        payload = _mobile_payload(request)
        if payload is None or "sharing_enabled" not in payload:
            return JsonResponse({"detail": "Indicá la preferencia de historial compartido."}, status=400)
        enabled = payload["sharing_enabled"] is True or str(payload["sharing_enabled"]).lower() in {"true", "1", "on"}
        contact_ids = OwnerAccountLink.objects.filter(user=request.mobile_user).values_list("contact_id", flat=True)
        contact_id = patient.patientcontact_set.filter(contact_id__in=contact_ids).values_list("contact_id", flat=True).first()
        PatientSharingConsent.objects.update_or_create(
            patient=patient,
            contact_id=contact_id,
            defaults={"enabled": enabled},
        )
    return JsonResponse({"animal": _mobile_patient_data(request, patient)})


@csrf_exempt
@require_POST
@token_required("lost_pets.view_lostpetreport")
def mobile_family_invite_create(request, patient_id):
    patient = _mobile_owned_patient(request, patient_id)
    if not patient:
        return JsonResponse({"detail": "Animal no encontrado o no vinculado a tu cuenta."}, status=404)
    if not _mobile_can_share_with_family(request, patient):
        return JsonResponse({"detail": "Solo el responsable principal puede compartir esta ficha."}, status=403)
    active_invites = PatientFamilyInvite.objects.filter(
        patient=patient,
        invited_by=request.mobile_user,
        accepted_at__isnull=True,
        revoked_at__isnull=True,
        expires_at__gt=timezone.now(),
    )
    if active_invites.count() >= 3:
        return JsonResponse({"detail": "Ya hay tres códigos familiares activos. Esperá a que venzan o compartí uno de ellos."}, status=429)
    code, invitation = PatientFamilyInvite.issue(
        patient=patient,
        invited_by=request.mobile_user,
        expires_at=timezone.now() + timedelta(minutes=15),
    )
    return JsonResponse({
        "code": code,
        "expires_at": invitation.expires_at.isoformat(),
        "detail": "Código familiar creado. Compartilo solo con una persona de confianza; vence en 15 minutos y se usa una sola vez.",
    }, status=201)


@csrf_exempt
@require_POST
@token_required("lost_pets.view_lostpetreport")
def mobile_family_invite_accept(request):
    payload = _mobile_payload(request)
    if payload is None:
        return JsonResponse({"detail": "JSON inválido."}, status=400)
    raw_code = (payload.get("code") or "").strip()
    if not raw_code:
        return JsonResponse({"detail": "Ingresá el código familiar."}, status=400)
    digest = hashlib.sha256(raw_code.encode()).hexdigest()
    with transaction.atomic():
        invitation = PatientFamilyInvite.objects.select_for_update().select_related("patient", "invited_by").filter(digest=digest).first()
        if not invitation or not invitation.is_active:
            return JsonResponse({"detail": "El código no es válido, ya fue utilizado o venció."}, status=400)
        if invitation.invited_by_id == request.mobile_user.id:
            return JsonResponse({"detail": "No podés usar tu propio código familiar."}, status=400)
        contact = _mobile_user_contact(request.mobile_user)
        PatientContact.objects.get_or_create(
            patient=invitation.patient,
            contact=contact,
            role=PatientContact.Role.CUSTODIAN,
            defaults={"is_primary": False},
        )
        PatientFamilyAccess.objects.update_or_create(
            patient=invitation.patient,
            user=request.mobile_user,
            defaults={
                "contact": contact,
                "granted_by": invitation.invited_by,
                "invitation": invitation,
                "revoked_at": None,
            },
        )
        invitation.accepted_by = request.mobile_user
        invitation.accepted_at = timezone.now()
        invitation.save(update_fields=["accepted_by", "accepted_at"])
    return JsonResponse({
        "detail": f"{invitation.patient.name} ya está vinculada a tu cuenta familiar.",
        "animal": _mobile_patient_data(request, invitation.patient),
    }, status=201)


@csrf_exempt
@require_POST
@token_required("lost_pets.view_lostpetreport")
def mobile_family_access_revoke(request, patient_id, access_id):
    patient = _mobile_owned_patient(request, patient_id)
    if not patient:
        return JsonResponse({"detail": "Animal no encontrado o no vinculado a tu cuenta."}, status=404)
    if not _mobile_can_share_with_family(request, patient):
        return JsonResponse({"detail": "Solo el responsable principal puede revocar accesos familiares."}, status=403)
    access = PatientFamilyAccess.objects.filter(pk=access_id, patient=patient, revoked_at__isnull=True).first()
    if not access:
        return JsonResponse({"detail": "El acceso familiar ya no está disponible."}, status=404)
    access.revoked_at = timezone.now()
    access.save(update_fields=["revoked_at"])
    return JsonResponse({"detail": "Acceso familiar revocado."})


@csrf_exempt
@require_POST
@token_required("lost_pets.view_lostpetreport")
def mobile_my_animal_credential(request, patient_id):
    patient = _mobile_owned_patient(request, patient_id)
    if not patient:
        return JsonResponse({"detail": "Animal no encontrado o no vinculado a tu cuenta."}, status=404)
    if not _mobile_can_share_with_family(request, patient):
        return JsonResponse({"detail": "Solo el responsable principal puede crear una credencial de viaje."}, status=403)
    contact_ids = OwnerAccountLink.objects.filter(user=request.mobile_user).values_list("contact_id", flat=True)
    contact = patient.patientcontact_set.filter(contact_id__in=contact_ids).select_related("contact").first().contact
    code, credential = TravelCredential.issue(patient, contact, timezone.now() + timedelta(days=7))
    return JsonResponse({
        "code": code,
        "expires_at": credential.expires_at.isoformat(),
        "detail": "Credencial temporal creada. Mostrá este código voluntariamente en la veterinaria de destino.",
    }, status=201)


@csrf_exempt
@require_GET
@token_required("lost_pets.view_lostpetreport")
def mobile_adoptions(request):
    posts = AdoptionPost.objects.filter(status=AdoptionPost.Status.PUBLISHED).select_related("organization")
    query = request.GET.get("q", "").strip()
    if query:
        posts = posts.filter(Q(name__icontains=query) | Q(species__icontains=query) | Q(area_label__icontains=query))
    return JsonResponse({"adoptions": [_mobile_adoption_data(request, post) for post in posts[:60]]})


@csrf_exempt
@require_POST
@token_required("lost_pets.view_lostpetreport")
def mobile_adoption_request(request):
    payload = _mobile_payload(request)
    if payload is None:
        return JsonResponse({"detail": "Datos inválidos."}, status=400)
    species_map = {"perro": "dog", "perros": "dog", "dog": "dog", "gato": "cat", "gatos": "cat", "cat": "cat", "otro": "other", "other": "other"}
    name, area = (payload.get("name") or "").strip(), (payload.get("area") or "").strip()
    species = species_map.get((payload.get("species") or "").strip().lower())
    if not name or not species or not area:
        return JsonResponse({"detail": "Indicá nombre, especie y zona aproximada."}, status=400)
    try:
        photo = _mobile_photo(request)
    except ValueError as error:
        return JsonResponse({"detail": str(error)}, status=400)
    organization_id = payload.get("organization_id")
    membership_query = OrganizationMembership.objects.filter(user=request.mobile_user).select_related("organization")
    membership = membership_query.filter(organization_id=organization_id).first() if organization_id else membership_query.first()
    # Only the verified shelter's responsible person may publish immediately.
    # A general team member (or a veterinary organization) can submit a
    # proposal, but it remains pending for the shelter/refuge workflow.
    organization = membership.organization if membership else Organization.objects.filter(is_business_profile=True).first()
    institution_can_publish = bool(
        membership
        and membership.role == OrganizationMembership.Role.MANAGER
        and membership.organization.kind == Organization.Kind.SHELTER
        and membership.organization.is_verified
    )
    post = AdoptionPost.objects.create(
        publisher=request.mobile_user, organization=organization, name=name[:100], species=species,
        breed=(payload.get("breed") or "").strip()[:100], age_label=(payload.get("age") or "").strip()[:80],
        description=(payload.get("description") or "").strip(), area_label=area[:120], photo=photo,
        status=AdoptionPost.Status.PUBLISHED if institution_can_publish else AdoptionPost.Status.PENDING,
    )
    detail = "Tu refugio publicó el animal para adopción." if institution_can_publish else "Recibimos la publicación. La veterinaria o refugio responsable la revisará antes de mostrarla."
    return JsonResponse({"id": post.id, "detail": detail}, status=201)


@csrf_exempt
@require_POST
@token_required("lost_pets.view_lostpetreport")
def mobile_adoption_interest(request, post_id):
    post = AdoptionPost.objects.filter(pk=post_id, status=AdoptionPost.Status.PUBLISHED).first()
    if not post:
        return JsonResponse({"detail": "Esta publicación ya no está disponible."}, status=404)
    payload = _mobile_payload(request)
    if payload is None:
        return JsonResponse({"detail": "Datos inválidos."}, status=400)
    message = (payload.get("message") or "").strip()
    if len(message) < 10:
        return JsonResponse({"detail": "Contanos brevemente por qué te interesa adoptar (al menos 10 caracteres)."}, status=400)
    interest, created = AdoptionInterest.objects.get_or_create(post=post, applicant=request.mobile_user, defaults={"message": message[:700]})
    if not created:
        return JsonResponse({"detail": "Ya enviaste un interés por este animal. Podés seguir su estado en Mi actividad."}, status=409)
    return JsonResponse({"interest": _mobile_interest_data(interest), "detail": "Interés enviado. La veterinaria o refugio revisará tu mensaje de forma privada."}, status=201)


@csrf_exempt
@require_GET
@token_required("lost_pets.view_lostpetreport")
def mobile_my_adoption_interests(request):
    interests = AdoptionInterest.objects.filter(applicant=request.mobile_user).select_related("post")
    return JsonResponse({"interests": [_mobile_interest_data(interest) for interest in interests[:50]]})


@csrf_exempt
@require_POST
@token_required("lost_pets.add_sighting")
def mobile_sighting_create(request, report_id):
    report = LostPetReport.objects.filter(pk=report_id, status=LostPetReport.Status.PUBLISHED).first()
    if not report:
        return JsonResponse({"detail": "El aviso ya no está disponible para recibir avistamientos."}, status=404)
    payload = _mobile_payload(request)
    if payload is None:
        return JsonResponse({"detail": "Datos inválidos."}, status=400)
    area = (payload.get("area") or "").strip()
    if not area:
        return JsonResponse({"detail": "Indicá una zona aproximada para el avistamiento."}, status=400)
    latitude, longitude, coordinate_error = _mobile_coordinates(payload)
    if coordinate_error:
        return JsonResponse({"detail": coordinate_error}, status=400)
    try:
        photo = _mobile_photo(request)
    except ValueError as error:
        return JsonResponse({"detail": str(error)}, status=400)
    sighting = Sighting.objects.create(
        report=report,
        reporter=request.mobile_user,
        area_label=area[:120],
        description=(payload.get("description") or "").strip(),
        latitude=latitude,
        longitude=longitude,
        photo=photo,
        status=Sighting.Status.PUBLISHED,
    )
    notify_new_sighting(report, sighting)
    return JsonResponse({"id": sighting.id, "detail": "Avistamiento compartido. El mapa mostrará solo una zona aproximada."}, status=201)


@csrf_exempt
@require_POST
@token_required("lost_pets.view_lostpetreport")
def mobile_search_request(request):
    ip = request.META.get("REMOTE_ADDR", "unknown")
    cache_key = f"mobile-search-request:{ip}"
    if cache.get(cache_key, 0) >= 3:
        return JsonResponse({"detail": "Ya enviaste varias solicitudes desde esta conexión. Probá nuevamente más tarde."}, status=429)
    payload = _mobile_payload(request)
    if payload is None:
        return JsonResponse({"detail": "JSON inválido."}, status=400)

    species_map = {"perro": "dog", "perros": "dog", "dog": "dog", "gato": "cat", "gatos": "cat", "cat": "cat", "otro": "other", "other": "other"}
    species = species_map.get((payload.get("species") or "").strip().lower())
    name = (payload.get("name") or "").strip()
    area = (payload.get("area") or "").strip()
    if not name or not species or not area:
        return JsonResponse({"detail": "Indicá nombre del animal, especie (perro, gato u otro) y zona aproximada."}, status=400)
    try:
        photo = _mobile_photo(request)
    except ValueError as error:
        return JsonResponse({"detail": str(error)}, status=400)
    report = LostPetReport.objects.create(
        reporter=request.mobile_user,
        name=name[:100],
        species=species,
        breed=(payload.get("breed") or "").strip()[:100],
        description=(payload.get("description") or "").strip(),
        area_label=area[:120],
        last_seen_at=timezone.now(),
        status=LostPetReport.Status.HIDDEN,
        requested_via_mobile=True,
        photo=photo,
    )
    cache.set(cache_key, cache.get(cache_key, 0) + 1, 3600)
    return JsonResponse({"id": report.id, "detail": "Recibimos tu solicitud. El equipo la revisará antes de publicarla."}, status=201)


@csrf_exempt
@require_GET
@token_required("lost_pets.view_lostpetreport")
def mobile_my_search_requests(request):
    requests = LostPetReport.objects.filter(reporter=request.mobile_user, requested_via_mobile=True).order_by("-updated_at", "-id")
    return JsonResponse({"requests": [_mobile_request_data(request, report) for report in requests[:30]]})


@csrf_exempt
@require_POST
@token_required("lost_pets.view_lostpetreport")
def mobile_search_request_edit(request, report_id):
    report = LostPetReport.objects.filter(
        pk=report_id,
        reporter=request.mobile_user,
        requested_via_mobile=True,
    ).first()
    if not report:
        return JsonResponse({"detail": "Solicitud no encontrada."}, status=404)
    if report.status not in {LostPetReport.Status.HIDDEN, LostPetReport.Status.REJECTED}:
        return JsonResponse({"detail": "Esta solicitud ya fue publicada o cerrada y no se puede editar desde el teléfono."}, status=409)
    payload = _mobile_payload(request)
    if payload is None:
        return JsonResponse({"detail": "Datos inválidos."}, status=400)
    species_map = {"perro": "dog", "perros": "dog", "dog": "dog", "gato": "cat", "gatos": "cat", "cat": "cat", "otro": "other", "other": "other"}
    species = species_map.get((payload.get("species") or "").strip().lower())
    name = (payload.get("name") or "").strip()
    area = (payload.get("area") or "").strip()
    if not name or not species or not area:
        return JsonResponse({"detail": "Indicá nombre del animal, especie (perro, gato u otro) y zona aproximada."}, status=400)
    report.name = name[:100]
    report.species = species
    report.breed = (payload.get("breed") or "").strip()[:100]
    report.description = (payload.get("description") or "").strip()
    report.area_label = area[:120]
    try:
        photo = _mobile_photo(request)
    except ValueError as error:
        return JsonResponse({"detail": str(error)}, status=400)
    if photo:
        report.photo = photo
    report.status = LostPetReport.Status.HIDDEN
    report.review_note = ""
    report.save()
    return JsonResponse({"request": _mobile_request_data(request, report), "detail": "Solicitud actualizada. El equipo la revisará nuevamente."})


@csrf_exempt
@require_GET
@token_required("lost_pets.view_lostpetreport")
def mobile_notifications(request):
    items = CommunityNotification.objects.filter(recipient=request.mobile_user, read_at__isnull=True).select_related("report", "sighting")[:30]
    notifications = []
    for item in items:
        photo = item.sighting.photo if item.sighting and item.sighting.photo else item.report.photo
        description = item.sighting.description if item.sighting and item.sighting.description else item.report.description
        area = item.sighting.area_label if item.sighting else item.report.area_label
        notifications.append({
            "id": item.id,
            "title": item.title,
            "body": item.body,
            "report_id": item.report_id,
            "animal_name": item.report.name,
            "species": item.report.get_species_display(),
            "description": description,
            "area": area,
            "photo_url": request.build_absolute_uri(photo.url) if photo else None,
            "created_at": item.created_at.isoformat(),
        })
    return JsonResponse({"notifications": notifications})


@csrf_exempt
@require_POST
@token_required("lost_pets.view_lostpetreport")
def mobile_push_device_register(request):
    try:
        payload = json.loads(request.body)
    except (TypeError, ValueError):
        return JsonResponse({"detail": "JSON inválido."}, status=400)
    push_token = (payload.get("push_token") or "").strip()
    platform = (payload.get("platform") or "").lower()
    if not push_token.startswith(("ExponentPushToken[", "ExpoPushToken[")):
        return JsonResponse({"detail": "Token de notificación inválido."}, status=400)
    if platform not in {MobilePushDevice.Platform.ANDROID, MobilePushDevice.Platform.IOS}:
        return JsonResponse({"detail": "Plataforma de dispositivo inválida."}, status=400)
    device, created = MobilePushDevice.objects.update_or_create(
        token=push_token,
        defaults={"user": request.mobile_user, "platform": platform, "active": True},
    )
    return JsonResponse({"id": device.id, "registered": created})


@csrf_exempt
@require_http_methods(["GET", "POST"])
@token_required("lost_pets.view_lostpetreport")
def mobile_device_permissions(request):
    if request.method == "GET":
        device_key = request.GET.get("device_key", "").strip()
        if not device_key:
            return JsonResponse({"detail": "Identificador de dispositivo requerido."}, status=400)
        device = CommunityDevicePermission.objects.filter(user=request.mobile_user, device_key=device_key).first()
        return JsonResponse({"device": _device_permission_data(device) if device else None})

    payload = _mobile_payload(request)
    if payload is None:
        return JsonResponse({"detail": "JSON inválido."}, status=400)
    device_key = (payload.get("device_key") or "").strip()[:120]
    if not device_key:
        return JsonResponse({"detail": "Identificador de dispositivo requerido."}, status=400)
    statuses = {choice for choice, _ in CommunityDevicePermission.PermissionStatus.choices}
    values = {name: (payload.get(name) or CommunityDevicePermission.PermissionStatus.UNKNOWN).lower() for name in ("camera", "location", "notifications")}
    if any(value not in statuses for value in values.values()):
        return JsonResponse({"detail": "Estado de permiso inválido."}, status=400)
    device, _ = CommunityDevicePermission.objects.update_or_create(
        user=request.mobile_user,
        device_key=device_key,
        defaults={"device_name": (payload.get("device_name") or "Dispositivo móvil")[:80], "platform": (payload.get("platform") or "")[:16], **values},
    )
    return JsonResponse({"device": _device_permission_data(device)})


def _device_permission_data(device):
    return {"id": device.id, "device_name": device.device_name, "platform": device.platform, "camera": device.camera, "location": device.location, "notifications": device.notifications, "updated_at": device.updated_at.isoformat()}
