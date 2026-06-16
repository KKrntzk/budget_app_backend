from django.urls import path, include
from .views import RegisterView, HouseholdViewSet, CategoryViewSet, TransactionViewSet
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'households', HouseholdViewSet, basename='household')
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'transactions', TransactionViewSet, basename='transaction')

urlpatterns = [
    path('auth/register/', RegisterView.as_view(), name='auth_register'),
    path('', include(router.urls)),
]