"""PhonePe Standard Checkout.

A registration becomes PAID only inside ``process_callback``:
the X-VERIFY checksum must match, and the server-side status API must
confirm merchant, transaction id, and amount (50000 paise). The browser
return URL never marks a seat paid.
"""

import base64
import hashlib
import hmac
import json
import logging
from urllib.parse import quote

import requests
from django.conf import settings
from django.core.cache import cache
from django.db import connection, transaction
from django.utils import timezone

from registrations.models import Payment, Registration, WebhookEvent

logger = logging.getLogger(__name__)

PAY_PATH = "/pg/v1/pay"
_FAILED_STATES = {"FAILED", "DECLINED"}
_FAILED_CODES = {"PAYMENT_ERROR", "PAYMENT_DECLINED", "PAYMENT_FAILED"}


class PhonePeError(Exception):
    pass


class InvalidCallback(PhonePeError):
    pass


def _lock(queryset):
    if connection.vendor == "postgresql":
        return queryset.select_for_update()
    return queryset


def x_verify(material: str) -> str:
    digest = hashlib.sha256((material + settings.PHONEPE_SALT_KEY).encode()).hexdigest()
    return f"{digest}###{settings.PHONEPE_SALT_INDEX}"


def verify_callback_checksum(payload: str, header: str) -> bool:
    header = (header or "").strip()
    if header.count("###") != 1:
        return False
    digest, index = header.split("###")
    if index != str(settings.PHONEPE_SALT_INDEX):
        return False
    expected = hashlib.sha256((payload + settings.PHONEPE_SALT_KEY).encode()).hexdigest()
    if len(digest) != len(expected):
        return False
    return hmac.compare_digest(expected, digest.lower())


def _mock_cache_key(merchant_transaction_id: str) -> str:
    return f"phonepe-mock-outcome:{merchant_transaction_id}"


def remember_mock_outcome(merchant_transaction_id: str, outcome: str) -> None:
    cache.set(_mock_cache_key(merchant_transaction_id), outcome, 900)


def _require_credentials() -> None:
    if not settings.PHONEPE_MERCHANT_ID or not settings.PHONEPE_SALT_KEY:
        raise PhonePeError("PhonePe is not configured.")


def initiate_payment(payment: Payment) -> str:
    """Return the URL the student's browser should open next."""
    if settings.PHONEPE_MOCK:
        from django.urls import reverse

        return reverse(
            "registrations:mock_checkout",
            args=[payment.merchant_transaction_id],
        )

    _require_credentials()
    if payment.amount != settings.PAY_PAISE:
        raise PhonePeError("Refusing to start a checkout for an unexpected amount.")

    payload = {
        "merchantId": settings.PHONEPE_MERCHANT_ID,
        "merchantTransactionId": payment.merchant_transaction_id,
        "merchantUserId": f"U{payment.registration_id}",
        "amount": settings.PAY_PAISE,
        "redirectUrl": settings.PHONEPE_REDIRECT_URL,
        "redirectMode": "REDIRECT",
        "callbackUrl": settings.PHONEPE_CALLBACK_URL,
        "paymentInstrument": {"type": "PAY_PAGE"},
    }
    encoded = base64.b64encode(
        json.dumps(payload, separators=(",", ":")).encode()
    ).decode()
    try:
        response = requests.post(
            settings.PHONEPE_BASE_URL.rstrip("/") + PAY_PATH,
            json={"request": encoded},
            headers={
                "Content-Type": "application/json",
                "X-VERIFY": x_verify(encoded + PAY_PATH),
                "accept": "application/json",
            },
            timeout=20,
        )
        response.raise_for_status()
        body = response.json()
    except (requests.RequestException, ValueError) as exc:
        logger.warning("PhonePe initiate failed for %s", payment.merchant_transaction_id)
        raise PhonePeError("PhonePe checkout could not be started.") from exc

    url = (
        (body.get("data") or {})
        .get("instrumentResponse", {})
        .get("redirectInfo", {})
        .get("url")
    )
    if not url:
        raise PhonePeError("PhonePe did not return a checkout URL.")
    return url


def fetch_status(merchant_transaction_id: str) -> dict:
    if settings.PHONEPE_MOCK:
        outcome = cache.get(_mock_cache_key(merchant_transaction_id), "pending")
        state = {"success": "COMPLETED", "failure": "FAILED"}.get(outcome, "PENDING")
        code = {"success": "PAYMENT_SUCCESS", "failure": "PAYMENT_ERROR"}.get(
            outcome, "PAYMENT_PENDING"
        )
        return {
            "success": outcome == "success",
            "code": code,
            "message": "mock",
            "data": {
                "merchantId": settings.PHONEPE_MERCHANT_ID,
                "merchantTransactionId": merchant_transaction_id,
                "transactionId": f"MOCK{merchant_transaction_id[:12]}",
                "amount": settings.PAY_PAISE,
                "state": state,
                "responseCode": "SUCCESS" if outcome == "success" else "PENDING",
            },
        }

    _require_credentials()
    merchant_id = quote(settings.PHONEPE_MERCHANT_ID, safe="")
    txn = quote(merchant_transaction_id, safe="")
    path = f"/pg/v1/status/{merchant_id}/{txn}"
    url = settings.PHONEPE_BASE_URL.rstrip("/") + path
    try:
        response = requests.get(
            url,
            headers={
                "Content-Type": "application/json",
                "X-VERIFY": x_verify(path),
                "X-MERCHANT-ID": settings.PHONEPE_MERCHANT_ID,
                "accept": "application/json",
            },
            timeout=20,
        )
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError) as exc:
        logger.warning("PhonePe status check failed for %s", merchant_transaction_id)
        raise PhonePeError("PhonePe status check failed.") from exc


def _as_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def apply_status(payment: Payment, registration: Registration, status_body: dict, callback_payload):
    """Apply a verified status response. Caller holds the database transaction."""
    if registration.status == Registration.Status.PAID:
        if payment.state != Payment.State.COMPLETED:
            payment.delete()
        return "already_paid"

    data = status_body.get("data") or {}
    code = (status_body.get("code") or "").upper()
    state = (data.get("state") or "").upper()
    amount = _as_int(data.get("amount"))
    merchant_id = str(data.get("merchantId") or "")
    returned_txn = str(data.get("merchantTransactionId") or "")
    identity_matches = (
        returned_txn == payment.merchant_transaction_id
        and merchant_id == settings.PHONEPE_MERCHANT_ID
    )

    raw = {"status": status_body}


    if callback_payload is not None:


        raw["callback"] = callback_payload


    payment.raw_response = raw


    payment.phonepe_transaction_id = data.get("transactionId") or payment.phonepe_transaction_id


    if not identity_matches:


        payment.state = Payment.State.PENDING


        payment.save(update_fields=["raw_response", "phonepe_transaction_id", "state"])


        return "pending"

    success = (
        code == "PAYMENT_SUCCESS"
        and state == "COMPLETED"
        and amount == settings.PAY_PAISE
        and payment.amount == settings.PAY_PAISE
    )
    if success:
        payment.state = Payment.State.COMPLETED
        payment.save(update_fields=["raw_response", "phonepe_transaction_id", "state"])
        registration.status = Registration.Status.PAID
        registration.amount_due = 0
        registration.paid_at = registration.paid_at or timezone.now()
        registration.save(update_fields=["status", "amount_due", "paid_at"])
        return "paid"

    failed = state in _FAILED_STATES or code in _FAILED_CODES or (
        code == "PAYMENT_SUCCESS" and amount is not None and amount != settings.PAY_PAISE
    )
    if failed:
        # Keep the registration retryable, but discard unsuccessful payment attempts.
        payment.delete()
        if registration.status != Registration.Status.RESERVED:
            registration.status = Registration.Status.PENDING_PAYMENT
            registration.save(update_fields=["status"])
        return "failed"

    payment.state = Payment.State.PENDING
    payment.save(update_fields=["raw_response", "phonepe_transaction_id", "state"])
    if registration.status not in {Registration.Status.PAID, Registration.Status.RESERVED}:
        registration.status = Registration.Status.PENDING_PAYMENT
        registration.save(update_fields=["status"])
    return "pending"


def reconcile_from_status(merchant_transaction_id: str, callback_payload=None) -> str:
    status_body = fetch_status(merchant_transaction_id)
    with transaction.atomic():
        try:
            payment = _lock(Payment.objects).get(merchant_transaction_id=merchant_transaction_id)
        except Payment.DoesNotExist:
            logger.warning("No payment for transaction %s", merchant_transaction_id)
            return "unknown"
        registration = _lock(Registration.objects).get(pk=payment.registration_id)
        return apply_status(payment, registration, status_body, callback_payload)


def process_callback(response_b64: str, x_verify_header: str) -> str:
    """Verify the checksum, then confirm with the status API. Idempotent."""
    if not response_b64 or not verify_callback_checksum(response_b64, x_verify_header):
        raise InvalidCallback("checksum")
    try:
        decoded = json.loads(base64.b64decode(response_b64))
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise InvalidCallback("payload") from exc

    data = decoded.get("data") or {}
    merchant_transaction_id = data.get("merchantTransactionId") or ""
    if not merchant_transaction_id:
        raise InvalidCallback("missing transaction")

    result = reconcile_from_status(merchant_transaction_id, callback_payload=decoded)
    event_id = hashlib.sha256(response_b64.encode()).hexdigest()
    event_payload = {} if result == "failed" else decoded
    WebhookEvent.objects.get_or_create(event_id=event_id, defaults={"payload": event_payload})
    return result


