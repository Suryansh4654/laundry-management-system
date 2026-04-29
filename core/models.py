from decimal import Decimal

from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class UserRole(models.TextChoices):
    CUSTOMER = "CUSTOMER", _("Customer")
    WORKER = "WORKER", _("Worker")
    ADMIN = "ADMIN", _("Admin")


class User(AbstractUser):
    username = models.CharField(max_length=150)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=UserRole.choices, default=UserRole.CUSTOMER)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    def __str__(self) -> str:
        return f"{self.email} ({self.role})"


class Service(models.Model):
    name = models.CharField(max_length=120, unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))])
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name


class OrderStatus(models.TextChoices):
    PENDING = "PENDING", _("Pending")
    ACCEPTED = "ACCEPTED", _("Accepted")
    PROCESSING = "PROCESSING", _("Processing")
    COMPLETED = "COMPLETED", _("Completed")
    READY_FOR_DELIVERY = "READY_FOR_DELIVERY", _("Ready for Delivery")
    DELIVERED = "DELIVERED", _("Delivered")
    CANCELLED = "CANCELLED", _("Cancelled")


class PaymentStatus(models.TextChoices):
    UNPAID = "UNPAID", _("Unpaid")
    PAID = "PAID", _("Paid")
    REFUNDED = "REFUNDED", _("Refunded")


class PaymentMethod(models.TextChoices):
    CASH = "CASH", _("Cash")
    UPI = "UPI", _("UPI")
    CARD = "CARD", _("Card")
    BANK_TRANSFER = "BANK_TRANSFER", _("Bank Transfer")


class Order(models.Model):
    user = models.ForeignKey("User", on_delete=models.CASCADE, related_name="orders")
    assigned_worker = models.ForeignKey(
        "User",
        on_delete=models.SET_NULL,
        related_name="assigned_orders",
        null=True,
        blank=True,
    )
    status = models.CharField(max_length=20, choices=OrderStatus.choices, default=OrderStatus.PENDING)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    payment_status = models.CharField(max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.UNPAID)
    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices, blank=True)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    invoice_number = models.CharField(max_length=32, unique=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    drop_off_date = models.DateField()
    pickup_date = models.DateField()
    ready_for_pickup_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    admin_note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            self.invoice_number = f"INV-{timezone.now().strftime('%Y%m%d%H%M%S%f')}"
        super().save(*args, **kwargs)

    def recalculate_total(self) -> Decimal:
        total = sum(
            (item.quantity * item.unit_price for item in self.items.all()),
            start=Decimal("0.00"),
        )
        self.total_price = total
        self.save(update_fields=["total_price", "updated_at"])
        return total

    def __str__(self) -> str:
        return f"Order #{self.pk} - {self.user.email}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    service = models.ForeignKey(Service, on_delete=models.PROTECT, related_name="order_items")
    garment_type = models.CharField(max_length=120)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        unique_together = ("order", "service", "garment_type")

    def __str__(self) -> str:
        return f"{self.garment_type} - {self.service.name} x {self.quantity}"


class OrderStatusHistory(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="status_history")
    previous_status = models.CharField(max_length=20, choices=OrderStatus.choices, blank=True)
    new_status = models.CharField(max_length=20, choices=OrderStatus.choices)
    changed_by = models.ForeignKey("User", on_delete=models.SET_NULL, null=True, blank=True, related_name="order_status_updates")
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("created_at",)

    def __str__(self) -> str:
        return f"Order #{self.order_id}: {self.previous_status} -> {self.new_status}"


class IssueType(models.TextChoices):
    DAMAGED_ITEM = "DAMAGED_ITEM", _("Damaged Item")
    MISSING_ITEM = "MISSING_ITEM", _("Missing Item")
    WRONG_QUANTITY = "WRONG_QUANTITY", _("Wrong Quantity")
    BILLING_PROBLEM = "BILLING_PROBLEM", _("Billing Problem")
    OTHER = "OTHER", _("Other")


class IssueStatus(models.TextChoices):
    OPEN = "OPEN", _("Open")
    IN_REVIEW = "IN_REVIEW", _("In Review")
    RESOLVED = "RESOLVED", _("Resolved")
    DISMISSED = "DISMISSED", _("Dismissed")


class OrderIssue(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="issues")
    issue_type = models.CharField(max_length=30, choices=IssueType.choices)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=IssueStatus.choices, default=IssueStatus.OPEN)
    reported_by = models.ForeignKey("User", on_delete=models.SET_NULL, null=True, blank=True, related_name="reported_order_issues")
    resolution_note = models.TextField(blank=True)
    resolved_by = models.ForeignKey("User", on_delete=models.SET_NULL, null=True, blank=True, related_name="resolved_order_issues")
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"Issue #{self.pk} for Order #{self.order_id}"
