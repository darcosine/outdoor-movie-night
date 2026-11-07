import pytest

from registrations.models import Payment, Registration
from registrations.services.phonepe import apply_status


@pytest.mark.django_db
def test_failed_payment_attempt_is_removed_and_registration_remains_retryable(settings):
    settings.PHONEPE_MERCHANT_ID = "TESTMERCHANT"
    registration = Registration.objects.create(
        name="Asha Student", reg_number="251FW02030", phone="+919876543210",
        id_card_image_url="https://example.test/id.jpg",
        status=Registration.Status.PENDING_PAYMENT, amount_due=500,
    )
    payment = Payment.objects.create(
        registration=registration, merchant_transaction_id="failed-attempt-unique", amount=50000,
    )
    status = {
        "code": "PAYMENT_ERROR",
        "data": {
            "merchantId": "TESTMERCHANT",
            "merchantTransactionId": payment.merchant_transaction_id,
            "amount": 50000,
            "state": "FAILED",
        },
    }

    assert apply_status(payment, registration, status, None) == "failed"
    registration.refresh_from_db()
    assert registration.status == Registration.Status.PENDING_PAYMENT
    assert not Payment.objects.filter(merchant_transaction_id="failed-attempt-unique").exists()
