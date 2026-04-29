from decimal import Decimal

from django.db import migrations


def seed_services(apps, schema_editor):
    Service = apps.get_model("core", "Service")

    if Service.objects.exists():
        return

    Service.objects.bulk_create(
        [
            Service(name="Wash & Fold", price=Decimal("79.00"), is_active=True),
            Service(name="Dry Cleaning", price=Decimal("149.00"), is_active=True),
            Service(name="Steam Iron", price=Decimal("59.00"), is_active=True),
        ]
    )


def unseed_services(apps, schema_editor):
    Service = apps.get_model("core", "Service")
    Service.objects.filter(name__in=["Wash & Fold", "Dry Cleaning", "Steam Iron"]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_services, reverse_code=unseed_services),
    ]
