from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Order, OrderIssue, OrderItem, OrderStatusHistory, Service, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    fieldsets = BaseUserAdmin.fieldsets + (("Role", {"fields": ("role",)}),)
    add_fieldsets = BaseUserAdmin.add_fieldsets + (("Role", {"fields": ("role",)}),)
    list_display = ("email", "username", "role", "is_staff", "is_active")
    search_fields = ("email", "username")
    ordering = ("email",)


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("name", "price", "is_active")
    search_fields = ("name",)
    list_filter = ("is_active",)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "assigned_worker", "status", "payment_status", "total_price", "pickup_date", "created_at")
    search_fields = ("user__email", "user__username")
    list_filter = ("status", "created_at")
    inlines = [OrderItemInline]


@admin.register(OrderStatusHistory)
class OrderStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ("order", "previous_status", "new_status", "changed_by", "created_at")
    list_filter = ("new_status", "created_at")
    search_fields = ("order__id", "changed_by__email", "changed_by__username")


@admin.register(OrderIssue)
class OrderIssueAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "issue_type", "status", "reported_by", "resolved_by", "created_at")
    list_filter = ("issue_type", "status", "created_at")
    search_fields = ("order__id", "reported_by__email", "resolved_by__email")
