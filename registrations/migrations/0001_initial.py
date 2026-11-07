import uuid

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name="Registration",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("name", models.CharField(max_length=120)),
                ("reg_number", models.CharField(max_length=32, unique=True)),
                ("phone", models.CharField(max_length=16)),
                ("id_card_image_url", models.CharField(max_length=500)),
                ("status", models.CharField(choices=[("PAID", "Paid"), ("RESERVED", "Reserved"), ("PENDING_PAYMENT", "Pending payment"), ("FAILED", "Failed")], default="PENDING_PAYMENT", max_length=20)),
                ("amount_due", models.PositiveIntegerField(help_text="Rupees still owed. Zero once paid.")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("paid_at", models.DateTimeField(blank=True, null=True)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="Payment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("merchant_transaction_id", models.CharField(max_length=35, unique=True)),
                ("phonepe_transaction_id", models.CharField(blank=True, max_length=64)),
                ("amount", models.PositiveIntegerField(help_text="Amount in paise.")),
                ("state", models.CharField(choices=[("PENDING", "Pending"), ("COMPLETED", "Completed"), ("FAILED", "Failed")], default="PENDING", max_length=16)),
                ("raw_response", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("registration", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="payments", to="registrations.registration")),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="WebhookEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("event_id", models.CharField(max_length=64, unique=True)),
                ("payload", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.AddIndex(model_name="registration", index=models.Index(fields=["status"], name="registratio_status_42419d_idx")),
    ]

