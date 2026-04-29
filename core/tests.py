from datetime import timedelta

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from .models import IssueStatus, Order, OrderIssue, OrderStatus, PaymentStatus, Service, UserRole

User = get_user_model()


class AuthenticationTests(APITestCase):
    def test_user_can_signup_and_receive_account(self):
        payload = {
            "email": "user@example.com",
            "username": "laundryuser",
            "password": "StrongPass123!",
            "confirm_password": "StrongPass123!",
        }
        response = self.client.post(reverse("signup"), payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(User.objects.first().role, UserRole.CUSTOMER)

    def test_signup_allows_duplicate_username_but_not_duplicate_email(self):
        first_payload = {
            "email": "first@example.com",
            "username": "same-name",
            "password": "StrongPass123!",
            "confirm_password": "StrongPass123!",
        }
        second_payload = {
            "email": "second@example.com",
            "username": "same-name",
            "password": "StrongPass123!",
            "confirm_password": "StrongPass123!",
        }

        first_response = self.client.post(reverse("signup"), first_payload, format="json")
        second_response = self.client.post(reverse("signup"), second_payload, format="json")

        self.assertEqual(first_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.filter(username="same-name").count(), 2)

    def test_signup_creates_worker_when_role_selected(self):
        payload = {
            "email": "worker@example.com",
            "username": "team-member",
            "password": "StrongPass123!",
            "confirm_password": "StrongPass123!",
            "role": UserRole.WORKER,
        }
        response = self.client.post(reverse("signup"), payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.get(email="worker@example.com").role, UserRole.WORKER)


class OrderApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="customer@example.com",
            username="customer",
            password="StrongPass123!",
            role=UserRole.CUSTOMER,
        )
        self.worker = User.objects.create_user(
            email="worker@example.com",
            username="worker",
            password="StrongPass123!",
            role=UserRole.WORKER,
        )
        self.admin = User.objects.create_user(
            email="admin@example.com",
            username="admin",
            password="StrongPass123!",
            role=UserRole.ADMIN,
        )
        self.service, _ = Service.objects.get_or_create(
            name="Express Wash",
            defaults={"price": "50.00", "is_active": True},
        )

    def authenticate(self, email, password):
        user = User.objects.get(email=email)
        response = self.client.post(
            reverse("login"),
            {"email": email, "password": password, "role": user.role},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")

    def test_user_can_create_order(self):
        self.authenticate("customer@example.com", "StrongPass123!")
        payload = {
            "drop_off_date": str(timezone.localdate() + timedelta(days=1)),
            "pickup_date": str(timezone.localdate() + timedelta(days=1)),
            "account_password": "StrongPass123!",
            "items": [{"service_id": self.service.id, "garment_type": "T-Shirt", "quantity": 2}],
        }
        response = self.client.post(reverse("order-list"), payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(str(Order.objects.first().total_price), "100.00")

    def test_worker_can_deliver_order_with_customer_password(self):
        order = Order.objects.create(
            user=self.user,
            drop_off_date=timezone.localdate() + timedelta(days=1),
            pickup_date=timezone.localdate() + timedelta(days=1),
            status=OrderStatus.READY_FOR_DELIVERY,
        )
        self.authenticate("worker@example.com", "StrongPass123!")
        response = self.client.patch(
            reverse("worker-order-status", kwargs={"pk": order.id}),
            {"status": OrderStatus.DELIVERED, "verification_password": "StrongPass123!"},
            format="json",
        )

        order.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(order.status, OrderStatus.DELIVERED)

    def test_admin_can_assign_worker_and_mark_payment_paid(self):
        order = Order.objects.create(
            user=self.user,
            drop_off_date=timezone.localdate() + timedelta(days=1),
            pickup_date=timezone.localdate() + timedelta(days=1),
            total_price="150.00",
            status=OrderStatus.PENDING,
        )
        self.authenticate("admin@example.com", "StrongPass123!")
        response = self.client.patch(
            reverse("admin-order-manage", kwargs={"pk": order.id}),
            {
                "status": OrderStatus.ACCEPTED,
                "assigned_worker_id": self.worker.id,
                "payment_status": PaymentStatus.PAID,
                "payment_method": "UPI",
                "note": "Assigned and collected payment.",
            },
            format="json",
        )

        order.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(order.assigned_worker_id, self.worker.id)
        self.assertEqual(order.payment_status, PaymentStatus.PAID)
        self.assertEqual(str(order.amount_paid), "150.00")
        self.assertEqual(order.status_history.count(), 1)

    def test_customer_can_create_issue_and_admin_can_resolve_it(self):
        order = Order.objects.create(
            user=self.user,
            drop_off_date=timezone.localdate() + timedelta(days=1),
            pickup_date=timezone.localdate() + timedelta(days=1),
            status=OrderStatus.PROCESSING,
        )
        self.authenticate("customer@example.com", "StrongPass123!")
        create_response = self.client.post(
            reverse("issue-list"),
            {
                "order_id": order.id,
                "issue_type": "MISSING_ITEM",
                "description": "One shirt is missing.",
            },
            format="json",
        )
        issue_id = create_response.data["id"]

        self.authenticate("admin@example.com", "StrongPass123!")
        resolve_response = self.client.patch(
            reverse("issue-detail", kwargs={"pk": issue_id}),
            {
                "status": IssueStatus.RESOLVED,
                "resolution_note": "Recovered item and informed customer.",
            },
            format="json",
        )

        issue = OrderIssue.objects.get(pk=issue_id)
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resolve_response.status_code, status.HTTP_200_OK)
        self.assertEqual(issue.status, IssueStatus.RESOLVED)
