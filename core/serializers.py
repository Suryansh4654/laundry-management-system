from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import (
    IssueStatus,
    IssueType,
    Order,
    OrderIssue,
    OrderItem,
    OrderStatus,
    OrderStatusHistory,
    PaymentMethod,
    PaymentStatus,
    Service,
    UserRole,
)

User = get_user_model()


class SignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    confirm_password = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ("id", "email", "username", "password", "confirm_password", "role")
        read_only_fields = ("id",)
        extra_kwargs = {"role": {"required": False}}

    def validate_email(self, value):
        return value.strip().lower()

    def validate_role(self, value):
        request = self.context.get("request")
        if value == UserRole.ADMIN and (not request or not request.user.is_authenticated or request.user.role != UserRole.ADMIN):
            raise serializers.ValidationError("Only admins can create another admin account.")
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs.pop("confirm_password"):
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        return attrs

    def create(self, validated_data):
        role = validated_data.pop("role", UserRole.CUSTOMER)
        user = User.objects.create_user(role=role, **validated_data)
        return user


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = User.EMAIL_FIELD
    role = serializers.ChoiceField(choices=UserRole.choices, write_only=True)

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["email"] = user.email
        token["role"] = user.role
        return token

    def validate(self, attrs):
        requested_role = attrs.pop("role", None)
        data = super().validate(attrs)
        if requested_role and self.user.role != requested_role:
            raise serializers.ValidationError({"role": "Selected role does not match this account."})
        data["user"] = {
            "id": self.user.id,
            "email": self.user.email,
            "username": self.user.username,
            "role": self.user.role,
        }
        return data


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "email", "username", "role")


class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = ("id", "name", "price", "is_active", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")


class OrderItemWriteSerializer(serializers.Serializer):
    service_id = serializers.PrimaryKeyRelatedField(queryset=Service.objects.filter(is_active=True), source="service")
    garment_type = serializers.CharField(max_length=120)
    quantity = serializers.IntegerField(min_value=1)


class OrderItemReadSerializer(serializers.ModelSerializer):
    service = ServiceSerializer(read_only=True)
    line_total = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = ("id", "service", "garment_type", "quantity", "unit_price", "line_total")

    def get_line_total(self, obj):
        return obj.quantity * obj.unit_price


class OrderStatusHistorySerializer(serializers.ModelSerializer):
    changed_by = UserSerializer(read_only=True)

    class Meta:
        model = OrderStatusHistory
        fields = ("id", "previous_status", "new_status", "changed_by", "note", "created_at")


class OrderIssueSerializer(serializers.ModelSerializer):
    reported_by = UserSerializer(read_only=True)
    resolved_by = UserSerializer(read_only=True)
    order_id = serializers.PrimaryKeyRelatedField(source="order", queryset=Order.objects.all(), write_only=True)

    class Meta:
        model = OrderIssue
        fields = (
            "id",
            "order_id",
            "issue_type",
            "description",
            "status",
            "resolution_note",
            "reported_by",
            "resolved_by",
            "created_at",
            "resolved_at",
        )
        read_only_fields = ("id", "reported_by", "resolved_by", "created_at", "resolved_at")

    def validate_order(self, value):
        request = self.context["request"]
        if request.user.role == UserRole.CUSTOMER and value.user_id != request.user.id:
            raise serializers.ValidationError("Customers can only report issues for their own orders.")
        return value

    def create(self, validated_data):
        validated_data["reported_by"] = self.context["request"].user
        return super().create(validated_data)


class OrderIssueAdminSerializer(OrderIssueSerializer):
    status = serializers.ChoiceField(choices=IssueStatus.choices)

    class Meta(OrderIssueSerializer.Meta):
        read_only_fields = ("id", "reported_by", "created_at")

    def update(self, instance, validated_data):
        request = self.context["request"]
        new_status = validated_data.get("status", instance.status)
        instance.issue_type = validated_data.get("issue_type", instance.issue_type)
        instance.description = validated_data.get("description", instance.description)
        instance.status = new_status
        instance.resolution_note = validated_data.get("resolution_note", instance.resolution_note)
        if new_status in {IssueStatus.RESOLVED, IssueStatus.DISMISSED}:
            instance.resolved_by = request.user
            instance.resolved_at = timezone.now()
        instance.save()
        return instance


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemWriteSerializer(many=True, write_only=True)
    order_items = OrderItemReadSerializer(source="items", many=True, read_only=True)
    user = UserSerializer(read_only=True)
    status = serializers.ChoiceField(choices=OrderStatus.choices, read_only=True)
    account_password = serializers.CharField(write_only=True, required=True)
    assigned_worker = UserSerializer(read_only=True)
    status_history = OrderStatusHistorySerializer(many=True, read_only=True)
    issues = OrderIssueSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = (
            "id",
            "user",
            "assigned_worker",
            "status",
            "total_price",
            "payment_status",
            "payment_method",
            "amount_paid",
            "invoice_number",
            "paid_at",
            "drop_off_date",
            "pickup_date",
            "ready_for_pickup_at",
            "delivered_at",
            "admin_note",
            "created_at",
            "updated_at",
            "account_password",
            "items",
            "order_items",
            "status_history",
            "issues",
        )
        read_only_fields = (
            "id",
            "total_price",
            "payment_status",
            "payment_method",
            "amount_paid",
            "invoice_number",
            "paid_at",
            "ready_for_pickup_at",
            "delivered_at",
            "admin_note",
            "created_at",
            "updated_at",
        )

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("At least one order item is required.")

        unique_keys = [(item["service"].id, item["garment_type"].strip().lower()) for item in value]
        if len(unique_keys) != len(set(unique_keys)):
            raise serializers.ValidationError("Duplicate service and garment type combinations are not allowed.")
        return value

    def validate_drop_off_date(self, value):
        if value < timezone.localdate():
            raise serializers.ValidationError("Drop-off date cannot be in the past.")
        return value

    def validate(self, attrs):
        attrs = super().validate(attrs)
        drop_off_date = attrs.get("drop_off_date")
        pickup_date = attrs.get("pickup_date")
        if drop_off_date and pickup_date and pickup_date < drop_off_date:
            raise serializers.ValidationError({"pickup_date": "Pickup date must be on or after drop-off date."})

        request = self.context["request"]
        account_password = attrs.get("account_password")
        if account_password and not request.user.check_password(account_password):
            raise serializers.ValidationError({"account_password": "Password confirmation failed."})
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        validated_data.pop("account_password", None)
        items_data = validated_data.pop("items")
        order = Order.objects.create(user=self.context["request"].user, **validated_data)
        OrderItem.objects.bulk_create(
            [
                OrderItem(
                    order=order,
                    service=item["service"],
                    garment_type=item["garment_type"].strip(),
                    quantity=item["quantity"],
                    unit_price=item["service"].price,
                )
                for item in items_data
            ]
        )
        order.recalculate_total()
        OrderStatusHistory.objects.create(
            order=order,
            previous_status="",
            new_status=order.status,
            changed_by=self.context["request"].user,
            note="Order created by customer.",
        )
        return order

    @transaction.atomic
    def update(self, instance, validated_data):
        validated_data.pop("account_password", None)
        items_data = validated_data.pop("items", None)
        instance.drop_off_date = validated_data.get("drop_off_date", instance.drop_off_date)
        instance.pickup_date = validated_data.get("pickup_date", instance.pickup_date)
        instance.save(update_fields=["drop_off_date", "pickup_date", "updated_at"])

        if items_data is not None:
            instance.items.all().delete()
            OrderItem.objects.bulk_create(
                [
                    OrderItem(
                        order=instance,
                        service=item["service"],
                        garment_type=item["garment_type"].strip(),
                        quantity=item["quantity"],
                        unit_price=item["service"].price,
                    )
                    for item in items_data
                ]
            )
            instance.recalculate_total()

        return instance


class OrderStatusUpdateSerializer(serializers.ModelSerializer):
    verification_password = serializers.CharField(write_only=True, required=False, allow_blank=False)
    note = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = Order
        fields = ("status", "verification_password", "note")

    def validate(self, attrs):
        attrs = super().validate(attrs)
        order = self.instance
        next_status = attrs.get("status", order.status)

        transitions = {
            OrderStatus.PENDING: {OrderStatus.ACCEPTED, OrderStatus.CANCELLED},
            OrderStatus.ACCEPTED: {OrderStatus.PROCESSING, OrderStatus.CANCELLED},
            OrderStatus.PROCESSING: {OrderStatus.COMPLETED, OrderStatus.CANCELLED},
            OrderStatus.COMPLETED: {OrderStatus.READY_FOR_DELIVERY, OrderStatus.CANCELLED},
            OrderStatus.READY_FOR_DELIVERY: {OrderStatus.DELIVERED},
            OrderStatus.DELIVERED: set(),
            OrderStatus.CANCELLED: set(),
        }

        if next_status != order.status and next_status not in transitions.get(order.status, set()):
            raise serializers.ValidationError({"status": f"Invalid status transition from {order.status} to {next_status}."})

        if next_status == OrderStatus.DELIVERED and order.status != OrderStatus.DELIVERED:
            password = attrs.get("verification_password")
            if not password or not order.user.check_password(password):
                raise serializers.ValidationError({"verification_password": "Customer password verification failed."})
        return attrs

    def update(self, instance, validated_data):
        validated_data.pop("verification_password", None)
        note = validated_data.pop("note", "")
        new_status = validated_data.get("status", instance.status)
        previous_status = instance.status
        instance.status = new_status
        if new_status == OrderStatus.READY_FOR_DELIVERY:
            instance.ready_for_pickup_at = timezone.now()
        if new_status == OrderStatus.DELIVERED:
            instance.delivered_at = timezone.now()
        instance.save(update_fields=["status", "ready_for_pickup_at", "delivered_at", "updated_at"])
        OrderStatusHistory.objects.create(
            order=instance,
            previous_status=previous_status,
            new_status=new_status,
            changed_by=self.context["request"].user,
            note=note,
        )
        return instance


class AdminOrderManageSerializer(OrderStatusUpdateSerializer):
    admin_note = serializers.CharField(required=False, allow_blank=True)
    payment_status = serializers.ChoiceField(choices=PaymentStatus.choices, required=False)
    payment_method = serializers.ChoiceField(choices=PaymentMethod.choices, required=False, allow_blank=True)
    assigned_worker_id = serializers.PrimaryKeyRelatedField(
        source="assigned_worker",
        queryset=User.objects.filter(role=UserRole.WORKER),
        required=False,
        allow_null=True,
    )

    class Meta(OrderStatusUpdateSerializer.Meta):
        fields = (
            "status",
            "verification_password",
            "note",
            "admin_note",
            "payment_status",
            "payment_method",
            "assigned_worker_id",
        )

    def update(self, instance, validated_data):
        validated_data.pop("verification_password", None)
        note = validated_data.pop("note", "")
        new_status = validated_data.get("status", instance.status)
        previous_status = instance.status
        instance.status = new_status
        instance.admin_note = validated_data.get("admin_note", instance.admin_note)
        instance.assigned_worker = validated_data.get("assigned_worker", instance.assigned_worker)
        instance.payment_status = validated_data.get("payment_status", instance.payment_status)
        instance.payment_method = validated_data.get("payment_method", instance.payment_method)
        if instance.payment_status == PaymentStatus.PAID:
            instance.amount_paid = instance.total_price
            instance.paid_at = instance.paid_at or timezone.now()
        elif instance.payment_status == PaymentStatus.REFUNDED:
            instance.amount_paid = Decimal("0.00")
        if new_status == OrderStatus.READY_FOR_DELIVERY:
            instance.ready_for_pickup_at = timezone.now()
        if new_status == OrderStatus.DELIVERED:
            instance.delivered_at = timezone.now()
        instance.save(
            update_fields=[
                "status",
                "admin_note",
                "assigned_worker",
                "payment_status",
                "payment_method",
                "amount_paid",
                "paid_at",
                "ready_for_pickup_at",
                "delivered_at",
                "updated_at",
            ]
        )
        if previous_status != new_status or note:
            OrderStatusHistory.objects.create(
                order=instance,
                previous_status=previous_status,
                new_status=new_status,
                changed_by=self.context["request"].user,
                note=note or "Admin management update.",
            )
        return instance


class AnalyticsSerializer(serializers.Serializer):
    total_orders = serializers.IntegerField()
    delivered_orders = serializers.IntegerField()
    pending_orders = serializers.IntegerField()
    ready_for_delivery_orders = serializers.IntegerField()
    paid_orders = serializers.IntegerField()
    open_issues = serializers.IntegerField()
    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
