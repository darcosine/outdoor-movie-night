import pytest
from django.urls import reverse

from registrations.models import Registration


@pytest.mark.django_db
def test_reserve_flow_confirms_seat_and_shows_onsite_price(client):
    response = client.post(reverse("registrations:home"), {
        "name": "Asha Student", "reg_number": "22BCE10001", "phone": "9876543210",
    })
    registration = Registration.objects.get(reg_number="22BCE10001")
    assert response.status_code == 302
    assert registration.status == Registration.Status.RESERVED
    assert registration.amount_due == 500
    page = client.get(reverse("registrations:confirmation", args=[registration.public_id])).content.decode()
    assert "₹500" in page
    assert "On spot payments will be 600rs per person" in page


@pytest.mark.django_db
def test_registration_page_has_no_payment_or_id_upload_controls(client):
    page = client.get(reverse("registrations:home")).content.decode()
    assert "Student ID card photo" not in page
    assert "Pay now" not in page
    assert "On spot payments will be 600rs per person" in page


@pytest.mark.django_db
def test_duplicate_registration_number_gets_friendly_message(client):
    Registration.objects.create(
        name="Asha Student", reg_number="22BCE10005", phone="+919876543210",
    )
    response = client.post(reverse("registrations:home"), {
        "name": "Asha Student", "reg_number": "22BCE10005", "phone": "9876543210",
    })
    assert response.status_code == 200
    assert "already registered" in response.content.decode().lower()
