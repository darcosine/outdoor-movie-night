import uuid

from django.db import models


class Registration(models.Model):
    class Status(models.TextChoices):
        PAID = "PAID", "Paid"
        RESERVED = "RESERVED", "Reserved"
        PENDING_PAYMENT = "PENDING_PAYMENT", "Pending payment"
        FAILED = "FAILED", "Failed"

    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(max_length=120)
    reg_number = models.CharField(max_length=32, unique=True)
    phone = models.CharField(max_length=16)
    id_card_image_url = models.CharField(max_length=500)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING_PAYMENT,
    )
    amount_due = models.PositiveIntegerField(help_text="Rupees still owed. Zero once paid.")
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status"])]

    def __str__(self):
        return f"{self.reg_number} ({self.name})"

    @property
    def is_open_for_payment(self):
        return self.status in {self.Status.PENDING_PAYMENT, self.Status.FAILED}

    def amount_paid_rupees(self):
        completed = [p for p in self.payments.all() if p.state == Payment.State.COMPLETED]
        if not completed:
            return 0
        completed.sort(key=lambda payment: payment.created_at)
        return completed[0].amount // 100

    @property
    def amount_rupees(self):
        return self.amount // 100

    def money_label(self):
        if self.status == self.Status.PAID:
            return f"Rs {self.amount_paid_rupees()} paid"
        if self.status == self.Status.RESERVED:
            return f"Rs {self.amount_due} due"
        if self.status == self.Status.FAILED:
            return f"Rs {self.amount_due} unpaid"
        return f"Rs {self.amount_due} pending"

    def transaction_reference(self):
        completed = [p for p in self.payments.all() if p.state == Payment.State.COMPLETED]
        if not completed:
            return ""
        completed.sort(key=lambda payment: payment.created_at)
        payment = completed[0]
        return payment.phonepe_transaction_id or payment.merchant_transaction_id



class FeaturedMovie(models.Model):
    """The single movie promoted on the student registration page."""

    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    title = models.CharField(max_length=160)
    poster_image_url = models.CharField(max_length=500, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

class Payment(models.Model):
    class State(models.TextChoices):
        PENDING = "PENDING", "Pending"
        COMPLETED = "COMPLETED", "Completed"
        FAILED = "FAILED", "Failed"

    registration = models.ForeignKey(
        Registration,
        on_delete=models.PROTECT,
        related_name="payments",
    )
    merchant_transaction_id = models.CharField(max_length=35, unique=True)
    phonepe_transaction_id = models.CharField(max_length=64, blank=True)
    amount = models.PositiveIntegerField(help_text="Amount in paise.")
    state = models.CharField(max_length=16, choices=State.choices, default=State.PENDING)
    raw_response = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.merchant_transaction_id


class WebhookEvent(models.Model):
    """One row per callback body, so PhonePe retries do not double-apply."""

    event_id = models.CharField(max_length=64, unique=True)
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.event_id


def new_merchant_transaction_id():
    """PhonePe accepts up to 35 alphanumeric characters."""
    return uuid.uuid4().hex[:32]


