from datetime import timedelta
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from dashboard.views import _counts
from registrations.models import Payment, Registration


@pytest.mark.django_db
def test_staff_can_confirm_pending_payment_before_event(client):
    registration = Registration.objects.create(
        name="Asha Student", reg_number="251FW02028", phone="+919876543210",
        id_card_image_url="https://example.test/id.jpg",
        status=Registration.Status.PENDING_PAYMENT, amount_due=500,
    )
    Payment.objects.create(
        registration=registration, merchant_transaction_id="pending-admin-test-1", amount=50000,
    )
    staff = get_user_model().objects.create_user(
        username="event-staff", password="test-pass-12345", is_staff=True,
    )
    client.force_login(staff)

    with override_settings(EVENT_DATE=timezone.localdate() + timedelta(days=1)):
        response = client.post(reverse("dashboard:mark_paid", args=[registration.pk]))

    registration.refresh_from_db()
    assert response.status_code == 302
    assert registration.status == Registration.Status.PAID
    assert registration.amount_due == 0
    payments = list(registration.payments.all())
    assert len(payments) == 1
    assert payments[0].state == Payment.State.COMPLETED
    assert payments[0].amount == 50000
    assert payments[0].raw_response["source"] == "staff_manual"


@pytest.mark.django_db
def test_staff_cannot_change_pending_payment_on_event_date(client):
    registration = Registration.objects.create(
        name="Asha Student", reg_number="251FW02029", phone="+919876543210",
        id_card_image_url="https://example.test/id.jpg",
        status=Registration.Status.PENDING_PAYMENT, amount_due=500,
    )
    staff = get_user_model().objects.create_user(
        username="event-staff-2", password="test-pass-12345", is_staff=True,
    )
    client.force_login(staff)

    with override_settings(EVENT_DATE=timezone.localdate()):
        response = client.post(reverse("dashboard:mark_paid", args=[registration.pk]))

    registration.refresh_from_db()
    assert response.status_code == 302
    assert registration.status == Registration.Status.PENDING_PAYMENT
    assert not registration.payments.filter(state=Payment.State.COMPLETED).exists()

@pytest.mark.django_db
def test_staff_can_remove_registration_and_its_payment_records(client):
    registration = Registration.objects.create(
        name="Remove Me", reg_number="251FW02031", phone="+919876543210",
        id_card_image_url="https://example.test/id.jpg",
        status=Registration.Status.PENDING_PAYMENT, amount_due=500,
    )
    Payment.objects.create(
        registration=registration, merchant_transaction_id="remove-record-test", amount=50000,
    )
    staff = get_user_model().objects.create_user(
        username="event-remover", password="test-pass-12345", is_staff=True,
    )
    client.force_login(staff)

    with patch("dashboard.views.delete_id_card") as delete_image:
        response = client.post(reverse("dashboard:remove", args=[registration.pk]))
    delete_image.assert_called_once_with("https://example.test/id.jpg")

    assert response.status_code == 302
    assert not Registration.objects.filter(pk=registration.pk).exists()
    assert not Payment.objects.filter(merchant_transaction_id="remove-record-test").exists()



@pytest.mark.django_db
def test_pending_online_students_are_counted_separately_from_reservations():
    for reg_number in ("251FW02041", "251FW02042"):
        Registration.objects.create(
            name="Pending Student", reg_number=reg_number, phone="+919876543210",
            id_card_image_url="https://example.test/id.jpg",
            status=Registration.Status.PENDING_PAYMENT, amount_due=500,
        )

    counts = _counts()

    assert counts["reserved"] == 0
    assert counts["pending"] == 2
