from django.urls import path

from .views import frontend_app

urlpatterns = [
    path("", frontend_app, name="frontend-app"),
]
