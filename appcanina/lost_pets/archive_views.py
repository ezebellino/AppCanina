from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .adoption_archives import set_archive
from .adoption_updates import managed_interest_organizations
from .api import token_required, _mobile_payload, _mobile_managed_shelter_ids
from .models import AdoptionInterest


def scope(user, audience, mobile=False):
    if audience == "applicant":
        return AdoptionInterest.objects.filter(applicant=user)
    if audience == "institution":
        organizations = _mobile_managed_shelter_ids(user) if mobile else managed_interest_organizations(user).values_list("pk", flat=True)
        return AdoptionInterest.objects.filter(post__organization_id__in=organizations)
    return AdoptionInterest.objects.none()


@login_required
@require_POST
def archive(request, audience, interest_id):
    detail, status = set_archive(scope(request.user, audience), request.user, audience, interest_id,
                                 request.POST.get("action"), request.POST.get("expected_updated_at"))
    if status != 200:
        return JsonResponse({"detail": detail}, status=status)
    messages.success(request, detail)
    target = "my_adoption_interests" if audience == "applicant" else "adoption_interest_list"
    response = redirect(target)
    if request.POST.get("action") == "restore":
        response["Location"] += "?view=archived"
    if request.headers.get("Accept") == "application/json":
        return JsonResponse({"detail": detail, "redirect_url": response["Location"]})
    return response


@csrf_exempt
@require_POST
@token_required("lost_pets.view_lostpetreport")
def mobile_archive(request, audience, interest_id):
    payload = _mobile_payload(request)
    if not isinstance(payload, dict):
        return JsonResponse({"detail": "Datos inválidos."}, status=400)
    detail, status = set_archive(scope(request.mobile_user, audience, mobile=True), request.mobile_user,
                                 audience, interest_id, payload.get("action"), payload.get("expected_updated_at"))
    response = JsonResponse({"detail": detail}, status=status)
    response["Cache-Control"] = "no-store"
    return response
