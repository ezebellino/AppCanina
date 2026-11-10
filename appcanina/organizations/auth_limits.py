"""Persistent pre-authentication budgets shared by web, admin and mobile."""
import ipaddress
import json
import math
import unicodedata
from datetime import timedelta

from django.conf import settings
from django.db import DatabaseError, transaction
from django.db.models import F
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.utils.crypto import salted_hmac
from django.utils.deprecation import MiddlewareMixin

from .models import AuthAttemptBucket


WINDOW_SECONDS = 900
# Count all submissions, including successful ones: success cannot reset a spray budget.
LOGIN_LIMITS = {"ip": 60, "identifier": 20, "pair": 5}
RESET_LIMITS = {"ip": 10, "identifier": 3}


def client_network(request):
    raw = request.META.get("REMOTE_ADDR", "")
    # Only enable behind Railway's edge, with no direct public route to the origin.
    # X-Forwarded-For and client-selected forwarding headers are never consulted.
    if settings.AUTH_TRUST_RAILWAY_PROXY:
        raw = request.META.get("HTTP_X_REAL_IP", "")
    try:
        address = ipaddress.ip_address(raw)
        if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped:
            address = address.ipv4_mapped
        if address.version == 6:
            return str(ipaddress.ip_network(f"{address}/64", strict=False))
        return str(address)
    except ValueError:
        # Missing/ambiguous headers share a budget, never disable the limiter.
        return "unknown"


def budget_key(action, dimension, value):
    return salted_hmac("auth-attempt-v1", json.dumps([action, dimension, value]), algorithm="sha256").hexdigest()


def consume_budget(action, network, identifier):
    """Return seconds to retry, or zero. A window starts at its first submission.

    SQLite is the deployed backend. The first statement is a write, acquiring its
    writer lock BEFORE reading counters (select_for_update alone cannot do this).
    Conditional updates reserve slots before authentication/mail, even concurrently.
    No password hashing or SMTP runs inside the transaction.
    """
    now = timezone.now()
    limits = LOGIN_LIMITS if action == "login" else RESET_LIMITS
    values = {"ip": network, "identifier": identifier, "pair": [network, identifier]}
    wait = 0
    with transaction.atomic():
        AuthAttemptBucket.objects.filter(expires_at__lte=now).delete()
        for dimension, limit in limits.items():
            key = budget_key(action, dimension, values[dimension])
            bucket, _ = AuthAttemptBucket.objects.get_or_create(
                key=key, defaults={"expires_at": now + timedelta(seconds=WINDOW_SECONDS)},
            )
            reserved = AuthAttemptBucket.objects.filter(key=key, count__lt=limit).update(count=F("count") + 1)
            if not reserved:
                wait = max(wait, math.ceil((bucket.expires_at - now).total_seconds()))
                # Do not allocate attacker-selected identifiers after the source
                # has exhausted its budget. Keep upstream reservations committed.
                break
    return wait


class AuthAttemptLimitMiddleware(MiddlewareMixin):
    def process_view(self, request, view_func, view_args, view_kwargs):
        if request.method != "POST":
            return None
        name = request.resolver_match.view_name
        if name not in {"login", "admin:login", "mobile_login", "password_reset"}:
            return None
        mobile = name == "mobile_login"
        action = "reset" if name == "password_reset" else "login"
        if mobile:
            try:
                payload = json.loads(request.body)
            except (ValueError, UnicodeDecodeError):
                payload = {}
            identifier = payload.get("username", "") if isinstance(payload, dict) else ""
        else:
            identifier = request.POST.get("email" if action == "reset" else "username", "")
        if not isinstance(identifier, str):
            identifier = ""
        identifier = unicodedata.normalize("NFKC", identifier).strip().casefold()
        try:
            wait = consume_budget(action, client_network(request), identifier)
        except DatabaseError:
            # Never continue to authenticate/send mail if shared storage is unavailable.
            return self.unavailable(request, mobile, 60, status=503)
        if wait:
            return self.unavailable(request, mobile, wait)
        return None

    @staticmethod
    def unavailable(request, mobile, wait, status=429):
        message = (f"Hubo varios intentos seguidos. Esperá {max(1, math.ceil(wait / 60))} minutos y volvé a intentar."
                   if status == 429 else "No podemos procesar el acceso ahora. Esperá un minuto y volvé a intentar.")
        if mobile:
            response = JsonResponse({"detail": message}, status=status)
        else:
            response = render(request, "registration/access_wait.html", {"wait_message": message}, status=status)
        response["Retry-After"] = str(wait)
        response["Cache-Control"] = "no-store"
        return response
