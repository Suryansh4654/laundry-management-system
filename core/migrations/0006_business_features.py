from decimal import Decimal

from django.db import migrations, models
import django.db.models.deletion
from django.utils import timezone


def populate_invoice_numbers(apps, schema_editor):
    Order = apps.get_model("core", "Order")
    for order in Order.objects.all().order_by("id"):
        if not order.invoice_number:
            order.invoice_number = f"INV-{timezone.now().strftime('%Y%m%d')}-{order.id:05d}"
            order.save(update_fields=["invoice_number"])


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0005_update_status_flow"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="amount_paid",
            field=models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=10),
        ),
        migrations.AddField(
            model_name="order",
            name="invoice_number",
            field=models.CharField(blank=True, default="", max_length=32),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="order",
            name="paid_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="order",
            name="payment_method",
            field=models.CharField(blank=True, choices=[("CASH", "Cash"), ("UPI", "UPI"), ("CARD", "Card"), ("BANK_TRANSFER", "Bank Transfer")], max_length=20),
        ),
        migrations.AddField(
            model_name="order",
            name="payment_status",
            field=models.CharField(choices=[("UNPAID", "Unpaid"), ("PAID", "Paid"), ("REFUNDED", "Refunded")], default="UNPAID", max_length=20),
        ),
        migrations.CreateModel(
            name="OrderIssue",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("issue_type", models.CharField(choices=[("DAMAGED_ITEM", "Damaged Item"), ("MISSING_ITEM", "Missing Item"), ("WRONG_QUANTITY", "Wrong Quantity"), ("BILLING_PROBLEM", "Billing Problem"), ("OTHER", "Other")], max_length=30)),
                ("description", models.TextField()),
                ("status", models.CharField(choices=[("OPEN", "Open"), ("IN_REVIEW", "In Review"), ("RESOLVED", "Resolved"), ("DISMISSED", "Dismissed")], default="OPEN", max_length=20)),
                ("resolution_note", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("resolved_at", models.DateTimeField(blank=True, null=True)),
                ("order", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="issues", to="core.order")),
                ("reported_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="reported_order_issues", to="core.user")),
                ("resolved_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="resolved_order_issues", to="core.user")),
            ],
            options={"ordering": ("-created_at",)},
        ),
        migrations.CreateModel(
            name="OrderStatusHistory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("previous_status", models.CharField(blank=True, choices=[("PENDING", "Pending"), ("ACCEPTED", "Accepted"), ("PROCESSING", "Processing"), ("COMPLETED", "Completed"), ("READY_FOR_DELIVERY", "Ready for Delivery"), ("DELIVERED", "Delivered"), ("CANCELLED", "Cancelled")], max_length=20)),
                ("new_status", models.CharField(choices=[("PENDING", "Pending"), ("ACCEPTED", "Accepted"), ("PROCESSING", "Processing"), ("COMPLETED", "Completed"), ("READY_FOR_DELIVERY", "Ready for Delivery"), ("DELIVERED", "Delivered"), ("CANCELLED", "Cancelled")], max_length=20)),
                ("note", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("changed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="order_status_updates", to="core.user")),
                ("order", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="status_history", to="core.order")),
            ],
            options={"ordering": ("created_at",)},
        ),
        migrations.RunPython(populate_invoice_numbers, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="order",
            name="invoice_number",
            field=models.CharField(blank=True, max_length=32, unique=True),
        ),
    ]
