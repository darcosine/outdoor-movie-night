from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("registrations", "0002_discard_failed_payment_attempts")]

    operations = [
        migrations.CreateModel(
            name="FeaturedMovie",
            fields=[
                ("id", models.PositiveSmallIntegerField(default=1, editable=False, primary_key=True, serialize=False)),
                ("title", models.CharField(max_length=160)),
                ("poster_image_url", models.CharField(blank=True, max_length=500)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
    ]
