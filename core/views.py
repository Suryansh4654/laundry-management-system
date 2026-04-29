from django.contrib.auth import get_user_model
from django.db.models import Count, Q, Sum
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from rest_framework.exceptions import ValidationError

from .models import IssueStatus, Order, OrderIssue, OrderStatus, PaymentStatus, Service, UserRole
from .permissions import IsAdminOrWorkerRole, IsAdminRole, IsOrderOwnerOrAdmin, IsWorkerRole
from .serializers import (
    AdminOrderManageSerializer,
    AnalyticsSerializer,
    CustomTokenObtainPairSerializer,
    OrderIssueAdminSerializer,
    OrderIssueSerializer,
    OrderSerializer,
    OrderStatusUpdateSerializer,
    ServiceSerializer,
    SignupSerializer,
    UserSerializer,
)

User = get_user_model()


class SignupView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = SignupSerializer
    permission_classes = [permissions.AllowAny]


class LoginView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    permission_classes = [permissions.AllowAny]


class ProfileView(generics.RetrieveAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class StaffUserListView(generics.ListAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAdminRole]

    def get_queryset(self):
        role = self.request.query_params.get("role")
        queryset = User.objects.filter(role__in=[UserRole.WORKER, UserRole.ADMIN]).order_by("username")
        if role:
            queryset = queryset.filter(role=role)
        return queryset


@extend_schema_view(
    list=extend_schema(summary="List services"),
    create=extend_schema(summary="Create service (admin only)"),
    retrieve=extend_schema(summary="Retrieve service"),
    update=extend_schema(summary="Update service (admin only)"),
    partial_update=extend_schema(summary="Partially update service (admin only)"),
    destroy=extend_schema(summary="Delete service (admin only)"),
)
class ServiceViewSet(viewsets.ModelViewSet):
    queryset = Service.objects.all()
    serializer_class = ServiceSerializer
    filterset_fields = ("is_active",)
    ordering_fields = ("name", "price", "created_at")

    def get_permissions(self):
        if self.action in {"list", "retrieve"}:
            permission_classes = [permissions.AllowAny]
        else:
            permission_classes = [IsAdminRole]
        return [permission() for permission in permission_classes]


@extend_schema_view(
    list=extend_schema(summary="List orders"),
    create=extend_schema(summary="Create order"),
    retrieve=extend_schema(summary="Retrieve order"),
    update=extend_schema(summary="Update order"),
    partial_update=extend_schema(summary="Partially update order"),
    destroy=extend_schema(summary="Delete order"),
)
class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    filterset_fields = ("status",)
    ordering_fields = ("created_at", "pickup_date", "drop_off_date", "total_price")

    def get_queryset(self):
        queryset = Order.objects.select_related("user", "assigned_worker").prefetch_related(
            "items__service", "status_history__changed_by", "issues__reported_by", "issues__resolved_by"
        )
        if self.request.user.role in {UserRole.ADMIN, UserRole.WORKER}:
            return queryset
        return queryset.filter(user=self.request.user)

    def get_permissions(self):
        if self.action in {"list", "retrieve"}:
            permission_classes = [permissions.IsAuthenticated]
        elif self.action == "create":
            permission_classes = [permissions.IsAuthenticated]
        else:
            permission_classes = [permissions.IsAuthenticated, IsOrderOwnerOrAdmin]
        return [permission() for permission in permission_classes]

    def perform_create(self, serializer):
        if self.request.user.role != UserRole.CUSTOMER:
            raise ValidationError({"role": "Only customers can create orders."})
        serializer.save()

    def perform_update(self, serializer):
        order = self.get_object()
        if self.request.user.role != UserRole.ADMIN and order.status != OrderStatus.PENDING:
            raise ValidationError({"status": "Only pending orders can be modified by users."})
        serializer.save()

    def perform_destroy(self, instance):
        if instance.status != OrderStatus.PENDING and self.request.user.role != UserRole.ADMIN:
            raise ValidationError({"status": "Only pending orders can be deleted by users."})
        instance.delete()


class WorkerOrderStatusUpdateView(generics.UpdateAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderStatusUpdateSerializer
    permission_classes = [IsWorkerRole]


class AdminOrderManageView(generics.UpdateAPIView):
    queryset = Order.objects.all()
    serializer_class = AdminOrderManageSerializer
    permission_classes = [IsAdminRole]


@extend_schema_view(
    list=extend_schema(summary="List order issues"),
    create=extend_schema(summary="Create order issue"),
    update=extend_schema(summary="Update order issue"),
    partial_update=extend_schema(summary="Partially update order issue"),
)
class OrderIssueViewSet(viewsets.ModelViewSet):
    queryset = OrderIssue.objects.select_related("order", "reported_by", "resolved_by", "order__user")
    http_method_names = ["get", "post", "patch", "put", "head", "options"]

    def get_serializer_class(self):
        if self.request.user.is_authenticated and self.request.user.role == UserRole.ADMIN:
            return OrderIssueAdminSerializer
        return OrderIssueSerializer

    def get_queryset(self):
        queryset = self.queryset
        user = self.request.user
        if user.role == UserRole.CUSTOMER:
            return queryset.filter(order__user=user)
        return queryset

    def get_permissions(self):
        if self.action in {"update", "partial_update"}:
            permission_classes = [IsAdminRole]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]


class AnalyticsView(APIView):
    permission_classes = [IsAdminOrWorkerRole]

    @extend_schema(responses=AnalyticsSerializer)
    def get(self, request, *args, **kwargs):
        counts = Order.objects.aggregate(
            total_orders=Count("id"),
            delivered_orders=Count("id", filter=Q(status=OrderStatus.DELIVERED)),
            pending_orders=Count("id", filter=Q(status=OrderStatus.PENDING)),
            ready_for_delivery_orders=Count("id", filter=Q(status=OrderStatus.READY_FOR_DELIVERY)),
            paid_orders=Count("id", filter=Q(payment_status=PaymentStatus.PAID)),
            total_revenue=Sum("amount_paid", filter=Q(payment_status=PaymentStatus.PAID)),
        )
        counts["open_issues"] = OrderIssue.objects.filter(status__in=[IssueStatus.OPEN, IssueStatus.IN_REVIEW]).count()
        counts["total_revenue"] = counts["total_revenue"] or 0
        serializer = AnalyticsSerializer(counts)
        return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def health_check(request):
    return Response({"status": "ok"}, status=status.HTTP_200_OK)
