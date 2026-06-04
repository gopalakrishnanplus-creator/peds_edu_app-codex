from __future__ import annotations

import json
import time
import uuid
from urllib.parse import urlencode

from django.conf import settings
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods

from .jwt import decode_and_verify_hs256_jwt, JWTError


POST_LOGIN_REDIRECT_SESSION_KEY = "post_login_redirect"


def _is_staff_or_superuser(request) -> bool:
    user = getattr(request, "user", None)
    return bool(
        user
        and getattr(user, "is_authenticated", False)
        and (getattr(user, "is_staff", False) or getattr(user, "is_superuser", False))
    )


def _safe_next_url(request, next_url: str) -> str:
    target = (next_url or "/").strip() or "/"
    if url_has_allowed_host_and_scheme(
        target,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return target
    return "/"


def _staff_identity(request) -> dict:
    user = getattr(request, "user", None)
    email = (getattr(user, "email", "") or "").strip().lower()
    return {
        "sub": f"django-user:{getattr(user, 'pk', '')}",
        "username": email or str(user),
        "roles": ["publisher", "admin"],
        "iss": "django_staff",
        "aud": getattr(settings, "SSO_EXPECTED_AUDIENCE", "project2"),
        "email": email,
        "publisher_email": email,
        "auth_source": "django_staff",
    }


def _set_publisher_session(request, *, identity: dict, campaign_id: str) -> None:
    request.session[getattr(settings, "SSO_SESSION_KEY_IDENTITY", "sso_identity")] = identity
    request.session[getattr(settings, "SSO_SESSION_KEY_CAMPAIGN", "campaign_id")] = str(campaign_id)
    if hasattr(request.session, "set_expiry"):
        request.session.set_expiry(getattr(settings, "SSO_SESSION_AGE_SECONDS", 3600))
    request.session.modified = True


def _store_pending_campaign_redirect(request, *, campaign_id: str, next_url: str) -> str:
    safe_next = _safe_next_url(request, next_url)
    request.session[getattr(settings, "SSO_SESSION_KEY_CAMPAIGN", "campaign_id")] = str(campaign_id)
    request.session[POST_LOGIN_REDIRECT_SESSION_KEY] = safe_next
    request.session.modified = True
    return safe_next


def _redirect_to_login_for_campaign(request, *, campaign_id: str, next_url: str) -> HttpResponse:
    safe_next = _store_pending_campaign_redirect(
        request,
        campaign_id=campaign_id,
        next_url=next_url,
    )
    messages.info(request, "Please log in to continue campaign setup.")
    login_url = reverse("accounts:login")
    if safe_next:
        login_url = f"{login_url}?{urlencode({'next': safe_next})}"
    return redirect(login_url)


@require_http_methods(["GET"])
def consume(request):
    """
    SSO endpoint:
      GET /sso/consume/?token=...&campaign_id=...&next=/some/path

    Validates token and then creates Project2 session.

    Debug mode:
      Append ?debug_sso=1 to see plaintext progress output in browser.
      No sensitive values are exposed.
    """

    # ------------------------------------------------------------------
    # Debug helpers (NO-OP unless ?debug_sso=1)
    # ------------------------------------------------------------------
    debug_enabled = request.GET.get("debug_sso") == "1"
    debug_lines: list[str] = []

    def _debug(msg: str):
        if debug_enabled:
            debug_lines.append(msg)

    def _debug_response(final: bool = False):
        if debug_enabled and final:
            return HttpResponse(
                "\n".join(debug_lines),
                content_type="text/plain",
            )
        return None

    # ------------------------------------------------------------------
    # Structured log (still safe even without server access)
    # ------------------------------------------------------------------
    req_id = request.META.get("HTTP_X_REQUEST_ID") or uuid.uuid4().hex[:12]

    def _log(event: str, **data):
        payload = {
            "ts": int(time.time()),
            "req_id": req_id,
            "event": event,
        }
        payload.update(data)
        print(json.dumps(payload, default=str))

    # ------------------------------------------------------------------
    # Token + params (support alternate token names)
    # ------------------------------------------------------------------
    token = (
        request.GET.get("token")
        or request.GET.get("sso_token")
        or request.GET.get("jwt")
        or request.GET.get("access_token")
        or ""
    ).strip()

    campaign_id_raw = (
        request.GET.get("campaign_id")
        or request.GET.get("campaign-id")
        or ""
    ).strip()

    next_url = (request.GET.get("next") or "/").strip() or "/"

    _debug("Reached consume()")
    _debug(f"token present: {bool(token)}")
    _debug(f"campaign_id present: {bool(campaign_id_raw)}")

    _log(
        "sso.consume.start",
        token_len=len(token),
        has_campaign_id=bool(campaign_id_raw),
        next_path=next_url[:200],
    )

    # ------------------------------------------------------------------
    # Basic validation
    # ------------------------------------------------------------------
    if not token or not campaign_id_raw:
        _debug("FAIL: missing token or campaign_id")
        _log("sso.consume.missing_params")
        messages.error(request, "Missing token or campaign_id.")
        return _debug_response(final=True) or redirect("/")

    if _is_staff_or_superuser(request):
        campaign_id_value = campaign_id_raw
        try:
            campaign_id_value = str(uuid.UUID(campaign_id_raw))
            _debug("campaign_id normalized to UUID")
        except Exception:
            _debug("campaign_id treated as string")

        _set_publisher_session(
            request,
            identity=_staff_identity(request),
            campaign_id=campaign_id_value,
        )
        safe_next = _safe_next_url(request, next_url)
        _log("sso.consume.staff_session_set", next_url=safe_next)
        return _debug_response(final=True) or redirect(safe_next)

    if not getattr(settings, "SSO_SHARED_SECRET", ""):
        _debug("FAIL: SSO_SHARED_SECRET not configured")
        _log("sso.consume.misconfigured")
        messages.error(request, "SSO not configured.")
        return _debug_response(final=True) or redirect("/")

    # ------------------------------------------------------------------
    # Decode + verify JWT
    # ------------------------------------------------------------------
    try:
        payload = decode_and_verify_hs256_jwt(
            token,
            secret=settings.SSO_SHARED_SECRET,
            issuer=settings.SSO_EXPECTED_ISSUER,
            audience=settings.SSO_EXPECTED_AUDIENCE,
        )
        _debug("JWT verified successfully")
    except JWTError as e:
        _debug(f"FAIL: JWT error ({e.__class__.__name__})")
        _log("sso.consume.jwt_error", error=str(e))
        if campaign_id_raw:
            return _debug_response(final=True) or _redirect_to_login_for_campaign(
                request,
                campaign_id=campaign_id_raw,
                next_url=next_url,
            )
        messages.error(
            request,
            "SSO link is invalid or expired. Please reopen it from the publisher portal.",
        )
        return _debug_response(final=True) or redirect("/")

    # ------------------------------------------------------------------
    # Required claims
    # ------------------------------------------------------------------
    sub = (payload.get("sub") or "").strip()
    username = (payload.get("username") or "").strip()
    roles = payload.get("roles") or []

    _debug(f"sub present: {bool(sub)}")
    _debug(f"username present: {bool(username)}")
    _debug(f"roles valid list: {isinstance(roles, list)}")

    _log(
        "sso.consume.jwt_ok",
        sub=(sub[:6] + "***") if sub else "",
        username=(
            (username.split("@")[0][:2] + "***@" + username.split("@")[1])
            if "@" in username
            else (username[:3] + "***")
        ),
        roles=roles,
    )

    if not sub or not username or not isinstance(roles, list):
        _debug("FAIL: missing or invalid JWT claims")
        _log("sso.consume.claims_invalid")
        messages.error(request, "SSO token missing required claims.")
        return _debug_response(final=True) or redirect("/")

    # ------------------------------------------------------------------
    # Optional hardening: campaign_id inside JWT
    # ------------------------------------------------------------------
    token_campaign = (payload.get("campaign_id") or "").strip()
    if token_campaign and token_campaign != campaign_id_raw:
        _debug("FAIL: campaign_id mismatch (token vs query)")
        _log("sso.consume.campaign_mismatch")
        messages.error(request, "Invalid campaign_id.")
        return _debug_response(final=True) or redirect("/")

    # ------------------------------------------------------------------
    # Normalize campaign_id
    # ------------------------------------------------------------------
    campaign_id_value = campaign_id_raw
    try:
        campaign_id_value = str(uuid.UUID(campaign_id_raw))
        _debug("campaign_id normalized to UUID")
    except Exception:
        _debug("campaign_id treated as string")

    # ------------------------------------------------------------------
    # Create Project2 session
    # ------------------------------------------------------------------
    _set_publisher_session(
        request,
        identity={
            "sub": sub,
            "username": username,
            "roles": roles,
            "iss": payload.get("iss"),
            "aud": payload.get("aud"),
            "email": (payload.get("email") or "").strip(),
            "publisher_email": (payload.get("publisher_email") or "").strip(),
        },
        campaign_id=str(campaign_id_value),
    )

    _debug("Session created successfully")
    _log(
        "sso.consume.session_set",
        session_age_seconds=getattr(settings, "SSO_SESSION_AGE_SECONDS", 3600),
    )

    # ------------------------------------------------------------------
    # Safe redirect
    # ------------------------------------------------------------------
    if not url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        _debug("Unsafe next URL — redirecting to /")
        _log("sso.consume.unsafe_next_url")
        next_url = "/"

    _debug(f"Redirecting to: {next_url}")
    _log("sso.consume.redirect", next_url=next_url)

    return _debug_response(final=True) or redirect(next_url)
