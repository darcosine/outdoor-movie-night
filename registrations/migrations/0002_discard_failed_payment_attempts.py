from django.db import migrations


def discard_failed_attempts(apps, schema_editor):
    Payment = apps.get_model("registrations", "Payment")
    Registration = apps.get_model("registrations", "Registration")
    database = schema_editor.connection.alias

    Payment.objects.using(database).filter(state="FAILED").delete()
    Registration.objects.using(database).filter(status="FAILED").update(
        status="PENDING_PAYMENT"
    )


class Migration(migrations.Migration):
    dependencies = [("registrations", "0001_initial")]

    operations = [migrations.RunPython(discard_failed_attempts, migrations.RunPython.noop)]
