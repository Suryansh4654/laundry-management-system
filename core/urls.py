from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from .views import AdminOrderManageView, AnalyticsView, LoginView, OrderIssueViewSet, OrderViewSet, ProfileView, ServiceViewSet, SignupView, StaffUserListView, WorkerOrderStatusUpdateView, health_check

router = DefaultRouter()
router.register("services", ServiceViewSet, basename="service")
router.register("orders", OrderViewSet, basename="order")
router.register("issues", OrderIssueViewSet, basename="issue")

urlpatterns = [
    path("auth/signup/", SignupView.as_view(), name="signup"),
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/me/", ProfileView.as_view(), name="profile"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("admin/staff/", StaffUserListView.as_view(), name="staff-list"),
    path("worker/orders/<int:pk>/status/", WorkerOrderStatusUpdateView.as_view(), name="worker-order-status"),
    path("admin/orders/<int:pk>/manage/", AdminOrderManageView.as_view(), name="admin-order-manage"),
    path("admin/analytics/", AnalyticsView.as_view(), name="analytics"),
    path("health/", health_check, name="health-check"),
    path("", include(router.urls)),
]
