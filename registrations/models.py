import uuid

from django.db import models


class Registration(models.Model):
    class Status(models.TextChoices):
        RESERVED = "RESERVED", "Reserved"
        PAID = "PAID", "Paid"

    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(max_length=120)
    reg_number = models.CharField(max_length=32, unique=True)
    phone = models.CharField(max_length=16)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.RESERVED,
    )
    amount_due = models.PositiveIntegerField(default=500, help_text="Reservation amount in rupees.")
    amount_paid = models.PositiveIntegerField(null=True, blank=True, help_text="Amount recorded when marked paid, in rupees.")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status"])]

    def __str__(self):
        return f"{self.reg_number} ({self.name})"

    def money_label(self):
        if self.status == self.Status.PAID:
            return "Paid"
        return f"Rs {self.amount_due} due"



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
