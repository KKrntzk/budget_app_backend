from django.urls import path, include
from .views import RegisterView, HouseholdViewSet
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'households', HouseholdViewSet, basename='household')

urlpatterns = [
    path('auth/register/', RegisterView.as_view(), name='auth_register'),
    path('', include(router.urls)),
]