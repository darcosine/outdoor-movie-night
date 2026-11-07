import base64
import io
import json
from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from PIL import Image

from registrations.models import Payment, Registration, WebhookEvent
from registrations.services import phonepe


def image_upload():
    buffer = io.BytesIO()
    Image.new("RGB", (640, 400), "#d8e4ec").save(buffer, format="JPEG")
    return SimpleUploadedFile("student-id.jpg", buffer.getvalue(), content_type="image/jpeg")


def callback_payload(payment, *, state="COMPLETED", code="PAYMENT_SUCCESS", amount=50000):
    return {
        "success": state == "COMPLETED",
        "code": code,
        "data": {
            "merchantId": "TESTMERCHANT",
            "merchantTransactionId": payment.merchant_transaction_id,
            "transactionId": "PHONEPE-TEST-123",
            "amount": amount,
            "state": state,
        },
    }


@pytest.mark.django_db
@override_settings(ALLOW_LOCAL_MEDIA=True)
def test_reserve_flow_shows_600_due(client, tmp_path):
    with override_settings(MEDIA_ROOT=tmp_path):
        response = client.post(reverse("registrations:home"), {
            "name": "Asha Student", "reg_number": "22BCE10001", "phone": "9876543210",
            "choice": "reserve", "id_card": image_upload(),
        })
    registration = Registration.objects.get(reg_number="22BCE10001")
    assert response.status_code == 302
    assert registration.status == Registration.Status.RESERVED
    assert registration.amount_due == 600
    confirmation = client.get(reverse("registrations:confirmation", args=[registration.public_id]))
    page = confirmation.content.decode()
    assert "₹600" in page
    assert "Take a screenshot of this page as proof of registration." in page


@pytest.mark.django_db
@override_settings(ALLOW_LOCAL_MEDIA=True, PHONEPE_MOCK=True)
def test_pay_flow_uses_mock_checkout_and_verified_callback(client, tmp_path):
    with override_settings(MEDIA_ROOT=tmp_path):
        response = client.post(reverse("registrations:home"), {
            "name": "Asha Student", "reg_number": "22BCE10002", "phone": "9876543210",
            "choice": "pay", "id_card": image_upload(),
        })
    registration = Registration.objects.get(reg_number="22BCE10002")
    payment = registration.payments.get()
    assert response.status_code == 302
    assert response["Location"] == reverse(
        "registrations:mock_checkout", args=[payment.merchant_transaction_id]
    )
    checkout_page = client.get(response["Location"]).content.decode()
    assert "₹500" in checkout_page
    client.post(response["Location"], {"outcome": "success"})
    registration.refresh_from_db()
    payment.refresh_from_db()
    assert registration.status == Registration.Status.PAID
    assert registration.amount_due == 0
    assert payment.state == Payment.State.COMPLETED
    page = client.get(
        reverse("registrations:confirmation", args=[registration.public_id])
    ).content.decode()
    assert "MOCK" in page
    assert "Take a screenshot of this page as proof of registration." in page


@pytest.mark.django_db
def test_callback_requires_checksum_and_status_api_confirmation(settings):
    settings.PHONEPE_MERCHANT_ID = "TESTMERCHANT"
    settings.PHONEPE_SALT_KEY = "test-salt"
    settings.PHONEPE_SALT_INDEX = "1"
    registration = Registration.objects.create(
        name="Asha", reg_number="22BCE10003", phone="+919876543210",
        id_card_image_url="https://example.test/id.jpg", amount_due=500,
    )
    payment = Payment.objects.create(
        registration=registration, merchant_transaction_id="merchant-unique-3", amount=50000,
    )
    payload = callback_payload(payment)
    encoded = base64.b64encode(json.dumps(payload).encode()).decode()
    with pytest.raises(phonepe.InvalidCallback):
        phonepe.process_callback(encoded, "invalid")
    assert Registration.objects.get(pk=registration.pk).status == Registration.Status.PENDING_PAYMENT

    with patch("registrations.services.phonepe.fetch_status", return_value=payload):
        assert phonepe.process_callback(encoded, phonepe.x_verify(encoded)) == "paid"
        assert phonepe.process_callback(encoded, phonepe.x_verify(encoded)) == "already_paid"
    registration.refresh_from_db()
    payment.refresh_from_db()
    assert registration.status == Registration.Status.PAID
    assert payment.state == Payment.State.COMPLETED


@pytest.mark.django_db
def test_callback_does_not_mark_paid_when_status_api_amount_is_wrong(settings):
    settings.PHONEPE_MERCHANT_ID = "TESTMERCHANT"
    settings.PHONEPE_SALT_KEY = "test-salt"
    settings.PHONEPE_SALT_INDEX = "1"
    registration = Registration.objects.create(
        name="Asha", reg_number="22BCE10004", phone="+919876543210",
        id_card_image_url="https://example.test/id.jpg", amount_due=500,
    )
    payment = Payment.objects.create(
        registration=registration, merchant_transaction_id="merchant-unique-4", amount=50000,
    )
    callback = callback_payload(payment)
    status = callback_payload(payment, amount=1000)
    encoded = base64.b64encode(json.dumps(callback).encode()).decode()
    with patch("registrations.services.phonepe.fetch_status", return_value=status):
        assert phonepe.process_callback(encoded, phonepe.x_verify(encoded)) == "failed"
    registration.refresh_from_db()
    assert registration.status == Registration.Status.PENDING_PAYMENT
    assert not Payment.objects.filter(merchant_transaction_id=payment.merchant_transaction_id).exists()


@pytest.mark.django_db
@override_settings(ALLOW_LOCAL_MEDIA=True)
def test_duplicate_registration_number_gets_friendly_message(client, tmp_path):
    Registration.objects.create(
        name="Asha Student", reg_number="22BCE10005", phone="+919876543210",
        id_card_image_url="https://example.test/id.jpg", status=Registration.Status.RESERVED,
        amount_due=600,
    )
    with override_settings(MEDIA_ROOT=tmp_path):
        response = client.post(reverse("registrations:home"), {
            "name": "Asha Student", "reg_number": "22BCE10005", "phone": "9876543210",
            "choice": "reserve", "id_card": image_upload(),
        })
    assert response.status_code == 200
    assert "already registered" in response.content.decode().lower()


@pytest.mark.django_db
@override_settings(ALLOW_LOCAL_MEDIA=True, PHONEPE_MOCK=True)
def test_failed_mock_payment_is_not_saved_and_returns_retry_options(client, tmp_path):
    with override_settings(MEDIA_ROOT=tmp_path):
        response = client.post(reverse("registrations:home"), {
            "name": "Asha Student", "reg_number": "22BCE10006", "phone": "9876543210",
            "choice": "pay", "id_card": image_upload(),
        })
    registration = Registration.objects.get(reg_number="22BCE10006")
    failed_response = client.post(response["Location"], {"outcome": "failure"})
    assert failed_response.status_code == 302
    assert failed_response["Location"] == reverse(
        "registrations:confirmation", args=[registration.public_id]
    )
    registration.refresh_from_db()
    assert registration.status == Registration.Status.PENDING_PAYMENT
    assert not registration.payments.exists()
    assert WebhookEvent.objects.latest("created_at").payload == {}
    page = client.get(failed_response["Location"]).content.decode()
    assert "Retry payment" in page
    assert "Switch to reserve" in page
