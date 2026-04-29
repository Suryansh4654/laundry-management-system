from decimal import Decimal

from django.db import migrations, models


def migrate_user_roles(apps, schema_editor):
    User = apps.get_model("core", "User")
    User.objects.filter(role="USER").update(role="CUSTOMER")
    Order = apps.get_model("core", "Order")
    Order.objects.filter(status="COMPLETED").update(status="READY_FOR_PICKUP")


def backfill_order_item_prices(apps, schema_editor):
    OrderItem = apps.get_model("core", "OrderItem")
    for item in OrderItem.objects.select_related("service").all():
        item.unit_price = item.service.price
        item.save(update_fields=["unit_price"])


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0003_alter_user_username"),
    ]

    operations = [
        migrations.RunPython(migrate_user_roles, migrations.RunPython.noop),
        migrations.AddField(
            model_name="order",
            name="admin_note",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="order",
            name="assigned_worker",
            field=models.ForeignKey(blank=True, null=True, on_delete=models.SET_NULL, related_name="assigned_orders", to="core.user"),
        ),
        migrations.AddField(
            model_name="order",
            name="delivered_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="order",
            name="drop_off_date",
            field=models.DateField(default="2026-04-29"),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="order",
            name="ready_for_pickup_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="orderitem",
            name="garment_type",
            field=models.CharField(default="Clothes", max_length=120),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="orderitem",
            name="unit_price",
            field=models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=10),
        ),
        migrations.AlterField(
            model_name="user",
            name="role",
            field=models.CharField(choices=[("CUSTOMER", "Customer"), ("WORKER", "Worker"), ("ADMIN", "Admin")], default="CUSTOMER", max_length=20),
        ),
        migrations.AlterField(
            model_name="order",
            name="status",
            field=models.CharField(
                choices=[
                    ("PENDING", "Pending"),
                    ("ACCEPTED", "Accepted"),
                    ("PROCESSING", "Processing"),
                    ("READY_FOR_PICKUP", "Ready for Pickup"),
                    ("DELIVERED", "Delivered"),
                    ("CANCELLED", "Cancelled"),
                ],
                default="PENDING",
                max_length=20,
            ),
        ),
        migrations.AlterUniqueTogether(
            name="orderitem",
            unique_together={("order", "service", "garment_type")},
        ),
        migrations.RunPython(backfill_order_item_prices, migrations.RunPython.noop),
    ]
