from django.db import migrations, models


def migrate_status_values(apps, schema_editor):
    Order = apps.get_model("core", "Order")
    Order.objects.filter(status="READY_FOR_PICKUP").update(status="READY_FOR_DELIVERY")


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0004_role_workflow_upgrade"),
    ]

    operations = [
        migrations.RunPython(migrate_status_values, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="order",
            name="status",
            field=models.CharField(
                choices=[
                    ("PENDING", "Pending"),
                    ("ACCEPTED", "Accepted"),
                    ("PROCESSING", "Processing"),
                    ("COMPLETED", "Completed"),
                    ("READY_FOR_DELIVERY", "Ready for Delivery"),
                    ("DELIVERED", "Delivered"),
                    ("CANCELLED", "Cancelled"),
                ],
                default="PENDING",
                max_length=20,
            ),
        ),
    ]
